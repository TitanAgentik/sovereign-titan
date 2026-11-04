"""Sovereign Titan OS — Agent 25 (`sanctum-lst-superbundle-arb`):
Sanctum LST Depeg & 48-Hour Epoch-Boundary Kamino Flash Arbitrage +
5-Transaction Jito Super-Bundle Knapsack Combiner
(`src/engines/sanctum_lst_and_superbundle_engine.py`).

Implements:
1. **Sanctum LST Depeg & 48-Hour Epoch-Boundary Kamino Flash Arbitrage
   (`evaluate_sanctum_lst_flash_arbitrage`)**:
   - Models the canonical Solana Liquid Staking Token (LST) ecosystem unified by
     **Sanctum Infinity Pool (`INF`, `5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm`)** and
     **Sanctum Router / Unstake Reserve** across `jitoSOL`, `mSOL`, `bSOL`, `INF`,
     `jupsol`, `bonkSOL`, `hSOL`, and `compassSOL`.
   - Detects two deterministic risk-free arbitrage triggers:
     - **Trigger A (`WHALE_DEX_LST_DEPEG`)**: When a whale market-sells an LST on
       Orca Whirlpools, Raydium CLMM, or Meteora DLMM, depressing the DEX spot price
       $P_{\\text{DEX}}$ below the true stake-account Net Asset Value $P_{\\text{NAV}}$
       beyond combined fees
       ($\\text{spread\\_bps} > \\text{sanctum\\_fee\\_bps} + \\text{dex\\_fee\\_bps} + \\text{kamino\\_flash\\_fee\\_bps}$).
     - **Trigger B (`EPOCH_BOUNDARY_NAV_STEP_UP`)**: At the ~48-hour Solana Epoch
       boundary when validator staking rewards accrue to the stake pool and
       instantaneously step up $P_{\\text{NAV}}$ while DEX AMM reserves remain at the
       pre-epoch exchange rate.
   - Computes the exact closed-form optimal Kamino flash loan principal
     (`fee_bps = 0.1` = `0.001%`) to borrow, simulates the atomic 4-instruction sequence
     `[flashBorrowIx(SOL) -> DEX Swap SOL->LST -> Sanctum SwapViaStake / Unstake LST->SOL -> flashRepayIx(SOL)]`,
     enforces `net_profit_sol > 0.0` with `directional_memecoin_risk == 0.0`, and
     returns a structured dataclass/dict.

2. **5-Transaction Jito "Super-Bundle" Combiner & Knapsack Score Amplifier
   (`pack_5tx_super_bundle`)**:
   - Takes a primary high-priority transaction/bundle (e.g., `1–2` transactions at
     `Tx[0..1]`) and a queue of candidate secondary opportunities (micro-arbitrages,
     SPL token `CloseAccount` rent reclaims, and permissionless crank bounties).
   - Selects and packs up to **5 total transactions (`Tx[0..4]`)** into a single
     atomic Jito Super-Bundle subject to:
     - Disjoint write-locked account compatibility (no write-lock collisions that
       degrade CU efficiency or invalidate state assumptions).
     - Total bundle Compute Units $\\sum_{i=0}^{k-1} \\text{CU}_i \\le 1,400,000$.
     - Strict preservation of `jitodontfront` at Index 0 (`Tx[0]`).
     - Single aggregated Jito tip transfer placed as the **final instruction of the
       final transaction (`Tx[k-1]`)**.
   - Computes `single_opp_tip_per_cu`, `super_bundle_tip_per_cu`,
     `auction_win_rate_boost_pct` (quantifying the `+25.0% to +40.0%` Stage-2 Knapsack
     win-rate advantage over single-trade bots), and `combined_net_profit_sol`.

3. **`SanctumLstAndSuperBundleEngine` Facade Class**:
   - Provides `run_full_sanctum_superbundle_diagnostic() -> Dict[str, Any]` and
     `get_telemetry_summary() -> Dict[str, Any]` for `TitanIPCDaemon`
     (`RUN_SANCTUM_LST_SUPERBUNDLE_SUITE`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union


# ============================================================================
# Canonical Architectural & Protocol Constants — Agent 25
# ============================================================================

AGENT_25_ID: str = "sanctum-lst-superbundle-arb"
AGENT_25_INDEX: int = 25
AGENT_25_SUBSYSTEM: str = "SANCTUM_LST_AND_SUPERBUNDLE_ENGINE_AGENT_25"

IPC_COMMAND_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE: str = (
    "RUN_SANCTUM_LST_SUPERBUNDLE_SUITE"
)
IPC_ACTION_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE: str = (
    IPC_COMMAND_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE
)

LAMPORTS_PER_SOL: int = 1_000_000_000
BPS_DENOMINATOR: float = 10_000.0
SOLANA_BASE_TX_SIGNATURE_FEE_SOL: float = 0.000005  # 5,000 lamports per signature

# ----------------------------------------------------------------------------
# Pillar 1: Sanctum Infinity Pool, Router, Unstake Reserve & Kamino Constants
# ----------------------------------------------------------------------------
SANCTUM_INFINITY_POOL_SYMBOL: str = "INF"
SANCTUM_INFINITY_POOL_MINT: str = "5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm"
SANCTUM_INFINITY_CONTROLLER_PROGRAM_ID: str = (
    "5ocnV1qiCgaQR8Jb8xWnVbApfaygJ8tNoZfgPwsgx9kx"
)
SANCTUM_ROUTER_PROGRAM_ID: str = "stkitrT1Uoy18Dk1fTrgPw8W6MVzoCfYoAFT4MLsmhq"
SANCTUM_UNSTAKE_RESERVE_POOL_PUBKEY: str = (
    "unpXTU2Ndrc7WWNyEhQWe4udTzSibLPi25SXv2xbCHQ"
)
KAMINO_LENDING_PROGRAM_ID: str = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"

KAMINO_FLASH_LOAN_FEE_BPS: float = 0.1  # 0.1 bps = 0.001%
KAMINO_FLASH_LOAN_FEE_PCT: float = 0.001
KAMINO_FLASH_LOAN_FEE_FRACTION: float = 0.00001

SOLANA_EPOCH_DURATION_HOURS: float = 48.0
SOLANA_EPOCH_DURATION_SECONDS: int = 172_800
SOLANA_SLOTS_PER_EPOCH: int = 432_000

# Canonical 8 Sanctum LSTs required by specification
SUPPORTED_SANCTUM_LSTS: Tuple[str, ...] = (
    "jitoSOL",
    "mSOL",
    "bSOL",
    "INF",
    "jupsol",
    "bonkSOL",
    "hSOL",
    "compassSOL",
)

# Case-insensitive normalization map to canonical LST keys
_LST_CANONICAL_LOOKUP: Dict[str, str] = {
    "jitosol": "jitoSOL",
    "msol": "mSOL",
    "bsol": "bSOL",
    "inf": "INF",
    "jupsol": "jupsol",
    "bonksol": "bonkSOL",
    "hsol": "hSOL",
    "compasssol": "compassSOL",
}


@dataclass(frozen=True)
class SanctumLstMetadata:
    """Canonical on-chain specification for a Sanctum-supported Liquid Staking Token."""

    symbol: str
    mint: str
    stake_pool_program: str
    stake_pool_account: str
    default_nav_sol: float
    annualized_staking_yield_pct: float
    default_epoch_step_up_bps: float
    default_sanctum_fee_bps: float
    default_sanctum_reserve_sol: float


SANCTUM_LST_REGISTRY: Dict[str, SanctumLstMetadata] = {
    "jitoSOL": SanctumLstMetadata(
        symbol="jitoSOL",
        mint="J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
        stake_pool_program="SPoo1Ku8WFXoNDMHPsrGSTSG1Y47rzgn41SLUNakuHy",
        stake_pool_account="Jito4APyf642JPZPx3hGc6WWJ8zPKtRbRs4P815Awbb",
        default_nav_sol=1.1485,
        annualized_staking_yield_pct=7.95,
        default_epoch_step_up_bps=14.5,
        default_sanctum_fee_bps=1.0,
        default_sanctum_reserve_sol=45_000.0,
    ),
    "mSOL": SanctumLstMetadata(
        symbol="mSOL",
        mint="mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
        stake_pool_program="MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD",
        stake_pool_account="8szGkuLTAux9XMgZ2vtY39jVSowEcpBfFfD8hXSEqdGC",
        default_nav_sol=1.2140,
        annualized_staking_yield_pct=7.55,
        default_epoch_step_up_bps=13.8,
        default_sanctum_fee_bps=1.0,
        default_sanctum_reserve_sol=38_000.0,
    ),
    "bSOL": SanctumLstMetadata(
        symbol="bSOL",
        mint="bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
        stake_pool_program="SPoo1Ku8WFXoNDMHPsrGSTSG1Y47rzgn41SLUNakuHy",
        stake_pool_account="stk9ApL5HeVAwPLr3TLhDXdZS8ptVu7zp6ov8HFDuMi",
        default_nav_sol=1.1620,
        annualized_staking_yield_pct=7.40,
        default_epoch_step_up_bps=13.5,
        default_sanctum_fee_bps=1.0,
        default_sanctum_reserve_sol=25_000.0,
    ),
    "INF": SanctumLstMetadata(
        symbol="INF",
        mint=SANCTUM_INFINITY_POOL_MINT,
        stake_pool_program=SANCTUM_INFINITY_CONTROLLER_PROGRAM_ID,
        stake_pool_account="AYhux5gJzCoeoc1PoJ1VxwPDe22RwCVpHviLDD1oCGvW",
        default_nav_sol=1.2890,
        annualized_staking_yield_pct=8.85,
        default_epoch_step_up_bps=16.2,
        default_sanctum_fee_bps=1.0,
        default_sanctum_reserve_sol=60_000.0,
    ),
    "jupsol": SanctumLstMetadata(
        symbol="jupsol",
        mint="jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v",
        stake_pool_program="SPMBzsVUuoHA4Jm6KunbsotaahvVikZs1JyTW6iJvbn",
        stake_pool_account="8VpRhuxa7sUUepdY3kQiTmX9rS5vx4WgaXiAnXq4KCtr",
        default_nav_sol=1.0950,
        annualized_staking_yield_pct=8.15,
        default_epoch_step_up_bps=15.0,
        default_sanctum_fee_bps=1.0,
        default_sanctum_reserve_sol=32_000.0,
    ),
    "bonkSOL": SanctumLstMetadata(
        symbol="bonkSOL",
        mint="BonK1YhkXEGLZzwtcvRTip3gAL9nCeQD7ppZBLXhtTs",
        stake_pool_program="SPMBzsVUuoHA4Jm6KunbsotaahvVikZs1JyTW6iJvbn",
        stake_pool_account="ArAQfbzsdotoKB5jJcZa3ajQrrPcWr2YQoDAEAiFxJAC",
        default_nav_sol=1.0780,
        annualized_staking_yield_pct=7.90,
        default_epoch_step_up_bps=14.2,
        default_sanctum_fee_bps=1.5,
        default_sanctum_reserve_sol=18_000.0,
    ),
    "hSOL": SanctumLstMetadata(
        symbol="hSOL",
        mint="he1iusmfkpAdwvxLNGV8Y1iSbj4rUy6yMhEA3fotn9A",
        stake_pool_program="SPMBzsVUuoHA4Jm6KunbsotaahvVikZs1JyTW6iJvbn",
        stake_pool_account="3wK2g8ZdzAH8FJ7PKr2RcvGh7V9VYson5hrVsJM5Lmws",
        default_nav_sol=1.1120,
        annualized_staking_yield_pct=8.10,
        default_epoch_step_up_bps=14.8,
        default_sanctum_fee_bps=1.0,
        default_sanctum_reserve_sol=22_000.0,
    ),
    "compassSOL": SanctumLstMetadata(
        symbol="compassSOL",
        mint="AwDe52bdeJ4dcqhG2peNNdA9f3R12BfDRD3kYjK2E7H6",
        stake_pool_program="SPMBzsVUuoHA4Jm6KunbsotaahvVikZs1JyTW6iJvbn",
        stake_pool_account="CompassPool11111111111111111111111111111111",
        default_nav_sol=1.0840,
        annualized_staking_yield_pct=7.80,
        default_epoch_step_up_bps=14.0,
        default_sanctum_fee_bps=1.5,
        default_sanctum_reserve_sol=15_000.0,
    ),
}

SUPPORTED_LST_DEX_VENUES: Tuple[str, ...] = (
    "ORCA_WHIRLPOOL",
    "RAYDIUM_CLMM",
    "METEORA_DLMM",
)

DEX_VENUE_PROGRAM_IDS: Dict[str, str] = {
    "ORCA_WHIRLPOOL": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
    "RAYDIUM_CLMM": "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
    "METEORA_DLMM": "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
}

SUPPORTED_SANCTUM_REDEMPTION_ROUTES: Tuple[str, ...] = (
    "SANCTUM_INFINITY_SWAP_VIA_STAKE",
    "SANCTUM_UNSTAKE_RESERVE",
    "SANCTUM_ROUTER_SWAP_VIA_STAKE",
)

# Canonical Trigger & Decision Constants for Pillar 1
TRIGGER_WHALE_DEX_LST_DEPEG: str = "WHALE_DEX_LST_DEPEG"
TRIGGER_EPOCH_BOUNDARY_NAV_STEP_UP: str = "EPOCH_BOUNDARY_NAV_STEP_UP"
TRIGGER_DUAL_WHALE_DEPEG_AND_EPOCH_STEP_UP: str = (
    "DUAL_WHALE_DEX_DEPEG_AND_EPOCH_BOUNDARY_STEP_UP"
)
TRIGGER_NONE: str = "NONE"

DECISION_EXECUTE_SANCTUM_LST_FLASH_ARB: str = "EXECUTE_SANCTUM_LST_FLASH_ARBITRAGE"
DECISION_SKIP_SPREAD_BELOW_COMBINED_FEES: str = "SKIP_SPREAD_BELOW_COMBINED_FEES"
DECISION_SKIP_NO_DEPEG_OR_EPOCH_STEP_UP: str = "SKIP_NO_DEPEG_OR_EPOCH_STEP_UP"
DECISION_SKIP_NON_POSITIVE_NET_PROFIT: str = "SKIP_NON_POSITIVE_NET_PROFIT"

# Canonical 4-Instruction Atomic Flash Arbitrage Sequence
CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE: Tuple[str, str, str, str] = (
    "flashBorrowIx(SOL)",
    "DEX Swap SOL->LST",
    "Sanctum SwapViaStake / Unstake LST->SOL",
    "flashRepayIx(SOL)",
)

# ----------------------------------------------------------------------------
# Pillar 2: 5-Transaction Jito Super-Bundle Knapsack Constants
# ----------------------------------------------------------------------------
MAX_JITO_BUNDLE_TX_COUNT: int = 5
MAX_JITO_BUNDLE_CU_LIMIT: int = 1_400_000
JITODONTFRONT_PUBKEY: str = "jitodontfront111111111111111111111111111111"

JITO_TIP_PAYMENT_PROGRAM_ID: str = "T1pyyaTNZsKv2WcRAB8oVnk93mLJw2XzjtVYqCsaHqt"
JITO_CANONICAL_TIP_ACCOUNTS: Tuple[str, ...] = (
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
)

FINAL_AGGREGATED_JITO_TIP_IX_LABEL: str = (
    "JitoTipTransferIx(AggregatedBundleTip->JitoTipAccount)"
)

SECONDARY_OPPORTUNITY_TYPES: Tuple[str, ...] = (
    "MICRO_ARBITRAGE",
    "SPL_CLOSE_ACCOUNT_RENT_RECLAIM",
    "PERMISSIONLESS_CRANK_BOUNTY",
)

STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT: float = 25.0
STAGE2_KNAPSACK_WIN_RATE_BOOST_MAX_PCT: float = 40.0

DECISION_EXECUTE_5TX_JITO_SUPER_BUNDLE: str = "EXECUTE_5TX_JITO_SUPER_BUNDLE"
DECISION_EXECUTE_PRIMARY_ONLY_BUNDLE: str = "EXECUTE_PRIMARY_ONLY_BUNDLE"
DECISION_REJECT_INVALID_SUPER_BUNDLE: str = "REJECT_INVALID_SUPER_BUNDLE"


# ============================================================================
# Shared Dict-Compatible Dataclass Mixin
# ============================================================================


class DictLikeModelMixin:
    """Mixin enabling dataclasses to behave both as attribute models and dicts."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)

    def keys(self) -> List[str]:
        return list(self.to_dict().keys())

    def values(self) -> List[Any]:
        return list(self.to_dict().values())

    def items(self) -> List[Tuple[str, Any]]:
        return list(self.to_dict().items())

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.to_dict())


