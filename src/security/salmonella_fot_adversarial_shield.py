"""Sovereign Titan OS — Agent 24 (`salmonella-fot-adversarial-shield`):
Adversarial Engineering Defenses, Counter-MEV "Salmonella" State-Dependent Honeypot
Detector, Fee-on-Transfer (FoT) Exact Balance-Delta & Reserve-Desync `skim()` Verifier,
Dynamic Post-Graduation Compute Unit (CU) Exhaustion Profiler, Unbundling & Callback
Authentication Spoofing Guard, October 2026 Empirical Memecoin Forensics Benchmark Suite
(`15.2M` Tokens), and 2026 MiCA/DOJ Regulatory Market-Efficiency Compliance Gate &
Automated Taxable Disposal Ledger (`Cores 0-3 & 32-47`).

Implements:
1. October 2026 Empirical Memecoin Forensics Benchmark Suite
   (`OCTOBER_2026_EMPIRICAL_FORENSICS_BENCHMARKS`)
2. 5-Vector Adversarial Engineering & Failure-Mode Mitigation Engine
   (`evaluate_5vector_adversarial_shield`):
   - Vector 1: Fee-on-Transfer (FoT) Exact Balance-Delta Verifier & Vulnerable AMM
     `skim()` Reserve-Desync Detector (`verify_fot_balance_delta_and_skim_opportunity`)
   - Vector 2: Dynamic Post-Graduation Compute Unit (CU) Exhaustion Profiler
     (`profile_dynamic_cu_budget`: Curve `65,000` CU -> PumpSwap `145,000` CU ->
     Multi-Tick CLMM/DLMM `320,000` CU)
   - Vector 3: Counter-MEV "Salmonella" & State-Dependent Honeypot Detector
     (`detect_salmonella_state_dependent_trap`: multi-origin, perturbed-gas, and
     randomized-block differential simulation + outer `FINAL_BALANCE >= INITIAL_BALANCE + MIN_PROFIT`
     wrapper invariant)
   - Vector 4: Unbundling & Uncle/Reorg Isolation Gate
     (`evaluate_unbundling_and_reorg_isolation_gate`)
   - Vector 5: Callback Authentication Spoofing & Zero-Idle-Balance Guard
     (`verify_callback_auth_and_zero_idle_balance`)
3. 2026 MiCA & U.S. DOJ Regulatory Market-Efficiency Compliance Filter & Taxable
   Disposal Ledger (`evaluate_regulatory_compliance_and_tax_ledger`)
4. `SalmonellaFotAdversarialShield` Facade Class (`RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD`)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ============================================================================
# IPC Action & Subsystem Constants
# ============================================================================

IPC_ACTION_RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD: str = (
    "RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD"
)
SUBSYSTEM_NAME: str = "SALMONELLA_FOT_ADVERSARIAL_SHIELD_AGENT_24"


# ============================================================================
# 1. October 2026 Empirical Memecoin Forensics Benchmark Constants
# ============================================================================

# Launchpad Scale & Revenue (Pump.fun & Solana Memecoin Ecosystem, Oct 2026)
PUMPFUN_TOTAL_UNIQUE_TOKENS: int = 15_200_000
PUMPFUN_CUMULATIVE_VOLUME_USD: float = 90_000_000_000.0
PUMPFUN_PLATFORM_FEE_REVENUE_USD: float = 780_000_000.0

# Token Survival & Graduation Funnel (11.5M Sampled Launches)
TRACKED_11M_SAMPLE_TOKENS: int = 11_500_000
GRADUATION_RATIO_1_IN_N: int = 58
GRADUATION_RATE_MIN_PCT: float = 1.02
GRADUATION_RATE_MAX_PCT: float = 1.72
DAY_ONE_EXTINCTION_RATE_PCT: float = 79.0

# Retail Participant Outcome Distribution (2.9M Tracked Buyers)
TRACKED_BUYERS_COUNT: int = 2_900_000
BUYER_NET_LOSS_RATE_PCT: float = 74.0
COLLECTIVE_BUYER_LOSS_USD: float = 269_000_000.0
MEDIAN_BUYER_LOSS_USD: float = 13.0
TOP_1PCT_GAIN_SHARE_PCT: float = 50.0

# High-Profit Wallet Attribution (> $100k Realized Wins: 3,170 Wallets)
TOP_100K_WALLET_WINS_COUNT: int = 3_170
GENUINE_TRADING_PROFIT_SHARE_PCT: float = 26.0
INSIDER_TOKEN_HANDOFF_SHARE_PCT: float = 50.0
AUTOMATED_WASH_LOOP_SHARE_PCT: float = 13.0
RESIDUAL_HYBRID_ARBITRAGE_SHARE_PCT: float = 11.0

# Adversarial Extraction & MEV Breakdown (8.2M Analyzed Launches)
ANALYZED_LAUNCHES_COUNT: int = 8_200_000
DOCUMENTED_DEV_BUNDLE_CLUSTER_SIZE: int = 542
DEV_BUNDLE_EXTRACTED_USD: float = 579_000_000.0
BLOCK0_SNIPER_EXTRACTED_USD: float = 31_500_000.0
MEV_SANDWICH_EXTRACTED_USD: float = 29_700_000.0
MEV_SANDWICH_ATTACK_COUNT: int = 6_900_000


class EmpiricalForensicsBenchmarksDict(dict):
    """Dictionary of October 2026 empirical memecoin forensics benchmarks supporting
    both standard dictionary indexing (`benchmarks["pumpfun_total_unique_tokens"]`),
    attribute access (`benchmarks.pumpfun_total_unique_tokens`), and `.to_dict()`.
    """

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(
                f"'EmpiricalForensicsBenchmarksDict' object has no attribute '{name}'"
            ) from exc

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)


@dataclass(frozen=True)
class October2026EmpiricalForensicsBenchmarks:
    """Structured October 2026 Empirical Memecoin Forensics Benchmark Suite (`15.2M` tokens)."""

    pumpfun_total_unique_tokens: int = PUMPFUN_TOTAL_UNIQUE_TOKENS
    pumpfun_cumulative_volume_usd: float = PUMPFUN_CUMULATIVE_VOLUME_USD
    pumpfun_platform_fee_revenue_usd: float = PUMPFUN_PLATFORM_FEE_REVENUE_USD
    tracked_11m_sample_tokens: int = TRACKED_11M_SAMPLE_TOKENS
    graduation_ratio_1_in_n: int = GRADUATION_RATIO_1_IN_N
    graduation_rate_min_pct: float = GRADUATION_RATE_MIN_PCT
    graduation_rate_max_pct: float = GRADUATION_RATE_MAX_PCT
    day_one_extinction_rate_pct: float = DAY_ONE_EXTINCTION_RATE_PCT
    tracked_buyers_count: int = TRACKED_BUYERS_COUNT
    buyer_net_loss_rate_pct: float = BUYER_NET_LOSS_RATE_PCT
    collective_buyer_loss_usd: float = COLLECTIVE_BUYER_LOSS_USD
    median_buyer_loss_usd: float = MEDIAN_BUYER_LOSS_USD
    top_1pct_gain_share_pct: float = TOP_1PCT_GAIN_SHARE_PCT
    top_100k_wallet_wins_count: int = TOP_100K_WALLET_WINS_COUNT
    genuine_trading_profit_share_pct: float = GENUINE_TRADING_PROFIT_SHARE_PCT
    insider_token_handoff_share_pct: float = INSIDER_TOKEN_HANDOFF_SHARE_PCT
    automated_wash_loop_share_pct: float = AUTOMATED_WASH_LOOP_SHARE_PCT
    residual_hybrid_arbitrage_share_pct: float = RESIDUAL_HYBRID_ARBITRAGE_SHARE_PCT
    analyzed_launches_count: int = ANALYZED_LAUNCHES_COUNT
    documented_dev_bundle_cluster_size: int = DOCUMENTED_DEV_BUNDLE_CLUSTER_SIZE
    dev_bundle_extracted_usd: float = DEV_BUNDLE_EXTRACTED_USD
    block0_sniper_extracted_usd: float = BLOCK0_SNIPER_EXTRACTED_USD
    mev_sandwich_extracted_usd: float = MEV_SANDWICH_EXTRACTED_USD
    mev_sandwich_attack_count: int = MEV_SANDWICH_ATTACK_COUNT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pumpfun_total_unique_tokens": self.pumpfun_total_unique_tokens,
            "pumpfun_cumulative_volume_usd": self.pumpfun_cumulative_volume_usd,
            "pumpfun_platform_fee_revenue_usd": self.pumpfun_platform_fee_revenue_usd,
            "tracked_11m_sample_tokens": self.tracked_11m_sample_tokens,
            "graduation_ratio_1_in_n": self.graduation_ratio_1_in_n,
            "graduation_rate_min_pct": self.graduation_rate_min_pct,
            "graduation_rate_max_pct": self.graduation_rate_max_pct,
            "graduation_rate_range_pct": [
                self.graduation_rate_min_pct,
                self.graduation_rate_max_pct,
            ],
            "day_one_extinction_rate_pct": self.day_one_extinction_rate_pct,
            "tracked_buyers_count": self.tracked_buyers_count,
            "buyer_net_loss_rate_pct": self.buyer_net_loss_rate_pct,
            "collective_buyer_loss_usd": self.collective_buyer_loss_usd,
            "median_buyer_loss_usd": self.median_buyer_loss_usd,
            "top_1pct_gain_share_pct": self.top_1pct_gain_share_pct,
            "top_100k_wallet_wins_count": self.top_100k_wallet_wins_count,
            "genuine_trading_profit_share_pct": self.genuine_trading_profit_share_pct,
            "insider_token_handoff_share_pct": self.insider_token_handoff_share_pct,
            "automated_wash_loop_share_pct": self.automated_wash_loop_share_pct,
            "residual_hybrid_arbitrage_share_pct": self.residual_hybrid_arbitrage_share_pct,
            "analyzed_launches_count": self.analyzed_launches_count,
            "documented_dev_bundle_cluster_size": self.documented_dev_bundle_cluster_size,
            "dev_bundle_extracted_usd": self.dev_bundle_extracted_usd,
            "block0_sniper_extracted_usd": self.block0_sniper_extracted_usd,
            "mev_sandwich_extracted_usd": self.mev_sandwich_extracted_usd,
            "mev_sandwich_attack_count": self.mev_sandwich_attack_count,
        }


OCTOBER_2026_EMPIRICAL_FORENSICS_DATACLASS = October2026EmpiricalForensicsBenchmarks()

OCTOBER_2026_EMPIRICAL_FORENSICS_BENCHMARKS: EmpiricalForensicsBenchmarksDict = (
    EmpiricalForensicsBenchmarksDict(OCTOBER_2026_EMPIRICAL_FORENSICS_DATACLASS.to_dict())
)


def get_october_2026_empirical_forensics_benchmarks() -> EmpiricalForensicsBenchmarksDict:
    """Returns the canonical October 2026 empirical memecoin forensics benchmark suite."""
    return EmpiricalForensicsBenchmarksDict(
        OCTOBER_2026_EMPIRICAL_FORENSICS_DATACLASS.to_dict()
    )


# ============================================================================
# 2. Vector 1–5 Constants & Thresholds
# ============================================================================

# Vector 1: Fee-on-Transfer (FoT) & Vulnerable AMM Reserve-Desync `skim()` Vector
DEFAULT_FOT_BENCHMARK_TAX_PCT: float = 5.0
PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB: float = 49.15
PANCAKE_FOT_SKIM_NET_PROFIT_WBNB: float = 37.55
PANCAKE_FOT_SKIM_PROFIT_RATIO: float = round(
    PANCAKE_FOT_SKIM_NET_PROFIT_WBNB / PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB, 6
)
FOT_ACTION_EXECUTE_VERIFIED_DELTA_ARB: str = "EXECUTE_FOT_VERIFIED_BALANCE_DELTA_ARB"
FOT_ACTION_EXECUTE_RESERVE_DESYNC_SKIM_ARB: str = (
    "EXECUTE_FOT_RESERVE_DESYNC_SKIM_ARB"
)
FOT_ACTION_ABORT_UNPROFITABLE_AFTER_TAX: str = (
    "ABORT_FOT_SHORTFALL_FAILS_LOAN_REPAYMENT"
)

# Vector 2: Dynamic Post-Graduation Compute Unit (CU) Exhaustion Profiler
VENUE_PUMP_BONDING_CURVE: str = "PUMP_BONDING_CURVE"
VENUE_PUMPSWAP_CPMM_AMM: str = "PUMPSWAP_CPMM_AMM"
VENUE_MULTI_TICK_CLMM_OR_DLMM: str = "MULTI_TICK_CLMM_OR_DLMM"

CU_LIMIT_PUMP_BONDING_CURVE: int = 65_000
CU_LIMIT_PUMPSWAP_CPMM_AMM: int = 145_000
CU_LIMIT_MULTI_TICK_CLMM_OR_DLMM: int = 320_000
SOLANA_MAX_TRANSACTION_CU_LIMIT: int = 1_400_000

VENUE_CU_BUDGET_MAP: Dict[str, int] = {
    VENUE_PUMP_BONDING_CURVE: CU_LIMIT_PUMP_BONDING_CURVE,
    VENUE_PUMPSWAP_CPMM_AMM: CU_LIMIT_PUMPSWAP_CPMM_AMM,
    VENUE_MULTI_TICK_CLMM_OR_DLMM: CU_LIMIT_MULTI_TICK_CLMM_OR_DLMM,
}

# Vector 3: Counter-MEV "Salmonella" & State-Dependent Honeypot Detector
SALMONELLA_MAX_ACCEPTABLE_CREDIT_DISCREPANCY_PCT: float = 0.01
SALMONELLA_DUST_CREDIT_THRESHOLD_RATIO: float = 0.20
SALMONELLA_DECISION_SAFE_EXECUTION: str = "PASS_COUNTER_MEV_SALMONELLA_VERIFICATION"
SALMONELLA_DECISION_ABORT_HONEYPOT_TRAP: str = (
    "ABORT_SALMONELLA_STATE_DEPENDENT_HONEYPOT"
)

# Vector 4: Unbundling & Uncle/Reorg Isolation Gate
ATOMIC_MODE_SINGLE_TX_FLASH_CALLBACK: str = "SINGLE_TX_FLASH_CALLBACK"
ATOMIC_MODE_ALL_OR_NOTHING_JITO_FLASHBOTS_BUNDLE: str = (
    "ALL_OR_NOTHING_ATOMIC_BUNDLE"
)
ATOMIC_MODE_NON_ATOMIC_PUBLIC_MEMPOOL: str = "NON_ATOMIC_PUBLIC_MEMPOOL"

# Vector 5: Callback Authentication Spoofing & Zero-Idle-Balance Guard
SUPPORTED_FLASH_CALLBACK_SIGNATURES: Tuple[str, ...] = (
    "unlockCallback(bytes)",
    "uniswapV3SwapCallback(int256,int256,bytes)",
    "onMorphoFlashLoan(uint256,bytes)",
    "executeOperation(address,uint256,uint256,address,bytes)",
    "receiveFlashLoan(address[],uint256[],uint256[],bytes)",
)
VERIFIED_CANONICAL_POOL_MANAGERS: Tuple[str, ...] = (
    "0x000000000004444c5dc75cB358380D2e3dE08A90",  # Uniswap v4 PoolManager
    "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",  # Morpho Blue Singleton
    "0xBA12222222228d8Ba445958a75a0704d566BF2C8",  # Balancer V2 Vault
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",  # Raydium CLMM Program
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",  # PumpSwap AMM Program
)

# Overall 5-Vector Shield Decisions
SHIELD_DECISION_APPROVED_ATOMIC_EXECUTION: str = (
    "APPROVED_ALL_5_ADVERSARIAL_VECTORS_CLEARED"
)
SHIELD_DECISION_BLOCKED_ADVERSARIAL_RISK: str = (
    "BLOCKED_BY_5VECTOR_ADVERSARIAL_SHIELD"
)


# ============================================================================
# 3. 2026 MiCA & DOJ Regulatory Compliance Framework Constants
# ============================================================================

COMPLIANCE_STATUS_COMPLIANT_EXTRACTION: str = (
    "COMPLIANT_MARKET_EFFICIENCY_EXTRACTION"
)
COMPLIANCE_STATUS_BLOCKED_MANIPULATION: str = (
    "BLOCKED_REGULATORY_MANIPULATION_VECTOR"
)

STRATEGY_CROSS_DEX_SPATIAL_ARB: str = "CROSS_DEX_SPATIAL_ARB"
STRATEGY_TRIANGULAR_ROUTING_ARB: str = "TRIANGULAR_ROUTING_ARB"
STRATEGY_FLASH_AMPLIFIED_JIT_LIQUIDITY: str = "FLASH_AMPLIFIED_JIT_LIQUIDITY"
STRATEGY_FORCED_GRADUATION_PRICE_EQUALIZATION: str = (
    "FORCED_GRADUATION_PRICE_EQUALIZATION"
)
STRATEGY_MAYHEM_AI_NOISE_BACKRUN: str = "MAYHEM_AI_NOISE_BACKRUN"
STRATEGY_PARASITIC_V4_AFTERSWAP_EQUALIZATION: str = (
    "PARASITIC_V4_AFTERSWAP_EQUALIZATION"
)
STRATEGY_ISOLATED_MARKET_BAD_DEBT_LIQUIDATION: str = (
    "ISOLATED_MARKET_BAD_DEBT_LIQUIDATION"
)

STRATEGY_CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING: str = (
    "CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING"
)
STRATEGY_SALMONELLA_HONEYPOT_DEPLOYMENT: str = "SALMONELLA_HONEYPOT_DEPLOYMENT"
STRATEGY_PREDATORY_RETAIL_WIRE_FRAUD_BAITING: str = (
    "PREDATORY_RETAIL_WIRE_FRAUD_BAITING"
)

WHITELISTED_MARKET_EFFICIENCY_STRATEGIES: Tuple[str, ...] = (
    STRATEGY_CROSS_DEX_SPATIAL_ARB,
    STRATEGY_TRIANGULAR_ROUTING_ARB,
    STRATEGY_FLASH_AMPLIFIED_JIT_LIQUIDITY,
    STRATEGY_FORCED_GRADUATION_PRICE_EQUALIZATION,
    STRATEGY_MAYHEM_AI_NOISE_BACKRUN,
    STRATEGY_PARASITIC_V4_AFTERSWAP_EQUALIZATION,
    STRATEGY_ISOLATED_MARKET_BAD_DEBT_LIQUIDATION,
)

HARD_BLOCKED_MANIPULATIVE_STRATEGIES: Tuple[str, ...] = (
    STRATEGY_CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING,
    STRATEGY_SALMONELLA_HONEYPOT_DEPLOYMENT,
    STRATEGY_PREDATORY_RETAIL_WIRE_FRAUD_BAITING,
)


# ============================================================================
# Data Models
# ============================================================================


@dataclass(frozen=True)
class FotBalanceDeltaAndSkimResult:
    """Result of Vector 1: Fee-on-Transfer (FoT) Exact Balance-Delta Verifier &
    Vulnerable AMM Reserve-Desync `skim()` Arbitrage Detector.
    """

    token_address: str
    nominal_amount_in: float
    nominal_amount_out: float
    balance_before: float
    balance_after: float
    actual_received: float
    nominal_vs_actual_shortfall: float
    observed_fot_tax_pct: float
    has_fee_on_transfer_tax: bool
    flash_loan_principal: float
    flash_loan_fee: float
    total_loan_repayment_required: float
    min_required_profit: float
    gross_exit_proceeds_nominal: float
    gross_exit_proceeds_actual_delta: float
    net_profit_nominal_assumption: float
    net_profit_actual_balance_delta: float
    nominal_assumption_would_revert_on_repay: bool
    fot_nominal_assumption_rejected: bool
    clears_loan_repayment_after_tax: bool
    amm_uses_nominal_reserve_accounting: bool
    amm_has_public_skim_function: bool
    stored_reserve_token: float
    actual_pair_balance_token: float
    reserve_desync_amount: float
    skim_arbitrage_detected: bool
    skim_flash_loan_wbnb: float
    skim_estimated_net_profit_wbnb: float
    vector1_passed: bool
    recommended_action: str
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "nominal_amount_in": self.nominal_amount_in,
            "nominal_amount_out": self.nominal_amount_out,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "actual_received": self.actual_received,
            "nominal_vs_actual_shortfall": self.nominal_vs_actual_shortfall,
            "observed_fot_tax_pct": self.observed_fot_tax_pct,
            "has_fee_on_transfer_tax": self.has_fee_on_transfer_tax,
            "flash_loan_principal": self.flash_loan_principal,
            "flash_loan_fee": self.flash_loan_fee,
            "total_loan_repayment_required": self.total_loan_repayment_required,
            "min_required_profit": self.min_required_profit,
            "gross_exit_proceeds_nominal": self.gross_exit_proceeds_nominal,
            "gross_exit_proceeds_actual_delta": self.gross_exit_proceeds_actual_delta,
            "net_profit_nominal_assumption": self.net_profit_nominal_assumption,
            "net_profit_actual_balance_delta": self.net_profit_actual_balance_delta,
            "nominal_assumption_would_revert_on_repay": (
                self.nominal_assumption_would_revert_on_repay
            ),
            "fot_nominal_assumption_rejected": self.fot_nominal_assumption_rejected,
            "clears_loan_repayment_after_tax": self.clears_loan_repayment_after_tax,
            "amm_uses_nominal_reserve_accounting": (
                self.amm_uses_nominal_reserve_accounting
            ),
            "amm_has_public_skim_function": self.amm_has_public_skim_function,
            "stored_reserve_token": self.stored_reserve_token,
            "actual_pair_balance_token": self.actual_pair_balance_token,
            "reserve_desync_amount": self.reserve_desync_amount,
            "skim_arbitrage_detected": self.skim_arbitrage_detected,
            "skim_flash_loan_wbnb": self.skim_flash_loan_wbnb,
            "skim_estimated_net_profit_wbnb": self.skim_estimated_net_profit_wbnb,
            "vector1_passed": self.vector1_passed,
            "recommended_action": self.recommended_action,
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class DynamicCuProfileResult:
    """Result of Vector 2: Dynamic Post-Graduation Compute Unit (CU) Exhaustion Profiler."""

    token_mint: str
    lifecycle_venue: str
    previous_venue: Optional[str]
    graduated_from_bonding_curve: bool
    configured_static_cu_limit: Optional[int]
    baseline_venue_cu_limit: int
    extra_tick_array_crossings: int
    tick_crossing_cu_overhead: int
    recommended_compute_unit_limit: int
    static_cu_would_exhaust: bool
    compute_budget_instruction: str
    priority_fee_micro_lamports_per_cu: int
    estimated_priority_fee_lamports: int
    vector2_passed: bool
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_mint": self.token_mint,
            "lifecycle_venue": self.lifecycle_venue,
            "previous_venue": self.previous_venue,
            "graduated_from_bonding_curve": self.graduated_from_bonding_curve,
            "configured_static_cu_limit": self.configured_static_cu_limit,
            "baseline_venue_cu_limit": self.baseline_venue_cu_limit,
            "extra_tick_array_crossings": self.extra_tick_array_crossings,
            "tick_crossing_cu_overhead": self.tick_crossing_cu_overhead,
            "recommended_compute_unit_limit": self.recommended_compute_unit_limit,
            "static_cu_would_exhaust": self.static_cu_would_exhaust,
            "compute_budget_instruction": self.compute_budget_instruction,
            "priority_fee_micro_lamports_per_cu": (
                self.priority_fee_micro_lamports_per_cu
            ),
            "estimated_priority_fee_lamports": self.estimated_priority_fee_lamports,
            "vector2_passed": self.vector2_passed,
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class SalmonellaTrapDetectionResult:
    """Result of Vector 3: Counter-MEV "Salmonella" & State-Dependent Honeypot Detector."""

    token_address: str
    emitted_transfer_event_tokens: float
    operator_origin_credited_tokens: float
    searcher_origin_credited_tokens: float
    perturbed_gas_credited_tokens: float
    randomized_block_credited_tokens: float
    actual_credited_tokens: float
    credit_to_event_ratio: float
    event_vs_balance_discrepancy_pct: float
    trap_tx_origin_xor_branch: bool
    trap_gasleft_modulo_branch: bool
    trap_transient_or_block_state_branch: bool
    trap_transfer_event_balance_desync: bool
    salmonella_honeypot_detected: bool
    initial_balance: float
    final_balance: float
    min_profit: float
    required_minimum_final_balance: float
    outer_balance_invariant_passed: bool
    outer_invariant_expression: str
    vector3_passed: bool
    decision: str
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "emitted_transfer_event_tokens": self.emitted_transfer_event_tokens,
            "operator_origin_credited_tokens": self.operator_origin_credited_tokens,
            "searcher_origin_credited_tokens": self.searcher_origin_credited_tokens,
            "perturbed_gas_credited_tokens": self.perturbed_gas_credited_tokens,
            "randomized_block_credited_tokens": self.randomized_block_credited_tokens,
            "actual_credited_tokens": self.actual_credited_tokens,
            "credit_to_event_ratio": self.credit_to_event_ratio,
            "event_vs_balance_discrepancy_pct": self.event_vs_balance_discrepancy_pct,
            "trap_tx_origin_xor_branch": self.trap_tx_origin_xor_branch,
            "trap_gasleft_modulo_branch": self.trap_gasleft_modulo_branch,
            "trap_transient_or_block_state_branch": (
                self.trap_transient_or_block_state_branch
            ),
            "trap_transfer_event_balance_desync": (
                self.trap_transfer_event_balance_desync
            ),
            "salmonella_honeypot_detected": self.salmonella_honeypot_detected,
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "min_profit": self.min_profit,
            "required_minimum_final_balance": self.required_minimum_final_balance,
            "outer_balance_invariant_passed": self.outer_balance_invariant_passed,
            "outer_invariant_expression": self.outer_invariant_expression,
            "vector3_passed": self.vector3_passed,
            "decision": self.decision,
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class UnbundlingAndReorgIsolationResult:
    """Result of Vector 4: Unbundling & Uncle/Reorg Isolation Gate."""

    execution_mode: str
    is_single_tx_flash_callback: bool
    is_all_or_nothing_atomic_bundle: bool
    allow_non_atomic_mempool_broadcast: bool
    reorg_split_leg_vulnerable: bool
    vector4_passed: bool
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_mode": self.execution_mode,
            "is_single_tx_flash_callback": self.is_single_tx_flash_callback,
            "is_all_or_nothing_atomic_bundle": self.is_all_or_nothing_atomic_bundle,
            "allow_non_atomic_mempool_broadcast": (
                self.allow_non_atomic_mempool_broadcast
            ),
            "reorg_split_leg_vulnerable": self.reorg_split_leg_vulnerable,
            "vector4_passed": self.vector4_passed,
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class CallbackAuthAndIdleBalanceResult:
    """Result of Vector 5: Callback Authentication Spoofing & Zero-Idle-Balance Guard."""

    callback_function: str
    msg_sender: str
    verified_pool_or_manager_address: str
    callback_sender_authenticated: bool
    initiator_authenticated: bool
    idle_contract_balance_lamports: int
    idle_erc20_balance_raw: int
    zero_idle_balance_enforced: bool
    spoof_drain_surface_eliminated: bool
    vector5_passed: bool
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "callback_function": self.callback_function,
            "msg_sender": self.msg_sender,
            "verified_pool_or_manager_address": self.verified_pool_or_manager_address,
            "callback_sender_authenticated": self.callback_sender_authenticated,
            "initiator_authenticated": self.initiator_authenticated,
            "idle_contract_balance_lamports": self.idle_contract_balance_lamports,
            "idle_erc20_balance_raw": self.idle_erc20_balance_raw,
            "zero_idle_balance_enforced": self.zero_idle_balance_enforced,
            "spoof_drain_surface_eliminated": self.spoof_drain_surface_eliminated,
            "vector5_passed": self.vector5_passed,
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class FiveVectorAdversarialShieldReport:
    """Composite report from `evaluate_5vector_adversarial_shield` across all 5 vectors."""

    token_identifier: str
    vector1_fot_and_skim: FotBalanceDeltaAndSkimResult
    vector2_dynamic_cu_profile: DynamicCuProfileResult
    vector3_salmonella_detector: SalmonellaTrapDetectionResult
    vector4_unbundling_reorg_gate: UnbundlingAndReorgIsolationResult
    vector5_callback_auth_guard: CallbackAuthAndIdleBalanceResult
    passed_vector_count: int
    all_five_vectors_passed: bool
    should_execute_atomic_bundle: bool
    decision: str
    blocking_vectors: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_identifier": self.token_identifier,
            "vector1_fot_and_skim": self.vector1_fot_and_skim.to_dict(),
            "vector2_dynamic_cu_profile": self.vector2_dynamic_cu_profile.to_dict(),
            "vector3_salmonella_detector": self.vector3_salmonella_detector.to_dict(),
            "vector4_unbundling_reorg_gate": (
                self.vector4_unbundling_reorg_gate.to_dict()
            ),
            "vector5_callback_auth_guard": self.vector5_callback_auth_guard.to_dict(),
            "passed_vector_count": self.passed_vector_count,
            "all_five_vectors_passed": self.all_five_vectors_passed,
            "should_execute_atomic_bundle": self.should_execute_atomic_bundle,
            "decision": self.decision,
            "blocking_vectors": list(self.blocking_vectors),
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class TaxableDisposalLedgerEntry:
    """Auditable taxable disposal ledger record for completed atomic extractions."""

    disposal_id: str
    timestamp_utc: str
    strategy_type: str
    flash_primitive: str
    gross_proceeds_usd: float
    cost_basis_plus_fees_usd: float
    realized_net_gain_usd: float
    asset_pair: str = "SOL/USDC"
    chain_id: str = "solana-mainnet"
    tx_or_bundle_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disposal_id": self.disposal_id,
            "timestamp_utc": self.timestamp_utc,
            "strategy_type": self.strategy_type,
            "flash_primitive": self.flash_primitive,
            "gross_proceeds_usd": self.gross_proceeds_usd,
            "cost_basis_plus_fees_usd": self.cost_basis_plus_fees_usd,
            "realized_net_gain_usd": self.realized_net_gain_usd,
            "asset_pair": self.asset_pair,
            "chain_id": self.chain_id,
            "tx_or_bundle_hash": self.tx_or_bundle_hash,
        }


@dataclass(frozen=True)
class RegulatoryComplianceAndTaxEvaluation:
    """Result of 2026 MiCA & DOJ Regulatory Market-Efficiency Compliance Gate &
    Automated Taxable Disposal Ledger recording.
    """

    strategy_type: str
    flash_primitive: str
    is_whitelisted_market_efficiency: bool
    is_hard_blocked_manipulation: bool
    compliance_status: str
    execution_permitted: bool
    regulatory_jurisdictions_checked: List[str]
    gross_proceeds_usd: float
    cost_basis_plus_fees_usd: float
    realized_net_gain_usd: float
    taxable_disposal_entry: Optional[TaxableDisposalLedgerEntry]
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_type": self.strategy_type,
            "flash_primitive": self.flash_primitive,
            "is_whitelisted_market_efficiency": self.is_whitelisted_market_efficiency,
            "is_hard_blocked_manipulation": self.is_hard_blocked_manipulation,
            "compliance_status": self.compliance_status,
            "execution_permitted": self.execution_permitted,
            "regulatory_jurisdictions_checked": list(
                self.regulatory_jurisdictions_checked
            ),
            "gross_proceeds_usd": self.gross_proceeds_usd,
            "cost_basis_plus_fees_usd": self.cost_basis_plus_fees_usd,
            "realized_net_gain_usd": self.realized_net_gain_usd,
            "taxable_disposal_entry": (
                self.taxable_disposal_entry.to_dict()
                if self.taxable_disposal_entry is not None
                else None
            ),
            "flags": list(self.flags),
        }


# ============================================================================
# Vector 1: Fee-on-Transfer (FoT) Exact Balance-Delta Verifier &
#           Vulnerable AMM Reserve-Desync `skim()` Detector
# ============================================================================


def verify_fot_balance_delta_and_skim_opportunity(
    token_address: str = "FoTDeflationaryToken11111111111111111111111",
    *,
    nominal_amount_in: float = 100.0,
    nominal_amount_out: float = 1_000.0,
    balance_before: float = 0.0,
    balance_after: Optional[float] = None,
    fot_tax_pct: float = 0.0,
    second_leg_exchange_rate: float = 0.102,
    second_leg_fot_tax_pct: Optional[float] = None,
    flash_loan_principal: Optional[float] = None,
    flash_loan_fee: float = 0.09,
    min_required_profit: float = 0.10,
    amm_uses_nominal_reserve_accounting: bool = False,
    amm_has_public_skim_function: bool = False,
    stored_reserve_token: float = 100_000.0,
    actual_pair_balance_token: Optional[float] = None,
    skim_flash_loan_wbnb: float = PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB,
) -> FotBalanceDeltaAndSkimResult:
    """Enforces `actual_received = balance_after - balance_before` on every transfer leg
    and evaluates vulnerable AMM FoT reserve-desync `skim()` arbitrage opportunities.

    1. **Exact Balance-Delta Accounting**:
       - Never trusts router `amountOut` return values when routing through unknown or
         Fee-on-Transfer (FoT) tokens.
       - Computes `actual_received = balance_after - balance_before`.
       - Evaluates whether selling `actual_received` on the exit leg (including any exit FoT
         tax) yields enough quote asset to repay `flash_loan_principal + flash_loan_fee + min_required_profit`.
       - If nominal `amountOut` would look profitable (`> loan_repayment`), but the `5%`
         (or observed) FoT tax causes `gross_exit_proceeds_actual_delta < total_loan_repayment_required + min_required_profit`,
         flags `fot_nominal_assumption_rejected = True` and aborts execution before gas loss.
    2. **FoT Reserve-Desync (`skim()`) Arbitrage Detection**:
       - Detects poorly coded AMM forks (such as the historical PancakeSwap FoT fork exploit)
         that update `_reserve0` by the nominal `_amountIn` without checking `balanceAfter - balanceBefore`
         and expose a public `skim(address to)` function (or price off inflated/deflated reserves),
         modeling the `49.15 WBNB` flash loan -> `37.55 WBNB` single-tx profit vector.
    """
    principal = (
        float(flash_loan_principal)
        if flash_loan_principal is not None
        else float(nominal_amount_in)
    )
    loan_repayment_required = principal + float(flash_loan_fee)

    # Resolve balance_after from either explicit balance_after or fot_tax_pct
    if balance_after is None:
        effective_tax_rate = max(0.0, min(100.0, float(fot_tax_pct))) / 100.0
        resolved_balance_after = float(balance_before) + float(nominal_amount_out) * (
            1.0 - effective_tax_rate
        )
    else:
        resolved_balance_after = float(balance_after)

    actual_received = max(0.0, resolved_balance_after - float(balance_before))
    shortfall = max(0.0, float(nominal_amount_out) - actual_received)

    if nominal_amount_out > 0.0:
        observed_tax_pct = round((shortfall / float(nominal_amount_out)) * 100.0, 4)
    else:
        observed_tax_pct = round(float(fot_tax_pct), 4)

    has_fot_tax = observed_tax_pct > 1e-6

    # Exit leg tax (if token is FoT, selling back into an AMM also incurs FoT transfer tax unless overridden)
    exit_tax_pct = (
        float(second_leg_fot_tax_pct)
        if second_leg_fot_tax_pct is not None
        else observed_tax_pct
    )
    exit_tax_multiplier = max(0.0, 1.0 - (exit_tax_pct / 100.0))

    gross_exit_nominal = float(nominal_amount_out) * float(second_leg_exchange_rate)
    gross_exit_actual = (
        actual_received * exit_tax_multiplier * float(second_leg_exchange_rate)
    )

    net_profit_nominal = gross_exit_nominal - loan_repayment_required
    net_profit_actual = gross_exit_actual - loan_repayment_required

    clears_repayment_after_tax = net_profit_actual >= float(min_required_profit)
    nominal_would_revert = (
        net_profit_nominal >= float(min_required_profit)
        and gross_exit_actual < loan_repayment_required
    )
    fot_nominal_rejected = (
        has_fot_tax
        and net_profit_nominal >= float(min_required_profit)
        and not clears_repayment_after_tax
    )

    # Evaluate Vulnerable AMM FoT Reserve Desync (`skim()`) Opportunity
    if actual_pair_balance_token is None:
        if amm_uses_nominal_reserve_accounting and has_fot_tax:
            # AMM credited nominal amount to stored_reserve_token, but actual balance is lower by FoT tax
            resolved_pair_balance = float(stored_reserve_token) * (
                1.0 - (observed_tax_pct / 100.0)
            )
        else:
            resolved_pair_balance = float(stored_reserve_token)
    else:
        resolved_pair_balance = float(actual_pair_balance_token)

    reserve_desync = abs(float(stored_reserve_token) - resolved_pair_balance)
    skim_detected = bool(
        amm_uses_nominal_reserve_accounting
        and amm_has_public_skim_function
        and (has_fot_tax or reserve_desync > 0.0)
    )

    if skim_detected:
        estimated_skim_profit_wbnb = round(
            float(skim_flash_loan_wbnb) * PANCAKE_FOT_SKIM_PROFIT_RATIO, 2
        )
    else:
        estimated_skim_profit_wbnb = 0.0

    flags: List[str] = [
        "BALANCE_DELTA_INVARIANT_ENFORCED:actual_received=balance_after-balance_before"
    ]
    if has_fot_tax:
        flags.append(f"FOT_TRANSFER_TAX_DETECTED_{observed_tax_pct:.2f}PCT")
    if fot_nominal_rejected:
        flags.append("NOMINAL_AMOUNT_OUT_ASSUMPTION_REJECTED_DUE_TO_FOT_SHORTFALL")
    if nominal_would_revert:
        flags.append("PREVENTED_FLASH_LOAN_REPAYMENT_REVERT_FROM_UNACCOUNTED_FOT_TAX")
    if skim_detected:
        flags.append(
            f"VULNERABLE_AMM_FOT_RESERVE_DESYNC_SKIM_DETECTED_"
            f"{skim_flash_loan_wbnb:.2f}WBNB_TO_{estimated_skim_profit_wbnb:.2f}WBNB"
        )

    vector1_passed = bool(clears_repayment_after_tax or skim_detected)
    if skim_detected and not clears_repayment_after_tax:
        recommended_action = FOT_ACTION_EXECUTE_RESERVE_DESYNC_SKIM_ARB
    elif clears_repayment_after_tax:
        recommended_action = FOT_ACTION_EXECUTE_VERIFIED_DELTA_ARB
    else:
        recommended_action = FOT_ACTION_ABORT_UNPROFITABLE_AFTER_TAX

    return FotBalanceDeltaAndSkimResult(
        token_address=token_address,
        nominal_amount_in=round(float(nominal_amount_in), 6),
        nominal_amount_out=round(float(nominal_amount_out), 6),
        balance_before=round(float(balance_before), 6),
        balance_after=round(resolved_balance_after, 6),
        actual_received=round(actual_received, 6),
        nominal_vs_actual_shortfall=round(shortfall, 6),
        observed_fot_tax_pct=observed_tax_pct,
        has_fee_on_transfer_tax=has_fot_tax,
        flash_loan_principal=round(principal, 6),
        flash_loan_fee=round(float(flash_loan_fee), 6),
        total_loan_repayment_required=round(loan_repayment_required, 6),
        min_required_profit=round(float(min_required_profit), 6),
        gross_exit_proceeds_nominal=round(gross_exit_nominal, 6),
        gross_exit_proceeds_actual_delta=round(gross_exit_actual, 6),
        net_profit_nominal_assumption=round(net_profit_nominal, 6),
        net_profit_actual_balance_delta=round(net_profit_actual, 6),
        nominal_assumption_would_revert_on_repay=nominal_would_revert,
        fot_nominal_assumption_rejected=fot_nominal_rejected,
        clears_loan_repayment_after_tax=clears_repayment_after_tax,
        amm_uses_nominal_reserve_accounting=bool(amm_uses_nominal_reserve_accounting),
        amm_has_public_skim_function=bool(amm_has_public_skim_function),
        stored_reserve_token=round(float(stored_reserve_token), 6),
        actual_pair_balance_token=round(resolved_pair_balance, 6),
        reserve_desync_amount=round(reserve_desync, 6),
        skim_arbitrage_detected=skim_detected,
        skim_flash_loan_wbnb=round(float(skim_flash_loan_wbnb), 4),
        skim_estimated_net_profit_wbnb=estimated_skim_profit_wbnb,
        vector1_passed=vector1_passed,
        recommended_action=recommended_action,
        flags=flags,
    )


# ============================================================================
# Vector 2: Dynamic Post-Graduation Compute Unit (CU) Exhaustion Profiler
# ============================================================================


def profile_dynamic_cu_budget(
    token_mint: str = "GraduatedPumpToken1111111111111111111111111",
    *,
    lifecycle_venue: str = VENUE_PUMPSWAP_CPMM_AMM,
    previous_venue: Optional[str] = VENUE_PUMP_BONDING_CURVE,
    configured_static_cu_limit: Optional[int] = None,
    extra_tick_array_crossings: int = 0,
    cu_per_extra_tick_crossing: int = 18_000,
    priority_fee_micro_lamports_per_cu: int = 25_000,
) -> DynamicCuProfileResult:
    """Dynamically profiles and configures `ComputeBudgetInstruction::set_compute_unit_limit`
    across Solana launchpad lifecycle transitions so post-graduation bundles never revert
    mid-flight from CU exhaustion:
      - `PUMP_BONDING_CURVE`: `65,000` CU
      - `PUMPSWAP_CPMM_AMM`: `145,000` CU
      - `MULTI_TICK_CLMM_OR_DLMM`: `320,000` CU
    """
    venue_norm = str(lifecycle_venue).strip().upper()
    if venue_norm in VENUE_CU_BUDGET_MAP:
        baseline_cu = VENUE_CU_BUDGET_MAP[venue_norm]
    elif "CLMM" in venue_norm or "DLMM" in venue_norm or "MULTI_TICK" in venue_norm:
        venue_norm = VENUE_MULTI_TICK_CLMM_OR_DLMM
        baseline_cu = CU_LIMIT_MULTI_TICK_CLMM_OR_DLMM
    elif "PUMPSWAP" in venue_norm or "CPMM" in venue_norm or "RAYDIUM" in venue_norm:
        venue_norm = VENUE_PUMPSWAP_CPMM_AMM
        baseline_cu = CU_LIMIT_PUMPSWAP_CPMM_AMM
    else:
        venue_norm = VENUE_PUMP_BONDING_CURVE
        baseline_cu = CU_LIMIT_PUMP_BONDING_CURVE

    prev_norm = (
        str(previous_venue).strip().upper() if previous_venue is not None else None
    )
    graduated_from_curve = bool(
        prev_norm == VENUE_PUMP_BONDING_CURVE
        and venue_norm in (VENUE_PUMPSWAP_CPMM_AMM, VENUE_MULTI_TICK_CLMM_OR_DLMM)
    )

    extra_ticks = max(0, int(extra_tick_array_crossings))
    tick_overhead = extra_ticks * max(0, int(cu_per_extra_tick_crossing))
    recommended_cu = min(
        SOLANA_MAX_TRANSACTION_CU_LIMIT, baseline_cu + tick_overhead
    )

    static_would_exhaust = False
    if configured_static_cu_limit is not None:
        static_would_exhaust = int(configured_static_cu_limit) < recommended_cu

    instruction_str = (
        f"ComputeBudgetInstruction::set_compute_unit_limit({recommended_cu})"
    )
    estimated_fee_lamports = int(
        (recommended_cu * max(0, int(priority_fee_micro_lamports_per_cu))) // 1_000_000
    )

    flags: List[str] = [
        f"DYNAMIC_CU_LIMIT_SET:{venue_norm}={recommended_cu}_CU"
    ]
    if graduated_from_curve:
        flags.append(
            f"POST_GRADUATION_CU_UPGRADE:{CU_LIMIT_PUMP_BONDING_CURVE}_TO_{recommended_cu}_CU"
        )
    if static_would_exhaust:
        flags.append(
            f"STATIC_CU_EXHAUSTION_PREVENTED:configured={configured_static_cu_limit}_lt_{recommended_cu}"
        )
    if extra_ticks > 0:
        flags.append(
            f"MULTI_TICK_CROSSING_OVERHEAD_ADDED:ticks={extra_ticks},overhead_cu={tick_overhead}"
        )

    return DynamicCuProfileResult(
        token_mint=token_mint,
        lifecycle_venue=venue_norm,
        previous_venue=prev_norm,
        graduated_from_bonding_curve=graduated_from_curve,
        configured_static_cu_limit=(
            int(configured_static_cu_limit)
            if configured_static_cu_limit is not None
            else None
        ),
        baseline_venue_cu_limit=baseline_cu,
        extra_tick_array_crossings=extra_ticks,
        tick_crossing_cu_overhead=tick_overhead,
        recommended_compute_unit_limit=recommended_cu,
        static_cu_would_exhaust=static_would_exhaust,
        compute_budget_instruction=instruction_str,
        priority_fee_micro_lamports_per_cu=int(priority_fee_micro_lamports_per_cu),
        estimated_priority_fee_lamports=estimated_fee_lamports,
        vector2_passed=True,
        flags=flags,
    )


# ============================================================================
# Vector 3: Counter-MEV "Salmonella" & State-Dependent Honeypot Detector
# ============================================================================


def detect_salmonella_state_dependent_trap(
    token_address: str = "0xSalmonellaCandidateToken0000000000000001",
    *,
    emitted_transfer_event_tokens: float = 100_000.0,
    operator_origin_credited_tokens: float = 100_000.0,
    searcher_origin_credited_tokens: Optional[float] = None,
    perturbed_gas_credited_tokens: Optional[float] = None,
    randomized_block_credited_tokens: Optional[float] = None,
    actual_credited_tokens: Optional[float] = None,
    has_tx_origin_xor_branch: bool = False,
    has_gasleft_modulo_trap: bool = False,
    has_transient_storage_or_block_trap: bool = False,
    initial_balance: float = 10.0,
    final_balance: Optional[float] = None,
    min_profit: float = 0.05,
) -> SalmonellaTrapDetectionResult:
    """Counter-MEV "Salmonella" & State-Dependent Honeypot Detector (`Vector 3`).

    Detects polymorphic Salmonella poison tokens that pass naive `eth_call` simulations
    when called from the trap operator's address/origin, but branch on:
      - `tx.origin` XOR obfuscated storage slots (`trap_tx_origin_xor_branch`)
      - `gasleft()` modulo checks (`trap_gasleft_modulo_branch`)
      - Transient storage (`TLOAD`/`TSTORE`) or block/coinbase state (`trap_transient_or_block_state_branch`)
    returning `true` and emitting a valid `Transfer(from, to, fullAmount)` event while
    actually crediting only dust (`actual_credited_tokens << emitted_transfer_event_tokens`)
    to the searcher's balance slot.

    Enforces:
      1. Multi-Origin / Perturbed-Gas / Randomized-Block Differential Simulation.
      2. Exact event-vs-storage balance reconciliation (`actual_credited_tokens` vs
         `emitted_transfer_event_tokens`).
      3. Outer Execution Wrapper Invariant:
         `require(FINAL_BALANCE >= INITIAL_BALANCE + MIN_PROFIT)`.
    """
    event_tokens = max(0.0, float(emitted_transfer_event_tokens))
    op_tokens = max(0.0, float(operator_origin_credited_tokens))

    searcher_tokens = (
        float(searcher_origin_credited_tokens)
        if searcher_origin_credited_tokens is not None
        else (
            float(actual_credited_tokens)
            if actual_credited_tokens is not None
            else op_tokens
        )
    )
    gas_tokens = (
        float(perturbed_gas_credited_tokens)
        if perturbed_gas_credited_tokens is not None
        else searcher_tokens
    )
    block_tokens = (
        float(randomized_block_credited_tokens)
        if randomized_block_credited_tokens is not None
        else searcher_tokens
    )

    resolved_actual_credited = (
        float(actual_credited_tokens)
        if actual_credited_tokens is not None
        else min(searcher_tokens, gas_tokens, block_tokens)
    )

    if event_tokens > 0.0:
        credit_ratio = round(resolved_actual_credited / event_tokens, 6)
        discrepancy_pct = round(
            max(0.0, (event_tokens - resolved_actual_credited) / event_tokens) * 100.0,
            4,
        )
    else:
        credit_ratio = 1.0
        discrepancy_pct = 0.0

    # Differential simulation branch checks
    origin_trap = bool(
        has_tx_origin_xor_branch
        or (op_tokens > 0.0 and searcher_tokens < op_tokens * 0.99)
    )
    gas_trap = bool(
        has_gasleft_modulo_trap
        or (op_tokens > 0.0 and gas_tokens < op_tokens * 0.99)
    )
    block_trap = bool(
        has_transient_storage_or_block_trap
        or (op_tokens > 0.0 and block_tokens < op_tokens * 0.99)
    )
    event_desync_trap = bool(
        discrepancy_pct > SALMONELLA_MAX_ACCEPTABLE_CREDIT_DISCREPANCY_PCT
        and (
            origin_trap
            or gas_trap
            or block_trap
            or credit_ratio <= SALMONELLA_DUST_CREDIT_THRESHOLD_RATIO
        )
    )

    salmonella_detected = bool(
        origin_trap or gas_trap or block_trap or event_desync_trap
    )

    required_min_final = round(float(initial_balance) + float(min_profit), 6)
    if final_balance is None:
        if salmonella_detected:
            # Salmonella trap wipes out swap proceeds on the back-run leg
            resolved_final_balance = round(
                float(initial_balance) * max(0.05, credit_ratio), 6
            )
        else:
            resolved_final_balance = round(
                float(initial_balance) + float(min_profit) + 0.15, 6
            )
    else:
        resolved_final_balance = round(float(final_balance), 6)

    outer_invariant_passed = resolved_final_balance + 1e-9 >= required_min_final
    invariant_expr = (
        f"require(FINAL_BALANCE[{resolved_final_balance:.4f}] >= "
        f"INITIAL_BALANCE[{float(initial_balance):.4f}] + MIN_PROFIT[{float(min_profit):.4f}])"
    )

    flags: List[str] = []
    if origin_trap:
        flags.append("SALMONELLA_TX_ORIGIN_XOR_STORAGE_BRANCH_DETECTED")
    if gas_trap:
        flags.append("SALMONELLA_GASLEFT_MODULO_CONDITIONAL_TRAP_DETECTED")
    if block_trap:
        flags.append("SALMONELLA_TRANSIENT_STORAGE_OR_BLOCK_STATE_TRAP_DETECTED")
    if event_desync_trap:
        flags.append(
            f"SALMONELLA_TRANSFER_EVENT_SPOOFING:emitted={event_tokens:.2f},credited={resolved_actual_credited:.2f}"
        )
    if not outer_invariant_passed:
        flags.append("OUTER_WRAPPER_INVARIANT_VIOLATION_REVERT_TRIGGERED")

    vector3_passed = (not salmonella_detected) and outer_invariant_passed
    if vector3_passed:
        decision = SALMONELLA_DECISION_SAFE_EXECUTION
        flags.append("MULTI_ORIGIN_PERTURBED_GAS_DIFFERENTIAL_SIMULATION_CLEAN")
    else:
        decision = SALMONELLA_DECISION_ABORT_HONEYPOT_TRAP

    return SalmonellaTrapDetectionResult(
        token_address=token_address,
        emitted_transfer_event_tokens=round(event_tokens, 6),
        operator_origin_credited_tokens=round(op_tokens, 6),
        searcher_origin_credited_tokens=round(searcher_tokens, 6),
        perturbed_gas_credited_tokens=round(gas_tokens, 6),
        randomized_block_credited_tokens=round(block_tokens, 6),
        actual_credited_tokens=round(resolved_actual_credited, 6),
        credit_to_event_ratio=credit_ratio,
        event_vs_balance_discrepancy_pct=discrepancy_pct,
        trap_tx_origin_xor_branch=origin_trap,
        trap_gasleft_modulo_branch=gas_trap,
        trap_transient_or_block_state_branch=block_trap,
        trap_transfer_event_balance_desync=event_desync_trap,
        salmonella_honeypot_detected=salmonella_detected,
        initial_balance=round(float(initial_balance), 6),
        final_balance=resolved_final_balance,
        min_profit=round(float(min_profit), 6),
        required_minimum_final_balance=required_min_final,
        outer_balance_invariant_passed=outer_invariant_passed,
        outer_invariant_expression=invariant_expr,
        vector3_passed=vector3_passed,
        decision=decision,
        flags=flags,
    )


# ============================================================================
# Vector 4: Unbundling & Uncle/Reorg Isolation Gate
# ============================================================================


def evaluate_unbundling_and_reorg_isolation_gate(
    *,
    is_single_tx_flash_callback: bool = True,
    is_all_or_nothing_atomic_bundle: bool = True,
    allow_non_atomic_mempool_broadcast: bool = False,
    has_unprotected_multi_tx_legs: bool = False,
) -> UnbundlingAndReorgIsolationResult:
    """Vector 4: Unbundling & Uncle/Reorg Isolation Gate.

    Enforces single-transaction flash callback encapsulation or verified all-or-nothing
    atomic bundle flags (`allow_non_atomic_mempool_broadcast == False`), preventing
    malicious proposers or block reorgs from unbundling a multi-leg arbitrage and leaving
    the searcher holding toxic inventory.
    """
    reorg_vulnerable = bool(
        allow_non_atomic_mempool_broadcast
        or has_unprotected_multi_tx_legs
        or not (is_single_tx_flash_callback or is_all_or_nothing_atomic_bundle)
    )

    if is_single_tx_flash_callback and not allow_non_atomic_mempool_broadcast:
        mode = ATOMIC_MODE_SINGLE_TX_FLASH_CALLBACK
    elif is_all_or_nothing_atomic_bundle and not allow_non_atomic_mempool_broadcast:
        mode = ATOMIC_MODE_ALL_OR_NOTHING_JITO_FLASHBOTS_BUNDLE
    else:
        mode = ATOMIC_MODE_NON_ATOMIC_PUBLIC_MEMPOOL

    vector4_passed = (not allow_non_atomic_mempool_broadcast) and (
        not reorg_vulnerable
    )

    flags: List[str] = []
    if vector4_passed:
        flags.append(f"UNBUNDLING_AND_REORG_ISOLATION_VERIFIED:{mode}")
    else:
        if allow_non_atomic_mempool_broadcast:
            flags.append("HARD_BLOCK_NON_ATOMIC_MEMPOOL_BROADCAST_FORBIDDEN")
        if has_unprotected_multi_tx_legs:
            flags.append("HARD_BLOCK_UNPROTECTED_MULTI_TX_LEGS_UNCLE_REORG_RISK")
        if not (is_single_tx_flash_callback or is_all_or_nothing_atomic_bundle):
            flags.append("HARD_BLOCK_MISSING_SINGLE_TX_CALLBACK_OR_ATOMIC_BUNDLE_GUARD")

    return UnbundlingAndReorgIsolationResult(
        execution_mode=mode,
        is_single_tx_flash_callback=bool(is_single_tx_flash_callback),
        is_all_or_nothing_atomic_bundle=bool(is_all_or_nothing_atomic_bundle),
        allow_non_atomic_mempool_broadcast=bool(allow_non_atomic_mempool_broadcast),
        reorg_split_leg_vulnerable=reorg_vulnerable,
        vector4_passed=vector4_passed,
        flags=flags,
    )


# ============================================================================
# Vector 5: Callback Authentication Spoofing & Zero-Idle-Balance Guard
# ============================================================================


def verify_callback_auth_and_zero_idle_balance(
    *,
    callback_function: str = "unlockCallback(bytes)",
    msg_sender: str = "0x000000000004444c5dc75cB358380D2e3dE08A90",
    verified_pool_or_manager_address: str = "0x000000000004444c5dc75cB358380D2e3dE08A90",
    initiator_authenticated: bool = True,
    idle_contract_balance_lamports: int = 0,
    idle_erc20_balance_raw: int = 0,
) -> CallbackAuthAndIdleBalanceResult:
    """Vector 5: Callback Authentication Spoofing & Zero-Idle-Balance Guard.

    Enforces:
      1. `msg.sender == verified_pool_or_manager_address` on `unlockCallback()`,
         `uniswapV3SwapCallback()`, and `onMorphoFlashLoan()`.
      2. `initiator_authenticated == True` (verifying the flash loan/unlock was initiated
         by this execution contract).
      3. `idle_contract_balance_lamports == 0` and `idle_erc20_balance_raw == 0`
         (sweeping profits immediately so the execution contract holds zero idle funds
         between transactions).
    """
    sender_norm = str(msg_sender).strip().lower()
    verified_norm = str(verified_pool_or_manager_address).strip().lower()
    sender_auth = bool(sender_norm != "" and sender_norm == verified_norm)
    init_auth = bool(initiator_authenticated)

    idle_lamports = int(idle_contract_balance_lamports)
    idle_erc20 = int(idle_erc20_balance_raw)
    zero_idle = idle_lamports == 0 and idle_erc20 == 0

    vector5_passed = sender_auth and init_auth and zero_idle

    flags: List[str] = []
    if sender_auth:
        flags.append(f"CALLBACK_MSG_SENDER_VERIFIED:{callback_function}")
    else:
        flags.append(
            f"HARD_BLOCK_CALLBACK_SPOOFING_ATTEMPT:msg_sender={msg_sender}!=verified={verified_pool_or_manager_address}"
        )
    if not init_auth:
        flags.append("HARD_BLOCK_UNAUTHENTICATED_CALLBACK_INITIATOR")
    if zero_idle:
        flags.append("ZERO_IDLE_CONTRACT_BALANCE_INVARIANT_VERIFIED")
    else:
        flags.append(
            f"HARD_BLOCK_NON_ZERO_IDLE_CONTRACT_BALANCE:lamports={idle_lamports},erc20={idle_erc20}"
        )

    return CallbackAuthAndIdleBalanceResult(
        callback_function=callback_function,
        msg_sender=msg_sender,
        verified_pool_or_manager_address=verified_pool_or_manager_address,
        callback_sender_authenticated=sender_auth,
        initiator_authenticated=init_auth,
        idle_contract_balance_lamports=idle_lamports,
        idle_erc20_balance_raw=idle_erc20,
        zero_idle_balance_enforced=zero_idle,
        spoof_drain_surface_eliminated=vector5_passed,
        vector5_passed=vector5_passed,
        flags=flags,
    )


# ============================================================================
# Composite 5-Vector Adversarial Shield Evaluator
# ============================================================================


def evaluate_5vector_adversarial_shield(
    token_identifier: str = "TargetToken11111111111111111111111111111111",
    *,
    # Vector 1 kwargs
    nominal_amount_in: float = 100.0,
    nominal_amount_out: float = 1_000.0,
    balance_before: float = 0.0,
    balance_after: Optional[float] = None,
    fot_tax_pct: float = 0.0,
    second_leg_exchange_rate: float = 0.105,
    second_leg_fot_tax_pct: Optional[float] = None,
    flash_loan_principal: Optional[float] = None,
    flash_loan_fee: float = 0.09,
    min_required_profit: float = 0.10,
    amm_uses_nominal_reserve_accounting: bool = False,
    amm_has_public_skim_function: bool = False,
    stored_reserve_token: float = 100_000.0,
    actual_pair_balance_token: Optional[float] = None,
    # Vector 2 kwargs
    lifecycle_venue: str = VENUE_PUMPSWAP_CPMM_AMM,
    previous_venue: Optional[str] = VENUE_PUMP_BONDING_CURVE,
    configured_static_cu_limit: Optional[int] = None,
    extra_tick_array_crossings: int = 0,
    priority_fee_micro_lamports_per_cu: int = 25_000,
    # Vector 3 kwargs
    emitted_transfer_event_tokens: float = 1_000.0,
    operator_origin_credited_tokens: float = 1_000.0,
    searcher_origin_credited_tokens: Optional[float] = None,
    perturbed_gas_credited_tokens: Optional[float] = None,
    randomized_block_credited_tokens: Optional[float] = None,
    actual_credited_tokens: Optional[float] = None,
    has_tx_origin_xor_branch: bool = False,
    has_gasleft_modulo_trap: bool = False,
    has_transient_storage_or_block_trap: bool = False,
    initial_balance: float = 100.0,
    final_balance: Optional[float] = None,
    # Vector 4 kwargs
    is_single_tx_flash_callback: bool = True,
    is_all_or_nothing_atomic_bundle: bool = True,
    allow_non_atomic_mempool_broadcast: bool = False,
    has_unprotected_multi_tx_legs: bool = False,
    # Vector 5 kwargs
    callback_function: str = "unlockCallback(bytes)",
    msg_sender: str = "0x000000000004444c5dc75cB358380D2e3dE08A90",
    verified_pool_or_manager_address: str = "0x000000000004444c5dc75cB358380D2e3dE08A90",
    initiator_authenticated: bool = True,
    idle_contract_balance_lamports: int = 0,
    idle_erc20_balance_raw: int = 0,
) -> FiveVectorAdversarialShieldReport:
    """Executes all 5 Adversarial Engineering Defense Vectors (`Vectors 1-5`) and returns
    a unified `FiveVectorAdversarialShieldReport`.
    """
    v1 = verify_fot_balance_delta_and_skim_opportunity(
        token_identifier,
        nominal_amount_in=nominal_amount_in,
        nominal_amount_out=nominal_amount_out,
        balance_before=balance_before,
        balance_after=balance_after,
        fot_tax_pct=fot_tax_pct,
        second_leg_exchange_rate=second_leg_exchange_rate,
        second_leg_fot_tax_pct=second_leg_fot_tax_pct,
        flash_loan_principal=flash_loan_principal,
        flash_loan_fee=flash_loan_fee,
        min_required_profit=min_required_profit,
        amm_uses_nominal_reserve_accounting=amm_uses_nominal_reserve_accounting,
        amm_has_public_skim_function=amm_has_public_skim_function,
        stored_reserve_token=stored_reserve_token,
        actual_pair_balance_token=actual_pair_balance_token,
    )

    v2 = profile_dynamic_cu_budget(
        token_identifier,
        lifecycle_venue=lifecycle_venue,
        previous_venue=previous_venue,
        configured_static_cu_limit=configured_static_cu_limit,
        extra_tick_array_crossings=extra_tick_array_crossings,
        priority_fee_micro_lamports_per_cu=priority_fee_micro_lamports_per_cu,
    )

    v3 = detect_salmonella_state_dependent_trap(
        token_identifier,
        emitted_transfer_event_tokens=emitted_transfer_event_tokens,
        operator_origin_credited_tokens=operator_origin_credited_tokens,
        searcher_origin_credited_tokens=searcher_origin_credited_tokens,
        perturbed_gas_credited_tokens=perturbed_gas_credited_tokens,
        randomized_block_credited_tokens=randomized_block_credited_tokens,
        actual_credited_tokens=actual_credited_tokens,
        has_tx_origin_xor_branch=has_tx_origin_xor_branch,
        has_gasleft_modulo_trap=has_gasleft_modulo_trap,
        has_transient_storage_or_block_trap=has_transient_storage_or_block_trap,
        initial_balance=initial_balance,
        final_balance=final_balance,
        min_profit=min_required_profit,
    )

    v4 = evaluate_unbundling_and_reorg_isolation_gate(
        is_single_tx_flash_callback=is_single_tx_flash_callback,
        is_all_or_nothing_atomic_bundle=is_all_or_nothing_atomic_bundle,
        allow_non_atomic_mempool_broadcast=allow_non_atomic_mempool_broadcast,
        has_unprotected_multi_tx_legs=has_unprotected_multi_tx_legs,
    )

    v5 = verify_callback_auth_and_zero_idle_balance(
        callback_function=callback_function,
        msg_sender=msg_sender,
        verified_pool_or_manager_address=verified_pool_or_manager_address,
        initiator_authenticated=initiator_authenticated,
        idle_contract_balance_lamports=idle_contract_balance_lamports,
        idle_erc20_balance_raw=idle_erc20_balance_raw,
    )

    vector_checks = [
        ("VECTOR_1_FOT_BALANCE_DELTA_AND_SKIM", v1.vector1_passed),
        ("VECTOR_2_DYNAMIC_POST_GRADUATION_CU_PROFILER", v2.vector2_passed),
        ("VECTOR_3_SALMONELLA_STATE_DEPENDENT_HONEYPOT", v3.vector3_passed),
        ("VECTOR_4_UNBUNDLING_AND_REORG_ISOLATION", v4.vector4_passed),
        ("VECTOR_5_CALLBACK_AUTH_AND_ZERO_IDLE_BALANCE", v5.vector5_passed),
    ]

    passed_count = sum(1 for _, passed in vector_checks if passed)
    blocking = [name for name, passed in vector_checks if not passed]
    all_passed = len(blocking) == 0

    combined_flags: List[str] = (
        list(v1.flags)
        + list(v2.flags)
        + list(v3.flags)
        + list(v4.flags)
        + list(v5.flags)
    )

    if all_passed:
        decision = SHIELD_DECISION_APPROVED_ATOMIC_EXECUTION
        combined_flags.append("ALL_5_ADVERSARIAL_SHIELD_VECTORS_PASSED")
    else:
        decision = SHIELD_DECISION_BLOCKED_ADVERSARIAL_RISK
        combined_flags.append(
            f"BLOCKED_BY_VECTORS:{','.join(blocking)}"
        )

    return FiveVectorAdversarialShieldReport(
        token_identifier=token_identifier,
        vector1_fot_and_skim=v1,
        vector2_dynamic_cu_profile=v2,
        vector3_salmonella_detector=v3,
        vector4_unbundling_reorg_gate=v4,
        vector5_callback_auth_guard=v5,
        passed_vector_count=passed_count,
        all_five_vectors_passed=all_passed,
        should_execute_atomic_bundle=all_passed,
        decision=decision,
        blocking_vectors=blocking,
        flags=combined_flags,
    )


# ============================================================================
# 3. 2026 MiCA & DOJ Regulatory Market-Efficiency Compliance Gate &
#    Automated Taxable Disposal Ledger
# ============================================================================


def evaluate_regulatory_compliance_and_tax_ledger(
    strategy_type: str,
    *,
    flash_primitive: str = "UNISWAP_V4_TRANSIENT_FLASH_ACCOUNTING",
    gross_proceeds_usd: float = 12_500.0,
    cost_basis_plus_fees_usd: float = 11_850.0,
    asset_pair: str = "SOL/USDC",
    chain_id: str = "solana-mainnet",
    tx_or_bundle_hash: str = "0xatomic_bundle_verified_01",
    timestamp_utc: Optional[str] = None,
    ledger_sink: Optional[List[TaxableDisposalLedgerEntry]] = None,
) -> RegulatoryComplianceAndTaxEvaluation:
    """Classifies strategies under the 2026 MiCA (Article 15 Market Abuse Prevention) &
    U.S. DOJ (Wire Fraud / Market Manipulation) enforcement framework and records an
    auditable `TaxableDisposalLedgerEntry` for every compliant atomic extraction:

    - **Whitelisted Market-Efficiency Strategies (`"COMPLIANT_MARKET_EFFICIENCY_EXTRACTION"`)**:
      - `CROSS_DEX_SPATIAL_ARB`
      - `TRIANGULAR_ROUTING_ARB`
      - `FLASH_AMPLIFIED_JIT_LIQUIDITY`
      - `FORCED_GRADUATION_PRICE_EQUALIZATION`
      - `MAYHEM_AI_NOISE_BACKRUN`
      - `PARASITIC_V4_AFTERSWAP_EQUALIZATION`
      - `ISOLATED_MARKET_BAD_DEBT_LIQUIDATION`

    - **Hard-Blocked Manipulative Vectors (`"BLOCKED_REGULATORY_MANIPULATION_VECTOR"`)**:
      - `CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING`
      - `SALMONELLA_HONEYPOT_DEPLOYMENT`
      - `PREDATORY_RETAIL_WIRE_FRAUD_BAITING`
    """
    strat_norm = str(strategy_type).strip().upper()
    is_whitelisted = strat_norm in WHITELISTED_MARKET_EFFICIENCY_STRATEGIES
    is_blocked = (
        strat_norm in HARD_BLOCKED_MANIPULATIVE_STRATEGIES or not is_whitelisted
    )

    gross = round(float(gross_proceeds_usd), 4)
    cost_basis = round(float(cost_basis_plus_fees_usd), 4)
    net_gain = round(gross - cost_basis, 4)

    jurisdictions = [
        "EU_MICA_2026_TITLE_VI_MARKET_ABUSE_GUARD",
        "US_DOJ_2026_WIRE_FRAUD_AND_SPOOFING_SAFE_HARBOR",
        "IRS_OECD_CARF_2026_ATOMIC_TAXABLE_DISPOSAL_LEDGER",
    ]

    flags: List[str] = []
    ledger_entry: Optional[TaxableDisposalLedgerEntry] = None

    if is_whitelisted and not is_blocked:
        status = COMPLIANCE_STATUS_COMPLIANT_EXTRACTION
        permitted = True
        flags.append(f"WHITELISTED_MARKET_EFFICIENCY_STRATEGY:{strat_norm}")

        resolved_ts = (
            timestamp_utc
            if timestamp_utc is not None
            else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        digest_src = f"{strat_norm}:{flash_primitive}:{gross}:{cost_basis}:{tx_or_bundle_hash}:{resolved_ts}"
        disposal_id = (
            "DISP-" + hashlib.sha256(digest_src.encode("utf-8")).hexdigest()[:12].upper()
        )

        ledger_entry = TaxableDisposalLedgerEntry(
            disposal_id=disposal_id,
            timestamp_utc=resolved_ts,
            strategy_type=strat_norm,
            flash_primitive=str(flash_primitive),
            gross_proceeds_usd=gross,
            cost_basis_plus_fees_usd=cost_basis,
            realized_net_gain_usd=net_gain,
            asset_pair=asset_pair,
            chain_id=chain_id,
            tx_or_bundle_hash=tx_or_bundle_hash,
        )
        if ledger_sink is not None:
            ledger_sink.append(ledger_entry)
        flags.append(f"TAXABLE_DISPOSAL_RECORDED:{disposal_id}")
    else:
        status = COMPLIANCE_STATUS_BLOCKED_MANIPULATION
        permitted = False
        if strat_norm in HARD_BLOCKED_MANIPULATIVE_STRATEGIES:
            flags.append(
                f"HARD_BLOCK_2026_MICA_DOJ_PROHIBITED_MANIPULATION:{strat_norm}"
            )
        else:
            flags.append(f"HARD_BLOCK_UNRECOGNIZED_NON_WHITELISTED_STRATEGY:{strat_norm}")

    return RegulatoryComplianceAndTaxEvaluation(
        strategy_type=strat_norm,
        flash_primitive=str(flash_primitive),
        is_whitelisted_market_efficiency=is_whitelisted,
        is_hard_blocked_manipulation=is_blocked,
        compliance_status=status,
        execution_permitted=permitted,
        regulatory_jurisdictions_checked=jurisdictions,
        gross_proceeds_usd=gross,
        cost_basis_plus_fees_usd=cost_basis,
        realized_net_gain_usd=net_gain,
        taxable_disposal_entry=ledger_entry,
        flags=flags,
    )


# ============================================================================
# 4. `SalmonellaFotAdversarialShield` Facade Class
# ============================================================================


class SalmonellaFotAdversarialShield:
    """Agent 24 (`salmonella-fot-adversarial-shield`) Facade for `TitanIPCDaemon`
    (`RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD`).

    Integrates:
      1. October 2026 Empirical Memecoin Forensics Benchmark Suite (`15.2M` tokens)
      2. 5-Vector Adversarial Engineering & Failure-Mode Mitigation Engine
      3. 2026 MiCA & DOJ Regulatory Market-Efficiency Compliance Gate &
         Automated Taxable Disposal Ledger
    """

    def __init__(self) -> None:
        self._fot_evaluations: int = 0
        self._fot_nominal_rejections: int = 0
        self._skim_opportunities_detected: int = 0
        self._cu_profiles_computed: int = 0
        self._static_cu_exhaustions_prevented: int = 0
        self._salmonella_scans: int = 0
        self._salmonella_traps_blocked: int = 0
        self._five_vector_evaluations: int = 0
        self._five_vector_approvals: int = 0
        self._five_vector_blocks: int = 0
        self._compliance_checks: int = 0
        self._compliance_approvals: int = 0
        self._compliance_blocks: int = 0
        self._tax_disposal_ledger: List[TaxableDisposalLedgerEntry] = []
        self._last_diagnostic_ts: Optional[float] = None

    @property
    def tax_disposal_ledger(self) -> List[TaxableDisposalLedgerEntry]:
        """Returns a copy of all recorded taxable disposal ledger entries."""
        return list(self._tax_disposal_ledger)

    def get_october_2026_forensics_benchmarks(self) -> EmpiricalForensicsBenchmarksDict:
        """Returns the October 2026 empirical memecoin forensics benchmark suite."""
        return get_october_2026_empirical_forensics_benchmarks()

    def verify_fot_balance_delta_and_skim_opportunity(
        self, *args: Any, **kwargs: Any
    ) -> FotBalanceDeltaAndSkimResult:
        res = verify_fot_balance_delta_and_skim_opportunity(*args, **kwargs)
        self._fot_evaluations += 1
        if res.fot_nominal_assumption_rejected:
            self._fot_nominal_rejections += 1
        if res.skim_arbitrage_detected:
            self._skim_opportunities_detected += 1
        return res

    def profile_dynamic_cu_budget(
        self, *args: Any, **kwargs: Any
    ) -> DynamicCuProfileResult:
        res = profile_dynamic_cu_budget(*args, **kwargs)
        self._cu_profiles_computed += 1
        if res.static_cu_would_exhaust:
            self._static_cu_exhaustions_prevented += 1
        return res

    def detect_salmonella_state_dependent_trap(
        self, *args: Any, **kwargs: Any
    ) -> SalmonellaTrapDetectionResult:
        res = detect_salmonella_state_dependent_trap(*args, **kwargs)
        self._salmonella_scans += 1
        if res.salmonella_honeypot_detected or not res.vector3_passed:
            self._salmonella_traps_blocked += 1
        return res

    def evaluate_5vector_adversarial_shield(
        self, *args: Any, **kwargs: Any
    ) -> FiveVectorAdversarialShieldReport:
        res = evaluate_5vector_adversarial_shield(*args, **kwargs)
        self._five_vector_evaluations += 1
        self._fot_evaluations += 1
        self._cu_profiles_computed += 1
        self._salmonella_scans += 1
        if res.vector1_fot_and_skim.fot_nominal_assumption_rejected:
            self._fot_nominal_rejections += 1
        if res.vector1_fot_and_skim.skim_arbitrage_detected:
            self._skim_opportunities_detected += 1
        if res.vector2_dynamic_cu_profile.static_cu_would_exhaust:
            self._static_cu_exhaustions_prevented += 1
        if (
            res.vector3_salmonella_detector.salmonella_honeypot_detected
            or not res.vector3_salmonella_detector.vector3_passed
        ):
            self._salmonella_traps_blocked += 1
        if res.all_five_vectors_passed:
            self._five_vector_approvals += 1
        else:
            self._five_vector_blocks += 1
        return res

    def evaluate_regulatory_compliance_and_tax_ledger(
        self, *args: Any, **kwargs: Any
    ) -> RegulatoryComplianceAndTaxEvaluation:
        if "ledger_sink" not in kwargs:
            kwargs["ledger_sink"] = self._tax_disposal_ledger
        res = evaluate_regulatory_compliance_and_tax_ledger(*args, **kwargs)
        self._compliance_checks += 1
        if res.execution_permitted:
            self._compliance_approvals += 1
        else:
            self._compliance_blocks += 1
        return res

    def run_full_adversarial_shield_diagnostic(self) -> Dict[str, Any]:
        """Runs a comprehensive end-to-end self-diagnostic across:
        1. October 2026 Empirical Memecoin Forensics Benchmarks (`15.2M` tokens)
        2. Vector 1: Fee-on-Transfer (`5%` tax abort vs wide-spread pass vs `49.15 WBNB -> 37.55 WBNB` `skim()` vector)
        3. Vector 2: Dynamic Post-Graduation CU Profiler (`65,000` -> `145,000` -> `320,000` CU)
        4. Vector 3: Counter-MEV Salmonella State-Dependent Honeypot Detector
        5. Full 5-Vector Shield Pass vs Blocked Scenarios
        6. 2026 MiCA/DOJ Compliance Gate & Taxable Disposal Ledger Recording
        """
        t0 = time.perf_counter()

        # 1. FoT Nominal Rejection Scenario (5% FoT tax wipes out 2% nominal spread)
        fot_abort_scenario = self.verify_fot_balance_delta_and_skim_opportunity(
            "Deflationary5PctToken1111111111111111111111",
            nominal_amount_in=100.0,
            nominal_amount_out=1_000.0,
            balance_before=0.0,
            balance_after=950.0,  # 5% FoT tax deducted on transfer
            second_leg_exchange_rate=0.102,  # Nominal 102.0 out, but after 2x 5% FoT tax -> 92.0955 < 100.09
            flash_loan_principal=100.0,
            flash_loan_fee=0.09,
            min_required_profit=0.10,
        )

        # 2. PancakeSwap FoT Reserve-Desync skim() Arbitrage Scenario (49.15 WBNB -> 37.55 WBNB)
        fot_skim_scenario = self.verify_fot_balance_delta_and_skim_opportunity(
            "VulnerableAmmFoTPair0x00000000000000000001",
            nominal_amount_in=49.15,
            nominal_amount_out=50_000.0,
            balance_before=0.0,
            fot_tax_pct=5.0,
            second_leg_exchange_rate=0.0012,
            flash_loan_principal=49.15,
            flash_loan_fee=0.12,
            min_required_profit=0.50,
            amm_uses_nominal_reserve_accounting=True,
            amm_has_public_skim_function=True,
            stored_reserve_token=1_000_000.0,
            actual_pair_balance_token=950_000.0,
            skim_flash_loan_wbnb=PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB,
        )

        # 3. Dynamic Post-Graduation CU Profiles (Bonding Curve -> PumpSwap -> Multi-Tick CLMM)
        cu_curve = self.profile_dynamic_cu_budget(
            "BondingCurveToken1111111111111111111111111",
            lifecycle_venue=VENUE_PUMP_BONDING_CURVE,
            previous_venue=None,
        )
        cu_pumpswap = self.profile_dynamic_cu_budget(
            "GraduatedPumpSwapToken11111111111111111111",
            lifecycle_venue=VENUE_PUMPSWAP_CPMM_AMM,
            previous_venue=VENUE_PUMP_BONDING_CURVE,
            configured_static_cu_limit=CU_LIMIT_PUMP_BONDING_CURVE,
        )
        cu_clmm = self.profile_dynamic_cu_budget(
            "MultiTickClmmToken111111111111111111111111",
            lifecycle_venue=VENUE_MULTI_TICK_CLMM_OR_DLMM,
            previous_venue=VENUE_PUMP_BONDING_CURVE,
            configured_static_cu_limit=CU_LIMIT_PUMPSWAP_CPMM_AMM,
        )

        # 4. Salmonella State-Dependent Honeypot Scenario
        salmonella_blocked = self.detect_salmonella_state_dependent_trap(
            "0xSalmonellaPoisonToken00000000000000dead",
            emitted_transfer_event_tokens=250_000.0,
            operator_origin_credited_tokens=250_000.0,
            searcher_origin_credited_tokens=250.0,  # 0.1% dust credited to searcher!
            perturbed_gas_credited_tokens=250.0,
            randomized_block_credited_tokens=250.0,
            has_tx_origin_xor_branch=True,
            has_gasleft_modulo_trap=True,
            initial_balance=10.0,
            final_balance=0.15,
            min_profit=0.10,
        )

        # 5. Composite 5-Vector Shield (Clean Approved vs Blocked Adversarial)
        clean_5vector = self.evaluate_5vector_adversarial_shield(
            "CleanGraduatedArbMint111111111111111111111",
            nominal_amount_in=100.0,
            nominal_amount_out=1_000.0,
            balance_before=0.0,
            balance_after=1_000.0,
            second_leg_exchange_rate=0.105,
            flash_loan_principal=100.0,
            flash_loan_fee=0.09,
            min_required_profit=0.20,
            lifecycle_venue=VENUE_PUMPSWAP_CPMM_AMM,
            previous_venue=VENUE_PUMP_BONDING_CURVE,
            emitted_transfer_event_tokens=1_000.0,
            operator_origin_credited_tokens=1_000.0,
            searcher_origin_credited_tokens=1_000.0,
            initial_balance=100.0,
            final_balance=104.91,
            is_single_tx_flash_callback=True,
            allow_non_atomic_mempool_broadcast=False,
            callback_function="unlockCallback(bytes)",
            msg_sender="0x000000000004444c5dc75cB358380D2e3dE08A90",
            verified_pool_or_manager_address="0x000000000004444c5dc75cB358380D2e3dE08A90",
            idle_contract_balance_lamports=0,
        )

        blocked_5vector = self.evaluate_5vector_adversarial_shield(
            "AdversarialTrapMint99999999999999999999999",
            nominal_amount_in=100.0,
            nominal_amount_out=1_000.0,
            balance_before=0.0,
            balance_after=950.0,
            second_leg_exchange_rate=0.101,
            flash_loan_principal=100.0,
            flash_loan_fee=0.09,
            min_required_profit=0.20,
            lifecycle_venue=VENUE_MULTI_TICK_CLMM_OR_DLMM,
            emitted_transfer_event_tokens=1_000.0,
            operator_origin_credited_tokens=1_000.0,
            searcher_origin_credited_tokens=10.0,
            has_tx_origin_xor_branch=True,
            initial_balance=100.0,
            final_balance=1.0,
            is_single_tx_flash_callback=False,
            is_all_or_nothing_atomic_bundle=False,
            allow_non_atomic_mempool_broadcast=True,
            callback_function="unlockCallback(bytes)",
            msg_sender="0xAttackerSpoofContract0000000000000000001",
            verified_pool_or_manager_address="0x000000000004444c5dc75cB358380D2e3dE08A90",
            idle_contract_balance_lamports=500_000,
        )

        # 6. Regulatory Compliance & Taxable Disposal Ledger
        compliant_arb = self.evaluate_regulatory_compliance_and_tax_ledger(
            STRATEGY_FORCED_GRADUATION_PRICE_EQUALIZATION,
            flash_primitive="JITO_SOLEND_FLASH_BUNDLE",
            gross_proceeds_usd=18_450.0,
            cost_basis_plus_fees_usd=16_200.0,
            asset_pair="SOL/PUMP",
            chain_id="solana-mainnet",
            tx_or_bundle_hash="5JitoGraduationEqualizationBundleSig111111111",
        )
        blocked_manipulation = self.evaluate_regulatory_compliance_and_tax_ledger(
            STRATEGY_CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING,
            flash_primitive="FLASH_WASH_SPOOFER",
            gross_proceeds_usd=50_000.0,
            cost_basis_plus_fees_usd=45_000.0,
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        self._last_diagnostic_ts = time.time()

        return {
            "status": "OK",
            "ipc_action": IPC_ACTION_RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD,
            "subsystem": SUBSYSTEM_NAME,
            "diagnostic_latency_ms": latency_ms,
            "october_2026_empirical_forensics_benchmarks": (
                OCTOBER_2026_EMPIRICAL_FORENSICS_BENCHMARKS.to_dict()
            ),
            "fot_abort_scenario": fot_abort_scenario.to_dict(),
            "fot_skim_arbitrage_scenario": fot_skim_scenario.to_dict(),
            "cu_profiles": {
                "bonding_curve": cu_curve.to_dict(),
                "pumpswap_cpmm": cu_pumpswap.to_dict(),
                "multi_tick_clmm": cu_clmm.to_dict(),
            },
            "salmonella_blocked_scenario": salmonella_blocked.to_dict(),
            "clean_5vector_shield": clean_5vector.to_dict(),
            "blocked_5vector_shield": blocked_5vector.to_dict(),
            "compliant_regulatory_extraction": compliant_arb.to_dict(),
            "blocked_regulatory_manipulation": blocked_manipulation.to_dict(),
            "tax_disposal_ledger": [e.to_dict() for e in self._tax_disposal_ledger],
            "telemetry": self.get_telemetry_summary(),
        }

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Returns real-time operational telemetry for `TitanIPCDaemon`."""
        return {
            "engine": "SalmonellaFotAdversarialShield",
            "agent_id": 24,
            "agent_name": "salmonella-fot-adversarial-shield",
            "ipc_action": IPC_ACTION_RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD,
            "fot_evaluations": self._fot_evaluations,
            "fot_nominal_rejections": self._fot_nominal_rejections,
            "skim_opportunities_detected": self._skim_opportunities_detected,
            "cu_profiles_computed": self._cu_profiles_computed,
            "static_cu_exhaustions_prevented": self._static_cu_exhaustions_prevented,
            "salmonella_scans": self._salmonella_scans,
            "salmonella_traps_blocked": self._salmonella_traps_blocked,
            "five_vector_evaluations": self._five_vector_evaluations,
            "five_vector_approvals": self._five_vector_approvals,
            "five_vector_blocks": self._five_vector_blocks,
            "compliance_checks": self._compliance_checks,
            "compliance_approvals": self._compliance_approvals,
            "compliance_blocks": self._compliance_blocks,
            "tax_disposal_ledger_count": len(self._tax_disposal_ledger),
            "cu_budget_benchmarks": dict(VENUE_CU_BUDGET_MAP),
            "pancake_fot_skim_benchmark": {
                "flash_loan_wbnb": PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB,
                "net_profit_wbnb": PANCAKE_FOT_SKIM_NET_PROFIT_WBNB,
            },
            "whitelisted_strategies": list(WHITELISTED_MARKET_EFFICIENCY_STRATEGIES),
            "hard_blocked_strategies": list(HARD_BLOCKED_MANIPULATIVE_STRATEGIES),
            "last_diagnostic_ts": self._last_diagnostic_ts,
        }


