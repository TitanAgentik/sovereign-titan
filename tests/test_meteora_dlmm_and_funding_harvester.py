"""Comprehensive pytest verification suite for
`/home/titanagentik/sovereign-titan/src/engines/meteora_dlmm_and_funding_harvester.py`
implementing Agent 26 (`meteora-dlmm-funding-harvester`):
1. Meteora DLMM Dynamic Volatility Fee-Surge Harvester (`evaluate_meteora_dlmm_fee_surge_harvest`)
2. Delta-Neutral Perpetual Funding Rate & Cash-and-Carry Basis Harvester
   (`evaluate_delta_neutral_funding_harvest`)
3. `MeteoraDlmmAndFundingHarvester` Facade Class (`RUN_METEORA_DLMM_FUNDING_HARVESTER`)
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engines.meteora_dlmm_and_funding_harvester import (
    ACTION_AUTO_WITHDRAW_FEE_DECAY,
    ACTION_DEPLOY_3BIN_FEE_SURGE_HARVEST,
    ACTION_DEPLOY_DELTA_NEUTRAL_HARVEST,
    ACTION_HOLD_IDLE_BELOW_HURDLE,
    ACTION_SKIP_DLMM_ENTRY_GATES_FAILED,
    ACTION_UNWIND_NEGATIVE_FUNDING,
    DEFAULT_JITOSOL_LST_STAKING_APY_PCT,
    DELTA_NEUTRAL_LONG_SPOT_LEVERAGE,
    DELTA_NEUTRAL_SHORT_PERP_LEVERAGE,
    DELTA_NEUTRAL_TARGET_NET_DELTA_PCT,
    DLMM_ACTIVE_BIN_COUNT,
    DLMM_AUTO_WITHDRAW_FEE_DECAY_BPS,
    DLMM_AUTO_WITHDRAW_FEE_DECAY_PCT,
    DLMM_DEFAULT_BASE_FACTOR,
    DLMM_DEFAULT_BIN_STEP,
    DLMM_DEFAULT_TACTICAL_WINDOW_MINUTES,
    DLMM_DEFAULT_VARIABLE_FEE_CONTROL,
    DLMM_DEFAULT_VOLATILITY_ACCUMULATOR,
    DLMM_MAX_BOUNDED_NET_DELTA_PCT,
    DLMM_MAX_DYNAMIC_FEE_BPS,
    DLMM_MAX_DYNAMIC_FEE_PCT,
    DLMM_MIN_ORGANIC_VOLUME_RATIO,
    DLMM_MIN_TWO_SIDED_BUY_SELL_BALANCE,
    DLMM_SURGE_MIN_DYNAMIC_FEE_BPS,
    DLMM_SURGE_MIN_DYNAMIC_FEE_PCT,
    DLMM_TACTICAL_WINDOW_MAX_MINUTES,
    DLMM_TACTICAL_WINDOW_MIN_MINUTES,
    DLMM_TARGET_HOURLY_FEE_YIELD_MAX_PCT,
    DLMM_TARGET_HOURLY_FEE_YIELD_MIN_PCT,
    DLMM_VARIABLE_FEE_DENOMINATOR,
    FUNDING_1H_INTERVALS_PER_YEAR,
    FUNDING_8H_INTERVALS_PER_YEAR,
    IPC_ACTION_RUN_METEORA_DLMM_FUNDING_HARVESTER,
    MIN_DEPLOY_ANNUALIZED_FUNDING_APY_PCT,
    MeteoraDlmmAndFundingHarvester,
    SUPPORTED_FUNDING_VENUES,
    SUPPORTED_PERP_MARKETS,
    WEEKS_PER_YEAR,
    compute_meteora_dlmm_dynamic_fee,
    evaluate_delta_neutral_funding_harvest,
    evaluate_meteora_dlmm_fee_surge_harvest,
)


def test_meteora_dlmm_exact_dynamic_fee_formula_and_10pct_cap() -> None:
    """Verifies Meteora DLMM's exact dynamic fee formula:
    f_total(v_a) = min(f_max, f_base + f_variable(v_a)),
    f_base = B * s_bin,
    f_variable(v_a) = ((v_a * s_bin)^2 * V_control) / 10^11,
    across mid-surge (2.5%–10.0%) and max-cap (10.0% = 1,000 bps) regimes.
    """
    assert DLMM_VARIABLE_FEE_DENOMINATOR == pytest.approx(1e11)
    assert DLMM_SURGE_MIN_DYNAMIC_FEE_PCT == pytest.approx(2.50)
    assert DLMM_SURGE_MIN_DYNAMIC_FEE_BPS == pytest.approx(250.0)
    assert DLMM_MAX_DYNAMIC_FEE_PCT == pytest.approx(10.00)
    assert DLMM_MAX_DYNAMIC_FEE_BPS == pytest.approx(1000.0)
    assert DLMM_AUTO_WITHDRAW_FEE_DECAY_PCT == pytest.approx(1.00)
    assert DLMM_AUTO_WITHDRAW_FEE_DECAY_BPS == pytest.approx(100.0)

    # 1. Mid-surge verification: v_a = 300, s_bin = 100, B = 0.0025, V_control = 500
    # f_base = 0.0025 * 100 = 0.25% (25 bps)
    # f_variable = ((300 * 100)^2 * 500) / 10^11 = (9e8 * 500) / 1e11 = 4.50% (450 bps)
    # f_total = min(10.0, 0.25 + 4.50) = 4.75% (475 bps)
    fee_mid = compute_meteora_dlmm_dynamic_fee(
        volatility_accumulator=300.0,
        bin_step=100.0,
        base_factor=0.0025,
        variable_fee_control=500.0,
        max_fee_pct=10.0,
    )
    assert fee_mid.base_fee_pct == pytest.approx(0.25)
    assert fee_mid.base_fee_bps == pytest.approx(25.0)
    assert fee_mid.variable_fee_pct == pytest.approx(4.50)
    assert fee_mid.variable_fee_bps == pytest.approx(450.0)
    assert fee_mid.total_fee_pct == pytest.approx(4.75)
    assert fee_mid.total_fee_bps == pytest.approx(475.0)
    assert fee_mid.is_capped_at_max is False

    # 2. Extreme volatility surge capped at f_max = 10.00% (1,000 bps)
    fee_max = compute_meteora_dlmm_dynamic_fee(
        volatility_accumulator=500.0,
        bin_step=100.0,
        base_factor=0.0025,
        variable_fee_control=500.0,
        max_fee_pct=10.0,
    )
    assert fee_max.unclamped_total_fee_pct == pytest.approx(12.75)
    assert fee_max.total_fee_pct == pytest.approx(10.00)
    assert fee_max.total_fee_bps == pytest.approx(1000.0)
    assert fee_max.is_capped_at_max is True


def test_meteora_dlmm_3gate_entry_3bin_lp_delta_hedge_and_yield() -> None:
    """Verifies that when all 3 entry gates pass:
    1. dynamic_fee_pct >= 2.50% (>= 250 bps)
    2. organic_volume_ratio >= 0.65 (Tarjan SCC non-wash retail flow)
    3. two_sided_buy_sell_balance >= 0.35 (bidirectional churn)
    the engine deploys concentrated LP across [active_bin - 1, active_bin, active_bin + 1]
    for a tactical window (1–15 min), executes continuous PumpSwap/Jupiter delta-hedge
    rebalance trades keeping net directional exposure bounded, and achieves
    hourly_fee_yield_pct in [1.0%, 4.5%/hr] with net_harvested_fee_sol > 0.
    """
    res = evaluate_meteora_dlmm_fee_surge_harvest(
        pool_address="MeteoraDLMMPostGradPool11111111111111111111",
        token_mint="PostGradSurgeMemeMint1111111111111111111111",
        active_bin_id=8388608,
        volatility_accumulator=300.0,
        bin_step=100.0,
        base_factor=0.0025,
        variable_fee_control=500.0,
        max_fee_pct=10.0,
        organic_volume_ratio=0.80,
        two_sided_buy_sell_balance=0.46,
        lp_capital_deployed_sol=30.0,
        tactical_window_minutes=12.0,
        three_bin_tvl_sol=240.0,
        window_pool_volume_sol=380.0,
        bin_crossings_in_window=4,
    )

    assert res.dynamic_fee_pct == pytest.approx(4.75)
    assert res.dynamic_fee_bps == pytest.approx(475.0)
    assert 2.50 <= res.dynamic_fee_pct <= 10.00

    # 3-Gate Entry Filter verification
    assert res.gate1_fee_surge_passed is True
    assert res.gate2_organic_volume_passed is True
    assert res.gate3_two_sided_balance_passed is True
    assert res.all_three_entry_gates_passed is True
    assert res.tarjan_scc_wash_ratio == pytest.approx(0.20)

    # 3 active price bins [active_bin - 1, active_bin, active_bin + 1]
    assert len(res.deployed_bins) == DLMM_ACTIVE_BIN_COUNT == 3
    assert res.deployed_bins == (8388607, 8388608, 8388609)
    assert sum(res.bin_liquidity_weights) == pytest.approx(1.0)
    assert (
        DLMM_TACTICAL_WINDOW_MIN_MINUTES
        <= res.tactical_window_minutes
        <= DLMM_TACTICAL_WINDOW_MAX_MINUTES
    )

    # Hourly fee yield (1.0%–4.5%/hr) & net harvested SOL
    assert (
        DLMM_TARGET_HOURLY_FEE_YIELD_MIN_PCT
        <= res.hourly_fee_yield_pct
        <= DLMM_TARGET_HOURLY_FEE_YIELD_MAX_PCT
    )
    assert res.gross_harvested_fee_sol > 0.0
    assert res.net_harvested_fee_sol > 0.0

    # Continuous PumpSwap/Jupiter delta hedging
    assert res.delta_hedge_venue == "PumpSwap/Jupiter"
    assert res.delta_hedge_rebalance_count == 4
    assert len(res.delta_hedge_rebalance_trades) == 4
    venues_used = {leg["venue"] for leg in res.delta_hedge_rebalance_trades}
    assert venues_used == {"PumpSwap", "Jupiter"}
    assert res.net_directional_delta_pct <= DLMM_MAX_BOUNDED_NET_DELTA_PCT
    assert res.net_directional_exposure_sol < res.unhedged_inventory_delta_sol

    assert res.fee_decay_auto_withdraw_triggered is False
    assert res.should_deploy_lp is True
    assert res.should_withdraw_lp is False
    assert res.action == ACTION_DEPLOY_3BIN_FEE_SURGE_HARVEST


def test_meteora_dlmm_entry_gate_rejections_and_auto_withdraw_fee_decay() -> None:
    """Verifies that:
    - When dynamic_fee_pct < 1.00% (< 100 bps), AUTO_WITHDRAW_FEE_DECAY is triggered.
    - When 1.00% <= dynamic_fee_pct < 2.50%, Gate 1 rejects entry.
    - When organic_volume_ratio < 0.65 (Tarjan SCC wash trading), Gate 2 rejects entry.
    - When two_sided_buy_sell_balance < 0.35 (one-way rug dump), Gate 3 rejects entry.
    """
    # 1. Fee decay below 1.00% -> AUTO_WITHDRAW_FEE_DECAY
    decay_res = evaluate_meteora_dlmm_fee_surge_harvest(
        active_bin_id=5000,
        dynamic_fee_pct=0.72,
        organic_volume_ratio=0.80,
        two_sided_buy_sell_balance=0.50,
    )
    assert decay_res.dynamic_fee_pct == pytest.approx(0.72)
    assert decay_res.fee_decay_auto_withdraw_triggered is True
    assert decay_res.should_deploy_lp is False
    assert decay_res.should_withdraw_lp is True
    assert decay_res.action == ACTION_AUTO_WITHDRAW_FEE_DECAY

    # 2. Gate 1 failure: 1.00% <= dynamic_fee_pct < 2.50%
    gate1_fail = evaluate_meteora_dlmm_fee_surge_harvest(
        dynamic_fee_pct=1.85,
        organic_volume_ratio=0.82,
        two_sided_buy_sell_balance=0.45,
    )
    assert gate1_fail.gate1_fee_surge_passed is False
    assert gate1_fail.gate2_organic_volume_passed is True
    assert gate1_fail.gate3_two_sided_balance_passed is True
    assert gate1_fail.all_three_entry_gates_passed is False
    assert gate1_fail.fee_decay_auto_withdraw_triggered is False
    assert gate1_fail.should_deploy_lp is False
    assert gate1_fail.action == ACTION_SKIP_DLMM_ENTRY_GATES_FAILED

    # 3. Gate 2 failure: organic_volume_ratio < 0.65 (wash flow detected by Tarjan SCC)
    gate2_fail = evaluate_meteora_dlmm_fee_surge_harvest(
        dynamic_fee_pct=5.20,
        organic_volume_ratio=0.45,
        two_sided_buy_sell_balance=0.48,
    )
    assert gate2_fail.gate1_fee_surge_passed is True
    assert gate2_fail.gate2_organic_volume_passed is False
    assert gate2_fail.gate3_two_sided_balance_passed is True
    assert gate2_fail.all_three_entry_gates_passed is False
    assert gate2_fail.should_deploy_lp is False
    assert gate2_fail.action == ACTION_SKIP_DLMM_ENTRY_GATES_FAILED

    # 4. Gate 3 failure: two_sided_buy_sell_balance < 0.35 (one-way rug dump)
    gate3_fail = evaluate_meteora_dlmm_fee_surge_harvest(
        dynamic_fee_pct=6.10,
        organic_volume_ratio=0.79,
        two_sided_buy_sell_balance=None,
        buy_volume_sol=15.0,
        sell_volume_sol=100.0,  # 0.15 balance < 0.35
    )
    assert gate3_fail.two_sided_buy_sell_balance == pytest.approx(0.15)
    assert gate3_fail.gate1_fee_surge_passed is True
    assert gate3_fail.gate2_organic_volume_passed is True
    assert gate3_fail.gate3_two_sided_balance_passed is False
    assert gate3_fail.all_three_entry_gates_passed is False
    assert gate3_fail.should_deploy_lp is False
    assert gate3_fail.action == ACTION_SKIP_DLMM_ENTRY_GATES_FAILED


@pytest.mark.parametrize(
    ("venue", "market", "spot_price", "perp_mark_price", "r_8h"),
    [
        ("Drift Protocol", "SOL-PERP", 185.0, 185.74, 0.045),
        ("Jupiter Perps", "WIF-PERP", 2.50, 2.515, 0.060),
        ("Hyperliquid", "BONK-PERP", 0.000028, 0.00002821, 0.055),
        ("Drift Protocol", "POPCAT-PERP", 1.40, 1.4098, 0.070),
        ("Jupiter Perps", "MOODENG-PERP", 0.35, 0.3535, 0.080),
        ("Hyperliquid", "FARTCOIN-PERP", 1.20, 1.2144, 0.095),
    ],
)
def test_delta_neutral_funding_harvest_across_all_venues_and_markets(
    venue: str,
    market: str,
    spot_price: float,
    perp_mark_price: float,
    r_8h: float,
) -> None:
    """Verifies 100% delta-neutral cash-and-carry harvesting (+1.0x Long Spot / jitoSOL +
    -1.0x Short Perp, net_delta_pct == 0.0) across all 3 venues (Drift Protocol,
    Jupiter Perps, Hyperliquid) and all 6 supported perp markets (SOL-PERP, WIF-PERP,
    BONK-PERP, POPCAT-PERP, MOODENG-PERP, FARTCOIN-PERP).
    """
    assert len(SUPPORTED_FUNDING_VENUES) == 3
    assert len(SUPPORTED_PERP_MARKETS) == 6

    res = evaluate_delta_neutral_funding_harvest(
        venue=venue,
        market=market,
        spot_price=spot_price,
        perp_mark_price=perp_mark_price,
        r_8h=r_8h,
        lst_staking_apy_pct=DEFAULT_JITOSOL_LST_STAKING_APY_PCT,
        capital_sol=100.0,
        sol_price_usd=185.0,
    )

    assert res.is_supported_venue is True
    assert res.is_supported_market is True
    assert res.long_spot_leverage == pytest.approx(DELTA_NEUTRAL_LONG_SPOT_LEVERAGE)
    assert res.short_perp_leverage == pytest.approx(DELTA_NEUTRAL_SHORT_PERP_LEVERAGE)
    assert res.long_spot_notional_sol == pytest.approx(100.0)
    assert res.short_perp_notional_sol == pytest.approx(-100.0)
    assert res.net_delta_sol == pytest.approx(0.0)
    assert res.net_delta_pct == pytest.approx(DELTA_NEUTRAL_TARGET_NET_DELTA_PCT)
    assert res.is_strictly_delta_neutral is True

    expected_funding_apy = r_8h * FUNDING_8H_INTERVALS_PER_YEAR
    expected_total_apy = expected_funding_apy + DEFAULT_JITOSOL_LST_STAKING_APY_PCT
    expected_weekly_sol = 100.0 * (expected_total_apy / 100.0) / WEEKS_PER_YEAR
    expected_basis_bps = ((perp_mark_price - spot_price) / spot_price) * 10_000.0

    assert res.annualized_funding_apy_pct == pytest.approx(expected_funding_apy, rel=1e-4)
    assert res.combined_total_apy_pct == pytest.approx(expected_total_apy, rel=1e-4)
    assert res.weekly_expected_yield_sol == pytest.approx(expected_weekly_sol, rel=1e-4)
    assert res.basis_spread_bps == pytest.approx(expected_basis_bps, rel=1e-4)
    assert res.annualized_funding_apy_pct >= MIN_DEPLOY_ANNUALIZED_FUNDING_APY_PCT
    assert res.should_deploy is True
    assert res.should_unwind is False
    assert res.action == ACTION_DEPLOY_DELTA_NEUTRAL_HARVEST
    assert len(res.execution_legs) == 3


def test_delta_neutral_funding_hourly_rate_negative_unwind_and_below_hurdle() -> None:
    """Verifies:
    - Hourly funding rate r_1h conversion (r_8h = 8 * r_1h, APY = r_1h * 8760).
    - Negative funding (r_8h < 0.0) triggers UNWIND_NEGATIVE_FUNDING.
    - Positive but sub-hurdle funding (annualized_funding_apy_pct < 25.0%) holds idle.
    """
    # 1. Hourly rate r_1h = 0.005% -> r_8h = 0.04% -> 43.80% annualized funding APY
    hourly_res = evaluate_delta_neutral_funding_harvest(
        venue="Hyperliquid",
        market="SOL-PERP",
        spot_price=185.0,
        perp_mark_price=185.50,
        r_1h=0.005,
        lst_staking_apy_pct=7.8,
        capital_sol=100.0,
    )
    assert hourly_res.r_1h == pytest.approx(0.005)
    assert hourly_res.r_8h == pytest.approx(0.04)
    assert hourly_res.annualized_funding_apy_pct == pytest.approx(0.005 * FUNDING_1H_INTERVALS_PER_YEAR)
    assert hourly_res.combined_total_apy_pct == pytest.approx(43.80 + 7.8)
    assert hourly_res.action == ACTION_DEPLOY_DELTA_NEUTRAL_HARVEST

    # 2. Negative funding (r_8h < 0.0) -> UNWIND_NEGATIVE_FUNDING
    neg_res = evaluate_delta_neutral_funding_harvest(
        venue="Drift Protocol",
        market="WIF-PERP",
        spot_price=2.40,
        perp_mark_price=2.38,
        r_8h=-0.03,
        lst_staking_apy_pct=7.8,
        capital_sol=100.0,
    )
    assert neg_res.r_8h < 0.0
    assert neg_res.annualized_funding_apy_pct < 0.0
    assert neg_res.basis_spread_bps < 0.0
    assert neg_res.net_delta_pct == pytest.approx(0.0)
    assert neg_res.should_deploy is False
    assert neg_res.should_unwind is True
    assert neg_res.action == ACTION_UNWIND_NEGATIVE_FUNDING

    # 3. Positive funding below 25.0% hurdle (r_8h = 0.01% -> 10.95% APY < 25.0%)
    low_res = evaluate_delta_neutral_funding_harvest(
        venue="Jupiter Perps",
        market="BONK-PERP",
        spot_price=0.000025,
        perp_mark_price=0.00002502,
        r_8h=0.01,
        lst_staking_apy_pct=7.8,
        capital_sol=100.0,
    )
    assert low_res.annualized_funding_apy_pct == pytest.approx(10.95)
    assert low_res.should_deploy is False
    assert low_res.should_unwind is False
    assert low_res.action == ACTION_HOLD_IDLE_BELOW_HURDLE


def test_meteora_dlmm_and_funding_harvester_facade_and_telemetry() -> None:
    """Verifies `MeteoraDlmmAndFundingHarvester.run_full_dlmm_funding_diagnostic()`
    and `get_telemetry_summary()` for `TitanIPCDaemon` (`RUN_METEORA_DLMM_FUNDING_HARVESTER`).
    """
    harvester = MeteoraDlmmAndFundingHarvester()
    diag = harvester.run_full_dlmm_funding_diagnostic()

    assert diag["status"] == "OK"
    assert diag["ipc_action"] == IPC_ACTION_RUN_METEORA_DLMM_FUNDING_HARVESTER
    assert diag["subsystem"] == "METEORA_DLMM_AND_FUNDING_HARVESTER_AGENT_26"
    assert diag["diagnostic_latency_ms"] >= 0.0

    surge = diag["meteora_dlmm_fee_surge_harvest"]
    assert surge["action"] == ACTION_DEPLOY_3BIN_FEE_SURGE_HARVEST
    assert surge["all_three_entry_gates_passed"] is True
    assert surge["net_harvested_fee_sol"] > 0.0
    assert 1.0 <= surge["hourly_fee_yield_pct"] <= 4.5

    decay = diag["meteora_dlmm_fee_decay_withdraw"]
    assert decay["action"] == ACTION_AUTO_WITHDRAW_FEE_DECAY
    assert decay["fee_decay_auto_withdraw_triggered"] is True
    assert decay["dynamic_fee_pct"] < 1.00

    assert diag["drift_sol_perp_harvest"]["action"] == ACTION_DEPLOY_DELTA_NEUTRAL_HARVEST
    assert diag["drift_sol_perp_harvest"]["net_delta_pct"] == pytest.approx(0.0)
    assert diag["jupiter_wif_perp_harvest"]["action"] == ACTION_DEPLOY_DELTA_NEUTRAL_HARVEST
    assert diag["hyperliquid_fartcoin_perp_harvest"]["action"] == ACTION_DEPLOY_DELTA_NEUTRAL_HARVEST
    assert diag["negative_funding_unwind"]["action"] == ACTION_UNWIND_NEGATIVE_FUNDING

    telemetry = harvester.get_telemetry_summary()
    assert telemetry["engine"] == "MeteoraDlmmAndFundingHarvester"
    assert telemetry["agent_id"] == "meteora-dlmm-funding-harvester"
    assert telemetry["agent_number"] == 26
    assert telemetry["ipc_action"] == IPC_ACTION_RUN_METEORA_DLMM_FUNDING_HARVESTER
    assert telemetry["dlmm_evaluations"] == 2
    assert telemetry["dlmm_surges_deployed"] == 1
    assert telemetry["dlmm_fee_decay_withdrawals"] == 1
    assert telemetry["cumulative_dlmm_net_fees_sol"] > 0.0
    assert telemetry["funding_evaluations"] == 4
    assert telemetry["funding_harvests_deployed"] == 3
    assert telemetry["funding_negative_unwinds"] == 1
    assert telemetry["cumulative_weekly_expected_yield_sol"] > 0.0
    assert telemetry["last_diagnostic_ts"] is not None
