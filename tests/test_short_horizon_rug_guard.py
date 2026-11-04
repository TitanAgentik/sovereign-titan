"""Comprehensive pytest suite for `src/alpha/short_horizon_rug_guard.py`
implementing arXiv:2608.20271 — Short-Horizon Early Rug Pull Detection Across
6.4 Million Solana Memecoins (2026).
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.alpha.short_horizon_rug_guard import (
    BENCHMARK_5M_AUCPRC,
    BENCHMARK_5M_MCC,
    DEFAULT_MAX_IDLE_DELTA_T_SEC,
    DEFAULT_MDD_THETA,
    INACTIVITY_KILL_RATIO_THRESHOLD,
    INACTIVITY_WARNING_RATIO_THRESHOLD,
    PRIMARY_5M_FEATURE_DIM,
    PRIMARY_5M_FEATURE_NAMES,
    RUG_CLASS_IMBALANCE_PCT,
    SHORT_HORIZON_FORECAST_HORIZON_SEC,
    SHORT_HORIZON_OBSERVATION_WINDOW_SEC,
    SHORT_HORIZON_PAPER_CITATION,
    SOLANA_DATASET_MEMECOIN_COUNT,
    ShortHorizonRugGuard,
    ShortHorizonTradeRecord,
    compute_aucprc,
    compute_mcc,
    evaluate_5min_microstructure_vector,
    evaluate_dual_trigger_rug_indicator,
    evaluate_imbalanced_rug_benchmark,
)


def test_paper_constants_and_5m_feature_schema() -> None:
    """Verifies arXiv:2608.20271 empirical constants and the 7 primary 5-minute feature names."""
    assert "arXiv:2608.20271" in SHORT_HORIZON_PAPER_CITATION
    assert SOLANA_DATASET_MEMECOIN_COUNT == 6_400_000
    assert RUG_CLASS_IMBALANCE_PCT > 80.0
    assert SHORT_HORIZON_OBSERVATION_WINDOW_SEC == pytest.approx(300.0)
    assert SHORT_HORIZON_FORECAST_HORIZON_SEC == pytest.approx(3600.0)
    assert DEFAULT_MDD_THETA == pytest.approx(0.28)
    assert DEFAULT_MAX_IDLE_DELTA_T_SEC == pytest.approx(150.0)
    assert INACTIVITY_WARNING_RATIO_THRESHOLD == pytest.approx(0.45)
    assert INACTIVITY_KILL_RATIO_THRESHOLD == pytest.approx(0.50)
    assert PRIMARY_5M_FEATURE_DIM == 7
    assert PRIMARY_5M_FEATURE_NAMES == (
        "total_volume_sol",
        "avg_buy_ratio",
        "avg_sell_ratio",
        "avg_price_change_pct",
        "buy_sell_std_dev",
        "avg_last_trade_time_sec",
        "inactivity_time_ratio",
    )


def test_dual_trigger_rug_indicator_formula_and_thresholds() -> None:
    """Tests Rug_t = I((MDD_t < -theta) OR (Idle_t > Delta_t)) and INACTIVITY_WARNING_0_5."""
    # Case 1: Healthy pool (MDD_t = (110 - 120)/120 = -0.083333 >= -0.28, Idle_t = 18s <= 150s)
    healthy = evaluate_dual_trigger_rug_indicator(
        current_tvl_sol=110.0,
        peak_tvl_sol=120.0,
        idle_t_sec=18.0,
        theta=0.28,
        delta_t_sec=150.0,
        w_sec=300.0,
    )
    assert healthy.rug_t_indicator == 0
    assert healthy.is_rug_triggered is False
    assert healthy.mdd_t == pytest.approx(-10.0 / 120.0, rel=1e-4)
    assert healthy.mdd_breached is False
    assert healthy.idle_breached is False
    assert healthy.inactivity_time_ratio == pytest.approx(18.0 / 300.0)
    assert healthy.inactivity_warning_0_5 is False
    assert healthy.trigger_reasons == []

    # Case 2: TVL Drawdown Breach (MDD_t = (65 - 100)/100 = -0.35 < -0.28, Idle_t = 12s)
    mdd_kill = evaluate_dual_trigger_rug_indicator(
        current_tvl_sol=65.0,
        peak_tvl_sol=100.0,
        idle_t_sec=12.0,
        theta=0.28,
        delta_t_sec=150.0,
        w_sec=300.0,
    )
    assert mdd_kill.rug_t_indicator == 1
    assert mdd_kill.is_rug_triggered is True
    assert mdd_kill.mdd_t == pytest.approx(-0.35)
    assert mdd_kill.mdd_breached is True
    assert mdd_kill.idle_breached is False
    assert "TVL_MDD_BREACH" in mdd_kill.flags
    assert any("TVL_DRAWDOWN_BREACH_MDD_LT_NEG_THETA" in r for r in mdd_kill.trigger_reasons)

    # Case 3: Early Inactivity Warning approaching 0.50 (idle_t_sec = 141s / 300s = 0.47 >= 0.45, < 0.50)
    early_warn = evaluate_dual_trigger_rug_indicator(
        current_tvl_sol=96.0,
        peak_tvl_sol=100.0,
        idle_t_sec=141.0,
        theta=0.28,
        delta_t_sec=150.0,
        w_sec=300.0,
    )
    assert early_warn.inactivity_time_ratio == pytest.approx(0.47)
    assert early_warn.inactivity_warning_0_5 is True
    assert "INACTIVITY_WARNING_0_5" in early_warn.flags
    assert early_warn.idle_breached is False
    assert early_warn.rug_t_indicator == 0

    # Case 4: Hard Inactivity Abandonment Breach (idle_t_sec = 165s > 150s, ratio = 0.55 >= 0.50)
    idle_kill = evaluate_dual_trigger_rug_indicator(
        current_tvl_sol=95.0,
        peak_tvl_sol=100.0,
        idle_t_sec=165.0,
        theta=0.28,
        delta_t_sec=150.0,
        w_sec=300.0,
    )
    assert idle_kill.rug_t_indicator == 1
    assert idle_kill.is_rug_triggered is True
    assert idle_kill.mdd_breached is False
    assert idle_kill.idle_breached is True
    assert idle_kill.inactivity_time_ratio == pytest.approx(0.55)
    assert idle_kill.inactivity_warning_0_5 is True
    assert "INACTIVITY_ABANDONMENT_BREACH" in idle_kill.flags
    assert any("LIQUIDITY_ABANDONMENT_IDLE_GT_DELTA_T" in r for r in idle_kill.trigger_reasons)


def test_5min_microstructure_vector_and_1h_forecaster_tiers() -> None:
    """Verifies the 7-feature 5-minute microstructure vector and all 3 action tiers."""
    base_ts = 1_700_000_000.0
    # 1. Healthy high-velocity 5-minute trade stream (with 2 wash trades that must be excluded)
    trades = []
    for i in range(25):
        trades.append(
            {
                "timestamp_sec": base_ts + i * 11.5,
                "side": "BUY" if (i % 5 != 4) else "SELL",
                "amount_sol": 2.0 if (i % 5 != 4) else 0.6,
                "price_sol": 0.00010 * (1.0 + 0.015 * i),
                "tvl_sol": 90.0 + i * 2.0,
                "signer": f"buyer_{i}",
                "is_wash_trade": False,
            }
        )
    # Add 2 wash trades at the end that should be ignored when computing valid non-wash flow
    trades.append(
        {
            "timestamp_sec": base_ts + 295.0,
            "side": "SELL",
            "amount_sol": 50.0,
            "price_sol": 0.00001,
            "tvl_sol": 90.0,
            "signer": "wash_bot",
            "is_wash_trade": True,
        }
    )

    healthy_fc = evaluate_5min_microstructure_vector(
        trades=trades,
        current_tvl_sol=136.0,
        peak_tvl_sol=140.0,
        window_start_sec=base_ts,
        window_end_sec=base_ts + 300.0,
        base_trail_stop_pct=8.0,
    )
    assert healthy_fc.valid_trade_count == 25
    assert healthy_fc.wash_trade_count == 1
    assert len(healthy_fc.feature_vector) == 7
    assert healthy_fc.feature_names == list(PRIMARY_5M_FEATURE_NAMES)
    assert healthy_fc.total_volume_sol == pytest.approx(20 * 2.0 + 5 * 0.6)
    assert healthy_fc.avg_buy_ratio > 0.75
    assert healthy_fc.avg_sell_ratio == pytest.approx(1.0 - healthy_fc.avg_buy_ratio, abs=1e-5)
    assert healthy_fc.avg_price_change_pct > 0.0
    assert healthy_fc.inactivity_time_ratio == pytest.approx((300.0 - 24 * 11.5) / 300.0)
    assert healthy_fc.rug_t_indicator == 0
    assert healthy_fc.rug_probability_1h < 0.40
    assert healthy_fc.recommended_action == "HOLD_OR_SCALE"
    assert healthy_fc.tightened_trail_stop_pct == pytest.approx(8.0)

    # 2. Tighten Trail Stop tier: elevated inactivity warning (inactivity_time_ratio = 0.46)
    warn_fc = evaluate_5min_microstructure_vector(
        total_volume_sol=32.0,
        avg_buy_ratio=0.48,
        avg_sell_ratio=0.52,
        avg_price_change_pct=-6.0,
        buy_sell_std_dev=1.4,
        avg_last_trade_time_sec=22.0,
        inactivity_time_ratio=0.46,
        current_tvl_sol=86.0,
        peak_tvl_sol=100.0,
        w_sec=300.0,
        base_trail_stop_pct=8.0,
    )
    assert warn_fc.inactivity_warning_0_5 is True
    assert warn_fc.rug_t_indicator == 0
    assert warn_fc.recommended_action == "TIGHTEN_TRAIL_STOP"
    assert 1.5 <= warn_fc.tightened_trail_stop_pct <= 4.0

    # 3. Emergency Kill-Switch tier: severe sell pressure + TVL drain (mdd_t = -0.45 < -0.28)
    kill_fc = evaluate_5min_microstructure_vector(
        total_volume_sol=18.0,
        avg_buy_ratio=0.15,
        avg_sell_ratio=0.85,
        avg_price_change_pct=-48.0,
        buy_sell_std_dev=6.5,
        avg_last_trade_time_sec=45.0,
        inactivity_time_ratio=0.55,
        current_tvl_sol=55.0,
        peak_tvl_sol=100.0,
        w_sec=300.0,
        base_trail_stop_pct=8.0,
    )
    assert kill_fc.rug_t_indicator == 1
    assert kill_fc.rug_probability_1h >= 0.88
    assert kill_fc.recommended_action == "EMERGENCY_KILL_SWITCH_FLATTEN_100PCT"
    assert kill_fc.tightened_trail_stop_pct == pytest.approx(0.0)


def test_mcc_and_aucprc_imbalanced_benchmark_math() -> None:
    """Verifies exact MCC and AUCPRC formulas under >80% rug class imbalance."""
    # Exact manual check of MCC = (TP*TN - FP*FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))
    tp, tn, fp, fn = 820, 155, 15, 10
    expected_num = 820 * 155 - 15 * 10
    expected_den = math.sqrt((820 + 15) * (820 + 10) * (155 + 15) * (155 + 10))
    expected_mcc = expected_num / expected_den

    computed_mcc = compute_mcc(tp=tp, tn=tn, fp=fp, fn=fn)
    assert computed_mcc == pytest.approx(expected_mcc, abs=1e-6)
    assert computed_mcc > 0.85

    # Edge cases: perfect classifier, completely inverted classifier, zero denominator
    assert compute_mcc(tp=800, tn=200, fp=0, fn=0) == pytest.approx(1.0)
    assert compute_mcc(tp=0, tn=0, fp=200, fn=800) == pytest.approx(-1.0)
    assert compute_mcc(tp=0, tn=0, fp=0, fn=0) == pytest.approx(0.0)
    assert compute_mcc(tp=850, tn=0, fp=150, fn=0) == pytest.approx(0.0)

    # Verify AUCPRC and imbalanced benchmark evaluator (>80% rug class)
    y_true = [1] * 85 + [0] * 15
    y_scores = [0.95 - 0.004 * i for i in range(85)] + [0.25 - 0.01 * j for j in range(15)]
    aucprc = compute_aucprc(y_true=y_true, y_scores=y_scores)
    assert aucprc == pytest.approx(1.0, abs=1e-4)

    metrics = evaluate_imbalanced_rug_benchmark(y_true=y_true, y_scores=y_scores, threshold=0.50)
    assert metrics.total_samples == 100
    assert metrics.rug_class_prevalence_pct == pytest.approx(85.0)
    assert metrics.tp == 85
    assert metrics.tn == 15
    assert metrics.fp == 0
    assert metrics.fn == 0
    assert metrics.mcc == pytest.approx(1.0)
    assert metrics.aucprc == pytest.approx(1.0, abs=1e-4)


def test_short_horizon_rug_guard_simulation_and_telemetry() -> None:
    """Verifies ShortHorizonRugGuard stateful engine, simulation, and IPC telemetry."""
    guard = ShortHorizonRugGuard()
    sim = guard.simulate_healthy_vs_rug_abandonment()

    healthy = sim["healthy_launch"]
    tvl_drain = sim["tvl_drain_rug"]
    abandonment = sim["inactivity_abandonment_rug"]
    cohort = sim["imbalanced_cohort_metrics"]

    # 1. Healthy launch stays at Rug_t = 0 and HOLD_OR_SCALE
    assert healthy["rug_t_indicator"] == 0
    assert healthy["is_rug_triggered"] is False
    assert healthy["recommended_action"] == "HOLD_OR_SCALE"
    assert healthy["rug_probability_1h"] < 0.40

    # 2. TVL drain rug triggers MDD_t < -theta kill-switch
    assert tvl_drain["rug_t_indicator"] == 1
    assert tvl_drain["is_rug_triggered"] is True
    assert tvl_drain["dual_trigger"]["mdd_breached"] is True
    assert tvl_drain["recommended_action"] == "EMERGENCY_KILL_SWITCH_FLATTEN_100PCT"
    assert tvl_drain["tightened_trail_stop_pct"] == pytest.approx(0.0)

    # 3. Inactivity abandonment rug triggers Idle_t > Delta_t (inactivity_time_ratio >= 0.50)
    assert abandonment["rug_t_indicator"] == 1
    assert abandonment["is_rug_triggered"] is True
    assert abandonment["dual_trigger"]["idle_breached"] is True
    assert abandonment["inactivity_time_ratio"] >= 0.50
    assert abandonment["inactivity_warning_0_5"] is True
    assert abandonment["recommended_action"] == "EMERGENCY_KILL_SWITCH_FLATTEN_100PCT"

    # 4. Imbalanced cohort metrics (>80% rug prevalence)
    assert cohort["rug_class_prevalence_pct"] >= 80.0
    assert cohort["mcc"] > 0.75
    assert cohort["aucprc"] > 0.90

    # 5. Telemetry summary for TitanIPCDaemon
    telemetry = guard.get_telemetry_summary()
    assert telemetry["paper_citation"] == SHORT_HORIZON_PAPER_CITATION
    assert telemetry["dataset_memecoin_count"] == 6_400_000
    assert telemetry["primary_5m_feature_dim"] == 7
    assert telemetry["counters"]["total_evaluations"] == 3
    assert telemetry["counters"]["kill_switch_triggers"] == 2
    assert telemetry["counters"]["mdd_kill_triggers"] == 1
    assert telemetry["counters"]["idle_kill_triggers"] == 1
    assert telemetry["benchmark_metrics"]["mcc"] == pytest.approx(BENCHMARK_5M_MCC, abs=0.02)
    assert telemetry["benchmark_metrics"]["aucprc"] == pytest.approx(BENCHMARK_5M_AUCPRC, abs=0.02)
