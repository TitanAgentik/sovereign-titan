"""Sovereign Titan OS — Agent 27 (`crank-buyback-bridge-lookahead`):
Protocol Auto-Buyback-and-Burn / Token-2022 `TransferFeeConfig` Crank Front-Runner &
Cross-Chain (`Mayan Swift` / `deBridge DLN` / `Relay`) Inbound Whale Bridge Lookahead
(`src/engines/crank_buyback_and_bridge_lookahead.py`).

Implements:
1. **Protocol Auto-Buyback-and-Burn & Token-2022 `TransferFeeConfig` Crank Front-Runner
   (`evaluate_protocol_buyback_and_tax_crank`)**:
   - Models deterministic on-chain buyback/burn vaults:
     - `PUMPSWAP_CREATOR_FEE_AUTO_BURN`
     - `BELIEVE_LAUNCHCOIN_BUYBACK_VAULT`
     - `TOKEN2022_WITHHELD_TAX_HARVESTER`
     - `RAYDIUM_BUYBACK_BURN_CRANK`
   - Monitors `accumulated_vault_sol` (or withheld Token-2022 fee balance convertible via
     `withdrawWithheldTokensFromAccounts`) against `crank_trigger_threshold_sol`.
   - When `accumulated_vault_sol >= 0.98 * crank_trigger_threshold_sol` and
     `permissionless_crank_callable == True`:
     - Computes the exact price impact $\\Delta P_{\\text{crank}}$ that the protocol vault's
       forced market-buy will exert on the AMM pool $(R_{\\text{sol}}, R_{\\text{token}})$.
     - Simulates the **Atomic 3-Step Kamino Flash-Loan Crank Sandwich**:
       1. `Step 1`: Borrow optimal SOL via Kamino Flash Loan (`0.001%` fee) and buy the token
          on the AMM pool before the crank executes.
       2. `Step 2`: Invoke the permissionless `trigger_buyback_and_burn` /
          `harvest_withheld_tax_to_lp` crank instruction inside the exact same transaction/bundle,
          forcing the protocol's accumulated vault SOL to buy into our position at an elevated price.
       3. `Step 3`: Immediately sell the acquired tokens into the post-crank pool, repay Kamino,
          and capture risk-free deterministic profit (`net_profit_sol > 0.0`).

2. **Cross-Chain Inbound Whale Bridge Intent Lookahead (`Mayan Swift` / `deBridge DLN` / `Relay`)
   (`evaluate_cross_chain_whale_bridge_lookahead`)**:
   - Monitors source-chain order creation events (`OrderCreated` / `SwapInitiated`) emitted on
     **Ethereum, Base, and Arbitrum** across `MAYAN_SWIFT`, `DEBRIDGE_DLN`, and `RELAY_INTENTS`
     where `inbound_amount_usd >= 25_000.0` and the destination chain is Solana
     (`chain_id = 7565164` / `solana-mainnet`).
   - Models the **3.0 to 12.0 second Cross-Chain Solver Relay Window** (`estimated_arrival_window_sec`)
     between source-chain transaction inclusion and Solana destination fulfillment:
     - Verifies the target Solana token passes the 6-Gate Smart Contract Firewall
       (`firewall_passed == True`) and computes the expected price impact of the incoming whale
       bridge order on the target Solana AMM pool.
     - Triggers `PRE_POSITION_BEFORE_BRIDGE_SOLVER` (`3–10 seconds` ahead of the bridge solver
       on Solana) and sets an automatic limit/scale-out sell directly into the bridge solver's
       incoming market-buy sweep.
     - Also evaluates **Direct Intent Solver Fulfillment (`FULFILL_AS_LOCAL_DLN_SOLVER`)** using
       Kamino flash liquidity when the cross-chain auction offers a positive solver spread
       (`solver_spread_bps >= 8.0`).

3. **`CrankBuybackAndBridgeLookaheadEngine` Facade Class**:
   - Provides `run_full_crank_bridge_diagnostic() -> Dict[str, Any]` and
     `get_telemetry_summary() -> Dict[str, Any]` for `TitanIPCDaemon`
     (`RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================================
# Architectural & Empirical Constants
# ============================================================================

IPC_ACTION_RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD: str = (
    "RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD"
)

# 1. Protocol Auto-Buyback-and-Burn & Token-2022 TransferFeeConfig Crank Constants
VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN: str = "PUMPSWAP_CREATOR_FEE_AUTO_BURN"
VAULT_BELIEVE_LAUNCHCOIN_BUYBACK_VAULT: str = "BELIEVE_LAUNCHCOIN_BUYBACK_VAULT"
VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER: str = "TOKEN2022_WITHHELD_TAX_HARVESTER"
VAULT_RAYDIUM_BUYBACK_BURN_CRANK: str = "RAYDIUM_BUYBACK_BURN_CRANK"

SUPPORTED_BUYBACK_AND_TAX_VAULTS: Tuple[str, ...] = (
    VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN,
    VAULT_BELIEVE_LAUNCHCOIN_BUYBACK_VAULT,
    VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER,
    VAULT_RAYDIUM_BUYBACK_BURN_CRANK,
)

CRANK_TRIGGER_FILL_RATIO_MIN: float = 0.98  # accumulated_vault_sol >= 0.98 * crank_trigger_threshold_sol
KAMINO_FLASH_LOAN_FEE_PCT: float = 0.001  # 0.001% = 0.1 bps Kamino flash loan fee
KAMINO_FLASH_LOAN_FEE_RATE: float = 0.00001  # 1e-5 decimal fee multiplier
KAMINO_FLASH_LOAN_FEE_BPS: float = 0.1

DEFAULT_AMM_SWAP_FEE_BPS: float = 25.0  # 0.25% standard Raydium/PumpSwap pool swap fee
DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL: float = 0.0005  # 500,000 lamports priority bundle tip
DEFAULT_SOL_PRICE_USD: float = 190.0

# Instruction discriminators / names per vault archetype
VAULT_CRANK_INSTRUCTIONS: Dict[str, Tuple[str, ...]] = {
    VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN: (
        "trigger_buyback_and_burn",
        "pumpswap_burn_acquired_tokens",
    ),
    VAULT_BELIEVE_LAUNCHCOIN_BUYBACK_VAULT: (
        "trigger_buyback_and_burn",
        "believe_vault_burn_and_emit",
    ),
    VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER: (
        "withdrawWithheldTokensFromAccounts",
        "harvest_withheld_tax_to_lp",
    ),
    VAULT_RAYDIUM_BUYBACK_BURN_CRANK: (
        "trigger_buyback_and_burn",
        "raydium_cp_swap_buy_and_burn",
    ),
}

# Crank Action Verdicts
ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH: str = "EXECUTE_ATOMIC_CRANK_SANDWICH"
ACTION_STAGE_PRE_CRANK_ACCUMULATION: str = "STAGE_PRE_CRANK_ACCUMULATION"
ACTION_ABORT_CRANK_NOT_PERMISSIONLESS: str = "ABORT_CRANK_NOT_PERMISSIONLESS"
ACTION_ABORT_CRANK_UNSUPPORTED_VAULT: str = "ABORT_CRANK_UNSUPPORTED_VAULT"
ACTION_SKIP_CRANK_BELOW_THRESHOLD: str = "SKIP_CRANK_BELOW_THRESHOLD"
ACTION_SKIP_CRANK_NEGATIVE_NET_EV: str = "SKIP_CRANK_NEGATIVE_NET_EV"

# 2. Cross-Chain Inbound Whale Bridge Intent Lookahead Constants
BRIDGE_PROTOCOL_MAYAN_SWIFT: str = "MAYAN_SWIFT"
BRIDGE_PROTOCOL_DEBRIDGE_DLN: str = "DEBRIDGE_DLN"
BRIDGE_PROTOCOL_RELAY_INTENTS: str = "RELAY_INTENTS"

SUPPORTED_BRIDGE_PROTOCOLS: Tuple[str, ...] = (
    BRIDGE_PROTOCOL_MAYAN_SWIFT,
    BRIDGE_PROTOCOL_DEBRIDGE_DLN,
    BRIDGE_PROTOCOL_RELAY_INTENTS,
)

SOURCE_CHAIN_ETHEREUM: str = "ETHEREUM"
SOURCE_CHAIN_BASE: str = "BASE"
SOURCE_CHAIN_ARBITRUM: str = "ARBITRUM"

SUPPORTED_EVM_SOURCE_CHAINS: Tuple[str, ...] = (
    SOURCE_CHAIN_ETHEREUM,
    SOURCE_CHAIN_BASE,
    SOURCE_CHAIN_ARBITRUM,
)

SUPPORTED_BRIDGE_EVENTS: Tuple[str, ...] = (
    "OrderCreated",
    "SwapInitiated",
)

SOLANA_DEBRIDGE_DLN_CHAIN_ID: int = 7565164
SOLANA_MAINNET_CHAIN_ALIASES: Tuple[str, ...] = (
    "7565164",
    "solana-mainnet",
    "solana",
    "sol",
)

MIN_INBOUND_WHALE_BRIDGE_USD: float = 25_000.0
BRIDGE_RELAY_WINDOW_MIN_SEC: float = 3.0
BRIDGE_RELAY_WINDOW_MAX_SEC: float = 12.0

PRE_POSITION_LEAD_TIME_MIN_SEC: float = 3.0
PRE_POSITION_LEAD_TIME_MAX_SEC: float = 10.0

MIN_LOCAL_DLN_SOLVER_SPREAD_BPS: float = 8.0

# Empirical median solver relay latencies (seconds) per protocol & source chain
DEFAULT_PROTOCOL_RELAY_LATENCY_SEC: Dict[str, float] = {
    BRIDGE_PROTOCOL_MAYAN_SWIFT: 4.8,
    BRIDGE_PROTOCOL_DEBRIDGE_DLN: 6.2,
    BRIDGE_PROTOCOL_RELAY_INTENTS: 4.1,
}

# Bridge Lookahead Action Verdicts
ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER: str = "PRE_POSITION_BEFORE_BRIDGE_SOLVER"
ACTION_FULFILL_AS_LOCAL_DLN_SOLVER: str = "FULFILL_AS_LOCAL_DLN_SOLVER"
ACTION_ABORT_BRIDGE_FIREWALL_FAILED: str = "ABORT_BRIDGE_FIREWALL_FAILED"
ACTION_SKIP_BRIDGE_BELOW_WHALE_THRESHOLD: str = "SKIP_BRIDGE_BELOW_WHALE_THRESHOLD"
ACTION_SKIP_BRIDGE_NON_SOLANA_DEST: str = "SKIP_BRIDGE_NON_SOLANA_DEST"
ACTION_SKIP_BRIDGE_UNSUPPORTED_SOURCE: str = "SKIP_BRIDGE_UNSUPPORTED_SOURCE"
ACTION_SKIP_BRIDGE_OUTSIDE_RELAY_WINDOW: str = "SKIP_BRIDGE_OUTSIDE_RELAY_WINDOW"


# ============================================================================
# Dataclasses for Structured Telemetry & Audit Traces
# ============================================================================


@dataclass(frozen=True)
class CrankSandwichStepTrace:
    """Detailed execution trace for each of the 3 steps in the atomic Kamino
    flash-loan crank sandwich.
    """

    step_index: int
    step_name: str
    instruction_name: str
    sol_in: float
    sol_out: float
    tokens_delta: float
    pool_sol_reserve_after: float
    pool_token_reserve_after: float
    spot_price_sol_after: float
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProtocolBuybackAndTaxCrankResult:
    """Structured evaluation result for Strategy 1:
    Protocol Auto-Buyback-and-Burn & Token-2022 `TransferFeeConfig` Crank Front-Runner.
    """

    token_mint: str
    vault_type: str
    permissionless_crank_callable: bool
    accumulated_vault_sol: float
    crank_trigger_threshold_sol: float
    vault_fill_ratio: float
    near_or_above_threshold: bool
    withheld_token_balance: float
    withheld_accounts_count: int
    token2022_transfer_fee_bps: float
    withdraw_withheld_callable: bool
    pool_sol_reserve_before: float
    pool_token_reserve_before: float
    spot_price_sol_before: float
    crank_standalone_price_impact_pct: float
    crank_standalone_price_impact_bps: float
    kamino_flash_borrow_sol: float
    kamino_flash_fee_sol: float
    jito_bundle_tip_sol: float
    step1_tokens_acquired: float
    step1_spot_price_after_buy: float
    step2_crank_sol_injected: float
    step2_crank_tokens_burned_or_lp: float
    step2_spot_price_after_crank: float
    step3_sol_received_from_sell: float
    step3_spot_price_after_sell: float
    gross_profit_sol: float
    net_profit_sol: float
    net_profit_usd: float
    roi_on_flash_borrow_bps: float
    sandwich_triggered: bool
    recommended_action: str
    crank_instruction_name: str
    instruction_sequence: List[str]
    atomic_steps: List[Dict[str, Any]]
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScaleOutLimitOrderTranche:
    """Single scale-out limit order tranche placed ahead of an incoming cross-chain
    whale bridge solver sweep.
    """

    tranche_index: int
    allocation_pct: float
    token_quantity: float
    target_exit_price_sol: float
    target_upside_bps: float
    expected_proceeds_sol: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CrossChainWhaleBridgeLookaheadResult:
    """Structured evaluation result for Strategy 2:
    Cross-Chain Inbound Whale Bridge Intent Lookahead (`Mayan Swift`, `deBridge DLN`, `Relay`).
    """

    order_id: str
    bridge_protocol: str
    source_chain: str
    event_name: str
    destination_chain_id: int
    destination_is_solana: bool
    target_solana_mint: str
    inbound_amount_usd: float
    inbound_amount_sol_equiv: float
    whale_threshold_met: bool
    estimated_arrival_window_sec: float
    within_relay_window: bool
    firewall_passed: bool
    firewall_gates_verified: int
    pool_sol_reserve: float
    pool_token_reserve: float
    spot_price_sol_before: float
    expected_solver_price_impact_pct: float
    expected_solver_price_impact_bps: float
    spot_price_sol_after_solver: float
    pre_position_triggered: bool
    pre_position_lead_time_sec: float
    pre_position_size_sol: float
    pre_position_tokens_acquired: float
    pre_position_gross_profit_sol: float
    pre_position_net_profit_sol: float
    pre_position_net_profit_usd: float
    auto_scale_out_limit_orders: List[Dict[str, Any]]
    solver_spread_bps: float
    local_solver_eligible: bool
    local_solver_triggered: bool
    local_solver_action: str
    local_solver_kamino_flash_sol: float
    local_solver_kamino_fee_sol: float
    local_solver_net_profit_sol: float
    local_solver_net_profit_usd: float
    active_strategies: List[str]
    recommended_action: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Constant-Product AMM & Sandwich Optimization Helpers
# ============================================================================


def _amm_buy_tokens_with_sol(
    sol_in: float,
    reserve_sol: float,
    reserve_token: float,
    amm_fee_bps: float = DEFAULT_AMM_SWAP_FEE_BPS,
) -> Tuple[float, float, float]:
    """Executes a constant-product AMM buy (`SOL -> Token`) with fee `amm_fee_bps`.
    Returns `(tokens_out, new_reserve_sol, new_reserve_token)`.
    """
    if sol_in <= 0.0 or reserve_sol <= 0.0 or reserve_token <= 0.0:
        return 0.0, reserve_sol, reserve_token

    fee_multiplier = max(0.0, 1.0 - (amm_fee_bps / 10_000.0))
    effective_sol_in = sol_in * fee_multiplier
    k = reserve_sol * reserve_token
    new_reserve_token = k / (reserve_sol + effective_sol_in)
    tokens_out = max(0.0, reserve_token - new_reserve_token)
    new_reserve_sol = reserve_sol + sol_in
    return tokens_out, new_reserve_sol, new_reserve_token


def _amm_sell_tokens_for_sol(
    tokens_in: float,
    reserve_sol: float,
    reserve_token: float,
    amm_fee_bps: float = DEFAULT_AMM_SWAP_FEE_BPS,
) -> Tuple[float, float, float]:
    """Executes a constant-product AMM sell (`Token -> SOL`) with fee `amm_fee_bps`.
    Returns `(sol_out, new_reserve_sol, new_reserve_token)`.
    """
    if tokens_in <= 0.0 or reserve_sol <= 0.0 or reserve_token <= 0.0:
        return 0.0, reserve_sol, reserve_token

    fee_multiplier = max(0.0, 1.0 - (amm_fee_bps / 10_000.0))
    effective_tokens_in = tokens_in * fee_multiplier
    k = reserve_sol * reserve_token
    new_reserve_sol = k / (reserve_token + effective_tokens_in)
    sol_out = max(0.0, reserve_sol - new_reserve_sol)
    new_reserve_token = reserve_token + tokens_in
    return sol_out, new_reserve_sol, new_reserve_token


def _simulate_crank_sandwich_net_profit(
    flash_borrow_sol: float,
    crank_buy_sol: float,
    reserve_sol: float,
    reserve_token: float,
    amm_fee_bps: float = DEFAULT_AMM_SWAP_FEE_BPS,
    jito_tip_sol: float = DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL,
    token2022_transfer_fee_bps: float = 0.0,
) -> Tuple[float, float, float, float, float, float, float, float]:
    """Simulates the 3-step Kamino flash-loan crank sandwich for a given `flash_borrow_sol`:
      - Step 1: Buy tokens with `flash_borrow_sol` (deducting Token-2022 transfer tax if > 0)
      - Step 2: Protocol crank buys tokens with `crank_buy_sol` (and burns/LPs them)
      - Step 3: Sell our Step 1 tokens into the elevated post-crank pool and repay Kamino
    Returns:
      `(net_profit_sol, gross_profit_sol, kamino_fee_sol, step1_tokens,
        r_sol_1, r_tok_1, r_sol_2, r_tok_2)`
    """
    if flash_borrow_sol <= 0.0 or crank_buy_sol <= 0.0:
        return 0.0, 0.0, 0.0, 0.0, reserve_sol, reserve_token, reserve_sol, reserve_token

    transfer_tax_rate = max(0.0, min(0.5, float(token2022_transfer_fee_bps) / 10_000.0))

    # Step 1: Front-run buy with Kamino flash-borrowed SOL
    step1_tokens_raw, r_sol_1, r_tok_1 = _amm_buy_tokens_with_sol(
        flash_borrow_sol, reserve_sol, reserve_token, amm_fee_bps
    )
    step1_tokens = step1_tokens_raw * (1.0 - transfer_tax_rate)

    # Step 2: Permissionless crank forces vault SOL buy on the same pool
    _, r_sol_2, r_tok_2 = _amm_buy_tokens_with_sol(
        crank_buy_sol, r_sol_1, r_tok_1, amm_fee_bps
    )

    # Step 3: Back-run sell our acquired tokens into the post-crank pool
    step3_tokens_deliverable = step1_tokens * (1.0 - transfer_tax_rate)
    sol_out, _, _ = _amm_sell_tokens_for_sol(
        step3_tokens_deliverable, r_sol_2, r_tok_2, amm_fee_bps
    )

    gross_profit_sol = sol_out - flash_borrow_sol
    kamino_fee_sol = flash_borrow_sol * KAMINO_FLASH_LOAN_FEE_RATE
    net_profit_sol = gross_profit_sol - kamino_fee_sol - jito_tip_sol
    return (
        net_profit_sol,
        gross_profit_sol,
        kamino_fee_sol,
        step1_tokens,
        r_sol_1,
        r_tok_1,
        r_sol_2,
        r_tok_2,
    )


def _optimize_kamino_flash_borrow_sol(
    crank_buy_sol: float,
    reserve_sol: float,
    reserve_token: float,
    amm_fee_bps: float = DEFAULT_AMM_SWAP_FEE_BPS,
    jito_tip_sol: float = DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL,
    max_pool_Multiple: float = 1.5,
    token2022_transfer_fee_bps: float = 0.0,
) -> float:
    """Finds the profit-maximizing Kamino flash-loan borrow amount `F*` using
    golden-section search over `[0.01, reserve_sol * max_pool_Multiple]`.
    Since constant-product sandwich profit is strictly concave on the positive
    profit interval, golden-section search converges to machine precision in 45 steps.
    """
    if crank_buy_sol <= 0.0 or reserve_sol <= 0.0 or reserve_token <= 0.0:
        return 0.0

    low = 0.01
    high = max(1.0, reserve_sol * max_pool_Multiple)
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0  # ~0.61803398875

    c = high - inv_phi * (high - low)
    d = low + inv_phi * (high - low)

    fc = _simulate_crank_sandwich_net_profit(
        c, crank_buy_sol, reserve_sol, reserve_token, amm_fee_bps, jito_tip_sol, token2022_transfer_fee_bps
    )[0]
    fd = _simulate_crank_sandwich_net_profit(
        d, crank_buy_sol, reserve_sol, reserve_token, amm_fee_bps, jito_tip_sol, token2022_transfer_fee_bps
    )[0]

    for _ in range(48):
        if fc > fd:
            high = d
            d = c
            fd = fc
            c = high - inv_phi * (high - low)
            fc = _simulate_crank_sandwich_net_profit(
                c, crank_buy_sol, reserve_sol, reserve_token, amm_fee_bps, jito_tip_sol, token2022_transfer_fee_bps
            )[0]
        else:
            low = c
            c = d
            fc = fd
            d = low + inv_phi * (high - low)
            fd = _simulate_crank_sandwich_net_profit(
                d, crank_buy_sol, reserve_sol, reserve_token, amm_fee_bps, jito_tip_sol, token2022_transfer_fee_bps
            )[0]

    best_f = 0.5 * (low + high)
    best_net = _simulate_crank_sandwich_net_profit(
        best_f, crank_buy_sol, reserve_sol, reserve_token, amm_fee_bps, jito_tip_sol, token2022_transfer_fee_bps
    )[0]
    return round(best_f, 6) if best_net > 0.0 else 0.0


# ============================================================================
# 1. Protocol Auto-Buyback-and-Burn & Token-2022 TransferFeeConfig Front-Runner
# ============================================================================


def evaluate_protocol_buyback_and_tax_crank(
    token_mint: str,
    vault_type: str = VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN,
    accumulated_vault_sol: float = 50.0,
    crank_trigger_threshold_sol: float = 50.0,
    permissionless_crank_callable: bool = True,
    pool_sol_reserve: float = 250.0,
    pool_token_reserve: float = 250_000_000.0,
    kamino_flash_borrow_sol: Optional[float] = None,
    amm_fee_bps: float = DEFAULT_AMM_SWAP_FEE_BPS,
    jito_bundle_tip_sol: float = DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL,
    withheld_token_balance: float = 0.0,
    withheld_accounts_count: int = 0,
    token2022_transfer_fee_bps: float = 0.0,
    withdraw_withheld_callable: bool = True,
    sol_price_usd: float = DEFAULT_SOL_PRICE_USD,
) -> ProtocolBuybackAndTaxCrankResult:
    """Evaluates a deterministic protocol buyback-and-burn vault or Token-2022
    `TransferFeeConfig` withheld-tax harvester crank and simulates the Atomic 3-Step
    Kamino Flash-Loan Crank Sandwich when `accumulated_vault_sol >= 0.98 * crank_trigger_threshold_sol`
    and `permissionless_crank_callable == True`.
    """
    normalized_vault = str(vault_type).strip().upper()
    pool_sol = max(1e-6, float(pool_sol_reserve))
    pool_tok = max(1e-6, float(pool_token_reserve))
    threshold_sol = max(1e-6, float(crank_trigger_threshold_sol))
    spot_before = pool_sol / pool_tok

    # For Token-2022 Withheld Tax Harvester, if accumulated_vault_sol is zero but
    # withheld_token_balance is provided, compute the SOL equivalent convertible via
    # withdrawWithheldTokensFromAccounts + harvest_withheld_tax_to_lp
    effective_vault_sol = max(0.0, float(accumulated_vault_sol))
    if (
        normalized_vault == VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER
        and effective_vault_sol <= 0.0
        and withheld_token_balance > 0.0
    ):
        sol_equiv, _, _ = _amm_sell_tokens_for_sol(
            float(withheld_token_balance), pool_sol, pool_tok, amm_fee_bps
        )
        effective_vault_sol = sol_equiv

    fill_ratio = effective_vault_sol / threshold_sol
    near_or_above_threshold = (
        effective_vault_sol >= (CRANK_TRIGGER_FILL_RATIO_MIN - 1e-9) * threshold_sol
    )

    # Compute standalone price impact \Delta P_crank of the protocol vault's forced buy
    crank_tokens_standalone, r_sol_standalone, r_tok_standalone = _amm_buy_tokens_with_sol(
        effective_vault_sol, pool_sol, pool_tok, amm_fee_bps
    )
    spot_after_standalone = r_sol_standalone / max(1e-9, r_tok_standalone)
    crank_price_impact_pct = (
        ((spot_after_standalone - spot_before) / spot_before) * 100.0
        if spot_before > 0.0
        else 0.0
    )
    crank_price_impact_bps = crank_price_impact_pct * 100.0

    # Guard 1: Unsupported vault type
    if normalized_vault not in SUPPORTED_BUYBACK_AND_TAX_VAULTS:
        return ProtocolBuybackAndTaxCrankResult(
            token_mint=token_mint,
            vault_type=normalized_vault,
            permissionless_crank_callable=permissionless_crank_callable,
            accumulated_vault_sol=round(effective_vault_sol, 6),
            crank_trigger_threshold_sol=round(threshold_sol, 6),
            vault_fill_ratio=round(fill_ratio, 6),
            near_or_above_threshold=near_or_above_threshold,
            withheld_token_balance=round(float(withheld_token_balance), 4),
            withheld_accounts_count=int(withheld_accounts_count),
            token2022_transfer_fee_bps=round(float(token2022_transfer_fee_bps), 2),
            withdraw_withheld_callable=bool(withdraw_withheld_callable),
            pool_sol_reserve_before=round(pool_sol, 6),
            pool_token_reserve_before=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            crank_standalone_price_impact_pct=round(crank_price_impact_pct, 4),
            crank_standalone_price_impact_bps=round(crank_price_impact_bps, 2),
            kamino_flash_borrow_sol=0.0,
            kamino_flash_fee_sol=0.0,
            jito_bundle_tip_sol=0.0,
            step1_tokens_acquired=0.0,
            step1_spot_price_after_buy=round(spot_before, 10),
            step2_crank_sol_injected=0.0,
            step2_crank_tokens_burned_or_lp=0.0,
            step2_spot_price_after_crank=round(spot_before, 10),
            step3_sol_received_from_sell=0.0,
            step3_spot_price_after_sell=round(spot_before, 10),
            gross_profit_sol=0.0,
            net_profit_sol=0.0,
            net_profit_usd=0.0,
            roi_on_flash_borrow_bps=0.0,
            sandwich_triggered=False,
            recommended_action=ACTION_ABORT_CRANK_UNSUPPORTED_VAULT,
            crank_instruction_name="UNSUPPORTED_VAULT",
            instruction_sequence=[],
            atomic_steps=[],
            rationale=(
                f"Vault type '{normalized_vault}' is not in supported buyback/tax vaults: "
                f"{SUPPORTED_BUYBACK_AND_TAX_VAULTS}."
            ),
        )

    crank_ix_tuple = VAULT_CRANK_INSTRUCTIONS[normalized_vault]
    primary_crank_ix = (
        "harvest_withheld_tax_to_lp"
        if normalized_vault == VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER
        else "trigger_buyback_and_burn"
    )

    # Guard 2: Permissionless crank not callable (or Token-2022 withdrawWithheld not callable)
    if not permissionless_crank_callable or (
        normalized_vault == VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER
        and not withdraw_withheld_callable
    ):
        return ProtocolBuybackAndTaxCrankResult(
            token_mint=token_mint,
            vault_type=normalized_vault,
            permissionless_crank_callable=permissionless_crank_callable,
            accumulated_vault_sol=round(effective_vault_sol, 6),
            crank_trigger_threshold_sol=round(threshold_sol, 6),
            vault_fill_ratio=round(fill_ratio, 6),
            near_or_above_threshold=near_or_above_threshold,
            withheld_token_balance=round(float(withheld_token_balance), 4),
            withheld_accounts_count=int(withheld_accounts_count),
            token2022_transfer_fee_bps=round(float(token2022_transfer_fee_bps), 2),
            withdraw_withheld_callable=bool(withdraw_withheld_callable),
            pool_sol_reserve_before=round(pool_sol, 6),
            pool_token_reserve_before=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            crank_standalone_price_impact_pct=round(crank_price_impact_pct, 4),
            crank_standalone_price_impact_bps=round(crank_price_impact_bps, 2),
            kamino_flash_borrow_sol=0.0,
            kamino_flash_fee_sol=0.0,
            jito_bundle_tip_sol=0.0,
            step1_tokens_acquired=0.0,
            step1_spot_price_after_buy=round(spot_before, 10),
            step2_crank_sol_injected=0.0,
            step2_crank_tokens_burned_or_lp=0.0,
            step2_spot_price_after_crank=round(spot_before, 10),
            step3_sol_received_from_sell=0.0,
            step3_spot_price_after_sell=round(spot_before, 10),
            gross_profit_sol=0.0,
            net_profit_sol=0.0,
            net_profit_usd=0.0,
            roi_on_flash_borrow_bps=0.0,
            sandwich_triggered=False,
            recommended_action=ACTION_ABORT_CRANK_NOT_PERMISSIONLESS,
            crank_instruction_name=primary_crank_ix,
            instruction_sequence=[],
            atomic_steps=[],
            rationale=(
                "Crank instruction is gated to an authorized admin authority "
                "(permissionless_crank_callable=False); atomic Step 2 invocation cannot be bundled."
            ),
        )

    # Guard 3: Vault SOL below 98% trigger threshold
    if not near_or_above_threshold:
        action = (
            ACTION_STAGE_PRE_CRANK_ACCUMULATION
            if fill_ratio >= 0.85
            else ACTION_SKIP_CRANK_BELOW_THRESHOLD
        )
        return ProtocolBuybackAndTaxCrankResult(
            token_mint=token_mint,
            vault_type=normalized_vault,
            permissionless_crank_callable=permissionless_crank_callable,
            accumulated_vault_sol=round(effective_vault_sol, 6),
            crank_trigger_threshold_sol=round(threshold_sol, 6),
            vault_fill_ratio=round(fill_ratio, 6),
            near_or_above_threshold=False,
            withheld_token_balance=round(float(withheld_token_balance), 4),
            withheld_accounts_count=int(withheld_accounts_count),
            token2022_transfer_fee_bps=round(float(token2022_transfer_fee_bps), 2),
            withdraw_withheld_callable=bool(withdraw_withheld_callable),
            pool_sol_reserve_before=round(pool_sol, 6),
            pool_token_reserve_before=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            crank_standalone_price_impact_pct=round(crank_price_impact_pct, 4),
            crank_standalone_price_impact_bps=round(crank_price_impact_bps, 2),
            kamino_flash_borrow_sol=0.0,
            kamino_flash_fee_sol=0.0,
            jito_bundle_tip_sol=0.0,
            step1_tokens_acquired=0.0,
            step1_spot_price_after_buy=round(spot_before, 10),
            step2_crank_sol_injected=0.0,
            step2_crank_tokens_burned_or_lp=0.0,
            step2_spot_price_after_crank=round(spot_before, 10),
            step3_sol_received_from_sell=0.0,
            step3_spot_price_after_sell=round(spot_before, 10),
            gross_profit_sol=0.0,
            net_profit_sol=0.0,
            net_profit_usd=0.0,
            roi_on_flash_borrow_bps=0.0,
            sandwich_triggered=False,
            recommended_action=action,
            crank_instruction_name=primary_crank_ix,
            instruction_sequence=[],
            atomic_steps=[],
            rationale=(
                f"Vault fill ratio {fill_ratio:.4f} ({effective_vault_sol:.2f} / {threshold_sol:.2f} SOL) "
                f"is below the {CRANK_TRIGGER_FILL_RATIO_MIN:.2f} (98%) atomic crank front-run threshold."
            ),
        )

    # Determine optimal Kamino flash-loan borrow size if not explicitly supplied
    if kamino_flash_borrow_sol is not None and kamino_flash_borrow_sol > 0.0:
        borrow_sol = float(kamino_flash_borrow_sol)
    else:
        borrow_sol = _optimize_kamino_flash_borrow_sol(
            effective_vault_sol,
            pool_sol,
            pool_tok,
            amm_fee_bps=amm_fee_bps,
            jito_tip_sol=jito_bundle_tip_sol,
            token2022_transfer_fee_bps=token2022_transfer_fee_bps,
        )

    # Simulate the Atomic 3-Step Kamino Flash-Loan Crank Sandwich
    # Step 1: Borrow optimal SOL via Kamino Flash Loan (0.001% fee) and buy token on AMM
    step1_tokens_raw, r_sol_1, r_tok_1 = _amm_buy_tokens_with_sol(
        borrow_sol, pool_sol, pool_tok, amm_fee_bps
    )
    transfer_tax_rate = max(0.0, min(0.5, float(token2022_transfer_fee_bps) / 10_000.0))
    step1_tokens_net = step1_tokens_raw * (1.0 - transfer_tax_rate)
    spot_after_step1 = r_sol_1 / max(1e-9, r_tok_1)

    # Step 2: Invoke permissionless crank (`trigger_buyback_and_burn` / `harvest_withheld_tax_to_lp`)
    # inside the exact same transaction/bundle, forcing the vault SOL to buy at elevated price
    step2_vault_tokens, r_sol_2, r_tok_2 = _amm_buy_tokens_with_sol(
        effective_vault_sol, r_sol_1, r_tok_1, amm_fee_bps
    )
    spot_after_step2 = r_sol_2 / max(1e-9, r_tok_2)

    # Step 3: Immediately sell acquired tokens into post-crank pool and repay Kamino
    step3_tokens_deliverable = step1_tokens_net * (1.0 - transfer_tax_rate)
    step3_sol_out, r_sol_3, r_tok_3 = _amm_sell_tokens_for_sol(
        step3_tokens_deliverable, r_sol_2, r_tok_2, amm_fee_bps
    )
    spot_after_step3 = r_sol_3 / max(1e-9, r_tok_3)

    kamino_fee_sol = borrow_sol * KAMINO_FLASH_LOAN_FEE_RATE
    gross_profit_sol = step3_sol_out - borrow_sol
    net_profit_sol = gross_profit_sol - kamino_fee_sol - jito_bundle_tip_sol
    net_profit_usd = net_profit_sol * float(sol_price_usd)
    roi_bps = (net_profit_sol / borrow_sol) * 10_000.0 if borrow_sol > 0.0 else 0.0

    step1_trace = CrankSandwichStepTrace(
        step_index=1,
        step_name="STEP_1_KAMINO_FLASH_BORROW_AND_AMM_BUY",
        instruction_name="kamino_flash_borrow_sol -> amm_swap_exact_sol_for_tokens",
        sol_in=round(borrow_sol, 6),
        sol_out=0.0,
        tokens_delta=round(step1_tokens_net, 4),
        pool_sol_reserve_after=round(r_sol_1, 6),
        pool_token_reserve_after=round(r_tok_1, 4),
        spot_price_sol_after=round(spot_after_step1, 10),
        notes=(
            f"Borrowed {borrow_sol:.4f} SOL from Kamino (0.001% fee) and bought "
            f"{step1_tokens_net:,.2f} tokens ahead of crank."
        ),
    )

    step2_ix_label = " -> ".join(crank_ix_tuple)
    step2_trace = CrankSandwichStepTrace(
        step_index=2,
        step_name="STEP_2_PERMISSIONLESS_PROTOCOL_CRANK_INVOCATION",
        instruction_name=step2_ix_label,
        sol_in=round(effective_vault_sol, 6),
        sol_out=0.0,
        tokens_delta=round(step2_vault_tokens, 4),
        pool_sol_reserve_after=round(r_sol_2, 6),
        pool_token_reserve_after=round(r_tok_2, 4),
        spot_price_sol_after=round(spot_after_step2, 10),
        notes=(
            f"Invoked permissionless crank ({primary_crank_ix}), forcing "
            f"{effective_vault_sol:.4f} vault SOL to market-buy into our elevated pool."
        ),
    )

    step3_trace = CrankSandwichStepTrace(
        step_index=3,
        step_name="STEP_3_POST_CRANK_SELL_AND_KAMINO_FLASH_REPAY",
        instruction_name="amm_swap_exact_tokens_for_sol -> kamino_flash_repay_sol",
        sol_in=0.0,
        sol_out=round(step3_sol_out, 6),
        tokens_delta=round(-step1_tokens_net, 4),
        pool_sol_reserve_after=round(r_sol_3, 6),
        pool_token_reserve_after=round(r_tok_3, 4),
        spot_price_sol_after=round(spot_after_step3, 10),
        notes=(
            f"Sold {step1_tokens_net:,.2f} tokens for {step3_sol_out:.6f} SOL, repaid "
            f"Kamino ({borrow_sol + kamino_fee_sol:.6f} SOL), net profit = {net_profit_sol:.6f} SOL."
        ),
    )

    instruction_sequence = [
        "kamino_lending::flash_borrow_reserve_liquidity",
        "amm_router::swap_exact_sol_for_tokens_pre_crank",
        *list(crank_ix_tuple),
        "amm_router::swap_exact_tokens_for_sol_post_crank",
        "kamino_lending::flash_repay_reserve_liquidity",
    ]

    sandwich_triggered = bool(net_profit_sol > 0.0 and borrow_sol > 0.0)
    recommended_action = (
        ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH
        if sandwich_triggered
        else ACTION_SKIP_CRANK_NEGATIVE_NET_EV
    )

    rationale = (
        f"Vault {normalized_vault} at {fill_ratio * 100.0:.2f}% of trigger threshold "
        f"({effective_vault_sol:.2f}/{threshold_sol:.2f} SOL >= 98%). Standalone crank price impact "
        f"is +{crank_price_impact_pct:.2f}% (+{crank_price_impact_bps:.1f} bps). "
        f"Atomic 3-Step Kamino flash sandwich ({borrow_sol:.2f} SOL borrowed @ 0.001% fee) yields "
        f"{net_profit_sol:.6f} SOL (${net_profit_usd:.2f}) deterministic net profit."
        if sandwich_triggered
        else (
            f"Vault {normalized_vault} reached trigger threshold ({fill_ratio * 100.0:.2f}%), "
            f"but pool swap fees + transfer taxes exceed crank price impact "
            f"(net_profit_sol={net_profit_sol:.6f} SOL <= 0)."
        )
    )

    return ProtocolBuybackAndTaxCrankResult(
        token_mint=token_mint,
        vault_type=normalized_vault,
        permissionless_crank_callable=permissionless_crank_callable,
        accumulated_vault_sol=round(effective_vault_sol, 6),
        crank_trigger_threshold_sol=round(threshold_sol, 6),
        vault_fill_ratio=round(fill_ratio, 6),
        near_or_above_threshold=True,
        withheld_token_balance=round(float(withheld_token_balance), 4),
        withheld_accounts_count=int(withheld_accounts_count),
        token2022_transfer_fee_bps=round(float(token2022_transfer_fee_bps), 2),
        withdraw_withheld_callable=bool(withdraw_withheld_callable),
        pool_sol_reserve_before=round(pool_sol, 6),
        pool_token_reserve_before=round(pool_tok, 4),
        spot_price_sol_before=round(spot_before, 10),
        crank_standalone_price_impact_pct=round(crank_price_impact_pct, 4),
        crank_standalone_price_impact_bps=round(crank_price_impact_bps, 2),
        kamino_flash_borrow_sol=round(borrow_sol, 6),
        kamino_flash_fee_sol=round(kamino_fee_sol, 6),
        jito_bundle_tip_sol=round(jito_bundle_tip_sol, 6),
        step1_tokens_acquired=round(step1_tokens_net, 4),
        step1_spot_price_after_buy=round(spot_after_step1, 10),
        step2_crank_sol_injected=round(effective_vault_sol, 6),
        step2_crank_tokens_burned_or_lp=round(step2_vault_tokens, 4),
        step2_spot_price_after_crank=round(spot_after_step2, 10),
        step3_sol_received_from_sell=round(step3_sol_out, 6),
        step3_spot_price_after_sell=round(spot_after_step3, 10),
        gross_profit_sol=round(gross_profit_sol, 6),
        net_profit_sol=round(net_profit_sol, 6),
        net_profit_usd=round(net_profit_usd, 4),
        roi_on_flash_borrow_bps=round(roi_bps, 2),
        sandwich_triggered=sandwich_triggered,
        recommended_action=recommended_action,
        crank_instruction_name=primary_crank_ix,
        instruction_sequence=instruction_sequence,
        atomic_steps=[
            step1_trace.to_dict(),
            step2_trace.to_dict(),
            step3_trace.to_dict(),
        ],
        rationale=rationale,
    )


# ============================================================================
# 2. Cross-Chain Inbound Whale Bridge Intent Lookahead
#    (Mayan Swift / deBridge DLN / Relay Intents)
# ============================================================================


def _is_solana_destination(destination_chain: Union[int, str]) -> Tuple[bool, int]:
    """Verifies whether `destination_chain` corresponds to Solana mainnet
    (`chain_id = 7565164` or `"solana-mainnet"`).
    """
    if isinstance(destination_chain, int):
        return (
            destination_chain == SOLANA_DEBRIDGE_DLN_CHAIN_ID,
            destination_chain,
        )
    cleaned = str(destination_chain).strip().lower()
    if cleaned in SOLANA_MAINNET_CHAIN_ALIASES:
        return True, SOLANA_DEBRIDGE_DLN_CHAIN_ID
    try:
        parsed_id = int(cleaned)
        return parsed_id == SOLANA_DEBRIDGE_DLN_CHAIN_ID, parsed_id
    except ValueError:
        return False, -1


def evaluate_cross_chain_whale_bridge_lookahead(
    target_solana_mint: str,
    bridge_protocol: str = BRIDGE_PROTOCOL_DEBRIDGE_DLN,
    source_chain: str = SOURCE_CHAIN_ETHEREUM,
    event_name: str = "OrderCreated",
    inbound_amount_usd: float = 50_000.0,
    destination_chain: Union[int, str] = SOLANA_DEBRIDGE_DLN_CHAIN_ID,
    estimated_arrival_window_sec: Optional[float] = None,
    firewall_passed: bool = True,
    firewall_gates_verified: int = 6,
    pool_sol_reserve: float = 400.0,
    pool_token_reserve: float = 400_000_000.0,
    pre_position_size_sol: Optional[float] = None,
    solver_spread_bps: float = 12.0,
    prefer_local_dln_solver: bool = False,
    amm_fee_bps: float = DEFAULT_AMM_SWAP_FEE_BPS,
    sol_price_usd: float = DEFAULT_SOL_PRICE_USD,
    order_id: str = "0xbridge_whale_intent_001",
) -> CrossChainWhaleBridgeLookaheadResult:
    """Monitors source-chain order creation events (`OrderCreated` / `SwapInitiated`)
    emitted on Ethereum, Base, and Arbitrum across `MAYAN_SWIFT`, `DEBRIDGE_DLN`, and
    `RELAY_INTENTS` where `inbound_amount_usd >= 25_000.0` and destination is Solana
    (`chain_id = 7565164` / `solana-mainnet`).

    Models the 3.0 to 12.0 second Cross-Chain Solver Relay Window:
    - Verifies the 6-Gate Smart Contract Firewall (`firewall_passed == True`).
    - Computes expected price impact of the incoming whale bridge order on the Solana AMM pool.
    - Triggers `PRE_POSITION_BEFORE_BRIDGE_SOLVER` (`3-10 seconds` ahead of the bridge solver)
      and constructs a 3-tranche automatic limit/scale-out sell schedule into the solver sweep.
    - Evaluates Direct Intent Solver Fulfillment (`FULFILL_AS_LOCAL_DLN_SOLVER`) using Kamino
      flash liquidity when `solver_spread_bps >= 8.0`.
    """
    norm_protocol = str(bridge_protocol).strip().upper()
    norm_source = str(source_chain).strip().upper()
    norm_event = str(event_name).strip()

    dest_is_solana, resolved_chain_id = _is_solana_destination(destination_chain)
    sol_usd = max(1e-6, float(sol_price_usd))
    inbound_usd = max(0.0, float(inbound_amount_usd))
    inbound_sol_equiv = inbound_usd / sol_usd
    whale_threshold_met = inbound_usd >= MIN_INBOUND_WHALE_BRIDGE_USD

    if estimated_arrival_window_sec is None:
        arrival_sec = DEFAULT_PROTOCOL_RELAY_LATENCY_SEC.get(norm_protocol, 5.5)
    else:
        arrival_sec = float(estimated_arrival_window_sec)

    within_relay_window = (
        BRIDGE_RELAY_WINDOW_MIN_SEC <= arrival_sec <= BRIDGE_RELAY_WINDOW_MAX_SEC
    )

    pool_sol = max(1e-6, float(pool_sol_reserve))
    pool_tok = max(1e-6, float(pool_token_reserve))
    spot_before = pool_sol / pool_tok

    # Expected price impact of the incoming whale bridge order on the target Solana AMM pool
    _, r_sol_solver_only, r_tok_solver_only = _amm_buy_tokens_with_sol(
        inbound_sol_equiv, pool_sol, pool_tok, amm_fee_bps
    )
    spot_after_solver = r_sol_solver_only / max(1e-9, r_tok_solver_only)
    solver_impact_pct = (
        ((spot_after_solver - spot_before) / spot_before) * 100.0
        if spot_before > 0.0
        else 0.0
    )
    solver_impact_bps = solver_impact_pct * 100.0

    # Guard 1: Unsupported bridge protocol, source chain, or event
    if (
        norm_protocol not in SUPPORTED_BRIDGE_PROTOCOLS
        or norm_source not in SUPPORTED_EVM_SOURCE_CHAINS
        or norm_event not in SUPPORTED_BRIDGE_EVENTS
    ):
        return CrossChainWhaleBridgeLookaheadResult(
            order_id=order_id,
            bridge_protocol=norm_protocol,
            source_chain=norm_source,
            event_name=norm_event,
            destination_chain_id=resolved_chain_id,
            destination_is_solana=dest_is_solana,
            target_solana_mint=target_solana_mint,
            inbound_amount_usd=round(inbound_usd, 2),
            inbound_amount_sol_equiv=round(inbound_sol_equiv, 6),
            whale_threshold_met=whale_threshold_met,
            estimated_arrival_window_sec=round(arrival_sec, 3),
            within_relay_window=within_relay_window,
            firewall_passed=bool(firewall_passed),
            firewall_gates_verified=int(firewall_gates_verified),
            pool_sol_reserve=round(pool_sol, 6),
            pool_token_reserve=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            expected_solver_price_impact_pct=round(solver_impact_pct, 4),
            expected_solver_price_impact_bps=round(solver_impact_bps, 2),
            spot_price_sol_after_solver=round(spot_after_solver, 10),
            pre_position_triggered=False,
            pre_position_lead_time_sec=0.0,
            pre_position_size_sol=0.0,
            pre_position_tokens_acquired=0.0,
            pre_position_gross_profit_sol=0.0,
            pre_position_net_profit_sol=0.0,
            pre_position_net_profit_usd=0.0,
            auto_scale_out_limit_orders=[],
            solver_spread_bps=round(float(solver_spread_bps), 2),
            local_solver_eligible=False,
            local_solver_triggered=False,
            local_solver_action=ACTION_SKIP_BRIDGE_UNSUPPORTED_SOURCE,
            local_solver_kamino_flash_sol=0.0,
            local_solver_kamino_fee_sol=0.0,
            local_solver_net_profit_sol=0.0,
            local_solver_net_profit_usd=0.0,
            active_strategies=[],
            recommended_action=ACTION_SKIP_BRIDGE_UNSUPPORTED_SOURCE,
            rationale=(
                f"Unsupported bridge parameters: protocol={norm_protocol}, "
                f"source_chain={norm_source}, event={norm_event}."
            ),
        )

    # Guard 2: Destination chain is not Solana (chain_id = 7565164 / solana-mainnet)
    if not dest_is_solana:
        return CrossChainWhaleBridgeLookaheadResult(
            order_id=order_id,
            bridge_protocol=norm_protocol,
            source_chain=norm_source,
            event_name=norm_event,
            destination_chain_id=resolved_chain_id,
            destination_is_solana=False,
            target_solana_mint=target_solana_mint,
            inbound_amount_usd=round(inbound_usd, 2),
            inbound_amount_sol_equiv=round(inbound_sol_equiv, 6),
            whale_threshold_met=whale_threshold_met,
            estimated_arrival_window_sec=round(arrival_sec, 3),
            within_relay_window=within_relay_window,
            firewall_passed=bool(firewall_passed),
            firewall_gates_verified=int(firewall_gates_verified),
            pool_sol_reserve=round(pool_sol, 6),
            pool_token_reserve=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            expected_solver_price_impact_pct=round(solver_impact_pct, 4),
            expected_solver_price_impact_bps=round(solver_impact_bps, 2),
            spot_price_sol_after_solver=round(spot_after_solver, 10),
            pre_position_triggered=False,
            pre_position_lead_time_sec=0.0,
            pre_position_size_sol=0.0,
            pre_position_tokens_acquired=0.0,
            pre_position_gross_profit_sol=0.0,
            pre_position_net_profit_sol=0.0,
            pre_position_net_profit_usd=0.0,
            auto_scale_out_limit_orders=[],
            solver_spread_bps=round(float(solver_spread_bps), 2),
            local_solver_eligible=False,
            local_solver_triggered=False,
            local_solver_action=ACTION_SKIP_BRIDGE_NON_SOLANA_DEST,
            local_solver_kamino_flash_sol=0.0,
            local_solver_kamino_fee_sol=0.0,
            local_solver_net_profit_sol=0.0,
            local_solver_net_profit_usd=0.0,
            active_strategies=[],
            recommended_action=ACTION_SKIP_BRIDGE_NON_SOLANA_DEST,
            rationale=(
                f"Destination chain '{destination_chain}' is not Solana mainnet "
                f"(expected chain_id={SOLANA_DEBRIDGE_DLN_CHAIN_ID} / 'solana-mainnet')."
            ),
        )

    # Guard 3: Inbound order below $25,000 USD whale threshold
    if not whale_threshold_met:
        return CrossChainWhaleBridgeLookaheadResult(
            order_id=order_id,
            bridge_protocol=norm_protocol,
            source_chain=norm_source,
            event_name=norm_event,
            destination_chain_id=resolved_chain_id,
            destination_is_solana=True,
            target_solana_mint=target_solana_mint,
            inbound_amount_usd=round(inbound_usd, 2),
            inbound_amount_sol_equiv=round(inbound_sol_equiv, 6),
            whale_threshold_met=False,
            estimated_arrival_window_sec=round(arrival_sec, 3),
            within_relay_window=within_relay_window,
            firewall_passed=bool(firewall_passed),
            firewall_gates_verified=int(firewall_gates_verified),
            pool_sol_reserve=round(pool_sol, 6),
            pool_token_reserve=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            expected_solver_price_impact_pct=round(solver_impact_pct, 4),
            expected_solver_price_impact_bps=round(solver_impact_bps, 2),
            spot_price_sol_after_solver=round(spot_after_solver, 10),
            pre_position_triggered=False,
            pre_position_lead_time_sec=0.0,
            pre_position_size_sol=0.0,
            pre_position_tokens_acquired=0.0,
            pre_position_gross_profit_sol=0.0,
            pre_position_net_profit_sol=0.0,
            pre_position_net_profit_usd=0.0,
            auto_scale_out_limit_orders=[],
            solver_spread_bps=round(float(solver_spread_bps), 2),
            local_solver_eligible=False,
            local_solver_triggered=False,
            local_solver_action=ACTION_SKIP_BRIDGE_BELOW_WHALE_THRESHOLD,
            local_solver_kamino_flash_sol=0.0,
            local_solver_kamino_fee_sol=0.0,
            local_solver_net_profit_sol=0.0,
            local_solver_net_profit_usd=0.0,
            active_strategies=[],
            recommended_action=ACTION_SKIP_BRIDGE_BELOW_WHALE_THRESHOLD,
            rationale=(
                f"Inbound bridge amount ${inbound_usd:,.2f} is below the "
                f"${MIN_INBOUND_WHALE_BRIDGE_USD:,.2f} whale intent threshold."
            ),
        )

    # Guard 4: 6-Gate Smart Contract Firewall verification
    if not firewall_passed or firewall_gates_verified < 6:
        return CrossChainWhaleBridgeLookaheadResult(
            order_id=order_id,
            bridge_protocol=norm_protocol,
            source_chain=norm_source,
            event_name=norm_event,
            destination_chain_id=resolved_chain_id,
            destination_is_solana=True,
            target_solana_mint=target_solana_mint,
            inbound_amount_usd=round(inbound_usd, 2),
            inbound_amount_sol_equiv=round(inbound_sol_equiv, 6),
            whale_threshold_met=True,
            estimated_arrival_window_sec=round(arrival_sec, 3),
            within_relay_window=within_relay_window,
            firewall_passed=False,
            firewall_gates_verified=int(firewall_gates_verified),
            pool_sol_reserve=round(pool_sol, 6),
            pool_token_reserve=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            expected_solver_price_impact_pct=round(solver_impact_pct, 4),
            expected_solver_price_impact_bps=round(solver_impact_bps, 2),
            spot_price_sol_after_solver=round(spot_after_solver, 10),
            pre_position_triggered=False,
            pre_position_lead_time_sec=0.0,
            pre_position_size_sol=0.0,
            pre_position_tokens_acquired=0.0,
            pre_position_gross_profit_sol=0.0,
            pre_position_net_profit_sol=0.0,
            pre_position_net_profit_usd=0.0,
            auto_scale_out_limit_orders=[],
            solver_spread_bps=round(float(solver_spread_bps), 2),
            local_solver_eligible=False,
            local_solver_triggered=False,
            local_solver_action=ACTION_ABORT_BRIDGE_FIREWALL_FAILED,
            local_solver_kamino_flash_sol=0.0,
            local_solver_kamino_fee_sol=0.0,
            local_solver_net_profit_sol=0.0,
            local_solver_net_profit_usd=0.0,
            active_strategies=[],
            recommended_action=ACTION_ABORT_BRIDGE_FIREWALL_FAILED,
            rationale=(
                f"Target Solana token {target_solana_mint} failed the 6-Gate Smart Contract "
                f"Firewall (firewall_passed={firewall_passed}, gates={firewall_gates_verified}/6)."
            ),
        )

    # Guard 5: Solver arrival window outside [3.0s, 12.0s] lookahead bounds
    if not within_relay_window:
        return CrossChainWhaleBridgeLookaheadResult(
            order_id=order_id,
            bridge_protocol=norm_protocol,
            source_chain=norm_source,
            event_name=norm_event,
            destination_chain_id=resolved_chain_id,
            destination_is_solana=True,
            target_solana_mint=target_solana_mint,
            inbound_amount_usd=round(inbound_usd, 2),
            inbound_amount_sol_equiv=round(inbound_sol_equiv, 6),
            whale_threshold_met=True,
            estimated_arrival_window_sec=round(arrival_sec, 3),
            within_relay_window=False,
            firewall_passed=True,
            firewall_gates_verified=int(firewall_gates_verified),
            pool_sol_reserve=round(pool_sol, 6),
            pool_token_reserve=round(pool_tok, 4),
            spot_price_sol_before=round(spot_before, 10),
            expected_solver_price_impact_pct=round(solver_impact_pct, 4),
            expected_solver_price_impact_bps=round(solver_impact_bps, 2),
            spot_price_sol_after_solver=round(spot_after_solver, 10),
            pre_position_triggered=False,
            pre_position_lead_time_sec=0.0,
            pre_position_size_sol=0.0,
            pre_position_tokens_acquired=0.0,
            pre_position_gross_profit_sol=0.0,
            pre_position_net_profit_sol=0.0,
            pre_position_net_profit_usd=0.0,
            auto_scale_out_limit_orders=[],
            solver_spread_bps=round(float(solver_spread_bps), 2),
            local_solver_eligible=False,
            local_solver_triggered=False,
            local_solver_action=ACTION_SKIP_BRIDGE_OUTSIDE_RELAY_WINDOW,
            local_solver_kamino_flash_sol=0.0,
            local_solver_kamino_fee_sol=0.0,
            local_solver_net_profit_sol=0.0,
            local_solver_net_profit_usd=0.0,
            active_strategies=[],
            recommended_action=ACTION_SKIP_BRIDGE_OUTSIDE_RELAY_WINDOW,
            rationale=(
                f"Estimated arrival window {arrival_sec:.2f}s is outside the deterministic "
                f"[{BRIDGE_RELAY_WINDOW_MIN_SEC:.1f}s, {BRIDGE_RELAY_WINDOW_MAX_SEC:.1f}s] "
                f"cross-chain solver relay window."
            ),
        )

    # Path A: PRE_POSITION_BEFORE_BRIDGE_SOLVER (3-10 seconds ahead of bridge solver on Solana)
    # Lead time is bounded strictly inside [3.0, 10.0] seconds ahead of destination fulfillment
    lead_time_sec = max(
        PRE_POSITION_LEAD_TIME_MIN_SEC,
        min(PRE_POSITION_LEAD_TIME_MAX_SEC, round(arrival_sec - 0.4, 3)),
    )

    if pre_position_size_sol is not None and pre_position_size_sol > 0.0:
        pos_sol = float(pre_position_size_sol)
    else:
        pos_sol = _optimize_kamino_flash_borrow_sol(
            inbound_sol_equiv,
            pool_sol,
            pool_tok,
            amm_fee_bps=amm_fee_bps,
            jito_tip_sol=DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL,
            max_pool_Multiple=0.6,
        )
        if pos_sol <= 0.0:
            pos_sol = min(pool_sol * 0.10, inbound_sol_equiv * 0.25)

    # Simulate Pre-Position Buy -> Bridge Solver Market-Buy Sweep -> Scale-Out Sell
    pre_tokens, r_sol_1, r_tok_1 = _amm_buy_tokens_with_sol(
        pos_sol, pool_sol, pool_tok, amm_fee_bps
    )
    _, r_sol_2, r_tok_2 = _amm_buy_tokens_with_sol(
        inbound_sol_equiv, r_sol_1, r_tok_1, amm_fee_bps
    )
    post_sweep_spot = r_sol_2 / max(1e-9, r_tok_2)

    # Construct 3-tranche automatic limit/scale-out sell schedule into the solver sweep
    tranche_weights = (0.35, 0.40, 0.25)
    tranche_price_factors = (0.985, 1.000, 1.015)
    scale_out_orders: List[Dict[str, Any]] = []

    for idx, (weight, p_factor) in enumerate(
        zip(tranche_weights, tranche_price_factors), start=1
    ):
        tranche_qty = pre_tokens * weight
        target_price = post_sweep_spot * p_factor
        upside_bps = (
            ((target_price - spot_before) / spot_before) * 10_000.0
            if spot_before > 0.0
            else 0.0
        )
        scale_out_orders.append(
            ScaleOutLimitOrderTranche(
                tranche_index=idx,
                allocation_pct=round(weight * 100.0, 2),
                token_quantity=round(tranche_qty, 4),
                target_exit_price_sol=round(target_price, 10),
                target_upside_bps=round(upside_bps, 2),
                expected_proceeds_sol=round(tranche_qty * target_price, 6),
            ).to_dict()
        )

    sol_proceeds, _, _ = _amm_sell_tokens_for_sol(
        pre_tokens, r_sol_2, r_tok_2, amm_fee_bps
    )
    pre_gross_profit_sol = sol_proceeds - pos_sol
    pre_net_profit_sol = (
        pre_gross_profit_sol
        - (pos_sol * KAMINO_FLASH_LOAN_FEE_RATE)
        - DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL
    )
    pre_net_profit_usd = pre_net_profit_sol * sol_usd
    pre_position_triggered = bool(pre_net_profit_sol > 0.0)

    # Path B: Direct Intent Solver Fulfillment (FULFILL_AS_LOCAL_DLN_SOLVER) via Kamino Flash Loan
    spread_bps = float(solver_spread_bps)
    local_solver_eligible = spread_bps >= MIN_LOCAL_DLN_SOLVER_SPREAD_BPS
    if local_solver_eligible:
        local_flash_sol = inbound_sol_equiv
        local_kamino_fee_sol = local_flash_sol * KAMINO_FLASH_LOAN_FEE_RATE
        gross_solver_spread_sol = local_flash_sol * (spread_bps / 10_000.0)
        local_solver_net_sol = (
            gross_solver_spread_sol
            - local_kamino_fee_sol
            - DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL
        )
        local_solver_net_usd = local_solver_net_sol * sol_usd
        local_solver_triggered = bool(local_solver_net_sol > 0.0)
        local_solver_action = (
            ACTION_FULFILL_AS_LOCAL_DLN_SOLVER
            if local_solver_triggered
            else "SKIP_LOCAL_SOLVER_NEGATIVE_NET"
        )
    else:
        local_flash_sol = 0.0
        local_kamino_fee_sol = 0.0
        local_solver_net_sol = 0.0
        local_solver_net_usd = 0.0
        local_solver_triggered = False
        local_solver_action = "SOLVER_SPREAD_BELOW_MIN_8BPS"

    active_strategies: List[str] = []
    if pre_position_triggered:
        active_strategies.append(ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER)
    if local_solver_triggered:
        active_strategies.append(ACTION_FULFILL_AS_LOCAL_DLN_SOLVER)

    # Select primary recommended action
    if prefer_local_dln_solver and local_solver_triggered:
        recommended_action = ACTION_FULFILL_AS_LOCAL_DLN_SOLVER
    elif pre_position_triggered:
        recommended_action = ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER
    elif local_solver_triggered:
        recommended_action = ACTION_FULFILL_AS_LOCAL_DLN_SOLVER
    else:
        recommended_action = "HOLD_BRIDGE_LOOKAHEAD_NO_POSITIVE_EDGE"

    rationale = (
        f"Inbound {norm_protocol} {norm_event} from {norm_source} -> Solana "
        f"(chain_id={resolved_chain_id}): ${inbound_usd:,.2f} ({inbound_sol_equiv:.2f} SOL), "
        f"arrival window={arrival_sec:.2f}s (lead time={lead_time_sec:.2f}s). "
        f"Expected AMM solver impact=+{solver_impact_pct:.2f}% (+{solver_impact_bps:.1f} bps). "
        f"Pre-positioning {pos_sol:.2f} SOL yields {pre_net_profit_sol:.4f} SOL "
        f"(${pre_net_profit_usd:,.2f}) across 3 scale-out limit tranches; "
        f"local DLN solver fulfillment (spread={spread_bps:.1f} bps) yields "
        f"{local_solver_net_sol:.4f} SOL (${local_solver_net_usd:,.2f})."
    )

    return CrossChainWhaleBridgeLookaheadResult(
        order_id=order_id,
        bridge_protocol=norm_protocol,
        source_chain=norm_source,
        event_name=norm_event,
        destination_chain_id=resolved_chain_id,
        destination_is_solana=True,
        target_solana_mint=target_solana_mint,
        inbound_amount_usd=round(inbound_usd, 2),
        inbound_amount_sol_equiv=round(inbound_sol_equiv, 6),
        whale_threshold_met=True,
        estimated_arrival_window_sec=round(arrival_sec, 3),
        within_relay_window=True,
        firewall_passed=True,
        firewall_gates_verified=int(firewall_gates_verified),
        pool_sol_reserve=round(pool_sol, 6),
        pool_token_reserve=round(pool_tok, 4),
        spot_price_sol_before=round(spot_before, 10),
        expected_solver_price_impact_pct=round(solver_impact_pct, 4),
        expected_solver_price_impact_bps=round(solver_impact_bps, 2),
        spot_price_sol_after_solver=round(spot_after_solver, 10),
        pre_position_triggered=pre_position_triggered,
        pre_position_lead_time_sec=round(lead_time_sec, 3),
        pre_position_size_sol=round(pos_sol, 6),
        pre_position_tokens_acquired=round(pre_tokens, 4),
        pre_position_gross_profit_sol=round(pre_gross_profit_sol, 6),
        pre_position_net_profit_sol=round(pre_net_profit_sol, 6),
        pre_position_net_profit_usd=round(pre_net_profit_usd, 4),
        auto_scale_out_limit_orders=scale_out_orders,
        solver_spread_bps=round(spread_bps, 2),
        local_solver_eligible=local_solver_eligible,
        local_solver_triggered=local_solver_triggered,
        local_solver_action=local_solver_action,
        local_solver_kamino_flash_sol=round(local_flash_sol, 6),
        local_solver_kamino_fee_sol=round(local_kamino_fee_sol, 6),
        local_solver_net_profit_sol=round(local_solver_net_sol, 6),
        local_solver_net_profit_usd=round(local_solver_net_usd, 4),
        active_strategies=active_strategies,
        recommended_action=recommended_action,
        rationale=rationale,
    )


# ============================================================================
# 3. CrankBuybackAndBridgeLookaheadEngine Facade Class
# ============================================================================


class CrankBuybackAndBridgeLookaheadEngine:
    """Facade orchestrating Agent 27 (`crank-buyback-bridge-lookahead`):
    1. Protocol Auto-Buyback-and-Burn & Token-2022 `TransferFeeConfig` Crank Front-Runner
    2. Cross-Chain Inbound Whale Bridge Intent Lookahead (`Mayan Swift`, `deBridge DLN`, `Relay`)
    """

    def __init__(self) -> None:
        self._crank_evaluations: int = 0
        self._crank_sandwiches_triggered: int = 0
        self._cumulative_crank_profit_sol: float = 0.0
        self._cumulative_crank_profit_usd: float = 0.0
        self._bridge_lookahead_evaluations: int = 0
        self._bridge_pre_positions_triggered: int = 0
        self._bridge_local_solver_fills_triggered: int = 0
        self._cumulative_bridge_profit_usd: float = 0.0
        self._last_diagnostic_ts: Optional[float] = None

    def evaluate_protocol_buyback_and_tax_crank(
        self,
        token_mint: str,
        **kwargs: Any,
    ) -> ProtocolBuybackAndTaxCrankResult:
        """Evaluates a protocol buyback-and-burn or Token-2022 withheld-tax crank
        and updates internal telemetry counters.
        """
        res = evaluate_protocol_buyback_and_tax_crank(token_mint, **kwargs)
        self._crank_evaluations += 1
        if res.sandwich_triggered:
            self._crank_sandwiches_triggered += 1
            self._cumulative_crank_profit_sol = round(
                self._cumulative_crank_profit_sol + res.net_profit_sol, 6
            )
            self._cumulative_crank_profit_usd = round(
                self._cumulative_crank_profit_usd + res.net_profit_usd, 4
            )
        return res

    def evaluate_cross_chain_whale_bridge_lookahead(
        self,
        target_solana_mint: str,
        **kwargs: Any,
    ) -> CrossChainWhaleBridgeLookaheadResult:
        """Evaluates an inbound cross-chain whale bridge order intent and updates
        internal telemetry counters.
        """
        res = evaluate_cross_chain_whale_bridge_lookahead(target_solana_mint, **kwargs)
        self._bridge_lookahead_evaluations += 1
        if res.pre_position_triggered:
            self._bridge_pre_positions_triggered += 1
        if res.local_solver_triggered:
            self._bridge_local_solver_fills_triggered += 1
        if res.recommended_action == ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER:
            self._cumulative_bridge_profit_usd = round(
                self._cumulative_bridge_profit_usd + res.pre_position_net_profit_usd, 4
            )
        elif res.recommended_action == ACTION_FULFILL_AS_LOCAL_DLN_SOLVER:
            self._cumulative_bridge_profit_usd = round(
                self._cumulative_bridge_profit_usd + res.local_solver_net_profit_usd, 4
            )
        return res

    def run_full_crank_bridge_diagnostic(self) -> Dict[str, Any]:
        """Runs a full verification diagnostic across all 4 deterministic buyback/tax
        crank vaults and all 3 cross-chain whale bridge protocols (`MAYAN_SWIFT`,
        `DEBRIDGE_DLN`, `RELAY_INTENTS`) across Ethereum, Base, and Arbitrum.
        """
        t0 = time.perf_counter()

        # 1A. PumpSwap Creator Fee Auto-Burn Crank Sandwich (99% threshold reached)
        pumpswap_crank_res = self.evaluate_protocol_buyback_and_tax_crank(
            "PumpSwapAutoBurnMint11111111111111111111111",
            vault_type=VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN,
            accumulated_vault_sol=49.5,
            crank_trigger_threshold_sol=50.0,
            permissionless_crank_callable=True,
            pool_sol_reserve=240.0,
            pool_token_reserve=240_000_000.0,
        )

        # 1B. Token-2022 Withheld Tax Harvester Crank Sandwich (`withdrawWithheldTokensFromAccounts`)
        token2022_crank_res = self.evaluate_protocol_buyback_and_tax_crank(
            "Token2022TaxHarvesterMint222222222222222222",
            vault_type=VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER,
            accumulated_vault_sol=30.0,
            crank_trigger_threshold_sol=30.0,
            permissionless_crank_callable=True,
            pool_sol_reserve=180.0,
            pool_token_reserve=180_000_000.0,
            withheld_token_balance=30_000_000.0,
            withheld_accounts_count=142,
            token2022_transfer_fee_bps=0.0,
            withdraw_withheld_callable=True,
        )

        # 2A. Cross-Chain Whale Bridge Lookahead (deBridge DLN from Ethereum -> Solana, Pre-Position)
        debridge_whale_res = self.evaluate_cross_chain_whale_bridge_lookahead(
            "SolanaTargetMemeMint33333333333333333333333",
            bridge_protocol=BRIDGE_PROTOCOL_DEBRIDGE_DLN,
            source_chain=SOURCE_CHAIN_ETHEREUM,
            event_name="OrderCreated",
            inbound_amount_usd=65_000.0,
            destination_chain=SOLANA_DEBRIDGE_DLN_CHAIN_ID,
            estimated_arrival_window_sec=6.2,
            firewall_passed=True,
            firewall_gates_verified=6,
            pool_sol_reserve=350.0,
            pool_token_reserve=350_000_000.0,
            solver_spread_bps=14.0,
            prefer_local_dln_solver=False,
            order_id="0xdebridge_dln_eth_whale_65k",
        )

        # 2B. Cross-Chain Direct Intent Solver Fulfillment (Mayan Swift from Base -> Solana)
        mayan_local_solver_res = self.evaluate_cross_chain_whale_bridge_lookahead(
            "SolanaTargetMemeMint44444444444444444444444",
            bridge_protocol=BRIDGE_PROTOCOL_MAYAN_SWIFT,
            source_chain=SOURCE_CHAIN_BASE,
            event_name="SwapInitiated",
            inbound_amount_usd=45_000.0,
            destination_chain="solana-mainnet",
            estimated_arrival_window_sec=4.8,
            firewall_passed=True,
            firewall_gates_verified=6,
            pool_sol_reserve=1_200.0,
            pool_token_reserve=1_200_000_000.0,
            solver_spread_bps=18.5,
            prefer_local_dln_solver=True,
            order_id="0xmayan_swift_base_whale_45k",
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        self._last_diagnostic_ts = time.time()

        return {
            "status": "OK",
            "ipc_action": IPC_ACTION_RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD,
            "subsystem": "CRANK_BUYBACK_BRIDGE_LOOKAHEAD_ENGINE_AGENT_27",
            "diagnostic_latency_ms": latency_ms,
            "pumpswap_buyback_crank_sandwich": pumpswap_crank_res.to_dict(),
            "token2022_tax_harvester_crank_sandwich": token2022_crank_res.to_dict(),
            "debridge_dln_whale_pre_position": debridge_whale_res.to_dict(),
            "mayan_swift_local_solver_fulfillment": mayan_local_solver_res.to_dict(),
            "telemetry": self.get_telemetry_summary(),
        }

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Returns real-time operational telemetry for `TitanIPCDaemon`."""
        return {
            "engine": "CrankBuybackAndBridgeLookaheadEngine",
            "agent_id": "crank-buyback-bridge-lookahead",
            "agent_number": 27,
            "ipc_action": IPC_ACTION_RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD,
            "crank_evaluations": self._crank_evaluations,
            "crank_sandwiches_triggered": self._crank_sandwiches_triggered,
            "cumulative_crank_profit_sol": self._cumulative_crank_profit_sol,
            "cumulative_crank_profit_usd": self._cumulative_crank_profit_usd,
            "bridge_lookahead_evaluations": self._bridge_lookahead_evaluations,
            "bridge_pre_positions_triggered": self._bridge_pre_positions_triggered,
            "bridge_local_solver_fills_triggered": self._bridge_local_solver_fills_triggered,
            "cumulative_bridge_profit_usd": self._cumulative_bridge_profit_usd,
            "benchmarks": {
                "supported_buyback_vaults": list(SUPPORTED_BUYBACK_AND_TAX_VAULTS),
                "crank_trigger_fill_ratio_min": CRANK_TRIGGER_FILL_RATIO_MIN,
                "kamino_flash_loan_fee_pct": KAMINO_FLASH_LOAN_FEE_PCT,
                "supported_bridge_protocols": list(SUPPORTED_BRIDGE_PROTOCOLS),
                "supported_evm_source_chains": list(SUPPORTED_EVM_SOURCE_CHAINS),
                "solana_debridge_dln_chain_id": SOLANA_DEBRIDGE_DLN_CHAIN_ID,
                "min_inbound_whale_bridge_usd": MIN_INBOUND_WHALE_BRIDGE_USD,
                "bridge_relay_window_sec": [
                    BRIDGE_RELAY_WINDOW_MIN_SEC,
                    BRIDGE_RELAY_WINDOW_MAX_SEC,
                ],
                "pre_position_lead_time_sec": [
                    PRE_POSITION_LEAD_TIME_MIN_SEC,
                    PRE_POSITION_LEAD_TIME_MAX_SEC,
                ],
                "min_local_dln_solver_spread_bps": MIN_LOCAL_DLN_SOLVER_SPREAD_BPS,
            },
            "last_diagnostic_ts": self._last_diagnostic_ts,
        }