# ============================================================================
# Pillar 1 Models: Sanctum LST Depeg & Epoch-Boundary Kamino Flash Arbitrage
# ============================================================================


@dataclass
class SanctumFlashInstructionStep(DictLikeModelMixin):
    """Single instruction step within the 4-instruction Kamino -> DEX -> Sanctum -> Kamino atomic tx."""

    ix_index: int
    instruction_label: str
    program_id: str
    input_asset: str
    output_asset: str
    input_amount: float
    output_amount: float
    fee_bps: float
    fee_amount_sol_equiv: float


@dataclass
class SanctumLstFlashArbitrageResult(DictLikeModelMixin):
    """Structured result for `evaluate_sanctum_lst_flash_arbitrage`."""

    triggered: bool
    decision: str
    trigger_type: str
    whale_depeg_trigger_detected: bool
    epoch_boundary_trigger_detected: bool
    lst_symbol: str
    lst_mint: str
    sanctum_infinity_mint: str
    dex_venue: str
    dex_program_id: str
    sanctum_redemption_route: str
    sanctum_program_id: str
    kamino_program_id: str
    pre_event_nav_price_sol: float
    nav_price_sol: float
    dex_spot_price_sol: float
    post_arb_dex_price_sol: float
    whale_sell_lst_amount: float
    is_epoch_boundary: bool
    epoch_duration_hours: float
    epoch_reward_step_up_bps: float
    spread_bps: float
    sanctum_fee_bps: float
    dex_fee_bps: float
    kamino_flash_fee_bps: float
    combined_fee_threshold_bps: float
    net_edge_above_fees_bps: float
    optimal_flash_borrow_sol: float
    executed_flash_borrow_sol: float
    dex_lst_acquired: float
    sanctum_sol_redeemed: float
    kamino_flash_fee_sol: float
    kamino_repay_total_sol: float
    dex_fee_paid_sol: float
    sanctum_fee_paid_sol: float
    base_tx_fee_sol: float
    jito_tip_sol: float
    gross_profit_sol: float
    net_profit_sol: float
    net_profit_lamports: int
    directional_memecoin_risk: float
    atomic_instruction_sequence: List[str]
    instruction_breakdown: List[SanctumFlashInstructionStep]
    write_locked_accounts: List[str]
    read_only_accounts: List[str]
    estimated_compute_units: int


# ============================================================================
# Pillar 2 Models: 5-Transaction Jito Super-Bundle Knapsack Combiner
# ============================================================================


@dataclass
class BundleTransactionSpec(DictLikeModelMixin):
    """Input or packed specification for a transaction inside a Jito bundle."""

    tx_id: str
    opportunity_type: str
    compute_units: int
    gross_profit_sol: float
    tip_contribution_sol: float
    tip_contribution_lamports: int
    write_locked_accounts: List[str]
    read_only_accounts: List[str] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)
    bundle_index: Optional[int] = None
    has_jitodontfront: bool = False
    has_jito_tip_ix: bool = False
    aggregated_tip_lamports_on_tx: int = 0
    efficiency_tip_per_cu: float = 0.0


@dataclass
class RejectedBundleCandidate(DictLikeModelMixin):
    """Record of a candidate secondary transaction rejected by the Knapsack packer."""

    tx_id: str
    opportunity_type: str
    compute_units: int
    tip_contribution_lamports: int
    rejection_reason: str
    colliding_accounts: List[str] = field(default_factory=list)


@dataclass
class JitoSuperBundlePackResult(DictLikeModelMixin):
    """Structured result for `pack_5tx_super_bundle`."""

    packed: bool
    decision: str
    bundle_tx_count: int
    max_bundle_tx_limit: int
    primary_tx_count: int
    secondary_tx_packed_count: int
    candidates_evaluated_count: int
    candidates_rejected_count: int
    primary_compute_units: int
    total_bundle_compute_units: int
    max_bundle_compute_units: int
    cu_utilization_pct: float
    single_opp_tip_lamports: int
    super_bundle_total_tip_lamports: int
    single_opp_tip_per_cu: float
    super_bundle_tip_per_cu: float
    tip_per_cu_amplification_ratio: float
    tip_per_cu_improvement_pct: float
    auction_win_rate_boost_pct: float
    primary_net_profit_sol: float
    secondary_net_profit_sol: float
    combined_gross_profit_sol: float
    aggregated_jito_tip_sol: float
    total_base_tx_fees_sol: float
    combined_net_profit_sol: float
    tx0_has_jitodontfront: bool
    jitodontfront_pubkey: str
    disjoint_write_locks_verified: bool
    write_lock_collision_count: int
    single_aggregated_tip_verified: bool
    final_tx_index: int
    final_tx_has_aggregated_tip_ix: bool
    final_instruction_of_final_tx: str
    jito_tip_recipient_account: str
    packed_transactions: List[BundleTransactionSpec]
    rejected_candidates: List[RejectedBundleCandidate]
    union_write_locked_accounts: List[str]


# ============================================================================
# Pillar 1 Implementation: `evaluate_sanctum_lst_flash_arbitrage`
# ============================================================================


def normalize_sanctum_lst_symbol(lst_symbol: str) -> str:
    """Normalizes an LST symbol (case-insensitive) to its canonical Sanctum registry key."""
    cleaned = lst_symbol.strip()
    canonical = _LST_CANONICAL_LOOKUP.get(cleaned.lower())
    if canonical is None:
        raise ValueError(
            f"Unsupported Sanctum LST symbol '{lst_symbol}'. "
            f"Supported LSTs: {SUPPORTED_SANCTUM_LSTS}"
        )
    return canonical


