"""Comprehensive pytest verification suite for Agent 27 (`crank-buyback-bridge-lookahead`):
Protocol Auto-Buyback-and-Burn / Token-2022 `TransferFeeConfig` Crank Front-Runner &
Cross-Chain (`Mayan Swift` / `deBridge DLN` / `Relay`) Inbound Whale Bridge Lookahead
(`src/engines/crank_buyback_and_bridge_lookahead.py`).
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from src.engines.crank_buyback_and_bridge_lookahead import (
    ACTION_ABORT_BRIDGE_FIREWALL_FAILED,
    ACTION_ABORT_CRANK_NOT_PERMISSIONLESS,
    ACTION_ABORT_CRANK_UNSUPPORTED_VAULT,
    ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH,
    ACTION_FULFILL_AS_LOCAL_DLN_SOLVER,
    ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER,
    ACTION_SKIP_BRIDGE_BELOW_WHALE_THRESHOLD,
    ACTION_SKIP_BRIDGE_NON_SOLANA_DEST,
    ACTION_SKIP_BRIDGE_OUTSIDE_RELAY_WINDOW,
    ACTION_SKIP_BRIDGE_UNSUPPORTED_SOURCE,
    ACTION_SKIP_CRANK_BELOW_THRESHOLD,
    ACTION_SKIP_CRANK_NEGATIVE_NET_EV,
    ACTION_STAGE_PRE_CRANK_ACCUMULATION,
    BRIDGE_PROTOCOL_DEBRIDGE_DLN,
    BRIDGE_PROTOCOL_MAYAN_SWIFT,
    BRIDGE_PROTOCOL_RELAY_INTENTS,
    CRANK_TRIGGER_FILL_RATIO_MIN,
    CrankBuybackAndBridgeLookaheadEngine,
    IPC_ACTION_RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD,
    KAMINO_FLASH_LOAN_FEE_PCT,
    KAMINO_FLASH_LOAN_FEE_RATE,
    MIN_INBOUND_WHALE_BRIDGE_USD,
    MIN_LOCAL_DLN_SOLVER_SPREAD_BPS,
    SOLANA_DEBRIDGE_DLN_CHAIN_ID,
    SOURCE_CHAIN_ARBITRUM,
    SOURCE_CHAIN_BASE,
    SOURCE_CHAIN_ETHEREUM,
    SUPPORTED_BRIDGE_PROTOCOLS,
    SUPPORTED_BUYBACK_AND_TAX_VAULTS,
    SUPPORTED_EVM_SOURCE_CHAINS,
    VAULT_BELIEVE_LAUNCHCOIN_BUYBACK_VAULT,
    VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN,
    VAULT_RAYDIUM_BUYBACK_BURN_CRANK,
    VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER,
    evaluate_cross_chain_whale_bridge_lookahead,
    evaluate_protocol_buyback_and_tax_crank,
)


# ============================================================================
# 1. Protocol Auto-Buyback-and-Burn & Token-2022 TransferFeeConfig Tests
# ============================================================================


@pytest.mark.parametrize(
    "vault_type,expected_ix",
    [
        (VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN, "trigger_buyback_and_burn"),
        (VAULT_BELIEVE_LAUNCHCOIN_BUYBACK_VAULT, "trigger_buyback_and_burn"),
        (VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER, "harvest_withheld_tax_to_lp"),
        (VAULT_RAYDIUM_BUYBACK_BURN_CRANK, "trigger_buyback_and_burn"),
    ],
)
def test_all_four_buyback_and_tax_vaults_atomic_sandwich(
    vault_type: str, expected_ix: str
) -> None:
    """Verifies that all 4 supported buyback/burn & Token-2022 withheld-tax crank
    vaults trigger the Atomic 3-Step Kamino Flash-Loan Crank Sandwich when
    `accumulated_vault_sol >= 0.98 * crank_trigger_threshold_sol` and
    `permissionless_crank_callable == True`, generating `net_profit_sol > 0.0`.
    """
    res = evaluate_protocol_buyback_and_tax_crank(
        token_mint="BuybackVaultTargetMint111111111111111111111",
        vault_type=vault_type,
        accumulated_vault_sol=49.5,  # 99.0% of 50.0 SOL threshold (>= 0.98)
        crank_trigger_threshold_sol=50.0,
        permissionless_crank_callable=True,
        pool_sol_reserve=220.0,
        pool_token_reserve=220_000_000.0,
    )

    assert res.vault_type == vault_type
    assert res.near_or_above_threshold is True
    assert res.vault_fill_ratio == pytest.approx(0.99, rel=1e-5)
    assert res.crank_standalone_price_impact_pct > 40.0
    assert res.crank_standalone_price_impact_bps > 4_000.0
    assert res.sandwich_triggered is True
    assert res.recommended_action == ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH
    assert res.crank_instruction_name == expected_ix

    # Verify 3-step atomic execution invariants
    assert len(res.atomic_steps) == 3
    assert res.kamino_flash_borrow_sol > 0.0
    assert res.kamino_flash_fee_sol == pytest.approx(
        res.kamino_flash_borrow_sol * KAMINO_FLASH_LOAN_FEE_RATE, rel=1e-4
    )
    assert res.step1_tokens_acquired > 0.0
    assert res.step1_spot_price_after_buy > res.spot_price_sol_before
    assert res.step2_spot_price_after_crank > res.step1_spot_price_after_buy
    assert res.step3_sol_received_from_sell > res.kamino_flash_borrow_sol
    assert res.gross_profit_sol > 0.0
    assert res.net_profit_sol > 0.0
    assert res.net_profit_usd > 0.0


def test_exact_98_percent_threshold_boundary() -> None:
    """Verifies the exact `0.98 * crank_trigger_threshold_sol` boundary condition."""
    # Exactly at 0.98 * 100.0 = 98.0 SOL -> Triggers atomic crank sandwich
    at_98 = evaluate_protocol_buyback_and_tax_crank(
        token_mint="Boundary98Mint11111111111111111111111111111",
        vault_type=VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN,
        accumulated_vault_sol=98.0,
        crank_trigger_threshold_sol=100.0,
        permissionless_crank_callable=True,
        pool_sol_reserve=300.0,
        pool_token_reserve=300_000_000.0,
    )
    assert at_98.near_or_above_threshold is True
    assert at_98.sandwich_triggered is True
    assert at_98.recommended_action == ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH
    assert at_98.net_profit_sol > 0.0

    # At 0.90 * 100.0 = 90.0 SOL -> Stages pre-crank accumulation without firing bundle
    at_90 = evaluate_protocol_buyback_and_tax_crank(
        token_mint="Boundary90Mint11111111111111111111111111111",
        vault_type=VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN,
        accumulated_vault_sol=90.0,
        crank_trigger_threshold_sol=100.0,
        permissionless_crank_callable=True,
        pool_sol_reserve=300.0,
        pool_token_reserve=300_000_000.0,
    )
    assert at_90.near_or_above_threshold is False
    assert at_90.sandwich_triggered is False
    assert at_90.recommended_action == ACTION_STAGE_PRE_CRANK_ACCUMULATION

    # At 0.50 * 100.0 = 50.0 SOL -> Skips crank below threshold
    at_50 = evaluate_protocol_buyback_and_tax_crank(
        token_mint="Boundary50Mint11111111111111111111111111111",
        vault_type=VAULT_PUMPSWAP_CREATOR_FEE_AUTO_BURN,
        accumulated_vault_sol=50.0,
        crank_trigger_threshold_sol=100.0,
        permissionless_crank_callable=True,
        pool_sol_reserve=300.0,
        pool_token_reserve=300_000_000.0,
    )
    assert at_50.near_or_above_threshold is False
    assert at_50.sandwich_triggered is False
    assert at_50.recommended_action == ACTION_SKIP_CRANK_BELOW_THRESHOLD


def test_token2022_withheld_tokens_conversion_and_guards() -> None:
    """Verifies Token-2022 `withdrawWithheldTokensFromAccounts` conversion when
    `accumulated_vault_sol` is derived directly from `withheld_token_balance`,
    and verifies rejection when `permissionless_crank_callable == False` or
    unsupported vault type is supplied.
    """
    # Derive SOL equivalent from 40M withheld tokens on a 200 SOL / 200M token pool
    res_derived = evaluate_protocol_buyback_and_tax_crank(
        token_mint="Token2022DerivedSolMint11111111111111111111",
        vault_type=VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER,
        accumulated_vault_sol=0.0,
        crank_trigger_threshold_sol=32.0,
        permissionless_crank_callable=True,
        pool_sol_reserve=200.0,
        pool_token_reserve=200_000_000.0,
        withheld_token_balance=40_000_000.0,
        withheld_accounts_count=85,
        token2022_transfer_fee_bps=50.0,
        withdraw_withheld_callable=True,
    )
    assert res_derived.accumulated_vault_sol > 33.0
    assert res_derived.near_or_above_threshold is True
    assert res_derived.sandwich_triggered is True
    assert "withdrawWithheldTokensFromAccounts" in res_derived.instruction_sequence
    assert "harvest_withheld_tax_to_lp" in res_derived.instruction_sequence
    assert res_derived.net_profit_sol > 0.0

    # Non-permissionless crank must abort
    res_gated = evaluate_protocol_buyback_and_tax_crank(
        token_mint="GatedCrankMint11111111111111111111111111111",
        vault_type=VAULT_BELIEVE_LAUNCHCOIN_BUYBACK_VAULT,
        accumulated_vault_sol=60.0,
        crank_trigger_threshold_sol=50.0,
        permissionless_crank_callable=False,
    )
    assert res_gated.sandwich_triggered is False
    assert res_gated.recommended_action == ACTION_ABORT_CRANK_NOT_PERMISSIONLESS

    # Unsupported vault must abort cleanly
    res_unsupported = evaluate_protocol_buyback_and_tax_crank(
        token_mint="UnknownVaultMint111111111111111111111111111",
        vault_type="UNKNOWN_PROTOCOL_VAULT",
        accumulated_vault_sol=60.0,
        crank_trigger_threshold_sol=50.0,
    )
    assert res_unsupported.sandwich_triggered is False
    assert res_unsupported.recommended_action == ACTION_ABORT_CRANK_UNSUPPORTED_VAULT

    # Excessive transfer tax (e.g. 40% transfer fee) renders sandwich net-negative EV
    res_neg_ev = evaluate_protocol_buyback_and_tax_crank(
        token_mint="ExcessiveTaxMint111111111111111111111111111",
        vault_type=VAULT_TOKEN2022_WITHHELD_TAX_HARVESTER,
        accumulated_vault_sol=50.0,
        crank_trigger_threshold_sol=50.0,
        permissionless_crank_callable=True,
        pool_sol_reserve=250.0,
        pool_token_reserve=250_000_000.0,
        kamino_flash_borrow_sol=20.0,
        token2022_transfer_fee_bps=4_000.0,
    )
    assert res_neg_ev.sandwich_triggered is False
    assert res_neg_ev.recommended_action == ACTION_SKIP_CRANK_NEGATIVE_NET_EV


# ============================================================================
# 2. Cross-Chain Inbound Whale Bridge Intent Lookahead Tests
# ============================================================================


@pytest.mark.parametrize(
    "bridge_protocol,source_chain,event_name,dest_chain",
    [
        (
            BRIDGE_PROTOCOL_MAYAN_SWIFT,
            SOURCE_CHAIN_ETHEREUM,
            "OrderCreated",
            SOLANA_DEBRIDGE_DLN_CHAIN_ID,
        ),
        (
            BRIDGE_PROTOCOL_DEBRIDGE_DLN,
            SOURCE_CHAIN_BASE,
            "OrderCreated",
            "solana-mainnet",
        ),
        (
            BRIDGE_PROTOCOL_RELAY_INTENTS,
            SOURCE_CHAIN_ARBITRUM,
            "SwapInitiated",
            "7565164",
        ),
    ],
)
def test_cross_chain_whale_bridge_pre_position_across_protocols_and_chains(
    bridge_protocol: str,
    source_chain: str,
    event_name: str,
    dest_chain: int | str,
) -> None:
    """Verifies cross-chain whale bridge intent lookahead across `MAYAN_SWIFT`,
    `DEBRIDGE_DLN`, and `RELAY_INTENTS` originating from Ethereum, Base, and
    Arbitrum with `inbound_amount_usd >= 25_000.0` targeting Solana (`7565164` /
    `solana-mainnet`).
    """
    res = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="WhaleBridgeSolanaMint1111111111111111111111",
        bridge_protocol=bridge_protocol,
        source_chain=source_chain,
        event_name=event_name,
        inbound_amount_usd=55_000.0,
        destination_chain=dest_chain,
        firewall_passed=True,
        firewall_gates_verified=6,
        pool_sol_reserve=320.0,
        pool_token_reserve=320_000_000.0,
        solver_spread_bps=12.5,
        prefer_local_dln_solver=False,
    )

    assert res.bridge_protocol == bridge_protocol
    assert res.source_chain == source_chain
    assert res.destination_is_solana is True
    assert res.destination_chain_id == SOLANA_DEBRIDGE_DLN_CHAIN_ID
    assert res.whale_threshold_met is True
    assert 3.0 <= res.estimated_arrival_window_sec <= 12.0
    assert res.within_relay_window is True
    assert res.firewall_passed is True
    assert res.expected_solver_price_impact_pct > 50.0
    assert res.pre_position_triggered is True
    assert 3.0 <= res.pre_position_lead_time_sec <= 10.0
    assert res.pre_position_net_profit_sol > 0.0
    assert res.pre_position_net_profit_usd > 0.0
    assert len(res.auto_scale_out_limit_orders) == 3
    assert res.recommended_action == ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER
    assert ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER in res.active_strategies
    assert ACTION_FULFILL_AS_LOCAL_DLN_SOLVER in res.active_strategies


def test_direct_intent_solver_fulfillment_via_kamino_flash_liquidity() -> None:
    """Verifies `FULFILL_AS_LOCAL_DLN_SOLVER` when `solver_spread_bps >= 8.0` and
     verifies rejection when `solver_spread_bps < 8.0`.
    """
    # Positive solver spread >= 8.0 bps with prefer_local_dln_solver=True
    res_solver = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="LocalSolverTargetMint1111111111111111111111",
        bridge_protocol=BRIDGE_PROTOCOL_DEBRIDGE_DLN,
        source_chain=SOURCE_CHAIN_ARBITRUM,
        event_name="OrderCreated",
        inbound_amount_usd=80_000.0,
        destination_chain=SOLANA_DEBRIDGE_DLN_CHAIN_ID,
        estimated_arrival_window_sec=7.5,
        firewall_passed=True,
        firewall_gates_verified=6,
        pool_sol_reserve=900.0,
        pool_token_reserve=900_000_000.0,
        solver_spread_bps=15.0,
        prefer_local_dln_solver=True,
    )
    assert res_solver.local_solver_eligible is True
    assert res_solver.local_solver_triggered is True
    assert res_solver.local_solver_action == ACTION_FULFILL_AS_LOCAL_DLN_SOLVER
    assert res_solver.recommended_action == ACTION_FULFILL_AS_LOCAL_DLN_SOLVER
    assert res_solver.local_solver_kamino_flash_sol > 0.0
    assert res_solver.local_solver_net_profit_sol > 0.0
    assert res_solver.local_solver_net_profit_usd > 0.0

    # Solver spread < 8.0 bps -> local solver not eligible
    res_low_spread = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="LowSpreadSolverMint111111111111111111111111",
        bridge_protocol=BRIDGE_PROTOCOL_RELAY_INTENTS,
        source_chain=SOURCE_CHAIN_BASE,
        event_name="SwapInitiated",
        inbound_amount_usd=30_000.0,
        destination_chain="solana-mainnet",
        estimated_arrival_window_sec=4.5,
        firewall_passed=True,
        firewall_gates_verified=6,
        solver_spread_bps=5.5,
    )
    assert res_low_spread.local_solver_eligible is False
    assert res_low_spread.local_solver_triggered is False
    assert res_low_spread.local_solver_action == "SOLVER_SPREAD_BELOW_MIN_8BPS"


def test_cross_chain_bridge_lookahead_safety_guards() -> None:
    """Verifies all safety guards on cross-chain bridge lookahead:
    1. Below `$25,000` whale threshold
    2. Non-Solana destination chain
    3. 6-Gate Smart Contract Firewall failure
    4. Arrival window outside `[3.0s, 12.0s]`
    5. Unsupported source chain or protocol
    """
    # 1. Below $25,000 whale threshold
    below_whale = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="SmallOrderMint11111111111111111111111111111",
        inbound_amount_usd=18_500.0,
    )
    assert below_whale.whale_threshold_met is False
    assert below_whale.recommended_action == ACTION_SKIP_BRIDGE_BELOW_WHALE_THRESHOLD

    # 2. Non-Solana destination chain (e.g., Arbitrum 42161)
    non_solana = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="WrongDestMint111111111111111111111111111111",
        inbound_amount_usd=50_000.0,
        destination_chain=42161,
    )
    assert non_solana.destination_is_solana is False
    assert non_solana.recommended_action == ACTION_SKIP_BRIDGE_NON_SOLANA_DEST

    # 3. 6-Gate Smart Contract Firewall failure
    firewall_fail = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="MaliciousMint111111111111111111111111111111",
        inbound_amount_usd=50_000.0,
        firewall_passed=False,
        firewall_gates_verified=4,
    )
    assert firewall_fail.firewall_passed is False
    assert firewall_fail.recommended_action == ACTION_ABORT_BRIDGE_FIREWALL_FAILED

    # 4. Arrival window outside [3.0s, 12.0s]
    outside_window = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="LateArrivalMint1111111111111111111111111111",
        inbound_amount_usd=50_000.0,
        estimated_arrival_window_sec=18.5,
    )
    assert outside_window.within_relay_window is False
    assert outside_window.recommended_action == ACTION_SKIP_BRIDGE_OUTSIDE_RELAY_WINDOW

    # 5. Unsupported source chain
    unsupported_src = evaluate_cross_chain_whale_bridge_lookahead(
        target_solana_mint="UnsupportedChainMint11111111111111111111111",
        source_chain="POLYGON",
        inbound_amount_usd=50_000.0,
    )
    assert unsupported_src.recommended_action == ACTION_SKIP_BRIDGE_UNSUPPORTED_SOURCE


# ============================================================================
# 3. CrankBuybackAndBridgeLookaheadEngine Facade & Telemetry Tests
# ============================================================================


def test_engine_facade_diagnostic_and_telemetry() -> None:
    """Verifies `CrankBuybackAndBridgeLookaheadEngine.run_full_crank_bridge_diagnostic()`
    and `get_telemetry_summary()` for `TitanIPCDaemon` (`RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD`).
    """
    engine = CrankBuybackAndBridgeLookaheadEngine()
    diag = engine.run_full_crank_bridge_diagnostic()

    assert diag["status"] == "OK"
    assert diag["ipc_action"] == IPC_ACTION_RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD
    assert diag["subsystem"] == "CRANK_BUYBACK_BRIDGE_LOOKAHEAD_ENGINE_AGENT_27"
    assert diag["diagnostic_latency_ms"] >= 0.0

    # Verify both crank sandwich scenarios succeeded with positive profit
    pumpswap_crank = diag["pumpswap_buyback_crank_sandwich"]
    assert pumpswap_crank["sandwich_triggered"] is True
    assert pumpswap_crank["net_profit_sol"] > 0.0
    assert pumpswap_crank["recommended_action"] == ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH

    token2022_crank = diag["token2022_tax_harvester_crank_sandwich"]
    assert token2022_crank["sandwich_triggered"] is True
    assert token2022_crank["net_profit_sol"] > 0.0
    assert token2022_crank["recommended_action"] == ACTION_EXECUTE_ATOMIC_CRANK_SANDWICH

    # Verify both cross-chain bridge scenarios succeeded
    debridge_pre = diag["debridge_dln_whale_pre_position"]
    assert debridge_pre["pre_position_triggered"] is True
    assert debridge_pre["recommended_action"] == ACTION_PRE_POSITION_BEFORE_BRIDGE_SOLVER

    mayan_solver = diag["mayan_swift_local_solver_fulfillment"]
    assert mayan_solver["local_solver_triggered"] is True
    assert mayan_solver["recommended_action"] == ACTION_FULFILL_AS_LOCAL_DLN_SOLVER

    # Verify telemetry counters
    telemetry = engine.get_telemetry_summary()
    assert telemetry["engine"] == "CrankBuybackAndBridgeLookaheadEngine"
    assert telemetry["agent_id"] == "crank-buyback-bridge-lookahead"
    assert telemetry["agent_number"] == 27
    assert telemetry["ipc_action"] == IPC_ACTION_RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD
    assert telemetry["crank_evaluations"] == 2
    assert telemetry["crank_sandwiches_triggered"] == 2
    assert telemetry["cumulative_crank_profit_sol"] > 0.0
    assert telemetry["cumulative_crank_profit_usd"] > 0.0
    assert telemetry["bridge_lookahead_evaluations"] == 2
    assert telemetry["bridge_pre_positions_triggered"] == 2
    assert telemetry["bridge_local_solver_fills_triggered"] == 2
    assert telemetry["cumulative_bridge_profit_usd"] > 0.0
    assert telemetry["benchmarks"]["crank_trigger_fill_ratio_min"] == CRANK_TRIGGER_FILL_RATIO_MIN
    assert telemetry["benchmarks"]["kamino_flash_loan_fee_pct"] == KAMINO_FLASH_LOAN_FEE_PCT
    assert telemetry["benchmarks"]["solana_debridge_dln_chain_id"] == SOLANA_DEBRIDGE_DLN_CHAIN_ID
    assert telemetry["benchmarks"]["min_inbound_whale_bridge_usd"] == MIN_INBOUND_WHALE_BRIDGE_USD
    assert (
        telemetry["benchmarks"]["min_local_dln_solver_spread_bps"]
        == MIN_LOCAL_DLN_SOLVER_SPREAD_BPS
    )
    assert set(telemetry["benchmarks"]["supported_buyback_vaults"]) == set(
        SUPPORTED_BUYBACK_AND_TAX_VAULTS
    )
    assert set(telemetry["benchmarks"]["supported_bridge_protocols"]) == set(
        SUPPORTED_BRIDGE_PROTOCOLS
    )
    assert set(telemetry["benchmarks"]["supported_evm_source_chains"]) == set(
        SUPPORTED_EVM_SOURCE_CHAINS
    )