__all__ = [
    "ACTION_ABORT_BRIDGE_FIREWALL_FAILED",
    "ACTION_ABORT_CRANK_NOT_PERMISSIONLESS",
    "ACTION_ABORT_CRANK_UNSUPPORTED_VAULT",
    "ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH",
    "ACTION_FULFILL_AS_LOCAL_DLN_SOLVER",
    "ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER",
    "ACTION_SKIP_BRIDGE_BELOW_WHALE_THRESHOLD",
    "ACTION_SKIP_BRIDGE_NON_SOLANA_DEST",
    "ACTION_SKIP_BRIDGE_OUTSIDE_RELAY_WINDOW",
    "ACTION_SKIP_BRIDGE_UNSUPPORTED_SOURCE",
    "ACTION_SKIP_CRANK_BELOW_THRESHOLD",
    "ACTION_SKIP_CRANK_NEGATIVE_NET_EV",
    "ACTION_STAGE_PRE_CRANK_ACCUMULATION",
    "BRIDGE_PROTOCOL_DEBRIDGE_DLN",
    "BRIDGE_PROTOCOL_MAYAN_SWIFT",
    "BRIDGE_PROTOCOL_RELAY_INTENTS",
    "BRIDGE_RELAY_WINDOW_MAX_SEC",
    "BRIDGE_RELAY_WINDOW_MIN_SEC",
    "CRANK_TRIGGER_FILL_RATIO_MIN",
    "CrankBuybackAndBridgeLookaheadEngine",
    "CrankSandwichStepTrace",
    "CrossChainWhaleBridgeLookaheadResult",
    "DEFAULT_AMM_SWAP_FEE_BPS",
    "DEFAULT_JITO_CRANK_BUNDLE_TIP_SOL",
    "DEFAULT_PROTOCOL_RELAY_LATENCY_SEC",
    "DEFAULT_SOL_PRICE_USD",
    "IPC_ACTION_RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD",
    "KAMINO_FLASH_LOAN_FEE_BPS",
    "KAMINO_FLASH_LOAN_FEE_PCT",
    "KAMINO_FLASH_LOAN_FEE_RATE",
    "MIN_INBOUND_WHALE_BRIDGE_USD",
    "MIN_LOCAL_DLN_SOLVER_SPREAD_BPS",
    "PRE_POSITION_LEAD_TIME_MAX_SEC",
    "PRE_POSITION_LEAD_TIME_MIN_SEC",
    "ProtocolBuybackAndTaxCrankResult",
    "SOLANA_DEBRIDGE_DLN_CHAIN_ID",
    "SOLANA_MAINNET_CHAIN_ALIASES",
    "SOURCE_CHAIN_ARBITRUM",
    "SOURCE_CHAIN_BASE",
    "SOURCE_CHAIN_ETHEREUM",
    "SUPPORTED_BRIDGE_EVENTS",
    "SUPPORTED_BRIDGE_PROTOCOLS",
    "SUPPORTED_BUYBACK_AND_TAX_VAULTS",
    "SUPPORTED_EVM_SOURCE_CHAINS",
    "ScaleOutLimitOrderTranche",
    "VAULT_BELIEVE_LAUNCHCOIN_BUYBACK_VAULT",
    "VAULT_CRANK_INSTRUCTIONS",
    "VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN",
    "VAULT_RAYDIUM_BUYBACK_BURN_CRANK",
    "VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER",
    "evaluate_cross_chain_whale_bridge_lookahead",
    "evaluate_protocol_buyback_and_tax_crank",
]