def compute_optimal_kamino_flash_principal_sol(
    *,
    dex_sol_reserve: float,
    dex_lst_reserve: float,
    nav_price_sol: float,
    dex_fee_bps: float,
    sanctum_fee_bps: float,
    kamino_flash_fee_bps: float = KAMINO_FLASH_LOAN_FEE_BPS,
    max_flash_borrow_sol: float = 5_000.0,
    sanctum_sol_reserve_depth: float = 50_000.0,
) -> float:
    """Computes the exact closed-form optimal Kamino flash loan principal (in SOL)
    that maximizes single-slot risk-free profit across:
        `[flashBorrowIx(SOL) -> DEX Swap SOL->LST -> Sanctum SwapViaStake/Unstake LST->SOL -> flashRepayIx(SOL)]`.

    Mathematical Derivation:
        Let $R_{\\text{SOL}}$ and $R_{\\text{LST}}$ be the effective virtual reserves of the
        concentrated DEX pool such that $P_{\\text{DEX}} = R_{\\text{SOL}} / R_{\\text{LST}}$.
        For borrowed principal $\\Delta_{\\text{SOL}}$:
            $\\text{LST}_{\\text{out}}(\\Delta_{\\text{SOL}}) = \\frac{R_{\\text{LST}} \\Delta_{\\text{SOL}} (1 - f_{\\text{DEX}})}{R_{\\text{SOL}} + \\Delta_{\\text{SOL}} (1 - f_{\\text{DEX}})}$
            $\\text{SOL}_{\\text{redeemed}}(\\Delta_{\\text{SOL}}) = \\text{LST}_{\\text{out}}(\\Delta_{\\text{SOL}}) \\cdot P_{\\text{NAV}} \\cdot (1 - f_{\\text{Sanctum}})$
            $\\text{SOL}_{\\text{repay}}(\\Delta_{\\text{SOL}}) = \\Delta_{\\text{SOL}} (1 + f_{\\text{Kamino}})$

        Setting $\\frac{d}{d\\Delta_{\\text{SOL}}} \\left(\\text{SOL}_{\\text{redeemed}} - \\text{SOL}_{\\text{repay}}\\right) = 0$ yields:
            $\\Delta_{\\text{SOL}}^* = \\frac{\\sqrt{R_{\\text{SOL}} \\cdot R_{\\text{LST}} \\cdot P_{\\text{NAV}} \\cdot (1 - f_{\\text{DEX}}) (1 - f_{\\text{Sanctum}}) / (1 + f_{\\text{Kamino}})} - R_{\\text{SOL}}}{1 - f_{\\text{DEX}}}$
    """
    if dex_sol_reserve <= 0.0 or dex_lst_reserve <= 0.0 or nav_price_sol <= 0.0:
        return 0.0

    f_dex = max(0.0, dex_fee_bps / BPS_DENOMINATOR)
    f_sanctum = max(0.0, sanctum_fee_bps / BPS_DENOMINATOR)
    f_kamino = max(0.0, kamino_flash_fee_bps / BPS_DENOMINATOR)

    if f_dex >= 1.0 or f_sanctum >= 1.0:
        return 0.0

    numerator_term = (
        dex_sol_reserve
        * dex_lst_reserve
        * nav_price_sol
        * (1.0 - f_dex)
        * (1.0 - f_sanctum)
        / (1.0 + f_kamino)
    )
    if numerator_term <= 0.0:
        return 0.0

    raw_optimal_sol = (math.sqrt(numerator_term) - dex_sol_reserve) / (1.0 - f_dex)
    if raw_optimal_sol <= 0.0:
        return 0.0

    # Cap by available Sanctum reserve liquidity and max flash loan ceiling
    reserve_cap_sol = max(0.0, sanctum_sol_reserve_depth * 0.95)
    capped_optimal_sol = min(raw_optimal_sol, max_flash_borrow_sol, reserve_cap_sol)
    return round(max(0.0, capped_optimal_sol), 6)


