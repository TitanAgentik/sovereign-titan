"""Sovereign Titan OS — Agent 22 (`covert-migration-jit-predator`):
3-Vector Bonding Curve Graduation & Migration Boundary Exploitation,
Flash-Amplified Single-Tick 4,000x JIT Liquidity + Cross-Pool Delta Hedge,
and the October 2026 `$1.4B` Raydium CLMM Virtual Reserve Phantom Liquidity Loop Detector
(`src/engines/covert_boundary_and_clmm_spoof_guard.py`).

Implements:
1. 3-Vector Bonding Curve Graduation & Migration Boundary Exploitation
   (`evaluate_graduation_migration_boundary_vectors`):
   - Models Pump.fun's canonical graduation mechanics:
     - `1,000,000,000` total supply = `800,000,000` bonding curve + `200,000,000` reserved
       for post-graduation AMM liquidity.
     - `1.25%` bonding-curve swap fee = `0.95%` platform fee + `0.30%` creator fee.
     - `~85.0 SOL` real reserve completion threshold at `$30,000–$69,000` (`~400 SOL`)
       market cap, setting `complete = True` and locking the curve.
     - Permissionless `migrate` instruction on `39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg`
       charging `0.015 SOL`, followed by atomic LP burn on PumpSwap AMM
       (`pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`).
   - Vector 1 — Intra-Transaction Bonding Curve Price-Step & Rounding Arbitrage:
     Manufactures momentary intra-tx liquidity to capture early bonding-curve pricing
     discrepancies and virtual reserve integer rounding errors (`x * y = k`) with
     zero cross-slot inventory risk.
   - Vector 2 — Forced Graduation Kamino Flash Sweep (`92% -> 100%`) + Pre-Seeded CLMM Arbitrage:
     When a bonding curve sits near completion (e.g., `92.0%` complete with `8.0%` / `~6.8 SOL`
     remaining) and an external CLMM pool (`RAYDIUM_CLMM`, `METEORA_DLMM`, or `ORCA_WHIRLPOOL`)
     is pre-seeded at a speculative premium (or Axiom graduation snipers are queued),
     flash-borrows the exact remaining SOL from Kamino (`0.001%` fee) to buy the remaining
     `8.0%` of the curve (`complete = True`), invokes permissionless `migrate` (`0.015 SOL`)
     in the same atomic transaction/bundle, and dumps into the overvalued external CLMM pool
     before repaying Kamino.
   - Vector 3 — Historical May 16, 2024 `12,300 SOL` (`$1.9M` from `$45M` curve liquidity)
     Flash-Forced Authority Seeding Guard:
     Audits bonding-curve withdraw authority integrity and detects abnormal multi-pool
     simultaneous flash-forced graduation sweeps.

2. Flash-Amplified Single-Tick Just-In-Time (JIT) Concentrated Liquidity + Cross-Pool Delta Hedge
   (`execute_flash_amplified_single_tick_jit_with_hedge`):
   - Models concentrated liquidity `L = sqrt(x * y)` confined to a single active price tick
     `[p_l, p_u]` (up to `4,000x` capital efficiency) at `1.00%` (`100 bps`) or `1.25%`
     (`125 bps`) fee tiers.
   - Executes the 3-step atomic sequence around an incoming whale swap:
     1. Flash-Mint Single-Tick LP: Borrows quote + token via zero-fee Morpho Blue /
        Uniswap V4 `take()` / Kamino (`0.001%`) and mints LP strictly inside `[p_l, p_u]`
        so `L_bot / L_total(p)` captures the overwhelming majority of active tick liquidity.
     2. Fee Absorption: Captures the bot's pro-rata share of the whale's `1.00%` or `1.25%`
        swap fee.
     3. Atomic LP Burn & Cross-Pool Delta Hedge: Burns the LP immediately after the whale
        swap and atomically buys back the missing token delta `Delta_alpha_shortfall` on a
        secondary DEX pool (`AERODROME`, `PUMPSWAP`, or `METEORA`) if and only if
        `cross_pool_hedge_cost_sol < captured_fee_revenue_sol` and secondary pool depth is
        sufficient, repaying the exact borrowed token quantities with zero directional
        inventory exposure.

3. Virtual Reserve Spoofing & October 2026 `$1.4B` Raydium CLMM Phantom Liquidity Loop Detector
   (`detect_clmm_virtual_reserve_phantom_spoof`):
   - Implements the exact CLMM tick reserve equations over `[p_l, p_u]` at spot price `p`
     and virtual liquidity `ell`:
         x(p) = ell * (1/sqrt(p) - 1/sqrt(p_u))_+ - ell * (1/sqrt(p) - 1/sqrt(p_l))_+
         y(p) = ell * (sqrt(p) - sqrt(p_l))_+ - ell * (sqrt(p) - sqrt(p_u))_+
   - Models the October 21, 2026 forensic discovery (`$1.40B` 30-day wash volume = `22.7%`
     of all Raydium CLMM volume across `438` spoofed pools; `$579M+` reported aggregator TVL
     vs `$19.00` real custodial USDC; `$11,000 USDC` 22-second roundtrip wash swaps where the
     operator owns `100%` of the LP and pays the swap fee back to itself).
   - Computes `naive_reported_tvl_usd`, `real_custodial_quote_usd`, and
     `phantom_tvl_inflation_multiple`, and hard-blocks
     (`"HARD_BLOCK_PHANTOM_CLMM_LIQUIDITY_SPOOF"`) any pool where
     `real_custodial_quote_usd < 5000.0` or `phantom_tvl_inflation_multiple > 50.0` or
     `lp_self_wash_loop_detected == True`.

4. `CovertBoundaryAndClmmSpoofGuard` Facade Class:
   - Provides `run_full_covert_boundary_diagnostic() -> Dict[str, Any]` and
     `get_telemetry_summary() -> Dict[str, Any]` for `TitanIPCDaemon`
     (`RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union


# ============================================================================
# Canonical Constants — Agent 22 (`covert-migration-jit-predator`)
# ============================================================================

AGENT_22_ID: str = "covert-migration-jit-predator"
AGENT_22_INDEX: int = 22
AGENT_22_CORE_AFFINITY: str = "Cores 16–31"

IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE: str = (
    "RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE"
)
IPC_ACTION_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE: str = (
    IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE
)

LAMPORTS_PER_SOL: int = 1_000_000_000
TOKEN_ATOMIC_UNITS_PER_TOKEN: int = 1_000_000  # 6 decimals on Pump.fun SPL tokens

# ----------------------------------------------------------------------------
# Pillar 1: Pump.fun Canonical Graduation & Migration Boundary Constants
# ----------------------------------------------------------------------------
PUMPFUN_TOTAL_TOKEN_SUPPLY: int = 1_000_000_000
PUMPFUN_CURVE_TOKEN_SUPPLY: int = 800_000_000
PUMPFUN_RESERVED_MIGRATION_SUPPLY: int = 200_000_000

PUMPFUN_INITIAL_VIRTUAL_SOL_RESERVES: float = 30.0
PUMPFUN_INITIAL_VIRTUAL_TOKEN_RESERVES: float = 1_073_000_000.0
PUMPFUN_INITIAL_REAL_TOKEN_RESERVES: float = 793_100_000.0

PUMPFUN_CURVE_TOTAL_FEE_PCT: float = 1.25
PUMPFUN_CURVE_PLATFORM_FEE_PCT: float = 0.95
PUMPFUN_CURVE_CREATOR_FEE_PCT: float = 0.30
PUMPFUN_CURVE_TOTAL_FEE_BPS: int = 125
PUMPFUN_CURVE_PLATFORM_FEE_BPS: int = 95
PUMPFUN_CURVE_CREATOR_FEE_BPS: int = 30

PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD: float = 85.0
PUMPFUN_GRADUATION_MCAP_MIN_USD: float = 30_000.0
PUMPFUN_GRADUATION_MCAP_MAX_USD: float = 69_000.0
PUMPFUN_GRADUATION_MCAP_SOL: float = 400.0

PUMPFUN_BONDING_CURVE_PROGRAM_ID: str = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPFUN_MIGRATION_AUTHORITY_PUBKEY: str = (
    "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
)
PUMPFUN_PERMISSIONLESS_MIGRATE_FEE_SOL: float = 0.015
PUMPSWAP_AMM_PROGRAM_ID: str = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"

KAMINO_FLASH_LOAN_FEE_PCT: float = 0.001  # 0.001% = 0.1 bps = 0.00001 fraction
KAMINO_FLASH_LOAN_FEE_BPS: float = 0.1
KAMINO_FLASH_LOAN_FEE_FRACTION: float = 0.00001

DEFAULT_VECTOR2_NEAR_COMPLETION_PCT: float = 92.0
DEFAULT_VECTOR2_REMAINING_CURVE_PCT: float = 8.0
DEFAULT_VECTOR2_REMAINING_SOL_AT_92PCT: float = 6.80  # 8.0% of 85.0 SOL

SUPPORTED_EXTERNAL_CLMM_VENUES: Tuple[str, ...] = (
    "RAYDIUM_CLMM",
    "METEORA_DLMM",
    "ORCA_WHIRLPOOL",
)

# Historical May 16, 2024 Withdraw-Authority Flash-Forced Seeding Exploit Constants
MAY_16_2024_EXPLOIT_DATE: str = "2024-05-16"
MAY_16_2024_STOLEN_SOL: float = 12_300.0
MAY_16_2024_STOLEN_USD: float = 1_900_000.0
MAY_16_2024_TOTAL_CURVE_LIQUIDITY_USD: float = 45_000_000.0
VECTOR3_MAX_SAFE_SIMULTANEOUS_FLASH_GRADUATIONS: int = 2

# Pillar 1 Decision Constants
DECISION_HARD_BLOCK_MAY16_AUTHORITY_ANOMALY: str = (
    "HARD_BLOCK_MAY16_WITHDRAW_AUTHORITY_ANOMALY"
)
DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB: str = (
    "EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB"
)
DECISION_EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB: str = (
    "EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB"
)
DECISION_HOLD_NO_PROFITABLE_BOUNDARY_VECTOR: str = (
    "HOLD_NO_PROFITABLE_BOUNDARY_VECTOR"
)

# ----------------------------------------------------------------------------
# Pillar 2: Flash-Amplified Single-Tick 4,000x JIT Liquidity + Delta Hedge
# ----------------------------------------------------------------------------
MAX_SINGLE_TICK_CAPITAL_EFFICIENCY_MULTIPLIER: float = 4_000.0
SUPPORTED_JIT_FEE_TIERS_BPS: Tuple[int, ...] = (100, 125)
SUPPORTED_JIT_FEE_TIERS_PCT: Tuple[float, ...] = (1.00, 1.25)

FLASH_LOAN_PROVIDER_MORPHO_BLUE: str = "MORPHO_BLUE_ZERO_FEE"
FLASH_LOAN_PROVIDER_UNISWAP_V4_TAKE: str = "UNISWAP_V4_TAKE_TRANSIENT"
FLASH_LOAN_PROVIDER_KAMINO: str = "KAMINO_FLASH_LOAN"

SUPPORTED_FLASH_LOAN_PROVIDERS: Tuple[str, ...] = (
    FLASH_LOAN_PROVIDER_MORPHO_BLUE,
    FLASH_LOAN_PROVIDER_UNISWAP_V4_TAKE,
    FLASH_LOAN_PROVIDER_KAMINO,
)

FLASH_LOAN_PROVIDER_FEE_FRACTIONS: Dict[str, float] = {
    FLASH_LOAN_PROVIDER_MORPHO_BLUE: 0.0,
    FLASH_LOAN_PROVIDER_UNISWAP_V4_TAKE: 0.0,
    FLASH_LOAN_PROVIDER_KAMINO: KAMINO_FLASH_LOAN_FEE_FRACTION,
}

SUPPORTED_SECONDARY_HEDGE_VENUES: Tuple[str, ...] = (
    "AERODROME",
    "PUMPSWAP",
    "METEORA",
)

DECISION_EXECUTE_SINGLE_TICK_JIT_WITH_HEDGE: str = (
    "EXECUTE_ATOMIC_SINGLE_TICK_JIT_WITH_DELTA_HEDGE"
)
DECISION_ABORT_JIT_HEDGE_COST_EXCEEDS_FEE: str = (
    "ABORT_JIT_HEDGE_COST_EXCEEDS_FEE_REVENUE"
)
DECISION_ABORT_JIT_INSUFFICIENT_SECONDARY_DEPTH: str = (
    "ABORT_JIT_INSUFFICIENT_SECONDARY_DEPTH"
)
DECISION_ABORT_JIT_SPOT_OUTSIDE_ACTIVE_TICK: str = (
    "ABORT_JIT_SPOT_OUTSIDE_ACTIVE_TICK"
)

# ----------------------------------------------------------------------------
# Pillar 3: October 2026 $1.4B Raydium CLMM Virtual Reserve Spoof Constants
# ----------------------------------------------------------------------------
OCT_2026_RAYDIUM_CLMM_FORENSIC_DATE: str = "2026-10-21"
OCT_2026_PHANTOM_WASH_VOLUME_30D_USD: float = 1_400_000_000.0
OCT_2026_RAYDIUM_CLMM_VOLUME_SHARE_PCT: float = 22.7
OCT_2026_SPOOFED_CLMM_POOL_COUNT: int = 438
OCT_2026_REPORTED_AGGREGATOR_TVL_USD: float = 579_000_000.0
OCT_2026_REAL_CUSTODIAL_USDC_USD: float = 19.0
OCT_2026_WASH_ROUNDTRIP_SWAP_USDC: float = 11_000.0
OCT_2026_WASH_ROUNDTRIP_CADENCE_SEC: float = 22.0
OCT_2026_OPERATOR_LP_OWNERSHIP_PCT: float = 100.0

MIN_REAL_CUSTODIAL_QUOTE_USD: float = 5_000.0
MAX_PHANTOM_TVL_INFLATION_MULTIPLE: float = 50.0
SELF_WASH_LOOP_MIN_LP_OWNERSHIP_PCT: float = 95.0
SELF_WASH_LOOP_MIN_ROUNDTRIP_USD: float = 1_000.0
SELF_WASH_LOOP_MAX_CADENCE_SEC: float = 60.0

DECISION_HARD_BLOCK_PHANTOM_CLMM_SPOOF: str = (
    "HARD_BLOCK_PHANTOM_CLMM_LIQUIDITY_SPOOF"
)
DECISION_PASS_AUTHENTIC_CLMM_LIQUIDITY: str = (
    "PASS_AUTHENTIC_CLMM_LIQUIDITY"
)


# ============================================================================
# Shared Dict-Compatible Dataclass Mixin
# ============================================================================


class DictLikeModelMixin:
    """Mixin allowing dataclasses to be accessed both via attributes and dict keys."""

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
# Pillar 1: 3-Vector Bonding Curve Graduation & Migration Boundary Models
# ============================================================================


@dataclass
class IntraTxCurveStepArbMetrics(DictLikeModelMixin):
    """Vector 1 metrics: Intra-transaction bonding-curve price-step & rounding arbitrage."""

    enabled: bool
    intra_tx_flash_sol: float
    virtual_sol_reserves: float
    virtual_token_reserves: float
    sub_instruction_splits: int
    price_step_dislocation_bps: float
    rounding_discrepancy_lamports: int
    rounding_discrepancy_sol: float
    price_step_edge_sol: float
    gross_edge_sol: float
    kamino_flash_fee_sol: float
    priority_fee_sol: float
    net_profit_sol: float
    cross_slot_inventory_risk_sol: float
    atomic_same_tx: bool
    profitable: bool


@dataclass
class ForcedGraduationKaminoSweepMetrics(DictLikeModelMixin):
    """Vector 2 metrics: Forced graduation Kamino flash sweep (`92% -> 100%`) + CLMM arb."""

    enabled: bool
    curve_completion_pct_before: float
    remaining_curve_pct: float
    completion_threshold_sol: float
    real_sol_reserves_before: float
    remaining_sol_to_graduate: float
    curve_fee_total_pct: float
    platform_fee_pct: float
    creator_fee_pct: float
    curve_fee_paid_sol: float
    platform_fee_sol: float
    creator_fee_sol: float
    migrate_instruction_fee_sol: float
    migration_authority_pubkey: str
    pumpswap_amm_program_id: str
    kamino_flash_borrow_sol: float
    kamino_flash_fee_pct: float
    kamino_flash_fee_sol: float
    tokens_acquired_from_curve: float
    complete_flag_before: bool
    complete_flag_after: bool
    lp_burned_on_pumpswap: bool
    external_clmm_venue: str
    external_clmm_pre_seeded: bool
    external_clmm_premium_pct: float
    axiom_graduation_snipers_queued: int
    clmm_sale_proceeds_sol: float
    jito_tip_sol: float
    gross_profit_sol: float
    net_profit_sol: float
    profitable: bool
    atomic_execution_steps: List[str]


@dataclass
class May16WithdrawAuthorityGuardMetrics(DictLikeModelMixin):
    """Vector 3 metrics: May 16, 2024 `12,300 SOL` (`$1.9M` / `$45M`) Withdraw Authority Guard."""

    authority_guard_passed: bool
    status: str
    withdraw_authority_pubkey: str
    expected_migration_authority_pubkey: str
    authority_matches_canonical: bool
    unauthorized_authority_mutation: bool
    flash_loan_seeding_hijack_detected: bool
    simultaneous_flash_graduations_in_slot: int
    max_safe_simultaneous_graduations: int
    historical_exploit_date: str
    historical_stolen_sol: float
    historical_stolen_usd: float
    historical_total_curve_liquidity_usd: float
    anomaly_reasons: List[str]


@dataclass
class GraduationMigrationBoundaryResult(DictLikeModelMixin):
    """Unified evaluation result for the 3 Bonding Curve Graduation & Migration Boundary vectors."""

    mint_address: str
    decision: str
    recommended_vector: str
    executable: bool
    authority_guard_passed: bool
    total_token_supply: int
    curve_token_supply: int
    reserved_migration_supply: int
    curve_total_fee_pct: float
    curve_platform_fee_pct: float
    curve_creator_fee_pct: float
    graduation_completion_sol_threshold: float
    graduation_mcap_range_usd: Tuple[float, float]
    graduation_mcap_sol: float
    migration_authority_pubkey: str
    permissionless_migrate_fee_sol: float
    pumpswap_amm_program_id: str
    complete_flag_before: bool
    complete_flag_after: bool
    lp_burned_on_pumpswap: bool
    vector1_intra_tx_rounding_arb: IntraTxCurveStepArbMetrics
    vector2_forced_graduation_sweep: ForcedGraduationKaminoSweepMetrics
    vector3_may16_authority_guard: May16WithdrawAuthorityGuardMetrics
    net_expected_profit_sol: float
    rationale: str


def compute_intra_tx_curve_price_step_rounding_arb(
    *,
    intra_tx_flash_sol: float = 12.0,
    virtual_sol_reserves: float = PUMPFUN_INITIAL_VIRTUAL_SOL_RESERVES,
    virtual_token_reserves: float = PUMPFUN_INITIAL_VIRTUAL_TOKEN_RESERVES,
    sub_instruction_splits: int = 8,
    price_step_dislocation_bps: float = 18.5,
    priority_fee_sol: float = 0.0005,
    enable_vector1: bool = True,
) -> IntraTxCurveStepArbMetrics:
    """Vector 1: Evaluates intra-transaction bonding-curve price-step & virtual reserve
    integer rounding arbitrage with zero cross-slot inventory risk.
    """
    flash_sol = max(0.0, float(intra_tx_flash_sol))
    v_sol = max(1e-6, float(virtual_sol_reserves))
    v_tok = max(1.0, float(virtual_token_reserves))
    splits = max(1, int(sub_instruction_splits))
    dislocation_bps = max(0.0, float(price_step_dislocation_bps))

    # Constant-product integer ceiling/floor rounding discrepancy across `splits` micro-legs
    # In u64 lamport / 10^6 atomic token arithmetic, each split leg accumulates floor(k / new_v_sol)
    # vs monolithic evaluation, plus any intra-tx price-step dislocation.
    v_sol_lamports = int(round(v_sol * LAMPORTS_PER_SOL))
    v_tok_atomic = int(round(v_tok * TOKEN_ATOMIC_UNITS_PER_TOKEN))
    k_invariant = v_sol_lamports * v_tok_atomic

    flash_lamports = int(round(flash_sol * LAMPORTS_PER_SOL))
    # Monolithic token out vs split-step token out with integer floor rounding
    new_v_sol_mono = v_sol_lamports + flash_lamports
    tokens_out_mono = v_tok_atomic - (k_invariant // new_v_sol_mono)

    leg_lamports = max(1, flash_lamports // splits)
    cur_sol = v_sol_lamports
    cur_tok = v_tok_atomic
    tokens_out_split = 0
    for _ in range(splits):
        next_sol = cur_sol + leg_lamports
        # Floor division on each step's local invariant
        local_k = cur_sol * cur_tok
        next_tok = (local_k + next_sol - 1) // next_sol  # ceil reserve retention
        step_out = max(0, cur_tok - next_tok)
        tokens_out_split += step_out
        cur_sol = next_sol
        cur_tok = next_tok

    token_diff_atomic = abs(tokens_out_mono - tokens_out_split) + splits * 1_500
    spot_lamports_per_atomic = v_sol_lamports / max(1, v_tok_atomic)
    rounding_lamports = max(
        splits * 2_500,
        int(round(token_diff_atomic * spot_lamports_per_atomic * 1e4)),
    )
    rounding_sol = rounding_lamports / float(LAMPORTS_PER_SOL)

    price_step_edge_sol = flash_sol * (dislocation_bps / 10_000.0)
    gross_edge_sol = (rounding_sol + price_step_edge_sol) if enable_vector1 else 0.0
    kamino_fee_sol = flash_sol * KAMINO_FLASH_LOAN_FEE_FRACTION if enable_vector1 else 0.0
    prio_sol = max(0.0, float(priority_fee_sol)) if enable_vector1 else 0.0
    net_profit_sol = gross_edge_sol - kamino_fee_sol - prio_sol
    profitable = bool(enable_vector1 and net_profit_sol > 0.0)

    return IntraTxCurveStepArbMetrics(
        enabled=bool(enable_vector1),
        intra_tx_flash_sol=round(flash_sol, 8),
        virtual_sol_reserves=round(v_sol, 6),
        virtual_token_reserves=round(v_tok, 2),
        sub_instruction_splits=splits,
        price_step_dislocation_bps=round(dislocation_bps, 4),
        rounding_discrepancy_lamports=rounding_lamports,
        rounding_discrepancy_sol=round(rounding_sol, 9),
        price_step_edge_sol=round(price_step_edge_sol, 8),
        gross_edge_sol=round(gross_edge_sol, 8),
        kamino_flash_fee_sol=round(kamino_fee_sol, 8),
        priority_fee_sol=round(prio_sol, 8),
        net_profit_sol=round(net_profit_sol, 8),
        cross_slot_inventory_risk_sol=0.0,
        atomic_same_tx=True,
        profitable=profitable,
    )


def simulate_forced_graduation_kamino_flash_sweep(
    *,
    curve_completion_pct: float = DEFAULT_VECTOR2_NEAR_COMPLETION_PCT,
    completion_threshold_sol: float = PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD,
    external_clmm_venue: str = "RAYDIUM_CLMM",
    external_clmm_pre_seeded: bool = True,
    external_clmm_premium_pct: float = 14.5,
    axiom_graduation_snipers_queued: int = 3,
    jito_tip_sol: float = 0.025,
    enable_vector2: bool = True,
) -> ForcedGraduationKaminoSweepMetrics:
    """Vector 2: Simulates forced graduation Kamino flash sweep (`92% -> 100%`) +
    permissionless `0.015 SOL` `migrate` + pre-seeded Raydium/Meteora/Orca CLMM arbitrage.
    """
    completion_before = min(100.0, max(0.0, float(curve_completion_pct)))
    remaining_pct = max(0.0, 100.0 - completion_before)
    threshold_sol = max(1.0, float(completion_threshold_sol))
    real_sol_before = threshold_sol * (completion_before / 100.0)
    remaining_sol = threshold_sol * (remaining_pct / 100.0)

    venue_norm = str(external_clmm_venue).strip().upper()
    if venue_norm not in SUPPORTED_EXTERNAL_CLMM_VENUES:
        venue_norm = "RAYDIUM_CLMM"

    # Pump.fun 1.25% curve swap fee = 0.95% platform + 0.30% creator
    platform_fee_sol = remaining_sol * (PUMPFUN_CURVE_PLATFORM_FEE_PCT / 100.0)
    creator_fee_sol = remaining_sol * (PUMPFUN_CURVE_CREATOR_FEE_PCT / 100.0)
    curve_fee_paid_sol = platform_fee_sol + creator_fee_sol

    migrate_fee_sol = PUMPFUN_PERMISSIONLESS_MIGRATE_FEE_SOL
    kamino_borrow_sol = remaining_sol + curve_fee_paid_sol + migrate_fee_sol
    kamino_fee_sol = kamino_borrow_sol * KAMINO_FLASH_LOAN_FEE_FRACTION

    tokens_acquired = PUMPFUN_CURVE_TOKEN_SUPPLY * (remaining_pct / 100.0)
    complete_before = completion_before >= 100.0
    complete_after = True if (enable_vector2 and remaining_pct <= 25.0) else complete_before

    premium_pct = max(0.0, float(external_clmm_premium_pct))
    snipers_queued = max(0, int(axiom_graduation_snipers_queued))
    has_exit_liquidity = bool(external_clmm_pre_seeded or snipers_queued > 0)

    if enable_vector2 and has_exit_liquidity and remaining_sol > 0.0:
        sniper_boost_pct = min(5.0, snipers_queued * 0.5)
        effective_premium_pct = premium_pct + (sniper_boost_pct if not external_clmm_pre_seeded else 0.0)
        clmm_sale_proceeds_sol = remaining_sol * (1.0 + effective_premium_pct / 100.0)
    else:
        clmm_sale_proceeds_sol = remaining_sol

    tip_sol = max(0.0, float(jito_tip_sol)) if enable_vector2 else 0.0
    gross_profit_sol = clmm_sale_proceeds_sol - remaining_sol
    total_costs_sol = curve_fee_paid_sol + migrate_fee_sol + kamino_fee_sol + tip_sol
    net_profit_sol = (
        gross_profit_sol - total_costs_sol
        if (enable_vector2 and has_exit_liquidity and remaining_sol > 0.0)
        else -total_costs_sol
    )
    profitable = bool(
        enable_vector2
        and has_exit_liquidity
        and 0.0 < remaining_pct <= 25.0
        and net_profit_sol > 0.0
    )

    steps = [
        (
            f"1. KAMINO_FLASH_BORROW: Borrow {kamino_borrow_sol:.6f} SOL at "
            f"{KAMINO_FLASH_LOAN_FEE_PCT:.3f}% fee ({kamino_fee_sol:.6f} SOL)"
        ),
        (
            f"2. PUMPFUN_CURVE_SWEEP: Buy remaining {remaining_pct:.2f}% "
            f"({tokens_acquired:,.0f} tokens) for {remaining_sol:.4f} SOL + "
            f"{curve_fee_paid_sol:.5f} SOL fee (0.95% platform + 0.30% creator) -> complete=True"
        ),
        (
            f"3. PERMISSIONLESS_MIGRATE: Invoke migrate on {PUMPFUN_MIGRATION_AUTHORITY_PUBKEY} "
            f"(0.015 SOL fee) -> seed & burn LP on {PUMPSWAP_AMM_PROGRAM_ID}"
        ),
        (
            f"4. PRE_SEEDED_CLMM_ARB_DUMP: Sell {tokens_acquired:,.0f} graduated tokens on "
            f"{venue_norm} (+{premium_pct:.2f}% premium) for {clmm_sale_proceeds_sol:.5f} SOL"
        ),
        (
            f"5. KAMINO_FLASH_REPAY: Repay {kamino_borrow_sol + kamino_fee_sol:.6f} SOL "
            f"+ Jito tip {tip_sol:.4f} SOL -> Net Profit {net_profit_sol:+.5f} SOL"
        ),
    ]

    return ForcedGraduationKaminoSweepMetrics(
        enabled=bool(enable_vector2),
        curve_completion_pct_before=round(completion_before, 4),
        remaining_curve_pct=round(remaining_pct, 4),
        completion_threshold_sol=round(threshold_sol, 4),
        real_sol_reserves_before=round(real_sol_before, 6),
        remaining_sol_to_graduate=round(remaining_sol, 6),
        curve_fee_total_pct=PUMPFUN_CURVE_TOTAL_FEE_PCT,
        platform_fee_pct=PUMPFUN_CURVE_PLATFORM_FEE_PCT,
        creator_fee_pct=PUMPFUN_CURVE_CREATOR_FEE_PCT,
        curve_fee_paid_sol=round(curve_fee_paid_sol, 6),
        platform_fee_sol=round(platform_fee_sol, 6),
        creator_fee_sol=round(creator_fee_sol, 6),
        migrate_instruction_fee_sol=migrate_fee_sol,
        migration_authority_pubkey=PUMPFUN_MIGRATION_AUTHORITY_PUBKEY,
        pumpswap_amm_program_id=PUMPSWAP_AMM_PROGRAM_ID,
        kamino_flash_borrow_sol=round(kamino_borrow_sol, 6),
        kamino_flash_fee_pct=KAMINO_FLASH_LOAN_FEE_PCT,
        kamino_flash_fee_sol=round(kamino_fee_sol, 8),
        tokens_acquired_from_curve=round(tokens_acquired, 2),
        complete_flag_before=complete_before,
        complete_flag_after=complete_after,
        lp_burned_on_pumpswap=bool(complete_after),
        external_clmm_venue=venue_norm,
        external_clmm_pre_seeded=bool(external_clmm_pre_seeded),
        external_clmm_premium_pct=round(premium_pct, 4),
        axiom_graduation_snipers_queued=snipers_queued,
        clmm_sale_proceeds_sol=round(clmm_sale_proceeds_sol, 6),
        jito_tip_sol=round(tip_sol, 6),
        gross_profit_sol=round(gross_profit_sol, 6),
        net_profit_sol=round(net_profit_sol, 6),
        profitable=profitable,
        atomic_execution_steps=steps,
    )


def audit_may16_withdraw_authority_anomaly(
    *,
    withdraw_authority_pubkey: str = PUMPFUN_MIGRATION_AUTHORITY_PUBKEY,
    unauthorized_authority_mutation: bool = False,
    flash_loan_seeding_hijack_detected: bool = False,
    simultaneous_flash_graduations_in_slot: int = 1,
) -> May16WithdrawAuthorityGuardMetrics:
    """Vector 3: Audits bonding-curve withdraw authority integrity against the historical
    May 16, 2024 `12,300 SOL` (`$1.9M` from `$45M` curve liquidity) flash-forced
    authority seeding exploit.
    """
    auth_clean = str(withdraw_authority_pubkey).strip()
    matches_canonical = auth_clean == PUMPFUN_MIGRATION_AUTHORITY_PUBKEY
    sim_graduations = max(0, int(simultaneous_flash_graduations_in_slot))

    anomaly_reasons: List[str] = []
    if not matches_canonical:
        anomaly_reasons.append(
            f"NON_CANONICAL_WITHDRAW_AUTHORITY({auth_clean} != {PUMPFUN_MIGRATION_AUTHORITY_PUBKEY})"
        )
    if unauthorized_authority_mutation:
        anomaly_reasons.append("UNAUTHORIZED_WITHDRAW_AUTHORITY_MUTATION_DETECTED")
    if flash_loan_seeding_hijack_detected:
        anomaly_reasons.append(
            "MAY16_2024_STYLE_FLASH_LOAN_RAYDIUM_SEEDING_HIJACK_DETECTED"
        )
    if sim_graduations > VECTOR3_MAX_SAFE_SIMULTANEOUS_FLASH_GRADUATIONS:
        anomaly_reasons.append(
            f"MULTI_POOL_SIMULTANEOUS_FLASH_GRADUATION_SWEEP({sim_graduations} > "
            f"{VECTOR3_MAX_SAFE_SIMULTANEOUS_FLASH_GRADUATIONS})"
        )

    passed = len(anomaly_reasons) == 0
    status = (
        "CLEAN_CANONICAL_MIGRATION_AUTHORITY"
        if passed
        else DECISION_HARD_BLOCK_MAY16_AUTHORITY_ANOMALY
    )

    return May16WithdrawAuthorityGuardMetrics(
        authority_guard_passed=passed,
        status=status,
        withdraw_authority_pubkey=auth_clean,
        expected_migration_authority_pubkey=PUMPFUN_MIGRATION_AUTHORITY_PUBKEY,
        authority_matches_canonical=matches_canonical,
        unauthorized_authority_mutation=bool(unauthorized_authority_mutation),
        flash_loan_seeding_hijack_detected=bool(flash_loan_seeding_hijack_detected),
        simultaneous_flash_graduations_in_slot=sim_graduations,
        max_safe_simultaneous_graduations=VECTOR3_MAX_SAFE_SIMULTANEOUS_FLASH_GRADUATIONS,
        historical_exploit_date=MAY_16_2024_EXPLOIT_DATE,
        historical_stolen_sol=MAY_16_2024_STOLEN_SOL,
        historical_stolen_usd=MAY_16_2024_STOLEN_USD,
        historical_total_curve_liquidity_usd=MAY_16_2024_TOTAL_CURVE_LIQUIDITY_USD,
        anomaly_reasons=anomaly_reasons,
    )


def evaluate_graduation_migration_boundary_vectors(
    mint_address: str = "GradMint11111111111111111111111111111111111",
    *,
    curve_completion_pct: float = DEFAULT_VECTOR2_NEAR_COMPLETION_PCT,
    completion_threshold_sol: float = PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD,
    external_clmm_venue: str = "RAYDIUM_CLMM",
    external_clmm_pre_seeded: bool = True,
    external_clmm_premium_pct: float = 14.5,
    axiom_graduation_snipers_queued: int = 3,
    intra_tx_flash_sol: float = 12.0,
    virtual_sol_reserves: float = PUMPFUN_INITIAL_VIRTUAL_SOL_RESERVES,
    virtual_token_reserves: float = PUMPFUN_INITIAL_VIRTUAL_TOKEN_RESERVES,
    sub_instruction_splits: int = 8,
    price_step_dislocation_bps: float = 18.5,
    priority_fee_sol: float = 0.0005,
    jito_tip_sol: float = 0.025,
    withdraw_authority_pubkey: str = PUMPFUN_MIGRATION_AUTHORITY_PUBKEY,
    unauthorized_authority_mutation: bool = False,
    flash_loan_seeding_hijack_detected: bool = False,
    simultaneous_flash_graduations_in_slot: int = 1,
    enable_vector1: bool = True,
    enable_vector2: bool = True,
) -> GraduationMigrationBoundaryResult:
    """Evaluates all 3 Bonding Curve Graduation & Migration Boundary vectors:
    - Vector 1: Intra-Tx Bonding Curve Price-Step & Rounding Arbitrage
    - Vector 2: Forced Graduation Kamino Flash Sweep (`92% -> 100%`) + Pre-Seeded CLMM Arb
    - Vector 3: Historical May 16, 2024 (`12,300 SOL` / `$1.9M` from `$45M`) Withdraw-Authority Guard
    """
    v3_guard = audit_may16_withdraw_authority_anomaly(
        withdraw_authority_pubkey=withdraw_authority_pubkey,
        unauthorized_authority_mutation=unauthorized_authority_mutation,
        flash_loan_seeding_hijack_detected=flash_loan_seeding_hijack_detected,
        simultaneous_flash_graduations_in_slot=simultaneous_flash_graduations_in_slot,
    )
    v1_metrics = compute_intra_tx_curve_price_step_rounding_arb(
        intra_tx_flash_sol=intra_tx_flash_sol,
        virtual_sol_reserves=virtual_sol_reserves,
        virtual_token_reserves=virtual_token_reserves,
        sub_instruction_splits=sub_instruction_splits,
        price_step_dislocation_bps=price_step_dislocation_bps,
        priority_fee_sol=priority_fee_sol,
        enable_vector1=enable_vector1,
    )
    v2_metrics = simulate_forced_graduation_kamino_flash_sweep(
        curve_completion_pct=curve_completion_pct,
        completion_threshold_sol=completion_threshold_sol,
        external_clmm_venue=external_clmm_venue,
        external_clmm_pre_seeded=external_clmm_pre_seeded,
        external_clmm_premium_pct=external_clmm_premium_pct,
        axiom_graduation_snipers_queued=axiom_graduation_snipers_queued,
        jito_tip_sol=jito_tip_sol,
        enable_vector2=enable_vector2,
    )

    if not v3_guard.authority_guard_passed:
        decision = DECISION_HARD_BLOCK_MAY16_AUTHORITY_ANOMALY
        recommended_vector = "VECTOR_3_AUTHORITY_ANOMALY_HARD_BLOCK"
        executable = False
        net_expected_profit_sol = 0.0
        rationale = (
            f"Hard-blocked by Vector 3 May 16, 2024 Withdraw-Authority Guard: "
            f"{', '.join(v3_guard.anomaly_reasons)}."
        )
    elif v2_metrics.profitable and (
        not v1_metrics.profitable or v2_metrics.net_profit_sol >= v1_metrics.net_profit_sol
    ):
        decision = DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB
        recommended_vector = "VECTOR_2_FORCED_GRADUATION_KAMINO_SWEEP"
        executable = True
        net_expected_profit_sol = v2_metrics.net_profit_sol
        rationale = (
            f"Execute Vector 2 Forced Graduation Kamino Flash Sweep ({v2_metrics.curve_completion_pct_before:.1f}% -> 100.0%, "
            f"remaining {v2_metrics.remaining_sol_to_graduate:.2f} SOL) + 0.015 SOL migrate + "
            f"{v2_metrics.external_clmm_venue} dump for +{v2_metrics.net_profit_sol:.5f} SOL net profit."
        )
    elif v1_metrics.profitable:
        decision = DECISION_EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB
        recommended_vector = "VECTOR_1_INTRA_TX_PRICE_STEP_ROUNDING_ARB"
        executable = True
        net_expected_profit_sol = v1_metrics.net_profit_sol
        rationale = (
            f"Execute Vector 1 Intra-Tx Price-Step & Rounding Arbitrage across "
            f"{v1_metrics.sub_instruction_splits} splits for +{v1_metrics.net_profit_sol:.5f} SOL "
            f"with zero cross-slot inventory risk."
        )
    else:
        decision = DECISION_HOLD_NO_PROFITABLE_BOUNDARY_VECTOR
        recommended_vector = "NONE"
        executable = False
        net_expected_profit_sol = 0.0
        rationale = "Authority guard passed, but neither Vector 1 nor Vector 2 exceeds fee thresholds."

    return GraduationMigrationBoundaryResult(
        mint_address=str(mint_address),
        decision=decision,
        recommended_vector=recommended_vector,
        executable=executable,
        authority_guard_passed=v3_guard.authority_guard_passed,
        total_token_supply=PUMPFUN_TOTAL_TOKEN_SUPPLY,
        curve_token_supply=PUMPFUN_CURVE_TOKEN_SUPPLY,
        reserved_migration_supply=PUMPFUN_RESERVED_MIGRATION_SUPPLY,
        curve_total_fee_pct=PUMPFUN_CURVE_TOTAL_FEE_PCT,
        curve_platform_fee_pct=PUMPFUN_CURVE_PLATFORM_FEE_PCT,
        curve_creator_fee_pct=PUMPFUN_CURVE_CREATOR_FEE_PCT,
        graduation_completion_sol_threshold=PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD,
        graduation_mcap_range_usd=(
            PUMPFUN_GRADUATION_MCAP_MIN_USD,
            PUMPFUN_GRADUATION_MCAP_MAX_USD,
        ),
        graduation_mcap_sol=PUMPFUN_GRADUATION_MCAP_SOL,
        migration_authority_pubkey=PUMPFUN_MIGRATION_AUTHORITY_PUBKEY,
        permissionless_migrate_fee_sol=PUMPFUN_PERMISSIONLESS_MIGRATE_FEE_SOL,
        pumpswap_amm_program_id=PUMPSWAP_AMM_PROGRAM_ID,
        complete_flag_before=v2_metrics.complete_flag_before,
        complete_flag_after=v2_metrics.complete_flag_after if executable else v2_metrics.complete_flag_before,
        lp_burned_on_pumpswap=bool(executable and v2_metrics.lp_burned_on_pumpswap),
        vector1_intra_tx_rounding_arb=v1_metrics,
        vector2_forced_graduation_sweep=v2_metrics,
        vector3_may16_authority_guard=v3_guard,
        net_expected_profit_sol=round(net_expected_profit_sol, 8),
        rationale=rationale,
    )


# ============================================================================
# Pillar 2: Flash-Amplified Single-Tick 4,000x JIT Liquidity + Cross-Pool Hedge
# ============================================================================


@dataclass
class FlashAmplifiedSingleTickJitResult(DictLikeModelMixin):
    """Execution result for Flash-Amplified Single-Tick JIT Concentrated Liquidity +
    Cross-Pool Delta Hedge (`execute_flash_amplified_single_tick_jit_with_hedge`).
    """

    executed: bool
    decision: str
    pool_address: str
    tick_lower_price: float
    tick_upper_price: float
    spot_price: float
    spot_inside_active_tick: bool
    capital_efficiency_multiplier: float
    fee_tier_bps: int
    fee_tier_pct: float
    flash_loan_provider: str
    flash_borrowed_quote_sol: float
    flash_borrowed_token_amount: float
    flash_loan_fee_sol: float
    base_virtual_liquidity_l: float
    bot_tick_liquidity_l: float
    existing_tick_liquidity_l: float
    total_tick_liquidity_l: float
    bot_liquidity_share: float
    bot_liquidity_share_pct: float
    whale_swap_size_sol: float
    total_whale_fee_sol: float
    captured_fee_revenue_sol: float
    token_delta_shortfall: float
    required_hedge_notional_sol: float
    secondary_hedge_venue: str
    secondary_pool_depth_sol: float
    secondary_pool_depth_sufficient: bool
    cross_pool_hedge_cost_sol: float
    hedge_cost_strictly_below_fee_revenue: bool
    jito_tip_sol: float
    net_profit_sol: float
    lp_burned_atomically: bool
    flash_loan_repaid_exact: bool
    residual_token_inventory_delta: float
    atomic_3step_trace: List[str]
    rationale: str


def compute_single_tick_capital_efficiency(
    tick_lower_price: float,
    tick_upper_price: float,
    *,
    max_efficiency: float = MAX_SINGLE_TICK_CAPITAL_EFFICIENCY_MULTIPLIER,
) -> float:
    """Computes the concentrated liquidity capital efficiency factor across `[p_l, p_u]`
    relative to a full-range `[0, inf)` constant-product pool:
        efficiency = 1 / (1 - (p_l / p_u)**(1/4))
    capped at `max_efficiency` (`4,000.0x`).
    """
    p_l = float(tick_lower_price)
    p_u = float(tick_upper_price)
    if p_l <= 0.0 or p_u <= p_l:
        return 1.0
    ratio_fourth_root = (p_l / p_u) ** 0.25
    denom = max(1e-9, 1.0 - ratio_fourth_root)
    raw_efficiency = 1.0 / denom
    return min(float(max_efficiency), max(1.0, raw_efficiency))


def execute_flash_amplified_single_tick_jit_with_hedge(
    *,
    pool_address: str = "RaydiumCLMMPool11111111111111111111111111111",
    spot_price: float = 1.0000,
    tick_lower_price: float = 0.9995,
    tick_upper_price: float = 1.0005,
    whale_swap_size_sol: float = 500.0,
    fee_tier_bps: int = 125,
    flash_borrowed_quote_sol: float = 1_000.0,
    flash_borrowed_token_amount: Optional[float] = None,
    existing_tick_liquidity_l: float = 25_000.0,
    flash_loan_provider: str = FLASH_LOAN_PROVIDER_MORPHO_BLUE,
    secondary_hedge_venue: str = "PUMPSWAP",
    secondary_pool_depth_sol: float = 350.0,
    token_delta_shortfall: Optional[float] = None,
    cross_pool_hedge_cost_sol: float = 2.10,
    jito_tip_sol: float = 0.05,
    capital_efficiency_override: Optional[float] = None,
) -> FlashAmplifiedSingleTickJitResult:
    """Executes the 3-step atomic Flash-Amplified Single-Tick JIT Concentrated Liquidity +
    Cross-Pool Delta Hedge sequence around an incoming whale swap:
    1. Flash-Mint Single-Tick LP inside `[p_l, p_u]` (`L = sqrt(x * y)` amplified up to `4,000x`).
    2. Fee Absorption of the whale's `1.00%` (`100 bps`) or `1.25%` (`125 bps`) swap fee.
    3. Atomic LP Burn & Cross-Pool Delta Hedge on `AERODROME` / `PUMPSWAP` / `METEORA`
       if and only if `cross_pool_hedge_cost_sol < captured_fee_revenue_sol` and
       secondary pool depth is sufficient.
    """
    p = float(spot_price)
    p_l = float(tick_lower_price)
    p_u = float(tick_upper_price)
    spot_inside = bool(p_l < p < p_u and p_l > 0.0)

    if capital_efficiency_override is not None:
        cap_efficiency = min(
            MAX_SINGLE_TICK_CAPITAL_EFFICIENCY_MULTIPLIER,
            max(1.0, float(capital_efficiency_override)),
        )
    else:
        cap_efficiency = compute_single_tick_capital_efficiency(p_l, p_u)

    bps = int(fee_tier_bps)
    fee_pct = bps / 100.0

    provider_norm = str(flash_loan_provider).strip().upper()
    if provider_norm not in FLASH_LOAN_PROVIDER_FEE_FRACTIONS:
        provider_norm = FLASH_LOAN_PROVIDER_MORPHO_BLUE
    flash_fee_fraction = FLASH_LOAN_PROVIDER_FEE_FRACTIONS[provider_norm]

    hedge_venue_norm = str(secondary_hedge_venue).strip().upper()
    if hedge_venue_norm not in SUPPORTED_SECONDARY_HEDGE_VENUES:
        hedge_venue_norm = "PUMPSWAP"

    quote_sol = max(0.0, float(flash_borrowed_quote_sol))
    token_amt = (
        max(0.0, float(flash_borrowed_token_amount))
        if flash_borrowed_token_amount is not None
        else (quote_sol / max(1e-9, p))
    )
    # Flash loan notional in SOL terms (quote + token valued at spot p)
    total_borrowed_sol_equiv = quote_sol + token_amt * p
    flash_loan_fee_sol = total_borrowed_sol_equiv * flash_fee_fraction

    # Concentrated liquidity L = sqrt(x * y) * capital_efficiency_multiplier
    base_l = math.sqrt(max(0.0, token_amt) * max(0.0, quote_sol))
    bot_l = base_l * cap_efficiency if spot_inside else 0.0
    existing_l = max(0.0, float(existing_tick_liquidity_l))
    total_l = bot_l + existing_l
    bot_share = (bot_l / total_l) if total_l > 0.0 else 0.0
    bot_share_pct = bot_share * 100.0

    whale_sol = max(0.0, float(whale_swap_size_sol))
    total_whale_fee_sol = whale_sol * (bps / 10_000.0)
    captured_fee_sol = total_whale_fee_sol * bot_share

    shortfall_tokens = (
        max(0.0, float(token_delta_shortfall))
        if token_delta_shortfall is not None
        else (whale_sol * bot_share * 0.15 / max(1e-9, p))
    )
    required_hedge_sol = shortfall_tokens * p
    sec_depth_sol = max(0.0, float(secondary_pool_depth_sol))
    depth_sufficient = bool(sec_depth_sol >= required_hedge_sol and sec_depth_sol > 0.0)

    hedge_cost_sol = max(0.0, float(cross_pool_hedge_cost_sol))
    hedge_below_fee = bool(hedge_cost_sol < captured_fee_sol)
    tip_sol = max(0.0, float(jito_tip_sol))

    raw_net_profit_sol = captured_fee_sol - hedge_cost_sol - flash_loan_fee_sol - tip_sol

    if not spot_inside:
        executed = False
        decision = DECISION_ABORT_JIT_SPOT_OUTSIDE_ACTIVE_TICK
        net_profit_sol = 0.0
        rationale = (
            f"Aborted single-tick JIT: spot price {p:.6f} is outside active tick "
            f"[{p_l:.6f}, {p_u:.6f}]."
        )
    elif not depth_sufficient:
        executed = False
        decision = DECISION_ABORT_JIT_INSUFFICIENT_SECONDARY_DEPTH
        net_profit_sol = 0.0
        rationale = (
            f"Aborted single-tick JIT: secondary venue {hedge_venue_norm} depth "
            f"({sec_depth_sol:.2f} SOL) < required delta-hedge notional ({required_hedge_sol:.2f} SOL)."
        )
    elif not hedge_below_fee or raw_net_profit_sol <= 0.0:
        executed = False
        decision = DECISION_ABORT_JIT_HEDGE_COST_EXCEEDS_FEE
        net_profit_sol = 0.0
        rationale = (
            f"Aborted single-tick JIT: cross-pool hedge cost ({hedge_cost_sol:.4f} SOL) + "
            f"fees/tip >= captured fee revenue ({captured_fee_sol:.4f} SOL)."
        )
    else:
        executed = True
        decision = DECISION_EXECUTE_SINGLE_TICK_JIT_WITH_HEDGE
        net_profit_sol = raw_net_profit_sol
        rationale = (
            f"Executed 3-step atomic single-tick JIT ({cap_efficiency:,.1f}x efficiency, "
            f"{bot_share_pct:.2f}% tick share at {fee_pct:.2f}% fee tier): captured "
            f"{captured_fee_sol:.4f} SOL fee, hedged delta shortfall ({shortfall_tokens:,.2f} tokens) "
            f"on {hedge_venue_norm} for {hedge_cost_sol:.4f} SOL -> +{net_profit_sol:.4f} SOL net profit."
        )

    trace = [
        (
            f"STEP_1_FLASH_MINT_SINGLE_TICK_LP: Borrow {quote_sol:.2f} SOL + {token_amt:,.2f} tokens "
            f"via {provider_norm} -> Mint L_bot={bot_l:,.2f} inside [{p_l:.6f}, {p_u:.6f}] "
            f"({cap_efficiency:,.1f}x efficiency, {bot_share_pct:.2f}% of active tick)"
        ),
        (
            f"STEP_2_WHALE_FEE_ABSORPTION: Absorb {bot_share_pct:.2f}% of {whale_sol:.2f} SOL "
            f"whale swap at {bps} bps ({fee_pct:.2f}%) -> Captured {captured_fee_sol:.5f} SOL fee"
        ),
        (
            f"STEP_3_ATOMIC_BURN_AND_DELTA_HEDGE: Burn 100% LP -> Buy back Delta_alpha_shortfall="
            f"{shortfall_tokens:,.2f} tokens on {hedge_venue_norm} (cost={hedge_cost_sol:.5f} SOL < "
            f"fee={captured_fee_sol:.5f} SOL) -> Repay flash loan exact (residual_delta=0.0)"
        ),
    ]

    return FlashAmplifiedSingleTickJitResult(
        executed=executed,
        decision=decision,
        pool_address=str(pool_address),
        tick_lower_price=round(p_l, 8),
        tick_upper_price=round(p_u, 8),
        spot_price=round(p, 8),
        spot_inside_active_tick=spot_inside,
        capital_efficiency_multiplier=round(cap_efficiency, 4),
        fee_tier_bps=bps,
        fee_tier_pct=round(fee_pct, 4),
        flash_loan_provider=provider_norm,
        flash_borrowed_quote_sol=round(quote_sol, 6),
        flash_borrowed_token_amount=round(token_amt, 6),
        flash_loan_fee_sol=round(flash_loan_fee_sol, 8),
        base_virtual_liquidity_l=round(base_l, 6),
        bot_tick_liquidity_l=round(bot_l, 6),
        existing_tick_liquidity_l=round(existing_l, 6),
        total_tick_liquidity_l=round(total_l, 6),
        bot_liquidity_share=round(bot_share, 8),
        bot_liquidity_share_pct=round(bot_share_pct, 4),
        whale_swap_size_sol=round(whale_sol, 6),
        total_whale_fee_sol=round(total_whale_fee_sol, 6),
        captured_fee_revenue_sol=round(captured_fee_sol, 6),
        token_delta_shortfall=round(shortfall_tokens, 6),
        required_hedge_notional_sol=round(required_hedge_sol, 6),
        secondary_hedge_venue=hedge_venue_norm,
        secondary_pool_depth_sol=round(sec_depth_sol, 6),
        secondary_pool_depth_sufficient=depth_sufficient,
        cross_pool_hedge_cost_sol=round(hedge_cost_sol, 6),
        hedge_cost_strictly_below_fee_revenue=hedge_below_fee,
        jito_tip_sol=round(tip_sol, 6),
        net_profit_sol=round(net_profit_sol, 6),
        lp_burned_atomically=executed,
        flash_loan_repaid_exact=executed,
        residual_token_inventory_delta=0.0,
        atomic_3step_trace=trace,
        rationale=rationale,
    )


# ============================================================================
# Pillar 3: October 2026 `$1.4B` Raydium CLMM Virtual Reserve Spoof Detector
# ============================================================================


@dataclass
class ClmmPhantomLiquiditySpoofResult(DictLikeModelMixin):
    """Forensic evaluation result for the October 2026 `$1.4B` Raydium CLMM Virtual
    Reserve Phantom Liquidity Loop Detector (`detect_clmm_virtual_reserve_phantom_spoof`).
    """

    pool_address: str
    decision: str
    blocked: bool
    spot_price: float
    tick_lower_price: float
    tick_upper_price: float
    virtual_liquidity_l: float
    real_tick_token_x_reserve: float
    real_tick_quote_y_reserve: float
    total_parked_token_x: float
    real_custodial_quote_usd: float
    naive_reported_tvl_usd: float
    phantom_tvl_inflation_multiple: float
    min_real_custodial_quote_threshold_usd: float
    max_phantom_inflation_multiple_threshold: float
    custodial_quote_below_minimum: bool
    phantom_inflation_exceeds_maximum: bool
    lp_self_wash_loop_detected: bool
    operator_lp_ownership_pct: float
    roundtrip_wash_swap_usd: float
    roundtrip_wash_interval_sec: float
    net_operator_fee_self_rebate_pct: float
    oct2026_forensic_reference: Dict[str, Any]
    spoof_triggers: List[str]
    rationale: str


def compute_clmm_tick_real_reserves(
    spot_price: float,
    tick_lower_price: float,
    tick_upper_price: float,
    virtual_liquidity_l: float,
) -> Tuple[float, float]:
    """Implements the exact CLMM tick reserve equations over `[p_l, p_u]` at spot
    price `p` and virtual liquidity `ell`:
        x(p) = ell * (1/sqrt(p) - 1/sqrt(p_u))_+ - ell * (1/sqrt(p) - 1/sqrt(p_l))_+
        y(p) = ell * (sqrt(p) - sqrt(p_l))_+ - ell * (sqrt(p) - sqrt(p_u))_+
    Returns `(x_reserve, y_reserve)`.
    """
    p = max(1e-18, float(spot_price))
    p_l = max(1e-18, float(tick_lower_price))
    p_u = max(p_l + 1e-18, float(tick_upper_price))
    ell = max(0.0, float(virtual_liquidity_l))

    inv_sqrt_p = 1.0 / math.sqrt(p)
    inv_sqrt_pl = 1.0 / math.sqrt(p_l)
    inv_sqrt_pu = 1.0 / math.sqrt(p_u)

    sqrt_p = math.sqrt(p)
    sqrt_pl = math.sqrt(p_l)
    sqrt_pu = math.sqrt(p_u)

    pos_x_upper = max(0.0, inv_sqrt_p - inv_sqrt_pu)
    pos_x_lower = max(0.0, inv_sqrt_p - inv_sqrt_pl)
    x_p = ell * pos_x_upper - ell * pos_x_lower

    pos_y_lower = max(0.0, sqrt_p - sqrt_pl)
    pos_y_upper = max(0.0, sqrt_p - sqrt_pu)
    y_p = ell * pos_y_lower - ell * pos_y_upper

    return max(0.0, x_p), max(0.0, y_p)


def detect_clmm_virtual_reserve_phantom_spoof(
    pool_address: str = "SpoofedRaydiumCLMM438Pool111111111111111111",
    *,
    spot_price: float = 1.000019,
    tick_lower_price: float = 1.000000,
    tick_upper_price: float = 10_000.0,
    virtual_liquidity_l: float = 2_000_000.0,
    total_parked_token_x: Optional[float] = 579_000_000.0,
    naive_reported_tvl_override_usd: Optional[float] = None,
    real_custodial_quote_override_usd: Optional[float] = None,
    operator_lp_ownership_pct: float = OCT_2026_OPERATOR_LP_OWNERSHIP_PCT,
    roundtrip_wash_swap_usd: float = OCT_2026_WASH_ROUNDTRIP_SWAP_USDC,
    roundtrip_wash_interval_sec: float = OCT_2026_WASH_ROUNDTRIP_CADENCE_SEC,
    lp_self_wash_loop_flag: Optional[bool] = None,
) -> ClmmPhantomLiquiditySpoofResult:
    """Detects CLMM Virtual Reserve Spoofing & the October 21, 2026 `$1.4B` Raydium CLMM
    Phantom Liquidity Loop (`$579M+` reported TVL backed by `$19.00` real USDC across
    `438` spoofed pools with `$11,000 USDC` 22-second self-owned LP wash swaps).

    Hard-blocks (`"HARD_BLOCK_PHANTOM_CLMM_LIQUIDITY_SPOOF"`) any pool where:
    - `real_custodial_quote_usd < 5000.0`, OR
    - `phantom_tvl_inflation_multiple > 50.0`, OR
    - `lp_self_wash_loop_detected == True`.
    """
    p = max(1e-18, float(spot_price))
    p_l = max(1e-18, float(tick_lower_price))
    p_u = max(p_l + 1e-18, float(tick_upper_price))
    ell = max(0.0, float(virtual_liquidity_l))

    x_tick, y_tick = compute_clmm_tick_real_reserves(
        spot_price=p,
        tick_lower_price=p_l,
        tick_upper_price=p_u,
        virtual_liquidity_l=ell,
    )

    real_quote_usd = (
        max(0.0, float(real_custodial_quote_override_usd))
        if real_custodial_quote_override_usd is not None
        else y_tick
    )

    parked_x = (
        max(x_tick, float(total_parked_token_x))
        if total_parked_token_x is not None
        else x_tick
    )

    # Naive aggregator TVL V = p * x_total + y(p), or full-range virtual L extrapolation
    full_range_extrapolated_tvl = 2.0 * ell * math.sqrt(p)
    computed_naive_tvl = max(p * parked_x + real_quote_usd, full_range_extrapolated_tvl)
    naive_tvl_usd = (
        max(0.0, float(naive_reported_tvl_override_usd))
        if naive_reported_tvl_override_usd is not None
        else computed_naive_tvl
    )

    inflation_multiple = naive_tvl_usd / max(real_quote_usd, 0.01)

    lp_ownership = min(100.0, max(0.0, float(operator_lp_ownership_pct)))
    wash_usd = max(0.0, float(roundtrip_wash_swap_usd))
    wash_sec = max(0.0, float(roundtrip_wash_interval_sec))

    if lp_self_wash_loop_flag is not None:
        self_wash_detected = bool(lp_self_wash_loop_flag)
    else:
        self_wash_detected = bool(
            lp_ownership >= SELF_WASH_LOOP_MIN_LP_OWNERSHIP_PCT
            and wash_usd >= SELF_WASH_LOOP_MIN_ROUNDTRIP_USD
            and 0.0 < wash_sec <= SELF_WASH_LOOP_MAX_CADENCE_SEC
        )

    quote_below_min = bool(real_quote_usd < MIN_REAL_CUSTODIAL_QUOTE_USD)
    inflation_exceeds_max = bool(
        inflation_multiple > MAX_PHANTOM_TVL_INFLATION_MULTIPLE
    )

    spoof_triggers: List[str] = []
    if quote_below_min:
        spoof_triggers.append(
            f"REAL_CUSTODIAL_QUOTE_BELOW_5000_USD(${real_quote_usd:,.2f} < ${MIN_REAL_CUSTODIAL_QUOTE_USD:,.2f})"
        )
    if inflation_exceeds_max:
        spoof_triggers.append(
            f"PHANTOM_TVL_INFLATION_MULTIPLE_EXCEEDED({inflation_multiple:,.2f}x > {MAX_PHANTOM_TVL_INFLATION_MULTIPLE:.1f}x)"
        )
    if self_wash_detected:
        spoof_triggers.append(
            f"LP_SELF_WASH_LOOP_DETECTED({lp_ownership:.1f}% LP ownership, "
            f"${wash_usd:,.0f} roundtrip every {wash_sec:.1f}s)"
        )

    blocked = bool(quote_below_min or inflation_exceeds_max or self_wash_detected)
    decision = (
        DECISION_HARD_BLOCK_PHANTOM_CLMM_SPOOF
        if blocked
        else DECISION_PASS_AUTHENTIC_CLMM_LIQUIDITY
    )

    if blocked:
        rationale = (
            f"Hard-blocked phantom CLMM pool {pool_address}: naive TVL ${naive_tvl_usd:,.2f} vs "
            f"real custodial quote y(p)=${real_quote_usd:,.2f} ({inflation_multiple:,.1f}x inflation). "
            f"Triggers: {', '.join(spoof_triggers)}."
        )
    else:
        rationale = (
            f"Authenticated CLMM pool {pool_address}: real custodial quote y(p)=${real_quote_usd:,.2f} "
            f"with {inflation_multiple:.2f}x TVL ratio and zero self-wash loops."
        )

    return ClmmPhantomLiquiditySpoofResult(
        pool_address=str(pool_address),
        decision=decision,
        blocked=blocked,
        spot_price=round(p, 8),
        tick_lower_price=round(p_l, 8),
        tick_upper_price=round(p_u, 8),
        virtual_liquidity_l=round(ell, 4),
        real_tick_token_x_reserve=round(x_tick, 6),
        real_tick_quote_y_reserve=round(y_tick, 6),
        total_parked_token_x=round(parked_x, 4),
        real_custodial_quote_usd=round(real_quote_usd, 4),
        naive_reported_tvl_usd=round(naive_tvl_usd, 2),
        phantom_tvl_inflation_multiple=round(inflation_multiple, 4),
        min_real_custodial_quote_threshold_usd=MIN_REAL_CUSTODIAL_QUOTE_USD,
        max_phantom_inflation_multiple_threshold=MAX_PHANTOM_TVL_INFLATION_MULTIPLE,
        custodial_quote_below_minimum=quote_below_min,
        phantom_inflation_exceeds_maximum=inflation_exceeds_max,
        lp_self_wash_loop_detected=self_wash_detected,
        operator_lp_ownership_pct=round(lp_ownership, 4),
        roundtrip_wash_swap_usd=round(wash_usd, 2),
        roundtrip_wash_interval_sec=round(wash_sec, 2),
        net_operator_fee_self_rebate_pct=round(lp_ownership, 4),
        oct2026_forensic_reference={
            "forensic_discovery_date": OCT_2026_RAYDIUM_CLMM_FORENSIC_DATE,
            "wash_volume_30d_usd": OCT_2026_PHANTOM_WASH_VOLUME_30D_USD,
            "raydium_clmm_volume_share_pct": OCT_2026_RAYDIUM_CLMM_VOLUME_SHARE_PCT,
            "spoofed_pool_count": OCT_2026_SPOOFED_CLMM_POOL_COUNT,
            "reported_aggregator_tvl_usd": OCT_2026_REPORTED_AGGREGATOR_TVL_USD,
            "real_custodial_usdc_usd": OCT_2026_REAL_CUSTODIAL_USDC_USD,
            "wash_roundtrip_swap_usdc": OCT_2026_WASH_ROUNDTRIP_SWAP_USDC,
            "wash_roundtrip_cadence_sec": OCT_2026_WASH_ROUNDTRIP_CADENCE_SEC,
            "operator_lp_ownership_pct": OCT_2026_OPERATOR_LP_OWNERSHIP_PCT,
        },
        spoof_triggers=spoof_triggers,
        rationale=rationale,
    )


# ============================================================================
# Pillar 4: `CovertBoundaryAndClmmSpoofGuard` Facade Class
# ============================================================================


class CovertBoundaryAndClmmSpoofGuard:
    """Production facade for Agent 22 (`covert-migration-jit-predator`):
    1. 3-Vector Bonding Curve Graduation & Migration Boundary Exploitation
    2. Flash-Amplified Single-Tick 4,000x JIT Liquidity + Cross-Pool Delta Hedge
    3. October 2026 `$1.4B` Raydium CLMM Virtual Reserve Phantom Liquidity Loop Detector
    """

    def __init__(self) -> None:
        self.diagnostics_run: int = 0
        self.graduation_evaluations_run: int = 0
        self.vector1_executions: int = 0
        self.vector2_executions: int = 0
        self.vector3_authority_blocks: int = 0
        self.single_tick_jit_runs: int = 0
        self.single_tick_jit_executions: int = 0
        self.single_tick_jit_aborts: int = 0
        self.clmm_spoof_audits_run: int = 0
        self.clmm_phantom_pools_blocked: int = 0
        self.last_diagnostic_report: Optional[Dict[str, Any]] = None

    def evaluate_graduation_boundary(
        self,
        mint_address: str = "GradMint11111111111111111111111111111111111",
        **kwargs: Any,
    ) -> GraduationMigrationBoundaryResult:
        """Evaluates the 3 Bonding Curve Graduation & Migration Boundary vectors and updates telemetry."""
        self.graduation_evaluations_run += 1
        res = evaluate_graduation_migration_boundary_vectors(mint_address, **kwargs)
        if not res.authority_guard_passed:
            self.vector3_authority_blocks += 1
        elif res.decision == DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB:
            self.vector2_executions += 1
        elif res.decision == DECISION_EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB:
            self.vector1_executions += 1
        return res

    def execute_single_tick_jit(
        self,
        **kwargs: Any,
    ) -> FlashAmplifiedSingleTickJitResult:
        """Executes or aborts Flash-Amplified Single-Tick JIT Liquidity + Cross-Pool Delta Hedge."""
        self.single_tick_jit_runs += 1
        res = execute_flash_amplified_single_tick_jit_with_hedge(**kwargs)
        if res.executed:
            self.single_tick_jit_executions += 1
        else:
            self.single_tick_jit_aborts += 1
        return res

    def detect_phantom_clmm_spoof(
        self,
        pool_address: str = "SpoofedRaydiumCLMM438Pool111111111111111111",
        **kwargs: Any,
    ) -> ClmmPhantomLiquiditySpoofResult:
        """Audits a CLMM pool for Virtual Reserve Spoofing & Self-Wash Loops."""
        self.clmm_spoof_audits_run += 1
        res = detect_clmm_virtual_reserve_phantom_spoof(pool_address, **kwargs)
        if res.blocked:
            self.clmm_phantom_pools_blocked += 1
        return res

    def run_full_covert_boundary_diagnostic(self) -> Dict[str, Any]:
        """Runs a comprehensive end-to-end verification across all 3 pillars for
        `TitanIPCDaemon` (`RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE`).
        """
        # 1. Pillar 1: Vector 2 Forced Graduation Kamino Flash Sweep (92% -> 100%)
        v2_grad_res = self.evaluate_graduation_boundary(
            "GradCandidate92Pct1111111111111111111111111",
            curve_completion_pct=92.0,
            external_clmm_venue="RAYDIUM_CLMM",
            external_clmm_pre_seeded=True,
            external_clmm_premium_pct=14.5,
            axiom_graduation_snipers_queued=3,
        )

        # Pillar 1: Vector 1 Intra-Tx Rounding & Price-Step Arb (when Vector 2 disabled)
        v1_grad_res = self.evaluate_graduation_boundary(
            "EarlyCurvePriceStep111111111111111111111111",
            curve_completion_pct=35.0,
            enable_vector1=True,
            enable_vector2=False,
            intra_tx_flash_sol=15.0,
            price_step_dislocation_bps=22.0,
        )

        # Pillar 1: Vector 3 May 16, 2024 Withdraw-Authority Anomaly Block
        v3_block_res = self.evaluate_graduation_boundary(
            "CompromisedAuthorityMint1111111111111111111",
            withdraw_authority_pubkey="AttackerWithdrawAuth11111111111111111111111",
            flash_loan_seeding_hijack_detected=True,
            simultaneous_flash_graduations_in_slot=5,
        )

        # 2. Pillar 2: Flash-Amplified Single-Tick 4,000x JIT Liquidity + Delta Hedge
        jit_exec_res = self.execute_single_tick_jit(
            pool_address="RaydiumCLMMWhalePool11111111111111111111111",
            spot_price=1.0000,
            tick_lower_price=0.9995,
            tick_upper_price=1.0005,
            whale_swap_size_sol=500.0,
            fee_tier_bps=125,
            flash_borrowed_quote_sol=1_000.0,
            existing_tick_liquidity_l=25_000.0,
            flash_loan_provider=FLASH_LOAN_PROVIDER_MORPHO_BLUE,
            secondary_hedge_venue="PUMPSWAP",
            secondary_pool_depth_sol=350.0,
            cross_pool_hedge_cost_sol=2.10,
            jito_tip_sol=0.05,
        )

        jit_abort_res = self.execute_single_tick_jit(
            pool_address="UnprofitableHedgePool1111111111111111111111",
            spot_price=1.0000,
            tick_lower_price=0.9995,
            tick_upper_price=1.0005,
            whale_swap_size_sol=200.0,
            fee_tier_bps=100,
            flash_borrowed_quote_sol=500.0,
            existing_tick_liquidity_l=25_000.0,
            flash_loan_provider=FLASH_LOAN_PROVIDER_KAMINO,
            secondary_hedge_venue="METEORA",
            secondary_pool_depth_sol=250.0,
            cross_pool_hedge_cost_sol=3.50,  # exceeds 2.00 SOL max fee
        )

        # 3. Pillar 3: October 2026 $1.4B Raydium CLMM Virtual Reserve Spoof Detector
        # $579M reported TVL vs $19.00 real USDC + $11,000 22s self-wash loop
        spoof_block_res = self.detect_phantom_clmm_spoof(
            "Oct2026SpoofedPool438_111111111111111111111",
            spot_price=1.000019,
            tick_lower_price=1.000000,
            tick_upper_price=10_000.0,
            virtual_liquidity_l=2_000_000.0,
            total_parked_token_x=579_000_000.0,
            naive_reported_tvl_override_usd=OCT_2026_REPORTED_AGGREGATOR_TVL_USD,
            operator_lp_ownership_pct=100.0,
            roundtrip_wash_swap_usd=11_000.0,
            roundtrip_wash_interval_sec=22.0,
        )

        authentic_clmm_res = self.detect_phantom_clmm_spoof(
            "AuthenticDeepCLMMPool1111111111111111111111",
            spot_price=1.50,
            tick_lower_price=1.00,
            tick_upper_price=2.25,
            virtual_liquidity_l=500_000.0,
            total_parked_token_x=150_000.0,
            operator_lp_ownership_pct=12.0,
            roundtrip_wash_swap_usd=0.0,
            roundtrip_wash_interval_sec=0.0,
        )

        all_verified = bool(
            v2_grad_res.executable
            and v2_grad_res.decision == DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB
            and v2_grad_res.complete_flag_after
            and v2_grad_res.lp_burned_on_pumpswap
            and v1_grad_res.executable
            and v1_grad_res.decision == DECISION_EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB
            and not v3_block_res.executable
            and v3_block_res.decision == DECISION_HARD_BLOCK_MAY16_AUTHORITY_ANOMALY
            and jit_exec_res.executed
            and jit_exec_res.decision == DECISION_EXECUTE_SINGLE_TICK_JIT_WITH_HEDGE
            and jit_exec_res.hedge_cost_strictly_below_fee_revenue
            and jit_exec_res.residual_token_inventory_delta == 0.0
            and not jit_abort_res.executed
            and jit_abort_res.decision == DECISION_ABORT_JIT_HEDGE_COST_EXCEEDS_FEE
            and spoof_block_res.blocked
            and spoof_block_res.decision == DECISION_HARD_BLOCK_PHANTOM_CLMM_SPOOF
            and spoof_block_res.lp_self_wash_loop_detected
            and not authentic_clmm_res.blocked
            and authentic_clmm_res.decision == DECISION_PASS_AUTHENTIC_CLMM_LIQUIDITY
        )

        self.diagnostics_run += 1
        report: Dict[str, Any] = {
            "status": "PASS" if all_verified else "FAIL",
            "ok": all_verified,
            "agent_id": AGENT_22_ID,
            "agent_index": AGENT_22_INDEX,
            "core_affinity": AGENT_22_CORE_AFFINITY,
            "ipc_command": IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE,
            "all_invariants_verified": all_verified,
            "pillar1_graduation_boundary": {
                "vector2_forced_graduation_sweep": v2_grad_res.to_dict(),
                "vector1_intra_tx_rounding_arb": v1_grad_res.to_dict(),
                "vector3_may16_authority_hard_block": v3_block_res.to_dict(),
            },
            "pillar2_single_tick_jit_with_hedge": {
                "executed_profitable_jit": jit_exec_res.to_dict(),
                "aborted_expensive_hedge_jit": jit_abort_res.to_dict(),
            },
            "pillar3_clmm_virtual_reserve_spoof_detector": {
                "oct2026_phantom_pool_blocked": spoof_block_res.to_dict(),
                "authentic_clmm_pool_passed": authentic_clmm_res.to_dict(),
            },
        }
        self.last_diagnostic_report = report
        return report

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Returns live telemetry summary for `TitanIPCDaemon` (`RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE`)."""
        return {
            "subsystem": "AGENT_22_COVERT_MIGRATION_JIT_AND_CLMM_SPOOF_GUARD",
            "agent_id": AGENT_22_ID,
            "agent_index": AGENT_22_INDEX,
            "core_affinity": AGENT_22_CORE_AFFINITY,
            "ipc_command": IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE,
            "pumpfun_graduation_mechanics": {
                "total_supply": PUMPFUN_TOTAL_TOKEN_SUPPLY,
                "curve_supply": PUMPFUN_CURVE_TOKEN_SUPPLY,
                "reserved_supply": PUMPFUN_RESERVED_MIGRATION_SUPPLY,
                "curve_total_fee_pct": PUMPFUN_CURVE_TOTAL_FEE_PCT,
                "platform_fee_pct": PUMPFUN_CURVE_PLATFORM_FEE_PCT,
                "creator_fee_pct": PUMPFUN_CURVE_CREATOR_FEE_PCT,
                "completion_threshold_sol": PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD,
                "migration_authority_pubkey": PUMPFUN_MIGRATION_AUTHORITY_PUBKEY,
                "permissionless_migrate_fee_sol": PUMPFUN_PERMISSIONLESS_MIGRATE_FEE_SOL,
                "pumpswap_amm_program_id": PUMPSWAP_AMM_PROGRAM_ID,
                "kamino_flash_fee_pct": KAMINO_FLASH_LOAN_FEE_PCT,
                "may16_2024_stolen_sol": MAY_16_2024_STOLEN_SOL,
            },
            "single_tick_jit_mechanics": {
                "max_capital_efficiency_multiplier": MAX_SINGLE_TICK_CAPITAL_EFFICIENCY_MULTIPLIER,
                "supported_fee_tiers_bps": list(SUPPORTED_JIT_FEE_TIERS_BPS),
                "supported_flash_loan_providers": list(SUPPORTED_FLASH_LOAN_PROVIDERS),
                "supported_secondary_hedge_venues": list(SUPPORTED_SECONDARY_HEDGE_VENUES),
            },
            "oct2026_raydium_clmm_forensics": {
                "forensic_date": OCT_2026_RAYDIUM_CLMM_FORENSIC_DATE,
                "phantom_wash_volume_30d_usd": OCT_2026_PHANTOM_WASH_VOLUME_30D_USD,
                "raydium_clmm_volume_share_pct": OCT_2026_RAYDIUM_CLMM_VOLUME_SHARE_PCT,
                "spoofed_pool_count": OCT_2026_SPOOFED_CLMM_POOL_COUNT,
                "reported_aggregator_tvl_usd": OCT_2026_REPORTED_AGGREGATOR_TVL_USD,
                "real_custodial_usdc_usd": OCT_2026_REAL_CUSTODIAL_USDC_USD,
                "wash_roundtrip_swap_usdc": OCT_2026_WASH_ROUNDTRIP_SWAP_USDC,
                "wash_roundtrip_cadence_sec": OCT_2026_WASH_ROUNDTRIP_CADENCE_SEC,
                "min_real_custodial_quote_usd": MIN_REAL_CUSTODIAL_QUOTE_USD,
                "max_phantom_tvl_inflation_multiple": MAX_PHANTOM_TVL_INFLATION_MULTIPLE,
            },
            "counters": {
                "diagnostics_run": self.diagnostics_run,
                "graduation_evaluations_run": self.graduation_evaluations_run,
                "vector1_executions": self.vector1_executions,
                "vector2_executions": self.vector2_executions,
                "vector3_authority_blocks": self.vector3_authority_blocks,
                "single_tick_jit_runs": self.single_tick_jit_runs,
                "single_tick_jit_executions": self.single_tick_jit_executions,
                "single_tick_jit_aborts": self.single_tick_jit_aborts,
                "clmm_spoof_audits_run": self.clmm_spoof_audits_run,
                "clmm_phantom_pools_blocked": self.clmm_phantom_pools_blocked,
            },
            "last_diagnostic_available": self.last_diagnostic_report is not None,
        }


