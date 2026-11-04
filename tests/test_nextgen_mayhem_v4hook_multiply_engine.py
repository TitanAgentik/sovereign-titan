"""Comprehensive pytest verification suite for
`/home/titanagentik/sovereign-titan/src/engines/nextgen_mayhem_v4hook_multiply_engine.py`
implementing Agent 23 (`mayhem-v4hook-multiply-synthesizer`):
1. Strategy 1 — Autonomous AI-Agent Orderflow Backrunning in Pump.fun "Mayhem Mode" Across
   90+ Custom Quote Pairs & Hour-24 Supply Burn Front-Runner
   (`evaluate_mayhem_mode_ai_backrun_and_hour24_burn`)
2. Strategy 2 — Parasitic Uniswap V4 `afterSwap` Hooks for Zero-Transfer Internalized Arbitrage
   on Base (`simulate_parasitic_v4_afterswap_hook`)
3. Strategy 3 — Flash-Bootstrapped Asymmetric `5x` "Multiply" Squeezes (`80% LTV`) & Zero-Capital
   Isolated Market Liquidation Hunting (`86% LLTV`, `1.05 LIF`)
   (`execute_multiply_squeeze_and_isolated_liquidation`)
4. `NextGenMayhemV4HookMultiplyEngine` Facade Class (`RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE`)
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engines.nextgen_mayhem_v4hook_multiply_engine import (
    ACTION_EXECUTE_5X_MULTIPLY_AND_ISOLATED_LIQUIDATION,
    ACTION_EXECUTE_5X_MULTIPLY_SQUEEZE_ONLY,
    ACTION_EXECUTE_HOUR24_BURN_FRONTRUN,
    ACTION_EXECUTE_MAYHEM_AI_TRIANGULAR_BACKRUN,
    ACTION_EXECUTE_PARASITIC_V4_AFTERSWAP_ARB,
    ACTION_EXECUTE_ZERO_CAPITAL_LIQUIDATION_ONLY,
    ACTION_HOLD_MULTIPLY_AND_LIQUIDATION_IDLE,
    ACTION_NOOP_PARASITIC_V4_HOOK,
    ACTION_SKIP_MAYHEM_NO_EDGE,
    AERODROME_SLIPSTREAM_DEFAULT_FEE_BPS,
    CLANKER_INITIAL_MCAP_USD,
    CLANKER_LP_FEE_CUT_PCT,
    CLANKER_UNIV3_FEE_BPS,
    CLANKER_UNIV3_FEE_PCT,
    IPC_ACTION_RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE,
    KAMINO_FLASH_LOAN_FEE_BPS,
    KAMINO_FLASH_LOAN_FEE_PCT,
    KNOWN_MAYHEM_AI_AGENT_AUTHORITIES,
    KNOWN_MAYHEM_CUSTOM_QUOTE_ASSETS,
    MAYHEM_AI_AGENT_MINTED_SUPPLY,
    MAYHEM_AI_MAX_ORDERS_PER_MINUTE_CAP,
    MAYHEM_AI_MAX_ORDER_SIZE_CAP_SOL,
    MAYHEM_CUSTOM_QUOTE_ASSETS_MIN_COUNT,
    MAYHEM_GRADUATION_ODDS_DENOMINATOR,
    MAYHEM_GRADUATION_RATE_PCT,
    MAYHEM_GRADUATION_SOL_THRESHOLD,
    MAYHEM_HOUR24_BURN_TIMESTAMP_SEC,
    MAYHEM_HOUR24_FRONTRUN_WINDOW_START_SEC,
    MAYHEM_INITIAL_TOTAL_SUPPLY,
    MAYHEM_MIN_BAYESIAN_MEAN_REVERSION_PROB,
    MAYHEM_RARITY_MULTIPLIER_VS_REGULAR,
    MAYHEM_STANDARD_SUPPLY,
    MORPHO_DEFAULT_LIF_BONUS_PCT,
    MORPHO_DEFAULT_LIF_MULTIPLIER,
    MORPHO_DEFAULT_LLTV_PCT,
    MORPHO_FLASH_LOAN_FEE_PCT,
    MORPHO_PROTOCOL_FEE_PCT,
    MULTIPLY_DEFAULT_BUYING_POWER_SOL,
    MULTIPLY_DEFAULT_FLASH_BORROW_SOL,
    MULTIPLY_DEFAULT_LEVERAGE_MULTIPLIER,
    MULTIPLY_DEFAULT_LTV_PCT,
    MULTIPLY_DEFAULT_SEED_CAPITAL_SOL,
    MULTIPLY_DEXSCREENER_BREAKOUT_VOLUME_SOL,
    NextGenMayhemV4HookMultiplyEngine,
    PARASITIC_V4_DYNAMIC_FEE_BPS,
    PARASITIC_V4_DYNAMIC_FEE_PCT,
    Q96_SCALE,
    V4_IS_UNLOCKED_SLOT_GAS_OVERHEAD,
    V4_IS_UNLOCKED_SLOT_TAKE_FEE_PCT,
    evaluate_mayhem_mode_ai_backrun_and_hour24_burn,
    execute_multiply_squeeze_and_isolated_liquidation,
    simulate_parasitic_v4_afterswap_hook,
)


def test_strategy1_mayhem_mode_constants_and_kamino_triangular_ai_backrun() -> None:
    """Verifies Pump.fun 2026 Mayhem Mode constants (2B supply = 1B standard + 1B AI agent,
    2.0% / 1-in-50 graduation rate at 85 SOL, 22x rarer, 90+ custom quote assets Q,
    Kamino 0.001% flash loan fee) and confirms profitable atomic triangular backrunning
    (`SOL -> Q -> MayhemMeme -> SOL`) behind the bounded AI noise trader's sell order.
    """
    assert MAYHEM_STANDARD_SUPPLY == 1_000_000_000
    assert MAYHEM_AI_AGENT_MINTED_SUPPLY == 1_000_000_000
    assert MAYHEM_INITIAL_TOTAL_SUPPLY == 2_000_000_000
    assert MAYHEM_GRADUATION_RATE_PCT == pytest.approx(2.0)
    assert MAYHEM_GRADUATION_ODDS_DENOMINATOR == 50
    assert MAYHEM_GRADUATION_SOL_THRESHOLD == pytest.approx(85.0)
    assert MAYHEM_RARITY_MULTIPLIER_VS_REGULAR == pytest.approx(22.0)
    assert MAYHEM_CUSTOM_QUOTE_ASSETS_MIN_COUNT == 90
    assert len(KNOWN_MAYHEM_CUSTOM_QUOTE_ASSETS) >= 90
    assert KAMINO_FLASH_LOAN_FEE_PCT == pytest.approx(0.001)
    assert KAMINO_FLASH_LOAN_FEE_BPS == pytest.approx(0.1)
    assert MAYHEM_HOUR24_BURN_TIMESTAMP_SEC == pytest.approx(86_400.0)
    assert MAYHEM_HOUR24_FRONTRUN_WINDOW_START_SEC == pytest.approx(85_800.0)

    res = evaluate_mayhem_mode_ai_backrun_and_hour24_burn(
        "MayhemTokenMint1111111111111111111111111111",
        quote_asset_symbol="USD1",
        is_mayhem_ai_agent_signer=True,
        ai_agent_order_side="SELL",
        ai_agent_order_size_sol=8.0,
        ai_orders_last_minute=5,
        cross_pair_dislocation_bps=190.0,
        kamino_flash_borrow_sol=40.0,
        elapsed_sec=12_000.0,
        unsold_ai_agent_inventory_tokens=700_000_000,
    )

    assert res.is_supported_custom_quote_asset is True
    assert res.supported_custom_quote_asset_count >= 90
    assert res.initial_total_supply == 2_000_000_000
    assert res.standard_curve_supply == 1_000_000_000
    assert res.ai_agent_minted_supply == 1_000_000_000
    assert res.is_mayhem_ai_agent_signer is True
    assert res.within_ai_noise_bounds is True
    assert res.insider_adverse_selection_prob == pytest.approx(0.0)
    assert res.bayesian_mean_reversion_prob >= MAYHEM_MIN_BAYESIAN_MEAN_REVERSION_PROB
    assert res.kamino_flash_borrow_sol == pytest.approx(40.0)
    assert res.kamino_flash_fee_pct == pytest.approx(0.001)
    assert res.kamino_flash_fee_sol == pytest.approx(0.0004)
    assert res.orca_meteora_quote_out_amount > 0.0
    assert res.mayhem_meme_acquired_tokens > 0.0
    assert res.parallel_sol_pool_gross_out_sol > res.kamino_flash_borrow_sol
    assert res.net_triangular_backrun_profit_sol > 0.0
    assert res.same_slot_settlement is True
    assert res.ai_noise_backrun_triggered is True
    assert res.hour24_burn_frontrun_triggered is False
    assert res.should_execute is True
    assert res.action == ACTION_EXECUTE_MAYHEM_AI_TRIANGULAR_BACKRUN
    assert len(res.execution_route_legs) == 5


def test_strategy1_hour24_deterministic_supply_burn_frontrunner_and_non_ai_rejection() -> None:
    """Verifies that right before Hour 24 (`85,800s <= elapsed_sec < 86,400s`), the engine
    triggers `"EXECUTE_HOUR24_BURN_MULTIPLY_FRONTRUN"` to front-run automated FDV-screener
    bots before the AI agent burns its unsold inventory out of the second billion tokens,
    and rejects non-AI informed orderflow outside the burn window.
    """
    burn_res = evaluate_mayhem_mode_ai_backrun_and_hour24_burn(
        "MayhemHour24Mint222222222222222222222222222",
        quote_asset_symbol="JitoSOL",
        is_mayhem_ai_agent_signer=False,
        elapsed_sec=86_150.0,  # Inside [85,800s, 86,400s) window
        unsold_ai_agent_inventory_tokens=800_000_000,
    )

    assert burn_res.in_hour24_burn_frontrun_window is True
    assert burn_res.unsold_ai_agent_inventory_tokens == 800_000_000
    assert burn_res.post_burn_total_supply == 1_200_000_000
    assert burn_res.supply_burn_shock_pct == pytest.approx(40.0)
    assert burn_res.implied_fdv_upshift_multiplier == pytest.approx(2_000_000_000 / 1_200_000_000, rel=1e-3)
    assert burn_res.implied_fdv_upshift_pct > 66.0
    assert burn_res.hour24_burn_frontrun_triggered is True
    assert burn_res.should_execute is True
    assert burn_res.action == ACTION_EXECUTE_HOUR24_BURN_FRONTRUN

    # Non-AI signer outside the Hour-24 burn window is rejected due to insider adverse selection risk
    non_ai_res = evaluate_mayhem_mode_ai_backrun_and_hour24_burn(
        "MayhemNonAISignerMint3333333333333333333333",
        quote_asset_symbol="USDC",
        is_mayhem_ai_agent_signer=False,
        ai_agent_order_side="SELL",
        cross_pair_dislocation_bps=220.0,
        elapsed_sec=20_000.0,
    )
    assert non_ai_res.is_mayhem_ai_agent_signer is False
    assert non_ai_res.insider_adverse_selection_prob > 0.5
    assert non_ai_res.ai_noise_backrun_triggered is False
    assert non_ai_res.hour24_burn_frontrun_triggered is False
    assert non_ai_res.should_execute is False
    assert non_ai_res.action == ACTION_SKIP_MAYHEM_NO_EDGE


def test_strategy2_parasitic_v4_afterswap_hook_three_stage_erc6909_extraction() -> None:
    """Verifies Strategy 2 on Base L2:
    - Low-fee (0.05% = 5 bps) Uniswap V4 pool intercepting UniversalRouter retail flow
    - Clanker ($30,000 initial MC, 1.00% fee, 20.0% Clanker LP fee cut) & Aerodrome Slipstream
    - Stage 1: poolManager.take(WETH) at 0.00% fee and 0 lock/unlock gas overhead inside IS_UNLOCKED_SLOT
    - Stage 2: Synchronous sqrtPriceX96 equalization inside the user's own transaction
    - Stage 3: poolManager.settle() + ERC-6909 internal claim mint(), leaving 0.0 bps post-tx spread.
    """
    assert CLANKER_INITIAL_MCAP_USD == pytest.approx(30_000.0)
    assert CLANKER_UNIV3_FEE_PCT == pytest.approx(1.00)
    assert CLANKER_UNIV3_FEE_BPS == pytest.approx(100.0)
    assert CLANKER_LP_FEE_CUT_PCT == pytest.approx(20.0)
    assert PARASITIC_V4_DYNAMIC_FEE_PCT == pytest.approx(0.05)
    assert PARASITIC_V4_DYNAMIC_FEE_BPS == pytest.approx(5.0)
    assert AERODROME_SLIPSTREAM_DEFAULT_FEE_BPS == pytest.approx(10.0)
    assert V4_IS_UNLOCKED_SLOT_TAKE_FEE_PCT == pytest.approx(0.0)
    assert V4_IS_UNLOCKED_SLOT_GAS_OVERHEAD == 0

    hook_res = simulate_parasitic_v4_afterswap_hook(
        "CLANKMEME",
        universal_router_retail_swap_weth=15.0,
        v4_pool_liquidity_weth=60.0,
        clanker_v3_liquidity_weth=80.0,
        aerodrome_slipstream_liquidity_weth=100.0,
        pre_swap_v4_sqrt_price_x96=Q96_SCALE,
        is_unlocked_slot_active=True,
    )

    assert hook_res.chain == "BASE_L2"
    assert hook_res.v4_dynamic_fee_bps == pytest.approx(5.0)
    assert hook_res.v4_dynamic_fee_pct == pytest.approx(0.05)
    assert hook_res.clanker_initial_mcap_usd == pytest.approx(30_000.0)
    assert hook_res.clanker_v3_fee_pct == pytest.approx(1.00)
    assert hook_res.clanker_lp_fee_cut_pct == pytest.approx(20.0)
    assert hook_res.is_unlocked_slot_active is True
    assert hook_res.stage1_take_weth_amount > 0.0
    assert hook_res.stage1_flash_fee_pct == pytest.approx(0.0)
    assert hook_res.stage1_lock_unlock_gas_overhead == 0
    assert hook_res.post_retail_v4_sqrt_price_x96 > hook_res.pre_swap_v4_sqrt_price_x96
    assert (
        hook_res.pre_swap_v4_sqrt_price_x96
        < hook_res.post_swap_equalized_sqrt_price_x96
        < hook_res.post_retail_v4_sqrt_price_x96
    )
    assert hook_res.pre_hook_spread_bps > 0.0
    assert hook_res.post_tx_external_spread_bps == pytest.approx(0.0)
    assert hook_res.stage3_settle_completed is True
    assert hook_res.erc6909_claim_minted_weth == pytest.approx(hook_res.net_profit_weth)
    assert hook_res.erc6909_claim_minted_weth > 0.0
    assert hook_res.net_profit_usd > 0.0
    assert hook_res.external_erc20_transfers_saved >= 2
    assert hook_res.synchronous_in_user_tx is True
    assert hook_res.triggered is True
    assert hook_res.action == ACTION_EXECUTE_PARASITIC_V4_AFTERSWAP_ARB
    assert len(hook_res.hook_stages_executed) == 3

    # Verify hook no-ops when spread is below external DEX fees or IS_UNLOCKED_SLOT is False
    noop_res = simulate_parasitic_v4_afterswap_hook(
        "CLANKMEME",
        universal_router_retail_swap_weth=0.02,
        v4_pool_liquidity_weth=200.0,
        pre_hook_spread_bps=4.0,
    )
    assert noop_res.triggered is False
    assert noop_res.erc6909_claim_minted_weth == pytest.approx(0.0)
    assert noop_res.action == ACTION_NOOP_PARASITIC_V4_HOOK


def test_strategy3_5x_multiply_squeeze_and_zero_capital_morpho_liquidation() -> None:
    """Verifies Strategy 3:
    - Part A: 20 SOL seed + 80 SOL Kamino flash loan -> 100 SOL (5.0x) breakout buy ->
      100 SOL collateral deposit -> 80 SOL isolated borrow (80% LTV) -> flashRepayIx,
      strictly capping downside risk at 20.0 SOL.
    - Part B: Morpho Blue 86.0% LLTV, 1.05 LIF (5.0% bonus), 0.0% protocol/flash fee.
      With $87,000 debt vs $100,000 collateral (87.0% LTV >= 86.0% LLTV), repays $87,000
      via 0% flash loan, seizes $91,350 collateral (+$4,350 gross bonus), and nets > $0
      with $0.0 upfront capital.
    """
    assert MULTIPLY_DEFAULT_SEED_CAPITAL_SOL == pytest.approx(20.0)
    assert MULTIPLY_DEFAULT_LTV_PCT == pytest.approx(80.0)
    assert MULTIPLY_DEFAULT_FLASH_BORROW_SOL == pytest.approx(80.0)
    assert MULTIPLY_DEFAULT_BUYING_POWER_SOL == pytest.approx(100.0)
    assert MULTIPLY_DEFAULT_LEVERAGE_MULTIPLIER == pytest.approx(5.0)
    assert MORPHO_DEFAULT_LLTV_PCT == pytest.approx(86.0)
    assert MORPHO_DEFAULT_LIF_MULTIPLIER == pytest.approx(1.05)
    assert MORPHO_DEFAULT_LIF_BONUS_PCT == pytest.approx(5.0)
    assert MORPHO_PROTOCOL_FEE_PCT == pytest.approx(0.0)
    assert MORPHO_FLASH_LOAN_FEE_PCT == pytest.approx(0.0)

    res = execute_multiply_squeeze_and_isolated_liquidation(
        "MEMESQUEEZE",
        seed_capital_sol=20.0,
        isolated_market_ltv_pct=80.0,
        dexscreener_breakout_threshold_sol=75.0,
        whale_collateral_usd=100_000.0,
        whale_debt_usd=87_000.0,
        market_lltv_pct=86.0,
        lif_multiplier=1.05,
        morpho_protocol_fee_pct=0.0,
        dex_swap_slippage_and_gas_usd=300.0,
    )

    # Part A assertions
    assert res.seed_capital_sol == pytest.approx(20.0)
    assert res.isolated_market_ltv_pct == pytest.approx(80.0)
    assert res.flash_borrowed_sol == pytest.approx(80.0)
    assert res.total_buying_power_sol == pytest.approx(100.0)
    assert res.leverage_multiplier == pytest.approx(5.0)
    assert res.kamino_flash_fee_pct == pytest.approx(0.001)
    assert res.kamino_flash_fee_sol == pytest.approx(0.0008)
    assert res.collateral_deposited_sol == pytest.approx(100.0)
    assert res.isolated_debt_borrowed_sol == pytest.approx(80.0)
    assert res.flash_repay_completed is True
    assert res.crossed_dexscreener_breakout_threshold is True
    assert res.max_downside_risk_sol == pytest.approx(20.0)
    assert res.cross_collateral_contagion_risk == pytest.approx(0.0)
    assert res.multiply_squeeze_triggered is True
    assert len(res.multiply_atomic_instructions) == 5

    # Part B assertions
    assert res.whale_collateral_usd == pytest.approx(100_000.0)
    assert res.whale_debt_usd == pytest.approx(87_000.0)
    assert res.whale_current_ltv_pct == pytest.approx(87.0)
    assert res.market_lltv_pct == pytest.approx(86.0)
    assert res.is_liquidatable is True
    assert res.lif_multiplier == pytest.approx(1.05)
    assert res.lif_bonus_pct == pytest.approx(5.0)
    assert res.morpho_protocol_fee_pct == pytest.approx(0.0)
    assert res.morpho_flash_loan_fee_pct == pytest.approx(0.0)
    assert res.upfront_capital_required_usd == pytest.approx(0.0)
    assert res.flash_loan_debt_repaid_usd == pytest.approx(87_000.0)
    assert res.seized_collateral_usd == pytest.approx(91_350.0)
    assert res.gross_liquidation_bonus_usd == pytest.approx(4_350.0)
    assert res.net_liquidation_profit_usd == pytest.approx(4_050.0)
    assert res.liquidation_triggered is True
    assert len(res.liquidation_atomic_steps) == 4
    assert res.should_execute is True
    assert res.action == ACTION_EXECUTE_5X_MULTIPLY_AND_ISOLATED_LIQUIDATION

    # Verify healthy whale position (< 86% LLTV) does not trigger liquidation
    healthy_res = execute_multiply_squeeze_and_isolated_liquidation(
        "SAFEMEME",
        enable_multiply_squeeze=False,
        whale_collateral_usd=100_000.0,
        whale_debt_usd=78_000.0,  # 78% LTV < 86% LLTV
        market_lltv_pct=86.0,
    )
    assert healthy_res.is_liquidatable is False
    assert healthy_res.liquidation_triggered is False
    assert healthy_res.multiply_squeeze_triggered is False
    assert healthy_res.should_execute is False
    assert healthy_res.action == ACTION_HOLD_MULTIPLY_AND_LIQUIDATION_IDLE


def test_nextgen_mayhem_v4hook_multiply_engine_facade_and_telemetry() -> None:
    """Verifies the `NextGenMayhemV4HookMultiplyEngine` facade diagnostic and telemetry
    integration for `TitanIPCDaemon` (`RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE`).
    """
    engine = NextGenMayhemV4HookMultiplyEngine()
    diag = engine.run_full_nextgen_strategies_diagnostic()

    assert diag["status"] == "OK"
    assert diag["ipc_action"] == IPC_ACTION_RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE
    assert diag["subsystem"] == "NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_ENGINE_AGENT_23"
    assert diag["mayhem_ai_triangular_backrun"]["ai_noise_backrun_triggered"] is True
    assert diag["mayhem_hour24_burn_frontrun"]["hour24_burn_frontrun_triggered"] is True
    assert (
        diag["mayhem_hour24_burn_frontrun"]["action"]
        == ACTION_EXECUTE_HOUR24_BURN_FRONTRUN
    )
    assert diag["parasitic_v4_afterswap_hook"]["triggered"] is True
    assert (
        diag["parasitic_v4_afterswap_hook"]["post_tx_external_spread_bps"]
        == pytest.approx(0.0)
    )
    assert (
        diag["multiply_squeeze_and_isolated_liquidation"]["max_downside_risk_sol"]
        == pytest.approx(20.0)
    )
    assert (
        diag["multiply_squeeze_and_isolated_liquidation"]["seized_collateral_usd"]
        == pytest.approx(91_350.0)
    )
    assert (
        diag["multiply_squeeze_and_isolated_liquidation"]["net_liquidation_profit_usd"]
        > 0.0
    )

    telemetry = engine.get_telemetry_summary()
    assert telemetry["engine"] == "NextGenMayhemV4HookMultiplyEngine"
    assert telemetry["agent_id"] == "mayhem-v4hook-multiply-synthesizer"
    assert telemetry["ipc_action"] == IPC_ACTION_RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE
    assert telemetry["mayhem_evaluations"] == 2
    assert telemetry["mayhem_ai_backruns_triggered"] >= 1
    assert telemetry["mayhem_hour24_burn_frontruns_triggered"] == 1
    assert telemetry["v4_hook_simulations"] == 1
    assert telemetry["v4_hook_arbs_triggered"] == 1
    assert telemetry["v4_cumulative_erc6909_weth"] > 0.0
    assert telemetry["multiply_and_liq_evaluations"] == 1
    assert telemetry["multiply_squeezes_triggered"] == 1
    assert telemetry["isolated_liquidations_triggered"] == 1
    assert telemetry["cumulative_liquidation_profit_usd"] > 0.0
    assert telemetry["benchmarks"]["mayhem_custom_quote_assets_count"] >= 90


def test_boundary_conditions_across_all_three_strategies() -> None:
    """Verifies exact boundary conditions across Strategy 1 (85,800s and 86,400s boundaries
    and authority matching), Strategy 2 (locked slot guard), and Strategy 3 (Multiply-only
    and Liquidation-only execution modes).
    """
    # Strategy 1: Authority auto-detection from KNOWN_MAYHEM_AI_AGENT_AUTHORITIES
    auto_auth_res = evaluate_mayhem_mode_ai_backrun_and_hour24_burn(
        "MayhemAutoAuthMint1111111111111111111111111",
        quote_asset_symbol="USDC",
        is_mayhem_ai_agent_signer=False,
        signer_authority=KNOWN_MAYHEM_AI_AGENT_AUTHORITIES[1],
        ai_agent_order_side="SELL",
        cross_pair_dislocation_bps=210.0,
        elapsed_sec=85_800.0,  # Exact start of Hour-24 frontrun window
        unsold_ai_agent_inventory_tokens=500_000_000,
    )
    assert auto_auth_res.is_mayhem_ai_agent_signer is True
    assert auto_auth_res.in_hour24_burn_frontrun_window is True
    assert auto_auth_res.hour24_burn_frontrun_triggered is True
    assert auto_auth_res.ai_noise_backrun_triggered is True
    assert auto_auth_res.action == ACTION_EXECUTE_HOUR24_BURN_FRONTRUN

    # Exact 86,400.0s boundary is post-burn (no longer in pre-burn front-run window)
    post_burn_boundary = evaluate_mayhem_mode_ai_backrun_and_hour24_burn(
        "MayhemPostBurnMint1111111111111111111111111",
        quote_asset_symbol="BONK",
        is_mayhem_ai_agent_signer=False,
        elapsed_sec=86_400.0,
        unsold_ai_agent_inventory_tokens=500_000_000,
    )
    assert post_burn_boundary.in_hour24_burn_frontrun_window is False
    assert post_burn_boundary.hour24_burn_frontrun_triggered is False

    # Strategy 2: Locked slot guard (`is_unlocked_slot_active=False`)
    locked_slot_res = simulate_parasitic_v4_afterswap_hook(
        "FLAUNCHMEME",
        universal_router_retail_swap_weth=25.0,
        is_unlocked_slot_active=False,
    )
    assert locked_slot_res.triggered is False
    assert locked_slot_res.stage1_take_weth_amount == pytest.approx(0.0)
    assert locked_slot_res.action == ACTION_NOOP_PARASITIC_V4_HOOK

    # Strategy 3: Multiply-Only vs Liquidation-Only actions
    multiply_only_res = execute_multiply_squeeze_and_isolated_liquidation(
        "MULTONLY",
        seed_capital_sol=20.0,
        isolated_market_ltv_pct=80.0,
        whale_collateral_usd=100_000.0,
        whale_debt_usd=70_000.0,  # Healthy (70% < 86% LLTV)
    )
    assert multiply_only_res.multiply_squeeze_triggered is True
    assert multiply_only_res.liquidation_triggered is False
    assert multiply_only_res.action == ACTION_EXECUTE_5X_MULTIPLY_SQUEEZE_ONLY

    liq_only_res = execute_multiply_squeeze_and_isolated_liquidation(
        "LIQONLY",
        enable_multiply_squeeze=False,
        whale_collateral_usd=100_000.0,
        whale_debt_usd=87_000.0,  # Underwater (87% >= 86% LLTV)
    )
    assert liq_only_res.multiply_squeeze_triggered is False
    assert liq_only_res.liquidation_triggered is True
    assert liq_only_res.action == ACTION_EXECUTE_ZERO_CAPITAL_LIQUIDATION_ONLY