def evaluate_sanctum_lst_flash_arbitrage(
    lst_symbol: str = "jitoSOL",
    *,
    dex_venue: str = "ORCA_WHIRLPOOL",
    sanctum_redemption_route: str = "SANCTUM_INFINITY_SWAP_VIA_STAKE",
    nav_price_sol: Optional[float] = None,
    dex_spot_price_sol: Optional[float] = None,
    whale_sell_lst_amount: float = 0.0,
    is_epoch_boundary: bool = False,
    epoch_reward_step_up_bps: float = 0.0,
    dex_sol_reserve: float = 25_000.0,
    sanctum_sol_reserve_depth: Optional[float] = None,
    sanctum_fee_bps: Optional[float] = None,
    dex_fee_bps: float = 1.0,
    kamino_flash_fee_bps: float = KAMINO_FLASH_LOAN_FEE_BPS,
    max_flash_borrow_sol: float = 5_000.0,
    override_flash_borrow_sol: Optional[float] = None,
    jito_tip_share_bps: float = 1_500.0,  # 15% of gross profit to Jito validator tip
    base_tx_fee_sol: float = SOLANA_BASE_TX_SIGNATURE_FEE_SOL,
) -> SanctumLstFlashArbitrageResult:
    """Evaluates and simulates a Sanctum LST Depeg (`WHALE_DEX_LST_DEPEG`) or
    48-Hour Solana Epoch-Boundary (`EPOCH_BOUNDARY_NAV_STEP_UP`) Kamino Flash Arbitrage.

    Enforces:
        1. $\\text{spread\\_bps} > \\text{sanctum\\_fee\\_bps} + \\text{dex\\_fee\\_bps} + \\text{kamino\\_flash\\_fee\\_bps}$
        2. Exact closed-form optimal Kamino flash loan sizing (`fee_bps = 0.1` = `0.001%`)
        3. Atomic 4-instruction sequence:
           `[flashBorrowIx(SOL) -> DEX Swap SOL->LST -> Sanctum SwapViaStake / Unstake LST->SOL -> flashRepayIx(SOL)]`
        4. `net_profit_sol > 0.0` and `directional_memecoin_risk == 0.0`
    """
    canonical_lst = normalize_sanctum_lst_symbol(lst_symbol)
    lst_meta = SANCTUM_LST_REGISTRY[canonical_lst]

    venue_normalized = dex_venue.strip().upper()
    if venue_normalized not in SUPPORTED_LST_DEX_VENUES:
        raise ValueError(
            f"Unsupported DEX venue '{dex_venue}'. "
            f"Supported venues: {SUPPORTED_LST_DEX_VENUES}"
        )

    route_normalized = sanctum_redemption_route.strip().upper()
    if route_normalized not in SUPPORTED_SANCTUM_REDEMPTION_ROUTES:
        raise ValueError(
            f"Unsupported Sanctum redemption route '{sanctum_redemption_route}'. "
            f"Supported routes: {SUPPORTED_SANCTUM_REDEMPTION_ROUTES}"
        )

    effective_sanctum_fee_bps = (
        float(sanctum_fee_bps)
        if sanctum_fee_bps is not None
        else lst_meta.default_sanctum_fee_bps
    )
    effective_dex_fee_bps = float(dex_fee_bps)
    effective_kamino_fee_bps = float(kamino_flash_fee_bps)
    effective_sanctum_reserve_sol = (
        float(sanctum_sol_reserve_depth)
        if sanctum_sol_reserve_depth is not None
        else lst_meta.default_sanctum_reserve_sol
    )

    # 1. Determine pre-event and post-event stake-account NAV (P_NAV)
    base_nav_sol = (
        float(nav_price_sol) if nav_price_sol is not None else lst_meta.default_nav_sol
    )
    effective_epoch_step_bps = float(epoch_reward_step_up_bps)
    if is_epoch_boundary and effective_epoch_step_bps <= 0.0 and dex_spot_price_sol is None:
        effective_epoch_step_bps = lst_meta.default_epoch_step_up_bps

    if is_epoch_boundary and effective_epoch_step_bps > 0.0:
        if dex_spot_price_sol is None:
            # DEX remains at pre-epoch NAV while on-chain stake pool NAV steps up instantaneously
            pre_event_nav_sol = base_nav_sol
            true_nav_sol = base_nav_sol * (1.0 + effective_epoch_step_bps / BPS_DENOMINATOR)
            effective_dex_spot_sol = pre_event_nav_sol
        elif nav_price_sol is not None and dex_spot_price_sol >= nav_price_sol:
            # Caller passed pre-epoch NAV and matching DEX price; apply step-up to NAV
            pre_event_nav_sol = base_nav_sol
            true_nav_sol = base_nav_sol * (1.0 + effective_epoch_step_bps / BPS_DENOMINATOR)
            effective_dex_spot_sol = float(dex_spot_price_sol)
        else:
            # Caller already passed post-step-up nav_price_sol and pre-epoch dex_spot_price_sol
            true_nav_sol = base_nav_sol
            pre_event_nav_sol = true_nav_sol / (
                1.0 + effective_epoch_step_bps / BPS_DENOMINATOR
            )
            effective_dex_spot_sol = float(dex_spot_price_sol)
    else:
        pre_event_nav_sol = base_nav_sol
        true_nav_sol = base_nav_sol
        effective_dex_spot_sol = (
            float(dex_spot_price_sol) if dex_spot_price_sol is not None else base_nav_sol
        )

    # 2. If whale_sell_lst_amount > 0 and dex_spot_price_sol was not explicitly depressed below NAV,
    # model the whale market-sell impact on the DEX reserves
    if whale_sell_lst_amount > 0.0 and effective_dex_spot_sol >= pre_event_nav_sol:
        initial_lst_reserve = dex_sol_reserve / pre_event_nav_sol
        f_dex = effective_dex_fee_bps / BPS_DENOMINATOR
        net_whale_lst = whale_sell_lst_amount * (1.0 - f_dex)
        new_lst_reserve = initial_lst_reserve + net_whale_lst
        new_sol_reserve = (dex_sol_reserve * initial_lst_reserve) / new_lst_reserve
        effective_dex_spot_sol = new_sol_reserve / new_lst_reserve
        active_dex_sol_reserve = new_sol_reserve
        active_dex_lst_reserve = new_lst_reserve
    else:
        active_dex_sol_reserve = max(1.0, float(dex_sol_reserve))
        active_dex_lst_reserve = active_dex_sol_reserve / max(1e-9, effective_dex_spot_sol)

    # 3. Compute spread_bps and compare against combined fee threshold
    if effective_dex_spot_sol <= 0.0:
        spread_bps = 0.0
    else:
        spread_bps = (
            (true_nav_sol - effective_dex_spot_sol) / effective_dex_spot_sol
        ) * BPS_DENOMINATOR

    combined_fee_threshold_bps = (
        effective_sanctum_fee_bps + effective_dex_fee_bps + effective_kamino_fee_bps
    )
    net_edge_above_fees_bps = spread_bps - combined_fee_threshold_bps

    # Identify trigger classification
    epoch_trigger_detected = bool(
        is_epoch_boundary
        and (effective_epoch_step_bps > 0.0 or true_nav_sol > effective_dex_spot_sol)
    )
    whale_depeg_detected = bool(
        whale_sell_lst_amount > 0.0
        or (not epoch_trigger_detected and true_nav_sol > effective_dex_spot_sol)
    )

    if whale_depeg_detected and epoch_trigger_detected and whale_sell_lst_amount > 0.0:
        trigger_type = TRIGGER_DUAL_WHALE_DEPEG_AND_EPOCH_STEP_UP
    elif epoch_trigger_detected:
        trigger_type = TRIGGER_EPOCH_BOUNDARY_NAV_STEP_UP
    elif whale_depeg_detected:
        trigger_type = TRIGGER_WHALE_DEX_LST_DEPEG
    else:
        trigger_type = TRIGGER_NONE

    sanctum_prog_id = (
        SANCTUM_INFINITY_CONTROLLER_PROGRAM_ID
        if route_normalized == "SANCTUM_INFINITY_SWAP_VIA_STAKE"
        else SANCTUM_ROUTER_PROGRAM_ID
    )
    dex_prog_id = DEX_VENUE_PROGRAM_IDS[venue_normalized]

    write_locked_accounts = [
        f"KaminoSOLReserveVault::{KAMINO_LENDING_PROGRAM_ID[:8]}",
        f"DEXPool::{venue_normalized}::{canonical_lst}_SOL",
        f"SanctumPool::{route_normalized}::{canonical_lst}",
        f"SearcherWSOLTokenAccount::{canonical_lst}",
        f"SearcherLSTTokenAccount::{canonical_lst}",
    ]
    read_only_accounts = [
        JITODONTFRONT_PUBKEY,
        KAMINO_LENDING_PROGRAM_ID,
        dex_prog_id,
        sanctum_prog_id,
        SANCTUM_INFINITY_POOL_MINT,
        lst_meta.mint,
        lst_meta.stake_pool_account,
    ]

    # 4. Compute closed-form optimal Kamino flash loan principal
    optimal_flash_borrow_sol = compute_optimal_kamino_flash_principal_sol(
        dex_sol_reserve=active_dex_sol_reserve,
        dex_lst_reserve=active_dex_lst_reserve,
        nav_price_sol=true_nav_sol,
        dex_fee_bps=effective_dex_fee_bps,
        sanctum_fee_bps=effective_sanctum_fee_bps,
        kamino_flash_fee_bps=effective_kamino_fee_bps,
        max_flash_borrow_sol=max_flash_borrow_sol,
        sanctum_sol_reserve_depth=effective_sanctum_reserve_sol,
    )

    if spread_bps <= 0.0:
        return SanctumLstFlashArbitrageResult(
            triggered=False,
            decision=DECISION_SKIP_NO_DEPEG_OR_EPOCH_STEP_UP,
            trigger_type=TRIGGER_NONE,
            whale_depeg_trigger_detected=False,
            epoch_boundary_trigger_detected=False,
            lst_symbol=canonical_lst,
            lst_mint=lst_meta.mint,
            sanctum_infinity_mint=SANCTUM_INFINITY_POOL_MINT,
            dex_venue=venue_normalized,
            dex_program_id=dex_prog_id,
            sanctum_redemption_route=route_normalized,
            sanctum_program_id=sanctum_prog_id,
            kamino_program_id=KAMINO_LENDING_PROGRAM_ID,
            pre_event_nav_price_sol=round(pre_event_nav_sol, 8),
            nav_price_sol=round(true_nav_sol, 8),
            dex_spot_price_sol=round(effective_dex_spot_sol, 8),
            post_arb_dex_price_sol=round(effective_dex_spot_sol, 8),
            whale_sell_lst_amount=round(whale_sell_lst_amount, 6),
            is_epoch_boundary=is_epoch_boundary,
            epoch_duration_hours=SOLANA_EPOCH_DURATION_HOURS,
            epoch_reward_step_up_bps=round(effective_epoch_step_bps, 4),
            spread_bps=round(spread_bps, 4),
            sanctum_fee_bps=round(effective_sanctum_fee_bps, 4),
            dex_fee_bps=round(effective_dex_fee_bps, 4),
            kamino_flash_fee_bps=round(effective_kamino_fee_bps, 4),
            combined_fee_threshold_bps=round(combined_fee_threshold_bps, 4),
            net_edge_above_fees_bps=round(net_edge_above_fees_bps, 4),
            optimal_flash_borrow_sol=0.0,
            executed_flash_borrow_sol=0.0,
            dex_lst_acquired=0.0,
            sanctum_sol_redeemed=0.0,
            kamino_flash_fee_sol=0.0,
            kamino_repay_total_sol=0.0,
            dex_fee_paid_sol=0.0,
            sanctum_fee_paid_sol=0.0,
            base_tx_fee_sol=round(base_tx_fee_sol, 8),
            jito_tip_sol=0.0,
            gross_profit_sol=0.0,
            net_profit_sol=0.0,
            net_profit_lamports=0,
            directional_memecoin_risk=0.0,
            atomic_instruction_sequence=list(CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE),
            instruction_breakdown=[],
            write_locked_accounts=write_locked_accounts,
            read_only_accounts=read_only_accounts,
            estimated_compute_units=185_000,
        )

    if spread_bps <= combined_fee_threshold_bps or optimal_flash_borrow_sol <= 0.0:
        return SanctumLstFlashArbitrageResult(
            triggered=False,
            decision=DECISION_SKIP_SPREAD_BELOW_COMBINED_FEES,
            trigger_type=trigger_type,
            whale_depeg_trigger_detected=whale_depeg_detected,
            epoch_boundary_trigger_detected=epoch_trigger_detected,
            lst_symbol=canonical_lst,
            lst_mint=lst_meta.mint,
            sanctum_infinity_mint=SANCTUM_INFINITY_POOL_MINT,
            dex_venue=venue_normalized,
            dex_program_id=dex_prog_id,
            sanctum_redemption_route=route_normalized,
            sanctum_program_id=sanctum_prog_id,
            kamino_program_id=KAMINO_LENDING_PROGRAM_ID,
            pre_event_nav_price_sol=round(pre_event_nav_sol, 8),
            nav_price_sol=round(true_nav_sol, 8),
            dex_spot_price_sol=round(effective_dex_spot_sol, 8),
            post_arb_dex_price_sol=round(effective_dex_spot_sol, 8),
            whale_sell_lst_amount=round(whale_sell_lst_amount, 6),
            is_epoch_boundary=is_epoch_boundary,
            epoch_duration_hours=SOLANA_EPOCH_DURATION_HOURS,
            epoch_reward_step_up_bps=round(effective_epoch_step_bps, 4),
            spread_bps=round(spread_bps, 4),
            sanctum_fee_bps=round(effective_sanctum_fee_bps, 4),
            dex_fee_bps=round(effective_dex_fee_bps, 4),
            kamino_flash_fee_bps=round(effective_kamino_fee_bps, 4),
            combined_fee_threshold_bps=round(combined_fee_threshold_bps, 4),
            net_edge_above_fees_bps=round(net_edge_above_fees_bps, 4),
            optimal_flash_borrow_sol=optimal_flash_borrow_sol,
            executed_flash_borrow_sol=0.0,
            dex_lst_acquired=0.0,
            sanctum_sol_redeemed=0.0,
            kamino_flash_fee_sol=0.0,
            kamino_repay_total_sol=0.0,
            dex_fee_paid_sol=0.0,
            sanctum_fee_paid_sol=0.0,
            base_tx_fee_sol=round(base_tx_fee_sol, 8),
            jito_tip_sol=0.0,
            gross_profit_sol=0.0,
            net_profit_sol=0.0,
            net_profit_lamports=0,
            directional_memecoin_risk=0.0,
            atomic_instruction_sequence=list(CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE),
            instruction_breakdown=[],
            write_locked_accounts=write_locked_accounts,
            read_only_accounts=read_only_accounts,
            estimated_compute_units=185_000,
        )

    # 5. Simulate the 4-instruction atomic sequence
    executed_borrow_sol = (
        float(override_flash_borrow_sol)
        if override_flash_borrow_sol is not None and override_flash_borrow_sol > 0.0
        else optimal_flash_borrow_sol
    )
    executed_borrow_sol = min(
        executed_borrow_sol,
        max_flash_borrow_sol,
        effective_sanctum_reserve_sol * 0.95,
    )

    f_dex = effective_dex_fee_bps / BPS_DENOMINATOR
    f_sanctum = effective_sanctum_fee_bps / BPS_DENOMINATOR
    f_kamino = effective_kamino_fee_bps / BPS_DENOMINATOR

    # Ix 0: flashBorrowIx(SOL)
    kamino_flash_fee_sol = executed_borrow_sol * f_kamino

    # Ix 1: DEX Swap SOL -> LST
    dex_fee_paid_sol = executed_borrow_sol * f_dex
    net_sol_into_dex = executed_borrow_sol - dex_fee_paid_sol
    dex_lst_acquired = (active_dex_lst_reserve * net_sol_into_dex) / (
        active_dex_sol_reserve + net_sol_into_dex
    )
    post_arb_sol_reserve = active_dex_sol_reserve + net_sol_into_dex
    post_arb_lst_reserve = active_dex_lst_reserve - dex_lst_acquired
    post_arb_dex_price_sol = post_arb_sol_reserve / max(1e-9, post_arb_lst_reserve)

    # Ix 2: Sanctum SwapViaStake / Unstake LST -> SOL at deterministic stake-account NAV
    gross_sanctum_sol = dex_lst_acquired * true_nav_sol
    sanctum_fee_paid_sol = gross_sanctum_sol * f_sanctum
    sanctum_sol_redeemed = gross_sanctum_sol - sanctum_fee_paid_sol

    # Ix 3: flashRepayIx(SOL)
    kamino_repay_total_sol = executed_borrow_sol + kamino_flash_fee_sol

    gross_profit_sol = sanctum_sol_redeemed - kamino_repay_total_sol
    if gross_profit_sol <= base_tx_fee_sol:
        return SanctumLstFlashArbitrageResult(
            triggered=False,
            decision=DECISION_SKIP_NON_POSITIVE_NET_PROFIT,
            trigger_type=trigger_type,
            whale_depeg_trigger_detected=whale_depeg_detected,
            epoch_boundary_trigger_detected=epoch_trigger_detected,
            lst_symbol=canonical_lst,
            lst_mint=lst_meta.mint,
            sanctum_infinity_mint=SANCTUM_INFINITY_POOL_MINT,
            dex_venue=venue_normalized,
            dex_program_id=dex_prog_id,
            sanctum_redemption_route=route_normalized,
            sanctum_program_id=sanctum_prog_id,
            kamino_program_id=KAMINO_LENDING_PROGRAM_ID,
            pre_event_nav_price_sol=round(pre_event_nav_sol, 8),
            nav_price_sol=round(true_nav_sol, 8),
            dex_spot_price_sol=round(effective_dex_spot_sol, 8),
            post_arb_dex_price_sol=round(post_arb_dex_price_sol, 8),
            whale_sell_lst_amount=round(whale_sell_lst_amount, 6),
            is_epoch_boundary=is_epoch_boundary,
            epoch_duration_hours=SOLANA_EPOCH_DURATION_HOURS,
            epoch_reward_step_up_bps=round(effective_epoch_step_bps, 4),
            spread_bps=round(spread_bps, 4),
            sanctum_fee_bps=round(effective_sanctum_fee_bps, 4),
            dex_fee_bps=round(effective_dex_fee_bps, 4),
            kamino_flash_fee_bps=round(effective_kamino_fee_bps, 4),
            combined_fee_threshold_bps=round(combined_fee_threshold_bps, 4),
            net_edge_above_fees_bps=round(net_edge_above_fees_bps, 4),
            optimal_flash_borrow_sol=optimal_flash_borrow_sol,
            executed_flash_borrow_sol=round(executed_borrow_sol, 6),
            dex_lst_acquired=round(dex_lst_acquired, 6),
            sanctum_sol_redeemed=round(sanctum_sol_redeemed, 6),
            kamino_flash_fee_sol=round(kamino_flash_fee_sol, 8),
            kamino_repay_total_sol=round(kamino_repay_total_sol, 6),
            dex_fee_paid_sol=round(dex_fee_paid_sol, 8),
            sanctum_fee_paid_sol=round(sanctum_fee_paid_sol, 8),
            base_tx_fee_sol=round(base_tx_fee_sol, 8),
            jito_tip_sol=0.0,
            gross_profit_sol=round(max(0.0, gross_profit_sol), 8),
            net_profit_sol=0.0,
            net_profit_lamports=0,
            directional_memecoin_risk=0.0,
            atomic_instruction_sequence=list(CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE),
            instruction_breakdown=[],
            write_locked_accounts=write_locked_accounts,
            read_only_accounts=read_only_accounts,
            estimated_compute_units=185_000,
        )

    tip_fraction = min(0.90, max(0.0, jito_tip_share_bps / BPS_DENOMINATOR))
    distributable_profit_sol = gross_profit_sol - base_tx_fee_sol
    jito_tip_sol = distributable_profit_sol * tip_fraction
    net_profit_sol = distributable_profit_sol - jito_tip_sol
    net_profit_lamports = int(round(net_profit_sol * LAMPORTS_PER_SOL))

    instruction_breakdown = [
        SanctumFlashInstructionStep(
            ix_index=0,
            instruction_label=CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE[0],
            program_id=KAMINO_LENDING_PROGRAM_ID,
            input_asset="SOL",
            output_asset="SOL",
            input_amount=round(executed_borrow_sol, 6),
            output_amount=round(executed_borrow_sol, 6),
            fee_bps=effective_kamino_fee_bps,
            fee_amount_sol_equiv=round(kamino_flash_fee_sol, 8),
        ),
        SanctumFlashInstructionStep(
            ix_index=1,
            instruction_label=CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE[1],
            program_id=dex_prog_id,
            input_asset="SOL",
            output_asset=canonical_lst,
            input_amount=round(executed_borrow_sol, 6),
            output_amount=round(dex_lst_acquired, 6),
            fee_bps=effective_dex_fee_bps,
            fee_amount_sol_equiv=round(dex_fee_paid_sol, 8),
        ),
        SanctumFlashInstructionStep(
            ix_index=2,
            instruction_label=CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE[2],
            program_id=sanctum_prog_id,
            input_asset=canonical_lst,
            output_asset="SOL",
            input_amount=round(dex_lst_acquired, 6),
            output_amount=round(sanctum_sol_redeemed, 6),
            fee_bps=effective_sanctum_fee_bps,
            fee_amount_sol_equiv=round(sanctum_fee_paid_sol, 8),
        ),
        SanctumFlashInstructionStep(
            ix_index=3,
            instruction_label=CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE[3],
            program_id=KAMINO_LENDING_PROGRAM_ID,
            input_asset="SOL",
            output_asset="SOL",
            input_amount=round(kamino_repay_total_sol, 6),
            output_amount=round(kamino_repay_total_sol, 6),
            fee_bps=effective_kamino_fee_bps,
            fee_amount_sol_equiv=round(kamino_flash_fee_sol, 8),
        ),
    ]

    return SanctumLstFlashArbitrageResult(
        triggered=True,
        decision=DECISION_EXECUTE_SANCTUM_LST_FLASH_ARB,
        trigger_type=trigger_type,
        whale_depeg_trigger_detected=whale_depeg_detected,
        epoch_boundary_trigger_detected=epoch_trigger_detected,
        lst_symbol=canonical_lst,
        lst_mint=lst_meta.mint,
        sanctum_infinity_mint=SANCTUM_INFINITY_POOL_MINT,
        dex_venue=venue_normalized,
        dex_program_id=dex_prog_id,
        sanctum_redemption_route=route_normalized,
        sanctum_program_id=sanctum_prog_id,
        kamino_program_id=KAMINO_LENDING_PROGRAM_ID,
        pre_event_nav_price_sol=round(pre_event_nav_sol, 8),
        nav_price_sol=round(true_nav_sol, 8),
        dex_spot_price_sol=round(effective_dex_spot_sol, 8),
        post_arb_dex_price_sol=round(post_arb_dex_price_sol, 8),
        whale_sell_lst_amount=round(whale_sell_lst_amount, 6),
        is_epoch_boundary=is_epoch_boundary,
        epoch_duration_hours=SOLANA_EPOCH_DURATION_HOURS,
        epoch_reward_step_up_bps=round(effective_epoch_step_bps, 4),
        spread_bps=round(spread_bps, 4),
        sanctum_fee_bps=round(effective_sanctum_fee_bps, 4),
        dex_fee_bps=round(effective_dex_fee_bps, 4),
        kamino_flash_fee_bps=round(effective_kamino_fee_bps, 4),
        combined_fee_threshold_bps=round(combined_fee_threshold_bps, 4),
        net_edge_above_fees_bps=round(net_edge_above_fees_bps, 4),
        optimal_flash_borrow_sol=optimal_flash_borrow_sol,
        executed_flash_borrow_sol=round(executed_borrow_sol, 6),
        dex_lst_acquired=round(dex_lst_acquired, 6),
        sanctum_sol_redeemed=round(sanctum_sol_redeemed, 6),
        kamino_flash_fee_sol=round(kamino_flash_fee_sol, 8),
        kamino_repay_total_sol=round(kamino_repay_total_sol, 6),
        dex_fee_paid_sol=round(dex_fee_paid_sol, 8),
        sanctum_fee_paid_sol=round(sanctum_fee_paid_sol, 8),
        base_tx_fee_sol=round(base_tx_fee_sol, 8),
        jito_tip_sol=round(jito_tip_sol, 8),
        gross_profit_sol=round(gross_profit_sol, 8),
        net_profit_sol=round(net_profit_sol, 8),
        net_profit_lamports=net_profit_lamports,
        directional_memecoin_risk=0.0,
        atomic_instruction_sequence=list(CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE),
        instruction_breakdown=instruction_breakdown,
        write_locked_accounts=write_locked_accounts,
        read_only_accounts=read_only_accounts,
        estimated_compute_units=185_000,
    )