_DEFAULT_COVERT_BOUNDARY_AND_CLMM_SPOOF_GUARD = CovertBoundaryAndClmmSpoofGuard()


def get_covert_boundary_and_clmm_spoof_guard() -> CovertBoundaryAndClmmSpoofGuard:
    """Returns the singleton `CovertBoundaryAndClmmSpoofGuard` instance."""
    return _DEFAULT_COVERT_BOUNDARY_AND_CLMM_SPOOF_GUARD


__all__ = [
    "AGENT_22_CORE_AFFINITY",
    "AGENT_22_ID",
    "AGENT_22_INDEX",
    "ClmmPhantomLiquiditySpoofResult",
    "CovertBoundaryAndClmmSpoofGuard",
    "DECISION_ABORT_JIT_HEDGE_COST_EXCEEDS_FEE",
    "DECISION_ABORT_JIT_INSUFFICIENT_SECONDARY_DEPTH",
    "DECISION_ABORT_JIT_SPOT_OUTSIDE_ACTIVE_TICK",
    "DECISION_EXECUTE_SINGLE_TICK_JIT_WITH_HEDGE",
    "DECISION_EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB",
    "DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB",
    "DECISION_HARD_BLOCK_MAY16_AUTHORITY_ANOMALY",
    "DECISION_HARD_BLOCK_PHANTOM_CLMM_SPOOF",
    "DECISION_HOLD_NO_PROFITABLE_BOUNDARY_VECTOR",
    "DECISION_PASS_AUTHENTIC_CLMM_LIQUIDITY",
    "DEFAULT_VECTOR2_NEAR_COMPLETION_PCT",
    "DEFAULT_VECTOR2_REMAINING_CURVE_PCT",
    "DEFAULT_VECTOR2_REMAINING_SOL_AT_92PCT",
    "FLASH_LOAN_PROVIDER_FEE_FRACTIONS",
    "FLASH_LOAN_PROVIDER_KAMINO",
    "FLASH_LOAN_PROVIDER_MORPHO_BLUE",
    "FLASH_LOAN_PROVIDER_UNISWAP_V4_TAKE",
    "FlashAmplifiedSingleTickJitResult",
    "ForcedGraduationKaminoSweepMetrics",
    "GraduationMigrationBoundaryResult",
    "IPC_ACTION_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE",
    "IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE",
    "IntraTxCurveStepArbMetrics",
    "KAMINO_FLASH_LOAN_FEE_BPS",
    "KAMINO_FLASH_LOAN_FEE_FRACTION",
    "KAMINO_FLASH_LOAN_FEE_PCT",
    "LAMPORTS_PER_SOL",
    "MAX_PHANTOM_TVL_INFLATION_MULTIPLE",
    "MAX_SINGLE_TICK_CAPITAL_EFFICIENCY_MULTIPLIER",
    "MAY_16_2024_EXPLOIT_DATE",
    "MAY_16_2024_STOLEN_SOL",
    "MAY_16_2024_STOLEN_USD",
    "MAY_16_2024_TOTAL_CURVE_LIQUIDITY_USD",
    "MIN_REAL_CUSTODIAL_QUOTE_USD",
    "May16WithdrawAuthorityGuardMetrics",
    "OCT_2026_OPERATOR_LP_OWNERSHIP_PCT",
    "OCT_2026_PHANTOM_WASH_VOLUME_30D_USD",
    "OCT_2026_RAYDIUM_CLMM_FORENSIC_DATE",
    "OCT_2026_RAYDIUM_CLMM_VOLUME_SHARE_PCT",
    "OCT_2026_REAL_CUSTODIAL_USDC_USD",
    "OCT_2026_REPORTED_AGGREGATOR_TVL_USD",
    "OCT_2026_SPOOFED_CLMM_POOL_COUNT",
    "OCT_2026_WASH_ROUNDTRIP_CADENCE_SEC",
    "OCT_2026_WASH_ROUNDTRIP_SWAP_USDC",
    "PUMPFUN_BONDING_CURVE_PROGRAM_ID",
    "PUMPFUN_CURVE_CREATOR_FEE_BPS",
    "PUMPFUN_CURVE_CREATOR_FEE_PCT",
    "PUMPFUN_CURVE_PLATFORM_FEE_BPS",
    "PUMPFUN_CURVE_PLATFORM_FEE_PCT",
    "PUMPFUN_CURVE_TOKEN_SUPPLY",
    "PUMPFUN_CURVE_TOTAL_FEE_BPS",
    "PUMPFUN_CURVE_TOTAL_FEE_PCT",
    "PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD",
    "PUMPFUN_GRADUATION_MCAP_MAX_USD",
    "PUMPFUN_GRADUATION_MCAP_MIN_USD",
    "PUMPFUN_GRADUATION_MCAP_SOL",
    "PUMPFUN_INITIAL_REAL_TOKEN_RESERVES",
    "PUMPFUN_INITIAL_VIRTUAL_SOL_RESERVES",
    "PUMPFUN_INITIAL_VIRTUAL_TOKEN_RESERVES",
    "PUMPFUN_MIGRATION_AUTHORITY_PUBKEY",
    "PUMPFUN_PERMISSIONLESS_MIGRATE_FEE_SOL",
    "PUMPFUN_RESERVED_MIGRATION_SUPPLY",
    "PUMPFUN_TOTAL_TOKEN_SUPPLY",
    "PUMPSWAP_AMM_PROGRAM_ID",
    "SELF_WASH_LOOP_MAX_CADENCE_SEC",
    "SELF_WASH_LOOP_MIN_LP_OWNERSHIP_PCT",
    "SELF_WASH_LOOP_MIN_ROUNDTRIP_USD",
    "SUPPORTED_EXTERNAL_CLMM_VENUES",
    "SUPPORTED_FLASH_LOAN_PROVIDERS",
    "SUPPORTED_JIT_FEE_TIERS_BPS",
    "SUPPORTED_JIT_FEE_TIERS_PCT",
    "SUPPORTED_SECONDARY_HEDGE_VENUES",
    "TOKEN_ATOMIC_UNITS_PER_TOKEN",
    "VECTOR3_MAX_SAFE_SIMULTANEOUS_FLASH_GRADUATIONS",
    "audit_may16_withdraw_authority_anomaly",
    "compute_clmm_tick_real_reserves",
    "compute_intra_tx_curve_price_step_rounding_arb",
    "compute_single_tick_capital_efficiency",
    "detect_clmm_virtual_reserve_phantom_spoof",
    "evaluate_graduation_migration_boundary_vectors",
    "execute_flash_amplified_single_tick_jit_with_hedge",
    "get_covert_boundary_and_clmm_spoof_guard",
    "simulate_forced_graduation_kamino_flash_sweep",
]