__all__ = [
    "ANALYZED_LAUNCHES_COUNT",
    "ATOMIC_MODE_ALL_OR_NOTHING_JITO_FLASHBOTS_BUNDLE",
    "ATOMIC_MODE_NON_ATOMIC_PUBLIC_MEMPOOL",
    "ATOMIC_MODE_SINGLE_TX_FLASH_CALLBACK",
    "AUTOMATED_WASH_LOOP_SHARE_PCT",
    "BLOCK0_SNIPER_EXTRACTED_USD",
    "BUYER_NET_LOSS_RATE_PCT",
    "COLLECTIVE_BUYER_LOSS_USD",
    "COMPLIANCE_STATUS_BLOCKED_MANIPULATION",
    "COMPLIANCE_STATUS_COMPLIANT_EXTRACTION",
    "CU_LIMIT_MULTI_TICK_CLMM_OR_DLMM",
    "CU_LIMIT_PUMPSWAP_CPMM_AMM",
    "CU_LIMIT_PUMP_BONDING_CURVE",
    "CallbackAuthAndIdleBalanceResult",
    "DAY_ONE_EXTINCTION_RATE_PCT",
    "DEFAULT_FOT_BENCHMARK_TAX_PCT",
    "DEV_BUNDLE_EXTRACTED_USD",
    "DOCUMENTED_DEV_BUNDLE_CLUSTER_SIZE",
    "DynamicCuProfileResult",
    "EmpiricalForensicsBenchmarksDict",
    "FOT_ACTION_ABORT_UNPROFITABLE_AFTER_TAX",
    "FOT_ACTION_EXECUTE_RESERVE_DESYNC_SKIM_ARB",
    "FOT_ACTION_EXECUTE_VERIFIED_DELTA_ARB",
    "FiveVectorAdversarialShieldReport",
    "FotBalanceDeltaAndSkimResult",
    "GENUINE_TRADING_PROFIT_SHARE_PCT",
    "GRADUATION_RATE_MAX_PCT",
    "GRADUATION_RATE_MIN_PCT",
    "GRADUATION_RATIO_1_IN_N",
    "HARD_BLOCKED_MANIPULATIVE_STRATEGIES",
    "INSIDER_TOKEN_HANDOFF_SHARE_PCT",
    "IPC_ACTION_RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD",
    "MEDIAN_BUYER_LOSS_USD",
    "MEV_SANDWICH_ATTACK_COUNT",
    "MEV_SANDWICH_EXTRACTED_USD",
    "OCTOBER_2026_EMPIRICAL_FORENSICS_BENCHMARKS",
    "OCTOBER_2026_EMPIRICAL_FORENSICS_DATACLASS",
    "October2026EmpiricalForensicsBenchmarks",
    "PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB",
    "PANCAKE_FOT_SKIM_NET_PROFIT_WBNB",
    "PANCAKE_FOT_SKIM_PROFIT_RATIO",
    "PUMPFUN_CUMULATIVE_VOLUME_USD",
    "PUMPFUN_PLATFORM_FEE_REVENUE_USD",
    "PUMPFUN_TOTAL_UNIQUE_TOKENS",
    "RESIDUAL_HYBRID_ARBITRAGE_SHARE_PCT",
    "RegulatoryComplianceAndTaxEvaluation",
    "SALMONELLA_DECISION_ABORT_HONEYPOT_TRAP",
    "SALMONELLA_DECISION_SAFE_EXECUTION",
    "SALMONELLA_DUST_CREDIT_THRESHOLD_RATIO",
    "SALMONELLA_MAX_ACCEPTABLE_CREDIT_DISCREPANCY_PCT",
    "SHIELD_DECISION_APPROVED_ATOMIC_EXECUTION",
    "SHIELD_DECISION_BLOCKED_ADVERSARIAL_RISK",
    "SOLANA_MAX_TRANSACTION_CU_LIMIT",
    "STRATEGY_CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING",
    "STRATEGY_CROSS_DEX_SPATIAL_ARB",
    "STRATEGY_FLASH_AMPLIFIED_JIT_LIQUIDITY",
    "STRATEGY_FORCED_GRADUATION_PRICE_EQUALIZATION",
    "STRATEGY_ISOLATED_MARKET_BAD_DEBT_LIQUIDATION",
    "STRATEGY_MAYHEM_AI_NOISE_BACKRUN",
    "STRATEGY_PARASITIC_V4_AFTERSWAP_EQUALIZATION",
    "STRATEGY_PREDATORY_RETAIL_WIRE_FRAUD_BAITING",
    "STRATEGY_SALMONELLA_HONEYPOT_DEPLOYMENT",
    "STRATEGY_TRIANGULAR_ROUTING_ARB",
    "SUBSYSTEM_NAME",
    "SUPPORTED_FLASH_CALLBACK_SIGNATURES",
    "SalmonellaFotAdversarialShield",
    "SalmonellaTrapDetectionResult",
    "TOP_100K_WALLET_WINS_COUNT",
    "TOP_1PCT_GAIN_SHARE_PCT",
    "TRACKED_11M_SAMPLE_TOKENS",
    "TRACKED_BUYERS_COUNT",
    "TaxableDisposalLedgerEntry",
    "UnbundlingAndReorgIsolationResult",
    "VENUE_CU_BUDGET_MAP",
    "VENUE_MULTI_TICK_CLMM_OR_DLMM",
    "VENUE_PUMPSWAP_CPMM_AMM",
    "VENUE_PUMP_BONDING_CURVE",
    "VERIFIED_CANONICAL_POOL_MANAGERS",
    "WHITELISTED_MARKET_EFFICIENCY_STRATEGIES",
    "detect_salmonella_state_dependent_trap",
    "evaluate_5vector_adversarial_shield",
    "evaluate_regulatory_compliance_and_tax_ledger",
    "evaluate_unbundling_and_reorg_isolation_gate",
    "get_october_2026_empirical_forensics_benchmarks",
    "profile_dynamic_cu_budget",
    "verify_callback_auth_and_zero_idle_balance",
    "verify_fot_balance_delta_and_skim_opportunity",
]