# ============================================================================
# Pillar 2 Implementation: `pack_5tx_super_bundle`
# ============================================================================


def _coerce_tx_spec(
    raw_tx: Union[BundleTransactionSpec, Mapping[str, Any]],
    *,
    default_id_prefix: str = "tx",
    idx: int = 0,
) -> BundleTransactionSpec:
    """Coerces a `BundleTransactionSpec` or dict into a normalized `BundleTransactionSpec`."""
    if isinstance(raw_tx, BundleTransactionSpec):
        cu = int(raw_tx.compute_units)
        tip_lamports = (
            int(raw_tx.tip_contribution_lamports)
            if raw_tx.tip_contribution_lamports > 0
            else int(round(raw_tx.tip_contribution_sol * LAMPORTS_PER_SOL))
        )
        tip_sol = tip_lamports / LAMPORTS_PER_SOL
        eff = tip_lamports / max(1, cu)
        return BundleTransactionSpec(
            tx_id=str(raw_tx.tx_id),
            opportunity_type=str(raw_tx.opportunity_type),
            compute_units=cu,
            gross_profit_sol=float(raw_tx.gross_profit_sol),
            tip_contribution_sol=round(tip_sol, 9),
            tip_contribution_lamports=tip_lamports,
            write_locked_accounts=list(raw_tx.write_locked_accounts),
            read_only_accounts=list(raw_tx.read_only_accounts),
            instructions=list(raw_tx.instructions),
            bundle_index=raw_tx.bundle_index,
            has_jitodontfront=bool(raw_tx.has_jitodontfront),
            has_jito_tip_ix=bool(raw_tx.has_jito_tip_ix),
            aggregated_tip_lamports_on_tx=int(raw_tx.aggregated_tip_lamports_on_tx),
            efficiency_tip_per_cu=round(eff, 4),
        )

    tx_id = str(raw_tx.get("tx_id", f"{default_id_prefix}_{idx}"))
    opp_type = str(raw_tx.get("opportunity_type", "MICRO_ARBITRAGE"))
    cu = int(raw_tx.get("compute_units", 60_000))
    gross_sol = float(raw_tx.get("gross_profit_sol", 0.01))

    if "tip_contribution_lamports" in raw_tx and raw_tx["tip_contribution_lamports"] is not None:
        tip_lamports = int(raw_tx["tip_contribution_lamports"])
        tip_sol = tip_lamports / LAMPORTS_PER_SOL
    elif "tip_contribution_sol" in raw_tx and raw_tx["tip_contribution_sol"] is not None:
        tip_sol = float(raw_tx["tip_contribution_sol"])
        tip_lamports = int(round(tip_sol * LAMPORTS_PER_SOL))
    else:
        tip_sol = round(gross_sol * 0.25, 9)
        tip_lamports = int(round(tip_sol * LAMPORTS_PER_SOL))

    write_locks = [str(acct) for acct in raw_tx.get("write_locked_accounts", [])]
    read_locks = [str(acct) for acct in raw_tx.get("read_only_accounts", [])]
    instructions = [str(ix) for ix in raw_tx.get("instructions", [])]
    if not instructions:
        instructions = [f"Execute::{opp_type}::{tx_id}"]

    eff = tip_lamports / max(1, cu)
    return BundleTransactionSpec(
        tx_id=tx_id,
        opportunity_type=opp_type,
        compute_units=cu,
        gross_profit_sol=gross_sol,
        tip_contribution_sol=round(tip_sol, 9),
        tip_contribution_lamports=tip_lamports,
        write_locked_accounts=write_locks,
        read_only_accounts=read_locks,
        instructions=instructions,
        bundle_index=None,
        has_jitodontfront=JITODONTFRONT_PUBKEY in read_locks,
        has_jito_tip_ix=False,
        aggregated_tip_lamports_on_tx=0,
        efficiency_tip_per_cu=round(eff, 4),
    )


def build_default_primary_transactions() -> List[BundleTransactionSpec]:
    """Constructs a canonical high-priority primary transaction (`Tx[0]`) representing
    a Sanctum LST Kamino Flash Arbitrage execution.
    """
    return [
        BundleTransactionSpec(
            tx_id="primary_tx0_sanctum_lst_flash_arb",
            opportunity_type="PRIMARY_SANCTUM_LST_FLASH_ARB",
            compute_units=220_000,
            gross_profit_sol=0.085,
            tip_contribution_sol=0.0154,
            tip_contribution_lamports=15_400_000,  # 70.0 lamports/CU baseline
            write_locked_accounts=[
                "KaminoSOLReserveVault::KLend2g3",
                "DEXPool::ORCA_WHIRLPOOL::jitoSOL_SOL",
                "SanctumPool::SANCTUM_INFINITY_SWAP_VIA_STAKE::jitoSOL",
                "SearcherWSOLTokenAccount::Primary",
                "SearcherLSTTokenAccount::jitoSOL",
            ],
            read_only_accounts=[
                JITODONTFRONT_PUBKEY,
                KAMINO_LENDING_PROGRAM_ID,
                SANCTUM_INFINITY_CONTROLLER_PROGRAM_ID,
                SANCTUM_INFINITY_POOL_MINT,
            ],
            instructions=list(CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE),
            efficiency_tip_per_cu=70.0,
        )
    ]


