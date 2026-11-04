"""Sovereign Titan OS — Agave 4.5 V0 Transaction Builder, `jitodontfront` & Auto ATA Rent Reclaim (`src/execution/atomic_tx_builder.py`).

Implements:
- Compressed `VersionedTransaction (V0)` construction using pre-warmed Address Lookup Tables (ALTs)
  from `ALTManager` so every multi-hop transaction serializes to `< 1,150 bytes` (under the
  1,232-byte Solana MTU limit).
- Supports both 2-hop cross-DEX arbs (`MAX_VERSIONED_TX_ACCOUNTS = 64`) and 3-hop triangular
  arbs (`SOL -> Pool A -> Pool B -> Pool C -> SOL` under Agave 4.5's `96`-account limit).
- Mandatory Directional Guards (/AGENTS.md):
  1. Injects read-only, non-signer `jitodontfront111111111111111111111111111111` pubkey into
     Instruction 0 of every directional buy (`Shadow Executor` and `Engine B` front-legs).
  2. Appends `spl_token::instruction::close_account` (instruction tag `9`) on every 100% token
     exit transaction to reclaim `0.00203928 SOL` (`2,039,280 lamports`) ATA rent immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import (
    ALTManager,
    SPL_ASSOCIATED_TOKEN_PROGRAM_ID,
    SPL_TOKEN_PROGRAM_ID,
)
from src.execution.flash_loan_builder import (
    DEXSwapLegSpec,
    FlashLoanAtomicSequence,
    FlashLoanBuilder,
    FlashLoanProvider,
)


JITO_DONT_FRONT_PUBKEY_STR = "jitodontfront111111111111111111111111111111"
JITO_DONT_FRONT_PUBKEY = Pubkey.from_string(JITO_DONT_FRONT_PUBKEY_STR)
CLOSE_ACCOUNT_IX_TAG = 9  # spl_token::instruction::TokenInstruction::CloseAccount
ATA_RENT_LAMPORTS = 2_039_280  # 0.00203928 SOL


def derive_associated_token_address(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """Derives the canonical Associated Token Account (ATA) PDA for `(owner, SPL_TOKEN_PROGRAM_ID, mint)`."""
    ata_program = Pubkey.from_string(SPL_ASSOCIATED_TOKEN_PROGRAM_ID)
    token_program = Pubkey.from_string(SPL_TOKEN_PROGRAM_ID)
    pda, _bump = Pubkey.find_program_address(
        [bytes(owner), bytes(token_program), bytes(mint)],
        ata_program,
    )
    return pda


def build_close_ata_instruction(
    token_ata: Pubkey,
    destination_sol_wallet: Pubkey,
    owner_authority: Pubkey,
) -> Instruction:
    """Builds `spl_token::instruction::close_account` (instruction tag 9) to reclaim 0.00203928 SOL ATA rent."""
    token_program = Pubkey.from_string(SPL_TOKEN_PROGRAM_ID)
    accounts = [
        AccountMeta(pubkey=token_ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=destination_sol_wallet, is_signer=False, is_writable=True),
        AccountMeta(pubkey=owner_authority, is_signer=True, is_writable=False),
    ]
    return Instruction(
        program_id=token_program,
        data=bytes([CLOSE_ACCOUNT_IX_TAG]),
        accounts=accounts,
    )


def inject_jito_dont_front_into_ix0(ix0: Instruction) -> Instruction:
    """Injects read-only, non-signer `jitodontfront111111111111111111111111111111` into Instruction 0."""
    existing_accounts = list(ix0.accounts)
    if not any(meta.pubkey == JITO_DONT_FRONT_PUBKEY for meta in existing_accounts):
        existing_accounts.append(
            AccountMeta(
                pubkey=JITO_DONT_FRONT_PUBKEY,
                is_signer=False,
                is_writable=False,
            )
        )
    return Instruction(
        program_id=ix0.program_id,
        data=ix0.data,
        accounts=existing_accounts,
    )


@dataclass
class AtomicTxBuildResult:
    """Compiled VersionedTransaction (V0) along with byte size and account compression telemetry."""

    transaction: VersionedTransaction
    raw_bytes: bytes
    serialized_size_bytes: int
    total_unique_accounts: int
    max_allowed_accounts: int
    alt_lookup_count: int
    instruction_count: int
    has_jito_dont_front_in_ix0: bool
    has_close_account_rent_reclaim: bool
    reclaimed_rent_lamports: int = 0


@dataclass
class MegaFlashSuperBundleResult:
    """Compiled 1-to-5 V0 Transaction Jito Super-Bundle for `$100K`–`$50M+` (`1,000`–`300,000 SOL`) Mega Flash Arbitrage."""

    sequence: FlashLoanAtomicSequence
    tx_results: List[AtomicTxBuildResult]
    bundle_tx_count: int
    total_borrow_lamports: int
    total_flash_fee_lamports: int
    min_net_profit_lamports: int
    jito_tip_lamports: int
    max_tx_serialized_bytes: int
    has_jito_dont_front_in_tx0: bool


class AtomicV0TransactionBuilder:
    """Agave 4.5 VersionedTransaction (V0) Builder with ALT compression, `jitodontfront`, and ATA rent reclaim."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        alt_manager: Optional[ALTManager] = None,
        flash_builder: Optional[FlashLoanBuilder] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.alt_manager = alt_manager or ALTManager(self.settings)
        self.flash_builder = flash_builder or FlashLoanBuilder(self.settings)

    def _compile_v0_transaction(
        self,
        payer_keypair: Keypair,
        instructions: List[Instruction],
        recent_blockhash: Optional[Hash] = None,
        agave_45_enabled: bool = False,
        auto_register_in_warm_alt: bool = True,
    ) -> AtomicTxBuildResult:
        if not instructions:
            raise ValueError("Cannot compile V0 transaction with 0 instructions.")

        blockhash = recent_blockhash or Hash.default()
        payer_pk = payer_keypair.pubkey()

        # Collect all unique accounts referenced across instructions
        unique_pubkeys = {payer_pk}
        non_signer_pubkeys: List[str] = []
        for ix in instructions:
            unique_pubkeys.add(ix.program_id)
            for meta in ix.accounts:
                unique_pubkeys.add(meta.pubkey)
                if not meta.is_signer and meta.pubkey != payer_pk:
                    non_signer_pubkeys.append(str(meta.pubkey))

        max_allowed = self.settings.effective_max_tx_accounts(
            agave_45_enabled=agave_45_enabled
        )
        if len(unique_pubkeys) > max_allowed:
            raise ValueError(
                f"Transaction references {len(unique_pubkeys)} unique accounts, exceeding limit of {max_allowed}."
            )

        if auto_register_in_warm_alt:
            self.alt_manager.register_custom_addresses(non_signer_pubkeys)

        alt_accounts = self.alt_manager.get_lookup_table_accounts()

        msg_v0 = MessageV0.try_compile(
            payer=payer_pk,
            instructions=instructions,
            address_lookup_table_accounts=alt_accounts,
            recent_blockhash=blockhash,
        )
        tx = VersionedTransaction(msg_v0, [payer_keypair])
        raw_bytes = bytes(tx)
        size_bytes = len(raw_bytes)

        if size_bytes >= self.settings.MAX_TX_SIZE_BYTES:
            raise ValueError(
                f"Compiled V0 transaction is {size_bytes} bytes, exceeding MAX_TX_SIZE_BYTES={self.settings.MAX_TX_SIZE_BYTES} (MTU={self.settings.SOLANA_MTU_LIMIT_BYTES})."
            )

        alt_lookup_count = sum(
            len(lookup.writable_indexes) + len(lookup.readonly_indexes)
            for lookup in msg_v0.address_table_lookups
        )

        ix0_has_dont_front = any(
            meta.pubkey == JITO_DONT_FRONT_PUBKEY
            and not meta.is_signer
            and not meta.is_writable
            for meta in instructions[0].accounts
        )
        last_ix = instructions[-1]
        has_close_account = (
            last_ix.program_id == Pubkey.from_string(SPL_TOKEN_PROGRAM_ID)
            and len(last_ix.data) == 1
            and last_ix.data[0] == CLOSE_ACCOUNT_IX_TAG
        )

        return AtomicTxBuildResult(
            transaction=tx,
            raw_bytes=raw_bytes,
            serialized_size_bytes=size_bytes,
            total_unique_accounts=len(unique_pubkeys),
            max_allowed_accounts=max_allowed,
            alt_lookup_count=alt_lookup_count,
            instruction_count=len(instructions),
            has_jito_dont_front_in_ix0=ix0_has_dont_front,
            has_close_account_rent_reclaim=has_close_account,
            reclaimed_rent_lamports=ATA_RENT_LAMPORTS if has_close_account else 0,
        )

    def build_flash_loan_arb_v0(
        self,
        payer_keypair: Keypair,
        user_wsol_ata: Pubkey,
        borrow_sol: float,
        dex_legs: List[DEXSwapLegSpec],
        min_net_profit_lamports: int,
        jito_tip_lamports: int,
        provider: FlashLoanProvider = "KAMINO",
        exact_compute_units: int = 380_000,
        recent_blockhash: Optional[Hash] = None,
        agave_45_enabled: bool = False,
    ) -> tuple[FlashLoanAtomicSequence, AtomicTxBuildResult]:
        """Builds a compressed V0 transaction for a 2-hop (64-account) or 3-hop (96-account Agave 4.5)
        Kamino/Marginfi Flash-Loan + ProfitGuard atomic arbitrage.
        """
        sequence = self.flash_builder.assemble_atomic_flash_arb_sequence(
            payer=payer_keypair.pubkey(),
            user_wsol_ata=user_wsol_ata,
            borrow_sol=borrow_sol,
            dex_legs=dex_legs,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
            provider=provider,
            exact_compute_units=exact_compute_units,
            agave_45_enabled=agave_45_enabled,
        )
        tx_result = self._compile_v0_transaction(
            payer_keypair=payer_keypair,
            instructions=sequence.instructions,
            recent_blockhash=recent_blockhash,
            agave_45_enabled=agave_45_enabled,
        )
        return sequence, tx_result

    def build_mega_flash_loan_arb_v0_or_bundle(
        self,
        payer_keypair: Keypair,
        user_wsol_ata: Pubkey,
        borrow_sol: float,
        dex_legs: List[DEXSwapLegSpec],
        min_net_profit_lamports: int,
        jito_tip_lamports: int,
        exact_compute_units: int = 1_150_000,
        recent_blockhash: Optional[Hash] = None,
    ) -> MegaFlashSuperBundleResult:
        """Builds an institutional `$100K`–`$50M+` (`100 SOL` to `300,000 SOL`) Multi-Protocol
        Mega Flash-Loan arbitrage as either a single Agave 4.5 V0 transaction (when `<= 3` legs
        fit within a single V0 packet) or a 1-to-5 V0 Transaction Jito Super-Bundle where every
        packet is `< 1,150 bytes` and `Tx[0]` locks `jitodontfront` in Instruction 0.
        """
        sequence = self.flash_builder.assemble_multi_protocol_mega_flash_sequence(
            payer=payer_keypair.pubkey(),
            user_wsol_ata=user_wsol_ata,
            borrow_sol=borrow_sol,
            dex_legs=dex_legs,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
            exact_compute_units=exact_compute_units,
        )

        all_ixs = list(sequence.instructions)
        all_ixs[0] = inject_jito_dont_front_into_ix0(all_ixs[0])

        # Attempt single-V0 compilation first when instruction count is compact
        if len(dex_legs) <= 3 and borrow_sol <= 80_000.0:
            try:
                single_tx = self._compile_v0_transaction(
                    payer_keypair=payer_keypair,
                    instructions=all_ixs,
                    recent_blockhash=recent_blockhash,
                    agave_45_enabled=True,
                )
                return MegaFlashSuperBundleResult(
                    sequence=sequence,
                    tx_results=[single_tx],
                    bundle_tx_count=1,
                    total_borrow_lamports=sequence.borrow_lamports,
                    total_flash_fee_lamports=sequence.flash_fee_lamports,
                    min_net_profit_lamports=min_net_profit_lamports,
                    jito_tip_lamports=jito_tip_lamports,
                    max_tx_serialized_bytes=single_tx.serialized_size_bytes,
                    has_jito_dont_front_in_tx0=single_tx.has_jito_dont_front_in_ix0,
                )
            except ValueError:
                pass

        # Partition across up to 5 atomic Jito bundle V0 transactions (< 1,150 bytes each)
        borrow_ixs = [
            ix
            for ix, lbl in zip(sequence.instructions, sequence.instruction_labels)
            if lbl.startswith("FlashBorrow") or lbl == "ProfitGuard::record_pre_balance"
        ]
        swap_ixs = [
            ix
            for ix, lbl in zip(sequence.instructions, sequence.instruction_labels)
            if lbl.startswith("DEX_Leg_")
        ]
        repay_and_guard_ixs = [
            ix
            for ix, lbl in zip(sequence.instructions, sequence.instruction_labels)
            if lbl.startswith("FlashRepay")
            or lbl == "ProfitGuard::assert_min_profit_and_tip"
        ]

        tx_instruction_groups: List[List[Instruction]] = []
        # Tx 0: jitodontfront + ComputeBudget + FlashBorrows + ProfitGuard::record_pre_balance
        tx0_cu = inject_jito_dont_front_into_ix0(set_compute_unit_limit(450_000))
        tx_instruction_groups.append([tx0_cu, *borrow_ixs])

        # Partition swap_ixs into chunks of at most 3 DEX legs per V0 transaction (up to 3 middle txs)
        chunk_size = 3
        for idx in range(0, len(swap_ixs), chunk_size):
            chunk = swap_ixs[idx : idx + chunk_size]
            tx_instruction_groups.append([set_compute_unit_limit(600_000), *chunk])

        # Final Tx: LIFO FlashRepays + ProfitGuard::assert_min_profit_and_tip
        tx_instruction_groups.append(
            [set_compute_unit_limit(450_000), *repay_and_guard_ixs]
        )

        # Ensure bundle never exceeds Jito's 5-Tx atomic limit
        while len(tx_instruction_groups) > 5:
            merged = tx_instruction_groups[-2] + tx_instruction_groups[-1][1:]
            tx_instruction_groups[-2] = merged
            tx_instruction_groups.pop()

        tx_results: List[AtomicTxBuildResult] = []
        for grp in tx_instruction_groups:
            compiled = self._compile_v0_transaction(
                payer_keypair=payer_keypair,
                instructions=grp,
                recent_blockhash=recent_blockhash,
                agave_45_enabled=True,
            )
            tx_results.append(compiled)

        return MegaFlashSuperBundleResult(
            sequence=sequence,
            tx_results=tx_results,
            bundle_tx_count=len(tx_results),
            total_borrow_lamports=sequence.borrow_lamports,
            total_flash_fee_lamports=sequence.flash_fee_lamports,
            min_net_profit_lamports=min_net_profit_lamports,
            jito_tip_lamports=jito_tip_lamports,
            max_tx_serialized_bytes=max(r.serialized_size_bytes for r in tx_results),
            has_jito_dont_front_in_tx0=tx_results[0].has_jito_dont_front_in_ix0,
        )

    def build_directional_buy_v0(
        self,
        payer_keypair: Keypair,
        swap_leg: DEXSwapLegSpec,
        compute_units: int = 180_000,
        priority_micro_lamports: int = 50_000,
        recent_blockhash: Optional[Hash] = None,
    ) -> AtomicTxBuildResult:
        """Builds a directional buy V0 transaction (`Shadow Executor` / `Engine B` front-leg)
        with `jitodontfront111111111111111111111111111111` injected as read-only non-signer in Instruction 0.
        """
        ix0 = inject_jito_dont_front_into_ix0(set_compute_unit_limit(compute_units))
        ix1 = set_compute_unit_price(priority_micro_lamports)
        ix_swap = swap_leg.to_instruction(payer_keypair.pubkey())

        return self._compile_v0_transaction(
            payer_keypair=payer_keypair,
            instructions=[ix0, ix1, ix_swap],
            recent_blockhash=recent_blockhash,
        )

    def build_partial_token_sell_v0(
        self,
        payer_keypair: Keypair,
        swap_leg: DEXSwapLegSpec,
        compute_units: int = 150_000,
        priority_micro_lamports: int = 65_000,
        recent_blockhash: Optional[Hash] = None,
    ) -> AtomicTxBuildResult:
        """Builds a partial scale-out sell V0 transaction (`Token ATA -> wSOL ATA`)
        WITHOUT injecting `jitodontfront` (which is for front-running protection on entries)
        and WITHOUT closing the token ATA (since remaining tokens are still held in the ATA).
        """
        ix0 = set_compute_unit_limit(compute_units)
        ix1 = set_compute_unit_price(priority_micro_lamports)
        ix_swap = swap_leg.to_instruction(payer_keypair.pubkey())

        return self._compile_v0_transaction(
            payer_keypair=payer_keypair,
            instructions=[ix0, ix1, ix_swap],
            recent_blockhash=recent_blockhash,
        )

    def build_full_token_exit_v0(
        self,
        payer_keypair: Keypair,
        swap_leg: DEXSwapLegSpec,
        token_ata_to_close: Pubkey,
        compute_units: int = 180_000,
        priority_micro_lamports: int = 50_000,
        recent_blockhash: Optional[Hash] = None,
    ) -> AtomicTxBuildResult:
        """Builds a 100% token exit V0 transaction and automatically appends
        `spl_token::instruction::close_account` to reclaim `0.00203928 SOL` ATA rent.
        """
        payer_pk = payer_keypair.pubkey()
        ix0 = set_compute_unit_limit(compute_units)
        ix1 = set_compute_unit_price(priority_micro_lamports)
        ix_swap = swap_leg.to_instruction(payer_pk)
        ix_close = build_close_ata_instruction(
            token_ata=token_ata_to_close,
            destination_sol_wallet=payer_pk,
            owner_authority=payer_pk,
        )

        return self._compile_v0_transaction(
            payer_keypair=payer_keypair,
            instructions=[ix0, ix1, ix_swap, ix_close],
            recent_blockhash=recent_blockhash,
        )


