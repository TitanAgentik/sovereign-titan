"""Sovereign Titan OS — Kamino Lend (KLend) & Marginfi 0-Fee Flash Loan CPI Builder (`src/execution/flash_loan_builder.py`).

Supports borrowing `100 SOL` (`100_000_000_000` lamports) to `5,000 SOL` (`5_000_000_000_000` lamports)
per atomic transaction via:
- Kamino Lend (`KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD`: `flash_borrow_reserve_liquidity` / `flash_repay_reserve_liquidity`)
- Marginfi (`MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA`)

Assembles the exact 7-instruction (or 8-instruction for 3-hop Agave 4.5) atomic sequence:
1. `SetComputeUnitLimit(exact_cu)`
2. `FlashBorrow(amount)`
3. `ProfitGuard::record_pre_balance`
4. `DEX_Leg_1`
5. `DEX_Leg_2`
   (Optional `DEX_Leg_3` when `MAX_VERSIONED_TX_ACCOUNTS == 96`)
6. `FlashRepay(amount + fee)`
7. `ProfitGuard::assert_min_profit_and_tip(min_profit, jito_tip)`
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import List, Literal, Optional

from solders.compute_budget import set_compute_unit_limit
from solders.instruction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import (
    KAMINO_LEND_PROGRAM_ID,
    KAMINO_RESERVE_ACCOUNTS,
    MARGINFI_RESERVE_ACCOUNTS,
    MARGINFI_V2_PROGRAM_ID,
    OFFICIAL_JITO_TIP_PDAS,
    PROFIT_GUARD_PROGRAM_ID,
    SPL_TOKEN_PROGRAM_ID,
    SYSTEM_PROGRAM_ID,
    SYSVAR_INSTRUCTIONS_PUBKEY,
    deterministic_pubkey,
)


FlashLoanProvider = Literal[
    "KAMINO",
    "MARGINFI",
    "SAVE_SOLEND",
    "SANCTUM_JUPITER",
    "MULTI_PROTOCOL_STACK",
]

REAL_KAMINO_KLEND_PROGRAM_ID = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
REAL_MARGINFI_V2_PROGRAM_ID = "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA"
REAL_SAVE_SOLEND_PROGRAM_ID = "So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo"
REAL_JUPITER_V6_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
REAL_RAYDIUM_V4_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
REAL_RAYDIUM_CLMM_PROGRAM_ID = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
REAL_ORCA_WHIRLPOOL_PROGRAM_ID = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
REAL_METEORA_DLMM_PROGRAM_ID = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
REAL_PHOENIX_CLOB_PROGRAM_ID = "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY"
REAL_LIFINITY_V2_PROGRAM_ID = "2wT8Yq49kHgDzXuPxZSaeLaH1qbmGXtEyPy64bL7aD3c"
REAL_PUMPSWAP_AMM_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
REAL_SANCTUM_S_CONTROLLER_PROGRAM_ID = "5ocnV1qiCgaQR8Jb8xWnVbApfaygJ8tNoZfgPwsgx9kx"

SAVE_SOLEND_RESERVE_ACCOUNTS = {
    "lending_market": str(deterministic_pubkey("save_solend:lending_market:main")),
    "lending_market_authority": str(deterministic_pubkey("save_solend:lending_market_authority:main")),
    "sol_reserve": str(deterministic_pubkey("save_solend:sol_reserve:main")),
    "sol_reserve_liquidity_supply": str(deterministic_pubkey("save_solend:sol_reserve_supply:main")),
    "fee_receiver": str(deterministic_pubkey("save_solend:sol_fee_receiver:main")),
}

SANCTUM_FLASH_SWAP_ACCOUNTS = {
    "pool_state": str(deterministic_pubkey("sanctum:s_controller:pool_state")),
    "pool_authority": str(deterministic_pubkey("sanctum:s_controller:authority")),
    "wsol_reserve_vault": str(deterministic_pubkey("sanctum:s_controller:wsol_vault")),
    "fee_vault": str(deterministic_pubkey("sanctum:s_controller:fee_vault")),
}

LAMPORTS_PER_SOL = 1_000_000_000
MIN_FLASH_LOAN_SOL = 100.0
MAX_FLASH_LOAN_SOL = 5_000.0
MAX_MEGA_FLASH_LOAN_SOL = 300_000.0
MIN_FLASH_LOAN_LAMPORTS = int(MIN_FLASH_LOAN_SOL * LAMPORTS_PER_SOL)
MAX_FLASH_LOAN_LAMPORTS = int(MAX_FLASH_LOAN_SOL * LAMPORTS_PER_SOL)
MAX_MEGA_FLASH_LOAN_LAMPORTS = int(MAX_MEGA_FLASH_LOAN_SOL * LAMPORTS_PER_SOL)


def derive_real_profit_guard_transient_pda(payer: Pubkey) -> Pubkey:
    """Derives the real Anchor `[b'profit_guard_state', payer.key().as_ref()]` PDA for `profit_guard`."""
    payer_pk = Pubkey.from_string(payer) if isinstance(payer, str) else payer
    return Pubkey.find_program_address(
        [b"profit_guard_state", bytes(payer_pk)],
        Pubkey.from_string(PROFIT_GUARD_PROGRAM_ID),
    )[0]


def anchor_ix_discriminator(ix_name: str) -> bytes:
    """Computes the canonical 8-byte Anchor instruction discriminator `sha256(f'global:{ix_name}')[:8]`."""
    return hashlib.sha256(f"global:{ix_name}".encode("utf-8")).digest()[:8]


@dataclass(frozen=True, init=False)
class DEXSwapLegSpec:
    """Specification for a single DEX swap leg inside an atomic flash-loan back-run."""

    program_id: Pubkey
    pool_state: Pubkey
    pool_Authority: Pubkey
    pool_authority: Pubkey
    vault_in: Pubkey
    vault_out: Pubkey
    user_source_token_account: Pubkey
    user_destination_token_account: Pubkey
    amount_in_lamports: int
    min_amount_out_lamports: int
    label: str = "DEX_Leg"

    def __init__(
        self,
        program_id: Pubkey,
        pool_state: Pubkey,
        pool_authority: Optional[Pubkey] = None,
        vault_in: Optional[Pubkey] = None,
        vault_out: Optional[Pubkey] = None,
        user_source_token_account: Optional[Pubkey] = None,
        user_destination_token_account: Optional[Pubkey] = None,
        amount_in_lamports: int = 0,
        min_amount_out_lamports: int = 0,
        label: str = "DEX_Leg",
        *,
        pool_Authority: Optional[Pubkey] = None,
    ) -> None:
        auth = pool_authority if pool_authority is not None else pool_Authority
        if (
            auth is None
            or vault_in is None
            or vault_out is None
            or user_source_token_account is None
            or user_destination_token_account is None
        ):
            raise TypeError("DEXSwapLegSpec missing required arguments")
        object.__setattr__(self, "program_id", program_id)
        object.__setattr__(self, "pool_state", pool_state)
        object.__setattr__(self, "pool_Authority", auth)
        object.__setattr__(self, "pool_authority", auth)
        object.__setattr__(self, "vault_in", vault_in)
        object.__setattr__(self, "vault_out", vault_out)
        object.__setattr__(self, "user_source_token_account", user_source_token_account)
        object.__setattr__(
            self, "user_destination_token_account", user_destination_token_account
        )
        object.__setattr__(self, "amount_in_lamports", amount_in_lamports)
        object.__setattr__(self, "min_amount_out_lamports", min_amount_out_lamports)
        object.__setattr__(self, "label", label)

    def to_instruction(self, payer: Pubkey) -> Instruction:
        """Builds a compact binary swap instruction for the DEX leg."""
        disc = anchor_ix_discriminator("swap_exact_in")
        data = disc + struct.pack("<QQ", self.amount_in_lamports, self.min_amount_out_lamports)
        accounts = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=self.pool_state, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.pool_authority, is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.vault_in, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.vault_out, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=self.user_source_token_account, is_signer=False, is_writable=True
            ),
            AccountMeta(
                pubkey=self.user_destination_token_account,
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=self.program_id, data=data, accounts=accounts)


@dataclass
class FlashLoanAtomicSequence:
    """Represents the assembled atomic instruction sequence and metadata."""

    provider: FlashLoanProvider
    borrow_lamports: int
    repay_lamports: int
    flash_fee_lamports: int
    min_net_profit_lamports: int
    jito_tip_lamports: int
    exact_compute_units: int
    hop_count: int
    instructions: List[Instruction]
    instruction_labels: List[str]


class FlashLoanBuilder:
    """Constructs Kamino Lend (`KLend`), Marginfi 0-Fee, Sanctum/Jupiter, and Save/Solend Flash Loan CPI sequences."""

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.settings = config or get_settings()

    @staticmethod
    def validate_borrow_amount_lamports(
        borrow_lamports: int,
        allow_mega_tier: bool = False,
    ) -> None:
        upper_bound = (
            MAX_MEGA_FLASH_LOAN_LAMPORTS if allow_mega_tier else MAX_FLASH_LOAN_LAMPORTS
        )
        max_sol_label = "300,000 SOL" if allow_mega_tier else "5,000 SOL"
        if not (MIN_FLASH_LOAN_LAMPORTS <= borrow_lamports <= upper_bound):
            sol_val = borrow_lamports / float(LAMPORTS_PER_SOL)
            raise ValueError(
                f"Flash loan amount must be between 100 SOL and {max_sol_label} (got {sol_val:.2f} SOL / {borrow_lamports} lamports)."
            )

    def build_kamino_flash_borrow_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        liquidity_amount_lamports: int,
        allow_mega_tier: bool = False,
    ) -> Instruction:
        """Builds Kamino Lend `flash_borrow_reserve_liquidity` instruction."""
        self.validate_borrow_amount_lamports(
            liquidity_amount_lamports, allow_mega_tier=allow_mega_tier
        )
        program_id = Pubkey.from_string(KAMINO_LEND_PROGRAM_ID)
        disc = anchor_ix_discriminator("flash_borrow_reserve_liquidity")
        data = disc + struct.pack("<Q", liquidity_amount_lamports)

        accounts = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["lending_market_authority"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["lending_market"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["sol_reserve"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(
                    KAMINO_RESERVE_ACCOUNTS["sol_reserve_liquidity_supply"]
                ),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["fee_receiver"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_kamino_flash_repay_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        repay_amount_lamports: int,
        borrow_instruction_index: int = 1,
    ) -> Instruction:
        """Builds Kamino Lend `flash_repay_reserve_liquidity` instruction."""
        program_id = Pubkey.from_string(KAMINO_LEND_PROGRAM_ID)
        disc = anchor_ix_discriminator("flash_repay_reserve_liquidity")
        data = disc + struct.pack("<QB", repay_amount_lamports, borrow_instruction_index)

        accounts = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["lending_market_authority"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["lending_market"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["sol_reserve"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(
                    KAMINO_RESERVE_ACCOUNTS["sol_reserve_liquidity_supply"]
                ),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(KAMINO_RESERVE_ACCOUNTS["fee_receiver"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_marginfi_flash_borrow_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        liquidity_amount_lamports: int,
        allow_mega_tier: bool = False,
    ) -> Instruction:
        """Builds Marginfi v2 0-fee flash borrow instruction."""
        self.validate_borrow_amount_lamports(
            liquidity_amount_lamports, allow_mega_tier=allow_mega_tier
        )
        program_id = Pubkey.from_string(MARGINFI_V2_PROGRAM_ID)
        disc = anchor_ix_discriminator("lending_account_start_flashloan")
        data = disc + struct.pack("<Q", liquidity_amount_lamports)
        accounts = [
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["marginfi_group"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["marginfi_account"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["sol_bank"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(
                    MARGINFI_RESERVE_ACCOUNTS["sol_liquidity_vault_authority"]
                ),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["sol_liquidity_vault"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_marginfi_flash_repay_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        repay_amount_lamports: int,
    ) -> Instruction:
        """Builds Marginfi v2 0-fee flash repay instruction."""
        program_id = Pubkey.from_string(MARGINFI_V2_PROGRAM_ID)
        disc = anchor_ix_discriminator("lending_account_end_flashloan")
        data = disc + struct.pack("<Q", repay_amount_lamports)
        accounts = [
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["marginfi_group"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["marginfi_account"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["sol_bank"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(MARGINFI_RESERVE_ACCOUNTS["sol_liquidity_vault"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_save_solend_flash_borrow_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        liquidity_amount_lamports: int,
        allow_mega_tier: bool = True,
    ) -> Instruction:
        """Builds Save (Solend) `flash_borrow_reserve_liquidity` instruction (`0.3 bps` fee)."""
        self.validate_borrow_amount_lamports(
            liquidity_amount_lamports, allow_mega_tier=allow_mega_tier
        )
        program_id = Pubkey.from_string(REAL_SAVE_SOLEND_PROGRAM_ID)
        disc = anchor_ix_discriminator("flash_borrow_reserve_liquidity")
        data = disc + struct.pack("<Q", liquidity_amount_lamports)
        accounts = [
            AccountMeta(
                pubkey=Pubkey.from_string(
                    SAVE_SOLEND_RESERVE_ACCOUNTS["sol_reserve_liquidity_supply"]
                ),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SAVE_SOLEND_RESERVE_ACCOUNTS["sol_reserve"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SAVE_SOLEND_RESERVE_ACCOUNTS["lending_market"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(
                    SAVE_SOLEND_RESERVE_ACCOUNTS["lending_market_authority"]
                ),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_save_solend_flash_repay_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        repay_amount_lamports: int,
        borrow_instruction_index: int = 1,
    ) -> Instruction:
        """Builds Save (Solend) `flash_repay_reserve_liquidity` instruction."""
        program_id = Pubkey.from_string(REAL_SAVE_SOLEND_PROGRAM_ID)
        disc = anchor_ix_discriminator("flash_repay_reserve_liquidity")
        data = disc + struct.pack("<QB", repay_amount_lamports, borrow_instruction_index)
        accounts = [
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(
                    SAVE_SOLEND_RESERVE_ACCOUNTS["sol_reserve_liquidity_supply"]
                ),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SAVE_SOLEND_RESERVE_ACCOUNTS["fee_receiver"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SAVE_SOLEND_RESERVE_ACCOUNTS["sol_reserve"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SAVE_SOLEND_RESERVE_ACCOUNTS["lending_market"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_sanctum_jupiter_flash_borrow_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        liquidity_amount_lamports: int,
        allow_mega_tier: bool = True,
    ) -> Instruction:
        """Builds Sanctum S-Controller / Jupiter LST flash-swap borrow instruction (`0.1 bps` fee)."""
        self.validate_borrow_amount_lamports(
            liquidity_amount_lamports, allow_mega_tier=allow_mega_tier
        )
        program_id = Pubkey.from_string(REAL_SANCTUM_S_CONTROLLER_PROGRAM_ID)
        disc = anchor_ix_discriminator("flash_swap_borrow")
        data = disc + struct.pack("<Q", liquidity_amount_lamports)
        accounts = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SANCTUM_FLASH_SWAP_ACCOUNTS["pool_state"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SANCTUM_FLASH_SWAP_ACCOUNTS["pool_authority"]),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SANCTUM_FLASH_SWAP_ACCOUNTS["wsol_reserve_vault"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_sanctum_jupiter_flash_repay_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        repay_amount_lamports: int,
    ) -> Instruction:
        """Builds Sanctum S-Controller / Jupiter LST flash-swap repay instruction."""
        program_id = Pubkey.from_string(REAL_SANCTUM_S_CONTROLLER_PROGRAM_ID)
        disc = anchor_ix_discriminator("flash_swap_repay")
        data = disc + struct.pack("<Q", repay_amount_lamports)
        accounts = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SANCTUM_FLASH_SWAP_ACCOUNTS["pool_state"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SANCTUM_FLASH_SWAP_ACCOUNTS["wsol_reserve_vault"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SANCTUM_FLASH_SWAP_ACCOUNTS["fee_vault"]),
                is_signer=False,
                is_writable=True,
            ),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSVAR_INSTRUCTIONS_PUBKEY),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_profit_guard_record_pre_balance_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        transient_state_pda: Pubkey,
        jito_tip_pda: Pubkey,
    ) -> Instruction:
        """Builds Instruction 1 of `profit_guard`: `record_pre_balance`."""
        program_id = Pubkey.from_string(PROFIT_GUARD_PROGRAM_ID)
        data = anchor_ix_discriminator("record_pre_balance")
        accounts = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=False),
            AccountMeta(pubkey=transient_state_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=jito_tip_pda, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSTEM_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def build_profit_guard_assert_min_profit_and_tip_ix(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        transient_state_pda: Pubkey,
        jito_tip_pda: Pubkey,
        min_net_profit_lamports: int,
        jito_tip_lamports: int,
    ) -> Instruction:
        """Builds Instruction 2 of `profit_guard`: `assert_min_profit_and_tip`."""
        program_id = Pubkey.from_string(PROFIT_GUARD_PROGRAM_ID)
        disc = anchor_ix_discriminator("assert_min_profit_and_tip")
        data = disc + struct.pack("<QQ", min_net_profit_lamports, jito_tip_lamports)
        accounts = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_wsol_ata, is_signer=False, is_writable=False),
            AccountMeta(pubkey=transient_state_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=jito_tip_pda, is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string(SYSTEM_PROGRAM_ID),
                is_signer=False,
                is_writable=False,
            ),
        ]
        return Instruction(program_id=program_id, data=data, accounts=accounts)

    def assemble_atomic_flash_arb_sequence(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        borrow_sol: float,
        dex_legs: List[DEXSwapLegSpec],
        min_net_profit_lamports: int,
        jito_tip_lamports: int,
        provider: FlashLoanProvider = "KAMINO",
        exact_compute_units: int = 380_000,
        flash_fee_lamports: int = 0,
        jito_tip_pda_index: int = 0,
        agave_45_enabled: bool = False,
        allow_mega_tier: bool = False,
    ) -> FlashLoanAtomicSequence:
        """Assembles the canonical 7-instruction (or 8-instruction for 3-hop) atomic sequence:
        [
          0: SetComputeUnitLimit(exact_cu),
          1: FlashBorrow(amount),
          2: ProfitGuard::record_pre_balance,
          3: DEX_Leg_1,
          4: DEX_Leg_2,
          (optional 5: DEX_Leg_3 when MAX_VERSIONED_TX_ACCOUNTS == 96 / agave_45_enabled),
          5/6: FlashRepay(amount + fee),
          6/7: ProfitGuard::assert_min_profit_and_tip(min_profit, jito_tip)
        ]
        """
        if not dex_legs:
            raise ValueError("swap_legs must be non-empty")
        if len(dex_legs) < 2 or len(dex_legs) > 3:
            raise ValueError(f"Expected 2 or 3 DEX swap legs, got {len(dex_legs)}.")

        effective_max_accounts = self.settings.effective_max_tx_accounts(
            agave_45_enabled=agave_45_enabled
        )
        if len(dex_legs) == 3 and effective_max_accounts < 96:
            raise ValueError(
                "3-hop triangular arbitrage (DEX_Leg_3) requires MAX_VERSIONED_TX_ACCOUNTS == 96 (Agave 4.5)."
            )

        is_mega = allow_mega_tier or provider == "MULTI_PROTOCOL_STACK"
        borrow_lamports = int(round(borrow_sol * LAMPORTS_PER_SOL))
        self.validate_borrow_amount_lamports(
            borrow_lamports, allow_mega_tier=is_mega
        )
        repay_lamports = borrow_lamports + flash_fee_lamports

        jito_tip_pda = Pubkey.from_string(
            OFFICIAL_JITO_TIP_PDAS[jito_tip_pda_index % len(OFFICIAL_JITO_TIP_PDAS)]
        )
        transient_state_pda = derive_real_profit_guard_transient_pda(payer)

        ix_cu = set_compute_unit_limit(exact_compute_units)

        if provider == "KAMINO":
            ix_borrow = self.build_kamino_flash_borrow_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                liquidity_amount_lamports=borrow_lamports,
                allow_mega_tier=is_mega,
            )
            ix_repay = self.build_kamino_flash_repay_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                repay_amount_lamports=repay_lamports,
                borrow_instruction_index=1,
            )
        elif provider == "SAVE_SOLEND":
            ix_borrow = self.build_save_solend_flash_borrow_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                liquidity_amount_lamports=borrow_lamports,
                allow_mega_tier=is_mega,
            )
            ix_repay = self.build_save_solend_flash_repay_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                repay_amount_lamports=repay_lamports,
                borrow_instruction_index=1,
            )
        elif provider == "SANCTUM_JUPITER":
            ix_borrow = self.build_sanctum_jupiter_flash_borrow_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                liquidity_amount_lamports=borrow_lamports,
                allow_mega_tier=is_mega,
            )
            ix_repay = self.build_sanctum_jupiter_flash_repay_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                repay_amount_lamports=repay_lamports,
            )
        else:
            ix_borrow = self.build_marginfi_flash_borrow_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                liquidity_amount_lamports=borrow_lamports,
                allow_mega_tier=is_mega,
            )
            ix_repay = self.build_marginfi_flash_repay_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                repay_amount_lamports=repay_lamports,
            )

        ix_record_pre = self.build_profit_guard_record_pre_balance_ix(
            payer=payer,
            user_wsol_ata=user_wsol_ata,
            transient_state_pda=transient_state_pda,
            jito_tip_pda=jito_tip_pda,
        )

        dex_instructions = [leg.to_instruction(payer) for leg in dex_legs]
        dex_labels = [f"DEX_Leg_{idx + 1}" for idx in range(len(dex_legs))]

        ix_assert_post = self.build_profit_guard_assert_min_profit_and_tip_ix(
            payer=payer,
            user_wsol_ata=user_wsol_ata,
            transient_state_pda=transient_state_pda,
            jito_tip_pda=jito_tip_pda,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
        )

        instructions = [
            ix_cu,
            ix_borrow,
            ix_record_pre,
            *dex_instructions,
            ix_repay,
            ix_assert_post,
        ]
        labels = [
            "SetComputeUnitLimit",
            "FlashBorrow",
            "ProfitGuard::record_pre_balance",
            *dex_labels,
            "FlashRepay",
            "ProfitGuard::assert_min_profit_and_tip",
        ]

        return FlashLoanAtomicSequence(
            provider=provider,
            borrow_lamports=borrow_lamports,
            repay_lamports=repay_lamports,
            flash_fee_lamports=flash_fee_lamports,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
            exact_compute_units=exact_compute_units,
            hop_count=len(dex_legs),
            instructions=instructions,
            instruction_labels=labels,
        )

    def assemble_multi_protocol_mega_flash_sequence(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        borrow_sol: float,
        dex_legs: List[DEXSwapLegSpec],
        min_net_profit_lamports: int,
        jito_tip_lamports: int,
        exact_compute_units: int = 1_150_000,
        jito_tip_pda_index: int = 0,
    ) -> FlashLoanAtomicSequence:
        """Assembles a multi-protocol stacked Mega Flash-Loan (`100 SOL` up to `300,000 SOL` / `$50M+`)
        atomic sequence in strict fee-ascending LIFO order:
        1. `MarginFi v2` (`0.0 bps`, up to `80,000 SOL`)
        2. `Kamino KLend` (`0.1 bps`, up to `120,000 SOL`)
        3. `Sanctum / Jupiter Flash Swap` (`0.1 bps`, up to `60,000 SOL`)
        4. `Save / Solend` (`0.3 bps`, up to `40,000 SOL`)
        """
        if not dex_legs:
            raise ValueError("dex_legs must be non-empty")

        borrow_lamports = int(round(borrow_sol * LAMPORTS_PER_SOL))
        self.validate_borrow_amount_lamports(borrow_lamports, allow_mega_tier=True)

        protocol_caps = [
            ("MARGINFI", 80_000 * LAMPORTS_PER_SOL, 0),
            ("KAMINO", 120_000 * LAMPORTS_PER_SOL, 1),
            ("SANCTUM_JUPITER", 60_000 * LAMPORTS_PER_SOL, 1),
            ("SAVE_SOLEND", 40_000 * LAMPORTS_PER_SOL, 3),
        ]

        remaining = borrow_lamports
        borrow_ixs: List[Instruction] = []
        borrow_labels: List[str] = []
        repay_builders = []
        total_fee_lamports = 0

        for proto_name, cap_lamports, fee_tenths_bps in protocol_caps:
            if remaining <= 0:
                break
            tranche_lamports = min(remaining, cap_lamports)
            fee_lamports = (tranche_lamports * fee_tenths_bps) // 100_000
            repay_tranche = tranche_lamports + fee_lamports
            total_fee_lamports += fee_lamports
            borrow_ix_idx = 1 + len(borrow_ixs)

            if proto_name == "MARGINFI":
                borrow_ixs.append(
                    self.build_marginfi_flash_borrow_ix(
                        payer=payer,
                        user_wsol_ata=user_wsol_ata,
                        liquidity_amount_lamports=tranche_lamports,
                        allow_mega_tier=True,
                    )
                )
                borrow_labels.append("FlashBorrow::MarginFiV2")
                repay_builders.append(
                    (
                        "FlashRepay::MarginFiV2",
                        self.build_marginfi_flash_repay_ix(
                            payer=payer,
                            user_wsol_ata=user_wsol_ata,
                            repay_amount_lamports=repay_tranche,
                        ),
                    )
                )
            elif proto_name == "KAMINO":
                borrow_ixs.append(
                    self.build_kamino_flash_borrow_ix(
                        payer=payer,
                        user_wsol_ata=user_wsol_ata,
                        liquidity_amount_lamports=tranche_lamports,
                        allow_mega_tier=True,
                    )
                )
                borrow_labels.append("FlashBorrow::KaminoKlend")
                repay_builders.append(
                    (
                        "FlashRepay::KaminoKlend",
                        self.build_kamino_flash_repay_ix(
                            payer=payer,
                            user_wsol_ata=user_wsol_ata,
                            repay_amount_lamports=repay_tranche,
                            borrow_instruction_index=borrow_ix_idx,
                        ),
                    )
                )
            elif proto_name == "SANCTUM_JUPITER":
                borrow_ixs.append(
                    self.build_sanctum_jupiter_flash_borrow_ix(
                        payer=payer,
                        user_wsol_ata=user_wsol_ata,
                        liquidity_amount_lamports=tranche_lamports,
                        allow_mega_tier=True,
                    )
                )
                borrow_labels.append("FlashBorrow::SanctumJupiter")
                repay_builders.append(
                    (
                        "FlashRepay::SanctumJupiter",
                        self.build_sanctum_jupiter_flash_repay_ix(
                            payer=payer,
                            user_wsol_ata=user_wsol_ata,
                            repay_amount_lamports=repay_tranche,
                        ),
                    )
                )
            else:
                borrow_ixs.append(
                    self.build_save_solend_flash_borrow_ix(
                        payer=payer,
                        user_wsol_ata=user_wsol_ata,
                        liquidity_amount_lamports=tranche_lamports,
                        allow_mega_tier=True,
                    )
                )
                borrow_labels.append("FlashBorrow::SaveSolend")
                repay_builders.append(
                    (
                        "FlashRepay::SaveSolend",
                        self.build_save_solend_flash_repay_ix(
                            payer=payer,
                            user_wsol_ata=user_wsol_ata,
                            repay_amount_lamports=repay_tranche,
                            borrow_instruction_index=borrow_ix_idx,
                        ),
                    )
                )

            remaining -= tranche_lamports

        repay_lamports = borrow_lamports + total_fee_lamports
        jito_tip_pda = Pubkey.from_string(
            OFFICIAL_JITO_TIP_PDAS[jito_tip_pda_index % len(OFFICIAL_JITO_TIP_PDAS)]
        )
        transient_state_pda = derive_real_profit_guard_transient_pda(payer)

        ix_cu = set_compute_unit_limit(exact_compute_units)
        ix_record_pre = self.build_profit_guard_record_pre_balance_ix(
            payer=payer,
            user_wsol_ata=user_wsol_ata,
            transient_state_pda=transient_state_pda,
            jito_tip_pda=jito_tip_pda,
        )
        dex_instructions = [leg.to_instruction(payer) for leg in dex_legs]
        dex_labels = [f"DEX_Leg_{idx + 1}" for idx in range(len(dex_legs))]

        # LIFO repay order
        repay_ixs = [ix for _, ix in reversed(repay_builders)]
        repay_labels = [lbl for lbl, _ in reversed(repay_builders)]

        ix_assert_post = self.build_profit_guard_assert_min_profit_and_tip_ix(
            payer=payer,
            user_wsol_ata=user_wsol_ata,
            transient_state_pda=transient_state_pda,
            jito_tip_pda=jito_tip_pda,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
        )

        instructions = [
            ix_cu,
            *borrow_ixs,
            ix_record_pre,
            *dex_instructions,
            *repay_ixs,
            ix_assert_post,
        ]
        labels = [
            "SetComputeUnitLimit",
            *borrow_labels,
            "ProfitGuard::record_pre_balance",
            *dex_labels,
            *repay_labels,
            "ProfitGuard::assert_min_profit_and_tip",
        ]

        return FlashLoanAtomicSequence(
            provider="MULTI_PROTOCOL_STACK",
            borrow_lamports=borrow_lamports,
            repay_lamports=repay_lamports,
            flash_fee_lamports=total_fee_lamports,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
            exact_compute_units=exact_compute_units,
            hop_count=len(dex_legs),
            instructions=instructions,
            instruction_labels=labels,
        )

    def assemble_zero_rent_native_flash_arb_sequence(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        borrow_sol: float,
        dex_legs: Optional[List[DEXSwapLegSpec]] = None,
        min_net_profit_lamports: int = 10_000,
        jito_tip_lamports: int = 10_000,
        provider: FlashLoanProvider = "KAMINO",
        exact_compute_units: int = 380_000,
        flash_fee_lamports: int = 0,
        jito_tip_pda_index: int = 0,
        agave_45_enabled: bool = False,
        *,
        swap_legs: Optional[List[DEXSwapLegSpec]] = None,
    ) -> FlashLoanAtomicSequence:
        """Assembles a zero-rent native flash-loan sequence without requiring `profit_guard`
        to be deployed on Mainnet (saving `1.85 SOL` deployment rent).
        Sets `min_amount_out_lamports = borrow_lamports + flash_fee_lamports + min_net_profit_lamports + jito_tip_lamports`
        directly on the final `DEXSwapLegSpec` and appends a native `SystemProgram::Transfer`
        for `jito_tip_lamports` to `jito_tip_pda`, guaranteeing atomic transaction revert on
        the final DEX leg itself if net profit is not met.
        """
        legs = dex_legs if dex_legs is not None else swap_legs
        if not legs:
            raise ValueError("swap_legs must be non-empty")
        if len(legs) < 2 or len(legs) > 3:
            raise ValueError(f"Expected 2 or 3 DEX swap legs, got {len(legs)}.")

        effective_max_accounts = self.settings.effective_max_tx_accounts(
            agave_45_enabled=agave_45_enabled
        )
        if len(legs) == 3 and effective_max_accounts < 96:
            raise ValueError(
                "3-hop triangular arbitrage (DEX_Leg_3) requires MAX_VERSIONED_TX_ACCOUNTS == 96 (Agave 4.5)."
            )

        borrow_lamports = int(round(borrow_sol * LAMPORTS_PER_SOL))
        self.validate_borrow_amount_lamports(borrow_lamports)
        repay_lamports = borrow_lamports + flash_fee_lamports
        required_final_min_out = (
            borrow_lamports
            + flash_fee_lamports
            + min_net_profit_lamports
            + jito_tip_lamports
        )

        # Enforce atomic profit floor directly on the final DEXSwapLegSpec
        final_leg = legs[-1]
        object.__setattr__(final_leg, "min_amount_out_lamports", required_final_min_out)

        jito_tip_pda = Pubkey.from_string(
            OFFICIAL_JITO_TIP_PDAS[jito_tip_pda_index % len(OFFICIAL_JITO_TIP_PDAS)]
        )

        ix_cu = set_compute_unit_limit(exact_compute_units)

        if provider == "KAMINO":
            ix_borrow = self.build_kamino_flash_borrow_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                liquidity_amount_lamports=borrow_lamports,
            )
            ix_repay = self.build_kamino_flash_repay_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                repay_amount_lamports=repay_lamports,
                borrow_instruction_index=1,
            )
        else:
            ix_borrow = self.build_marginfi_flash_borrow_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                liquidity_amount_lamports=borrow_lamports,
            )
            ix_repay = self.build_marginfi_flash_repay_ix(
                payer=payer,
                user_wsol_ata=user_wsol_ata,
                repay_amount_lamports=repay_lamports,
            )

        dex_instructions = [leg.to_instruction(payer) for leg in legs]
        dex_labels = [f"DEX_Leg_{idx + 1}" for idx in range(len(legs))]

        ix_jito_tip = transfer(
            TransferParams(
                from_pubkey=payer,
                to_pubkey=jito_tip_pda,
                lamports=jito_tip_lamports,
            )
        )

        instructions = [
            ix_cu,
            ix_borrow,
            *dex_instructions,
            ix_repay,
            ix_jito_tip,
        ]
        labels = [
            "SetComputeUnitLimit",
            "FlashBorrow",
            *dex_labels,
            "FlashRepay",
            "SystemProgram::Transfer(JitoTip)",
        ]

        return FlashLoanAtomicSequence(
            provider=provider,
            borrow_lamports=borrow_lamports,
            repay_lamports=repay_lamports,
            flash_fee_lamports=flash_fee_lamports,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
            exact_compute_units=exact_compute_units,
            hop_count=len(legs),
            instructions=instructions,
            instruction_labels=labels,
        )

    def build_atomic_flash_arb_instructions(
        self,
        payer: Pubkey,
        user_wsol_ata: Pubkey,
        borrow_sol: float,
        swap_legs: List[DEXSwapLegSpec],
        min_net_profit_lamports: int = 10_000,
        jito_tip_lamports: int = 10_000,
        provider: FlashLoanProvider = "KAMINO",
        exact_compute_units: int = 380_000,
        flash_fee_lamports: int = 0,
        jito_tip_pda_index: int = 0,
        agave_45_enabled: bool = False,
    ) -> List[Instruction]:
        """Builds the atomic flash-loan arbitrage instruction list, raising ValueError if `swap_legs` is empty."""
        if not swap_legs:
            raise ValueError("swap_legs must be non-empty")
        seq = self.assemble_atomic_flash_arb_sequence(
            payer=payer,
            user_wsol_ata=user_wsol_ata,
            borrow_sol=borrow_sol,
            dex_legs=swap_legs,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
            provider=provider,
            exact_compute_units=exact_compute_units,
            flash_fee_lamports=flash_fee_lamports,
            jito_tip_pda_index=jito_tip_pda_index,
            agave_45_enabled=agave_45_enabled,
        )
        return seq.instructions