def build_default_secondary_candidates() -> List[BundleTransactionSpec]:
    """Constructs a canonical queue of candidate secondary opportunities including
    SPL `CloseAccount` rent reclaims, permissionless crank bounties, micro-arbitrages,
    and an intentionally colliding candidate to verify write-lock filtering.
    """
    return [
        # 1. Batch SPL Token CloseAccount Rent Reclaim (5 empty ATAs = 5 * 0.00203928 SOL = 0.0101964 SOL)
        BundleTransactionSpec(
            tx_id="sec_cand_1_spl_close_account_rent_reclaim",
            opportunity_type="SPL_CLOSE_ACCOUNT_RENT_RECLAIM",
            compute_units=22_000,
            gross_profit_sol=0.0101964,
            tip_contribution_sol=0.0044,
            tip_contribution_lamports=4_400_000,  # 200.0 lamports/CU
            write_locked_accounts=[
                "DormantATA_1::EmptyTokenAccount",
                "DormantATA_2::EmptyTokenAccount",
                "DormantATA_3::EmptyTokenAccount",
                "DormantATA_4::EmptyTokenAccount",
                "DormantATA_5::EmptyTokenAccount",
                "SearcherRentDestinationWallet",
            ],
            read_only_accounts=["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],
            instructions=[
                "SPLToken::CloseAccount(DormantATA_1..5 -> SearcherRentDestinationWallet)"
            ],
            efficiency_tip_per_cu=200.0,
        ),
        # 2. Permissionless Crank Bounty (OpenBook / Phoenix / Kamino liquidation fee crank)
        BundleTransactionSpec(
            tx_id="sec_cand_2_permissionless_crank_bounty",
            opportunity_type="PERMISSIONLESS_CRANK_BOUNTY",
            compute_units=38_000,
            gross_profit_sol=0.0145,
            tip_contribution_sol=0.00684,
            tip_contribution_lamports=6_840_000,  # 180.0 lamports/CU
            write_locked_accounts=[
                "PhoenixMarketCrankState::SOL_USDC",
                "PhoenixFeeSweepVault::USDC",
                "SearcherCrankRewardATA::SOL",
            ],
            read_only_accounts=["PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY"],
            instructions=["Phoenix::ConsumeEventsPermissionlessCrankBounty"],
            efficiency_tip_per_cu=180.0,
        ),
        # 3. Colliding Candidate (shares DEXPool::ORCA_WHIRLPOOL::jitoSOL_SOL write lock with Tx[0])
        BundleTransactionSpec(
            tx_id="sec_cand_3_colliding_jitosol_pool_arb",
            opportunity_type="MICRO_ARBITRAGE",
            compute_units=50_000,
            gross_profit_sol=0.018,
            tip_contribution_sol=0.009,
            tip_contribution_lamports=9_000_000,  # 180.0 lamports/CU, but collides on write-lock!
            write_locked_accounts=[
                "DEXPool::ORCA_WHIRLPOOL::jitoSOL_SOL",
                "SearcherAuxWSOLAccount",
            ],
            read_only_accounts=[DEX_VENUE_PROGRAM_IDS["ORCA_WHIRLPOOL"]],
            instructions=["OrcaWhirlpool::TwoHopSwap(CollidingLock)"],
            efficiency_tip_per_cu=180.0,
        ),
        # 4. Disjoint Micro-Arbitrage across mSOL / bSOL Meteora DLMM
        BundleTransactionSpec(
            tx_id="sec_cand_4_meteora_msol_bsol_micro_arb",
            opportunity_type="MICRO_ARBITRAGE",
            compute_units=65_000,
            gross_profit_sol=0.0195,
            tip_contribution_sol=0.0091,
            tip_contribution_lamports=9_100_000,  # 140.0 lamports/CU
            write_locked_accounts=[
                "DEXPool::METEORA_DLMM::mSOL_bSOL",
                "SanctumPool::INF_mSOL_Reserve",
                "SearcherMicroArbATA::mSOL",
                "SearcherMicroArbATA::bSOL",
            ],
            read_only_accounts=[
                DEX_VENUE_PROGRAM_IDS["METEORA_DLMM"],
                SANCTUM_INFINITY_CONTROLLER_PROGRAM_ID,
            ],
            instructions=[
                "MeteoraDLMM::Swap(mSOL->bSOL)",
                "SanctumInfinity::SwapExactIn(bSOL->mSOL)",
            ],
            efficiency_tip_per_cu=140.0,
        ),
        # 5. Disjoint Secondary Permissionless Sanctum Unstake Reserve Crank + ATA Reclaim
        BundleTransactionSpec(
            tx_id="sec_cand_5_sanctum_epoch_stake_rebalance_crank",
            opportunity_type="PERMISSIONLESS_CRANK_BOUNTY",
            compute_units=45_000,
            gross_profit_sol=0.0128,
            tip_contribution_sol=0.00585,
            tip_contribution_lamports=5_850_000,  # 130.0 lamports/CU
            write_locked_accounts=[
                "SanctumEpochRebalanceState::jupsol",
                "SearcherBountyVault::jupsol",
            ],
            read_only_accounts=[SANCTUM_ROUTER_PROGRAM_ID],
            instructions=["SanctumRouter::CrankInactiveStakeAccountBounty"],
            efficiency_tip_per_cu=130.0,
        ),
        # 6. Extra candidate beyond the 5-tx cap to verify slot cap enforcement
        BundleTransactionSpec(
            tx_id="sec_cand_6_raydium_bonksol_micro_arb",
            opportunity_type="MICRO_ARBITRAGE",
            compute_units=70_000,
            gross_profit_sol=0.0095,
            tip_contribution_sol=0.0035,
            tip_contribution_lamports=3_500_000,  # 50.0 lamports/CU
            write_locked_accounts=[
                "DEXPool::RAYDIUM_CLMM::bonkSOL_SOL",
                "SearcherMicroArbATA::bonkSOL",
            ],
            read_only_accounts=[DEX_VENUE_PROGRAM_IDS["RAYDIUM_CLMM"]],
            instructions=["RaydiumCLMM::Swap(SOL->bonkSOL)"],
            efficiency_tip_per_cu=50.0,
        ),
    ]


def pack_5tx_super_bundle(
    primary_transactions: Optional[
        Sequence[Union[BundleTransactionSpec, Mapping[str, Any]]]
    ] = None,
    secondary_candidates: Optional[
        Sequence[Union[BundleTransactionSpec, Mapping[str, Any]]]
    ] = None,
    *,
    max_bundle_txs: int = MAX_JITO_BUNDLE_TX_COUNT,
    max_bundle_cu: int = MAX_JITO_BUNDLE_CU_LIMIT,
    jito_tip_recipient: Optional[str] = None,
    enforce_jitodontfront_tx0: bool = True,
    require_tip_per_cu_improvement: bool = False,
) -> JitoSuperBundlePackResult:
    """Packs a primary high-priority transaction/bundle (`Tx[0..p-1]`, typically 1–2 txs)
    and a queue of candidate secondary opportunities (micro-arbitrages, SPL token
    `CloseAccount` rent reclaims, and permissionless crank bounties) into a single
    atomic **5-Transaction Jito Super-Bundle (`Tx[0..4]`)**.

    Enforces:
        1. **Disjoint Write-Locked Accounts**: No two packed transactions may share any
           account in `write_locked_accounts`.
        2. **Total Compute Units Ceiling**: $\\sum_{i=0}^{k-1} \\text{CU}_i \\le 1,400,000$.
        3. **Maximum Bundle Length**: $k \\le 5$ (`Tx[0..4]`).
        4. **Strict `jitodontfront` Preservation**: `jitodontfront` pubkey is guaranteed
           in `Tx[0].read_only_accounts`.
        5. **Single Aggregated Jito Tip Transfer**: All individual tips are stripped from
           `Tx[0..k-2]` and aggregated into a single Jito tip instruction placed as the
           **final instruction of the final transaction (`Tx[k-1]`)**.
    """
    effective_max_txs = min(MAX_JITO_BUNDLE_TX_COUNT, max(1, int(max_bundle_txs)))
    effective_max_cu = min(MAX_JITO_BUNDLE_CU_LIMIT, max(10_000, int(max_bundle_cu)))
    selected_tip_account = (
        jito_tip_recipient
        if jito_tip_recipient is not None
        else JITO_CANONICAL_TIP_ACCOUNTS[0]
    )

    raw_primaries = (
        list(primary_transactions)
        if primary_transactions is not None
        else build_default_primary_transactions()
    )
    if not raw_primaries:
        raise ValueError("primary_transactions must contain at least 1 transaction.")
    if len(raw_primaries) > effective_max_txs:
        raise ValueError(
            f"primary_transactions count ({len(raw_primaries)}) exceeds max_bundle_txs ({effective_max_txs})."
        )

    raw_secondaries = (
        list(secondary_candidates)
        if secondary_candidates is not None
        else build_default_secondary_candidates()
    )

    # 1. Normalize primary transactions and verify primary write-lock disjointness & CU limit
    packed_txs: List[BundleTransactionSpec] = []
    active_write_locks: List[str] = []
    active_write_lock_set: set[str] = set()

    primary_cu = 0
    primary_tip_lamports = 0
    primary_gross_profit_sol = 0.0

    for idx, raw_p in enumerate(raw_primaries):
        spec = _coerce_tx_spec(raw_p, default_id_prefix="primary_tx", idx=idx)
        if spec.compute_units <= 0:
            raise ValueError(f"Primary transaction '{spec.tx_id}' has non-positive CU.")

        # Check write-lock collision among primary txs themselves
        overlap = [acct for acct in spec.write_locked_accounts if acct in active_write_lock_set]
        if overlap:
            raise ValueError(
                f"Primary transactions have internal write-lock collision on accounts: {overlap}"
            )

        for acct in spec.write_locked_accounts:
            if acct not in active_write_lock_set:
                active_write_lock_set.add(acct)
                active_write_locks.append(acct)

        primary_cu += spec.compute_units
        primary_tip_lamports += spec.tip_contribution_lamports
        primary_gross_profit_sol += spec.gross_profit_sol
        packed_txs.append(spec)

    if primary_cu > effective_max_cu:
        raise ValueError(
            f"Primary transactions CU ({primary_cu}) exceeds bundle CU limit ({effective_max_cu})."
        )

    single_opp_tip_per_cu = primary_tip_lamports / max(1, primary_cu)

    # 2. Normalize and rank secondary candidates by Knapsack density (tip_contribution_lamports / compute_units)
    normalized_candidates: List[BundleTransactionSpec] = [
        _coerce_tx_spec(cand, default_id_prefix="sec_cand", idx=i)
        for i, cand in enumerate(raw_secondaries)
    ]

    # Sort descending by efficiency (tip_per_cu), breaking ties by higher total tip_contribution_lamports
    sorted_candidates = sorted(
        normalized_candidates,
        key=lambda c: (c.efficiency_tip_per_cu, c.tip_contribution_lamports),
        reverse=True,
    )

    rejected_candidates: List[RejectedBundleCandidate] = []
    current_bundle_cu = primary_cu
    current_bundle_tip_lamports = primary_tip_lamports
    secondary_gross_profit_sol = 0.0
    write_lock_collisions_detected = 0

    for cand in sorted_candidates:
        if cand.compute_units <= 0 or cand.tip_contribution_lamports <= 0 or cand.gross_profit_sol <= 0.0:
            rejected_candidates.append(
                RejectedBundleCandidate(
                    tx_id=cand.tx_id,
                    opportunity_type=cand.opportunity_type,
                    compute_units=cand.compute_units,
                    tip_contribution_lamports=cand.tip_contribution_lamports,
                    rejection_reason="NON_POSITIVE_CONTRIBUTION",
                    colliding_accounts=[],
                )
            )
            continue

        # Check write-lock compatibility first
        colliding = [
            acct for acct in cand.write_locked_accounts if acct in active_write_lock_set
        ]
        if colliding:
            write_lock_collisions_detected += 1
            rejected_candidates.append(
                RejectedBundleCandidate(
                    tx_id=cand.tx_id,
                    opportunity_type=cand.opportunity_type,
                    compute_units=cand.compute_units,
                    tip_contribution_lamports=cand.tip_contribution_lamports,
                    rejection_reason="WRITE_LOCK_COLLISION",
                    colliding_accounts=colliding,
                )
            )
            continue

        # Check 5-tx bundle slot limit
        if len(packed_txs) >= effective_max_txs:
            rejected_candidates.append(
                RejectedBundleCandidate(
                    tx_id=cand.tx_id,
                    opportunity_type=cand.opportunity_type,
                    compute_units=cand.compute_units,
                    tip_contribution_lamports=cand.tip_contribution_lamports,
                    rejection_reason="BUNDLE_TX_SLOT_LIMIT_REACHED",
                    colliding_accounts=[],
                )
            )
            continue

        # Check 1,400,000 CU ceiling
        if current_bundle_cu + cand.compute_units > effective_max_cu:
            rejected_candidates.append(
                RejectedBundleCandidate(
                    tx_id=cand.tx_id,
                    opportunity_type=cand.opportunity_type,
                    compute_units=cand.compute_units,
                    tip_contribution_lamports=cand.tip_contribution_lamports,
                    rejection_reason="CU_LIMIT_EXCEEDED",
                    colliding_accounts=[],
                )
            )
            continue

        # Optional strict marginal tip/CU filter
        prospective_cu = current_bundle_cu + cand.compute_units
        prospective_tip = current_bundle_tip_lamports + cand.tip_contribution_lamports
        prospective_tip_per_cu = prospective_tip / prospective_cu
        if require_tip_per_cu_improvement and prospective_tip_per_cu < (
            current_bundle_tip_lamports / current_bundle_cu
        ):
            rejected_candidates.append(
                RejectedBundleCandidate(
                    tx_id=cand.tx_id,
                    opportunity_type=cand.opportunity_type,
                    compute_units=cand.compute_units,
                    tip_contribution_lamports=cand.tip_contribution_lamports,
                    rejection_reason="MARGINAL_TIP_PER_CU_DILUTION",
                    colliding_accounts=[],
                )
            )
            continue

        # Pack candidate into the Super-Bundle
        for acct in cand.write_locked_accounts:
            if acct not in active_write_lock_set:
                active_write_lock_set.add(acct)
                active_write_locks.append(acct)

        current_bundle_cu = prospective_cu
        current_bundle_tip_lamports = prospective_tip
        secondary_gross_profit_sol += cand.gross_profit_sol
        packed_txs.append(cand)

    # 3. Finalize bundle indices, jitodontfront on Tx[0], and single aggregated tip on Tx[k-1]
    k = len(packed_txs)
    final_tx_idx = k - 1

    for idx, tx in enumerate(packed_txs):
        tx.bundle_index = idx
        # Strip any pre-existing tip instructions from intermediate transactions
        cleaned_ixs = [
            ix
            for ix in tx.instructions
            if "JitoTipTransferIx" not in ix and "TipTransfer" not in ix
        ]
        if not cleaned_ixs:
            cleaned_ixs = [f"Execute::{tx.opportunity_type}::{tx.tx_id}"]

        if idx == 0 and enforce_jitodontfront_tx0:
            if JITODONTFRONT_PUBKEY not in tx.read_only_accounts:
                tx.read_only_accounts.insert(0, JITODONTFRONT_PUBKEY)
            tx.has_jitodontfront = True
        else:
            tx.has_jitodontfront = JITODONTFRONT_PUBKEY in tx.read_only_accounts

        if idx == final_tx_idx:
            cleaned_ixs.append(FINAL_AGGREGATED_JITO_TIP_IX_LABEL)
            tx.has_jito_tip_ix = True
            tx.aggregated_tip_lamports_on_tx = current_bundle_tip_lamports
        else:
            tx.has_jito_tip_ix = False
            tx.aggregated_tip_lamports_on_tx = 0

        tx.instructions = cleaned_ixs

    # 4. Verify disjointness and tip invariants across final packed bundle
    seen_locks: set[str] = set()
    disjoint_verified = True
    for tx in packed_txs:
        for acct in tx.write_locked_accounts:
            if acct in seen_locks:
                disjoint_verified = False
            seen_locks.add(acct)

    tx0_has_jitodontfront = (
        len(packed_txs) > 0 and JITODONTFRONT_PUBKEY in packed_txs[0].read_only_accounts
    )
    intermediate_have_no_tip = all(
        not tx.has_jito_tip_ix and tx.aggregated_tip_lamports_on_tx == 0
        for tx in packed_txs[:-1]
    )
    final_tx = packed_txs[final_tx_idx]
    final_ix_str = final_tx.instructions[-1] if final_tx.instructions else ""
    final_tx_has_tip = (
        final_tx.has_jito_tip_ix
        and final_tx.aggregated_tip_lamports_on_tx == current_bundle_tip_lamports
        and final_ix_str == FINAL_AGGREGATED_JITO_TIP_IX_LABEL
    )
    single_aggregated_tip_verified = bool(intermediate_have_no_tip and final_tx_has_tip)

    # 5. Compute Knapsack efficiency scores, win-rate boost (+25.0% to +40.0%), and net profit
    super_bundle_tip_per_cu = current_bundle_tip_lamports / max(1, current_bundle_cu)
    tip_per_cu_ratio = super_bundle_tip_per_cu / max(1e-9, single_opp_tip_per_cu)
    tip_per_cu_improvement_pct = (tip_per_cu_ratio - 1.0) * 100.0
    total_tip_ratio = current_bundle_tip_lamports / max(1, primary_tip_lamports)

    secondary_packed_count = k - len(raw_primaries)
    if secondary_packed_count > 0 and current_bundle_tip_lamports > primary_tip_lamports:
        # Stage-2 Jito Block Engine Knapsack win-rate boost scales between +25.0% and +40.0%
        # based on secondary slot utilization and tip-per-CU / total tip amplification.
        slot_fill_factor = min(1.0, secondary_packed_count / max(1, effective_max_txs - len(raw_primaries)))
        efficiency_factor = min(1.0, max(0.0, (tip_per_cu_ratio - 1.0) / 0.85))
        tip_volume_factor = min(1.0, max(0.0, (total_tip_ratio - 1.0) / 1.50))
        composite_score = (
            0.40 * slot_fill_factor + 0.35 * efficiency_factor + 0.25 * tip_volume_factor
        )
        auction_win_rate_boost_pct = round(
            STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT
            + composite_score
            * (
                STAGE2_KNAPSACK_WIN_RATE_BOOST_MAX_PCT
                - STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT
            ),
            2,
        )
        auction_win_rate_boost_pct = min(
            STAGE2_KNAPSACK_WIN_RATE_BOOST_MAX_PCT,
            max(STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT, auction_win_rate_boost_pct),
        )
        decision = DECISION_EXECUTE_5TX_JITO_SUPER_BUNDLE
    else:
        auction_win_rate_boost_pct = 0.0
        decision = DECISION_EXECUTE_PRIMARY_ONLY_BUNDLE

    primary_base_fees_sol = len(raw_primaries) * SOLANA_BASE_TX_SIGNATURE_FEE_SOL
    secondary_base_fees_sol = secondary_packed_count * SOLANA_BASE_TX_SIGNATURE_FEE_SOL
    total_base_tx_fees_sol = k * SOLANA_BASE_TX_SIGNATURE_FEE_SOL

    primary_tip_sol = primary_tip_lamports / LAMPORTS_PER_SOL
    secondary_tip_sol = (
        current_bundle_tip_lamports - primary_tip_lamports
    ) / LAMPORTS_PER_SOL
    aggregated_jito_tip_sol = current_bundle_tip_lamports / LAMPORTS_PER_SOL

    primary_net_profit_sol = (
        primary_gross_profit_sol - primary_tip_sol - primary_base_fees_sol
    )
    secondary_net_profit_sol = (
        secondary_gross_profit_sol - secondary_tip_sol - secondary_base_fees_sol
    )
    combined_gross_profit_sol = primary_gross_profit_sol + secondary_gross_profit_sol
    combined_net_profit_sol = (
        combined_gross_profit_sol - aggregated_jito_tip_sol - total_base_tx_fees_sol
    )

    cu_utilization_pct = (current_bundle_cu / effective_max_cu) * 100.0

    return JitoSuperBundlePackResult(
        packed=True,
        decision=decision,
        bundle_tx_count=k,
        max_bundle_tx_limit=effective_max_txs,
        primary_tx_count=len(raw_primaries),
        secondary_tx_packed_count=secondary_packed_count,
        candidates_evaluated_count=len(normalized_candidates),
        candidates_rejected_count=len(rejected_candidates),
        primary_compute_units=primary_cu,
        total_bundle_compute_units=current_bundle_cu,
        max_bundle_compute_units=effective_max_cu,
        cu_utilization_pct=round(cu_utilization_pct, 2),
        single_opp_tip_lamports=primary_tip_lamports,
        super_bundle_total_tip_lamports=current_bundle_tip_lamports,
        single_opp_tip_per_cu=round(single_opp_tip_per_cu, 4),
        super_bundle_tip_per_cu=round(super_bundle_tip_per_cu, 4),
        tip_per_cu_amplification_ratio=round(tip_per_cu_ratio, 4),
        tip_per_cu_improvement_pct=round(tip_per_cu_improvement_pct, 2),
        auction_win_rate_boost_pct=auction_win_rate_boost_pct,
        primary_net_profit_sol=round(primary_net_profit_sol, 8),
        secondary_net_profit_sol=round(secondary_net_profit_sol, 8),
        combined_gross_profit_sol=round(combined_gross_profit_sol, 8),
        aggregated_jito_tip_sol=round(aggregated_jito_tip_sol, 8),
        total_base_tx_fees_sol=round(total_base_tx_fees_sol, 8),
        combined_net_profit_sol=round(combined_net_profit_sol, 8),
        tx0_has_jitodontfront=tx0_has_jitodontfront,
        jitodontfront_pubkey=JITODONTFRONT_PUBKEY,
        disjoint_write_locks_verified=disjoint_verified,
        write_lock_collision_count=write_lock_collisions_detected,
        single_aggregated_tip_verified=single_aggregated_tip_verified,
        final_tx_index=final_tx_idx,
        final_tx_has_aggregated_tip_ix=final_tx_has_tip,
        final_instruction_of_final_tx=final_ix_str,
        jito_tip_recipient_account=selected_tip_account,
        packed_transactions=packed_txs,
        rejected_candidates=rejected_candidates,
        union_write_locked_accounts=active_write_locks,
    )


# ============================================================================
# Pillar 3: `SanctumLstAndSuperBundleEngine` Facade Class
# ============================================================================


class SanctumLstAndSuperBundleEngine:
    """Production facade for Agent 25 (`sanctum-lst-superbundle-arb`):
    Sanctum LST Depeg & 48h Epoch-Boundary Kamino Flash Arbitrage +
    5-Transaction Jito Super-Bundle Knapsack Combiner.

    Exposes `run_full_sanctum_superbundle_diagnostic()` and `get_telemetry_summary()`
    for `TitanIPCDaemon` (`RUN_SANCTUM_LST_SUPERBUNDLE_SUITE`).
    """

    def __init__(self) -> None:
        self._lst_arb_evaluations: int = 0
        self._lst_arb_triggered_count: int = 0
        self._whale_depeg_triggers: int = 0
        self._epoch_boundary_triggers: int = 0
        self._cumulative_lst_arb_net_profit_sol: float = 0.0
        self._super_bundle_packs: int = 0
        self._super_bundle_5tx_count: int = 0
        self._cumulative_super_bundle_net_profit_sol: float = 0.0
        self._last_auction_win_rate_boost_pct: float = 0.0
        self._last_diagnostic_ts: Optional[float] = None

    def evaluate_sanctum_lst_flash_arbitrage(
        self,
        lst_symbol: str = "jitoSOL",
        **kwargs: Any,
    ) -> SanctumLstFlashArbitrageResult:
        """Evaluates a Sanctum LST flash arbitrage opportunity and updates telemetry."""
        res = evaluate_sanctum_lst_flash_arbitrage(lst_symbol, **kwargs)
        self._lst_arb_evaluations += 1
        if res.triggered:
            self._lst_arb_triggered_count += 1
            if res.whale_depeg_trigger_detected:
                self._whale_depeg_triggers += 1
            if res.epoch_boundary_trigger_detected:
                self._epoch_boundary_triggers += 1
            self._cumulative_lst_arb_net_profit_sol = round(
                self._cumulative_lst_arb_net_profit_sol + res.net_profit_sol, 8
            )
        return res

    def pack_5tx_super_bundle(
        self,
        primary_transactions: Optional[
            Sequence[Union[BundleTransactionSpec, Mapping[str, Any]]]
        ] = None,
        secondary_candidates: Optional[
            Sequence[Union[BundleTransactionSpec, Mapping[str, Any]]]
        ] = None,
        **kwargs: Any,
    ) -> JitoSuperBundlePackResult:
        """Packs a 5-Transaction Jito Super-Bundle and updates telemetry."""
        res = pack_5tx_super_bundle(
            primary_transactions=primary_transactions,
            secondary_candidates=secondary_candidates,
            **kwargs,
        )
        self._super_bundle_packs += 1
        if res.bundle_tx_count == MAX_JITO_BUNDLE_TX_COUNT:
            self._super_bundle_5tx_count += 1
        self._cumulative_super_bundle_net_profit_sol = round(
            self._cumulative_super_bundle_net_profit_sol + res.combined_net_profit_sol, 8
        )
        self._last_auction_win_rate_boost_pct = res.auction_win_rate_boost_pct
        return res

    def run_full_sanctum_superbundle_diagnostic(self) -> Dict[str, Any]:
        """Runs a comprehensive end-to-end verification diagnostic across:
        1. Trigger A (`WHALE_DEX_LST_DEPEG`) on `jitoSOL` via Orca Whirlpool -> Sanctum Infinity Pool.
        2. Trigger B (`EPOCH_BOUNDARY_NAV_STEP_UP`) at the 48-hour Solana Epoch boundary on `INF` / `mSOL`.
        3. Multi-LST coverage across all 8 canonical LSTs (`jitoSOL`, `mSOL`, `bSOL`, `INF`,
           `jupsol`, `bonkSOL`, `hSOL`, `compassSOL`).
        4. 5-Transaction Jito Super-Bundle Knapsack packing (`Tx[0..4]`) combining the primary
           Sanctum LST Flash Arbitrage with disjoint SPL `CloseAccount` rent reclaims,
           permissionless crank bounties, and micro-arbitrages.
        """
        t0 = time.perf_counter()

        # 1. Trigger A: Whale DEX LST Depeg on jitoSOL (Orca Whirlpool -> Sanctum Infinity)
        whale_depeg_res = self.evaluate_sanctum_lst_flash_arbitrage(
            "jitoSOL",
            dex_venue="ORCA_WHIRLPOOL",
            sanctum_redemption_route="SANCTUM_INFINITY_SWAP_VIA_STAKE",
            nav_price_sol=1.1485,
            dex_spot_price_sol=1.1430,  # ~48.1 bps depeg from whale market-sell
            whale_sell_lst_amount=1_850.0,
            is_epoch_boundary=False,
            dex_sol_reserve=25_000.0,
            sanctum_fee_bps=1.0,
            dex_fee_bps=1.0,
            kamino_flash_fee_bps=0.1,
        )

        # 2. Trigger B: 48-Hour Solana Epoch Boundary NAV Step-Up on mSOL (Raydium CLMM -> Sanctum Unstake Reserve)
        epoch_boundary_res = self.evaluate_sanctum_lst_flash_arbitrage(
            "mSOL",
            dex_venue="RAYDIUM_CLMM",
            sanctum_redemption_route="SANCTUM_UNSTAKE_RESERVE",
            nav_price_sol=1.2140,
            is_epoch_boundary=True,
            epoch_reward_step_up_bps=18.5,  # 18.5 bps epoch boundary staking + MEV reward step-up
            dex_sol_reserve=30_000.0,
            sanctum_fee_bps=1.0,
            dex_fee_bps=1.0,
            kamino_flash_fee_bps=0.1,
        )

        # 3. Sweep all 8 canonical LSTs to verify ecosystem readiness
        ecosystem_sweep: Dict[str, Dict[str, Any]] = {}
        for symbol in SUPPORTED_SANCTUM_LSTS:
            meta = SANCTUM_LST_REGISTRY[symbol]
            lst_eval = self.evaluate_sanctum_lst_flash_arbitrage(
                symbol,
                dex_venue="METEORA_DLMM",
                sanctum_redemption_route="SANCTUM_INFINITY_SWAP_VIA_STAKE",
                nav_price_sol=meta.default_nav_sol,
                dex_spot_price_sol=round(meta.default_nav_sol * 0.9965, 8),  # ~35 bps depeg
                whale_sell_lst_amount=950.0,
                dex_sol_reserve=20_000.0,
            )
            ecosystem_sweep[symbol] = {
                "triggered": lst_eval.triggered,
                "mint": lst_eval.lst_mint,
                "spread_bps": lst_eval.spread_bps,
                "optimal_flash_borrow_sol": lst_eval.optimal_flash_borrow_sol,
                "net_profit_sol": lst_eval.net_profit_sol,
                "directional_memecoin_risk": lst_eval.directional_memecoin_risk,
            }

        # 4. Pack the Primary Sanctum LST Flash Arbitrage (`Tx[0]`) + Secondary Candidates into a 5-Tx Jito Super-Bundle
        primary_tx0 = BundleTransactionSpec(
            tx_id="tx0_sanctum_jitosol_flash_arb",
            opportunity_type="PRIMARY_SANCTUM_LST_FLASH_ARB",
            compute_units=whale_depeg_res.estimated_compute_units,
            gross_profit_sol=whale_depeg_res.gross_profit_sol,
            tip_contribution_sol=whale_depeg_res.jito_tip_sol,
            tip_contribution_lamports=int(
                round(whale_depeg_res.jito_tip_sol * LAMPORTS_PER_SOL)
            ),
            write_locked_accounts=list(whale_depeg_res.write_locked_accounts),
            read_only_accounts=list(whale_depeg_res.read_only_accounts),
            instructions=list(whale_depeg_res.atomic_instruction_sequence),
        )
        super_bundle_res = self.pack_5tx_super_bundle(
            primary_transactions=[primary_tx0],
            secondary_candidates=build_default_secondary_candidates(),
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        self._last_diagnostic_ts = time.time()

        return {
            "status": "OK",
            "ipc_action": IPC_ACTION_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE,
            "subsystem": AGENT_25_SUBSYSTEM,
            "agent_id": AGENT_25_ID,
            "diagnostic_latency_ms": latency_ms,
            "whale_depeg_flash_arbitrage": whale_depeg_res.to_dict(),
            "epoch_boundary_flash_arbitrage": epoch_boundary_res.to_dict(),
            "sanctum_8lst_ecosystem_sweep": ecosystem_sweep,
            "jito_5tx_super_bundle": super_bundle_res.to_dict(),
            "telemetry": self.get_telemetry_summary(),
        }

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Returns real-time operational telemetry for `TitanIPCDaemon`."""
        return {
            "engine": "SanctumLstAndSuperBundleEngine",
            "agent_id": AGENT_25_ID,
            "agent_index": AGENT_25_INDEX,
            "ipc_action": IPC_ACTION_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE,
            "sanctum_infinity_pool_mint": SANCTUM_INFINITY_POOL_MINT,
            "supported_lsts": list(SUPPORTED_SANCTUM_LSTS),
            "lst_arb_evaluations": self._lst_arb_evaluations,
            "lst_arb_triggered_count": self._lst_arb_triggered_count,
            "whale_depeg_triggers": self._whale_depeg_triggers,
            "epoch_boundary_triggers": self._epoch_boundary_triggers,
            "cumulative_lst_arb_net_profit_sol": self._cumulative_lst_arb_net_profit_sol,
            "super_bundle_packs": self._super_bundle_packs,
            "super_bundle_5tx_count": self._super_bundle_5tx_count,
            "cumulative_super_bundle_net_profit_sol": self._cumulative_super_bundle_net_profit_sol,
            "last_auction_win_rate_boost_pct": self._last_auction_win_rate_boost_pct,
            "benchmarks": {
                "kamino_flash_loan_fee_bps": KAMINO_FLASH_LOAN_FEE_BPS,
                "kamino_flash_loan_fee_pct": KAMINO_FLASH_LOAN_FEE_PCT,
                "solana_epoch_duration_hours": SOLANA_EPOCH_DURATION_HOURS,
                "max_jito_bundle_tx_count": MAX_JITO_BUNDLE_TX_COUNT,
                "max_jito_bundle_cu_limit": MAX_JITO_BUNDLE_CU_LIMIT,
                "jitodontfront_pubkey": JITODONTFRONT_PUBKEY,
                "stage2_knapsack_win_rate_boost_range_pct": [
                    STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT,
                    STAGE2_KNAPSACK_WIN_RATE_BOOST_MAX_PCT,
                ],
            },
            "last_diagnostic_ts": self._last_diagnostic_ts,
        }


__all__ = [
    "AGENT_25_ID",
    "AGENT_25_INDEX",
    "AGENT_25_SUBSYSTEM",
    "BPS_DENOMINATOR",
    "BundleTransactionSpec",
    "CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE",
    "DECISION_EXECUTE_5TX_JITO_SUPER_BUNDLE",
    "DECISION_EXECUTE_PRIMARY_ONLY_BUNDLE",
    "DECISION_EXECUTE_SANCTUM_LST_FLASH_ARB",
    "DECISION_REJECT_INVALID_SUPER_BUNDLE",
    "DECISION_SKIP_NON_POSITIVE_NET_PROFIT",
    "DECISION_SKIP_NO_DEPEG_OR_EPOCH_STEP_UP",
    "DECISION_SKIP_SPREAD_BELOW_COMBINED_FEES",
    "DEX_VENUE_PROGRAM_IDS",
    "DictLikeModelMixin",
    "FINAL_AGGREGATED_JITO_TIP_IX_LABEL",
    "IPC_ACTION_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE",
    "IPC_COMMAND_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE",
    "JITODONTFRONT_PUBKEY",
    "JITO_CANONICAL_TIP_ACCOUNTS",
    "JITO_TIP_PAYMENT_PROGRAM_ID",
    "JitoSuperBundlePackResult",
    "KAMINO_FLASH_LOAN_FEE_BPS",
    "KAMINO_FLASH_LOAN_FEE_FRACTION",
    "KAMINO_FLASH_LOAN_FEE_PCT",
    "KAMINO_LENDING_PROGRAM_ID",
    "LAMPORTS_PER_SOL",
    "MAX_JITO_BUNDLE_CU_LIMIT",
    "MAX_JITO_BUNDLE_TX_COUNT",
    "RejectedBundleCandidate",
    "SANCTUM_INFINITY_CONTROLLER_PROGRAM_ID",
    "SANCTUM_INFINITY_POOL_MINT",
    "SANCTUM_INFINITY_POOL_SYMBOL",
    "SANCTUM_LST_REGISTRY",
    "SANCTUM_ROUTER_PROGRAM_ID",
    "SANCTUM_UNSTAKE_RESERVE_POOL_PUBKEY",
    "SECONDARY_OPPORTUNITY_TYPES",
    "SOLANA_BASE_TX_SIGNATURE_FEE_SOL",
    "SOLANA_EPOCH_DURATION_HOURS",
    "SOLANA_EPOCH_DURATION_SECONDS",
    "SOLANA_SLOTS_PER_EPOCH",
    "STAGE2_KNAPSACK_WIN_RATE_BOOST_MAX_PCT",
    "STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT",
    "SUPPORTED_LST_DEX_VENUES",
    "SUPPORTED_SANCTUM_LSTS",
    "SUPPORTED_SANCTUM_REDEMPTION_ROUTES",
    "SanctumFlashInstructionStep",
    "SanctumLstAndSuperBundleEngine",
    "SanctumLstFlashArbitrageResult",
    "SanctumLstMetadata",
    "TRIGGER_DUAL_WHALE_DEPEG_AND_EPOCH_STEP_UP",
    "TRIGGER_EPOCH_BOUNDARY_NAV_STEP_UP",
    "TRIGGER_NONE",
    "TRIGGER_WHALE_DEX_LST_DEPEG",
    "build_default_primary_transactions",
    "build_default_secondary_candidates",
    "compute_optimal_kamino_flash_principal_sol",
    "evaluate_sanctum_lst_flash_arbitrage",
    "normalize_sanctum_lst_symbol",
    "pack_5tx_super_bundle",
]
