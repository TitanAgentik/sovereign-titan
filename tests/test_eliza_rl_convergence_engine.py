"""Comprehensive pytest verification suite for Subsystem 3:
`/home/titanagentik/sovereign-titan/src/agents/eliza_rl_convergence_engine.py`.

Verifies:
  1. ElizaOS 4-Primitive Cognitive Architecture (`ElizaCognitiveOrchestrator`)
  2. 8-Model Tabular + Deep Sequential MELT Pipeline (`evaluate_melt_8model_deep_sequence_ensemble`)
  3. Closed-Loop Post-Trade Weight Adaptation & RL Policy Engine (`run_closed_loop_weight_adaptation`)
  4. Mechanical Scale-Out (`2x, 3x, 5x` + Moonbag) & 3 Real-Time Emergency Exit Tripwires (`evaluate_rl_exit_and_tripwires`)
  5. `ElizaRlConvergenceEngine` Facade (`run_full_eliza_rl_diagnostic` & `get_telemetry_summary`)
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agents.eliza_rl_convergence_engine import (
    AUPRC_SWEEP_TAU_MAX,
    AUPRC_SWEEP_TAU_MIN,
    CONVERGENCE_3WALLET_ALLOCATION_PCT,
    CONVERGENCE_5WALLET_ALLOCATION_PCT,
    DEFAULT_CT_MOMENTUM_WEIGHT,
    DEFAULT_DEV_HISTORY_WEIGHT,
    DEFAULT_DISTRIBUTION_WEIGHT,
    DEFAULT_VOLUME_WEIGHT,
    ELIZA_PRIMITIVE_NAMES,
    HARD_SKIP_TOP10_PCT,
    MELT_8MODEL_LOSS_REDUCTION_PCT_POINTS,
    MELT_8MODEL_NAMES,
    MELT_DEEP_SEQUENCE_MODEL_NAMES,
    MELT_TABULAR_MODEL_NAMES,
    MIN_CLOSED_TRADES_FOR_ADAPTATION,
    MIN_STANDALONE_ALERT_TRUST_SCORE,
    SCALE_OUT_MULTIPLIERS,
    SWEET_SPOT_HOLDERS_MAX,
    SWEET_SPOT_HOLDERS_MIN,
    SWEET_SPOT_TOP10_MAX_PCT,
    TRIPWIRE_ACTION_CLUSTER_SELL,
    TRIPWIRE_ACTION_HARD_STOP,
    TRIPWIRE_ACTION_VOLUME_DROP,
    WALLET_TRUST_MAX,
    WALLET_TRUST_MIN,
    ElizaCognitiveOrchestrator,
    ElizaRlConvergenceEngine,
    FeatureDimensionWeights,
    analyze_melt_bundle_concentration_domain,
    compute_class_weighted_bce_loss,
    compute_class_weights_inverse_counts,
    evaluate_melt_8model_deep_sequence_ensemble,
    evaluate_rl_exit_and_tripwires,
    get_eliza_rl_convergence_engine,
    run_closed_loop_weight_adaptation,
    sweep_auprc_decision_thresholds,
    ts_collate,
    verify_immutable_safety_files,
)


def test_eliza_constants_and_baseline_weights() -> None:
    """Verifies ElizaOS 4-Primitive constants, trust bounds, and 30/25/25/20 baseline weights."""
    assert len(ELIZA_PRIMITIVE_NAMES) == 4
    assert DEFAULT_DEV_HISTORY_WEIGHT == pytest.approx(0.30)
    assert DEFAULT_DISTRIBUTION_WEIGHT == pytest.approx(0.25)
    assert DEFAULT_VOLUME_WEIGHT == pytest.approx(0.25)
    assert DEFAULT_CT_MOMENTUM_WEIGHT == pytest.approx(0.20)

    weights = FeatureDimensionWeights()
    w_dict = weights.to_dict()
    assert w_dict["sum"] == pytest.approx(1.0)
    assert WALLET_TRUST_MIN == pytest.approx(0.0)
    assert WALLET_TRUST_MAX == pytest.approx(2.0)
    assert MIN_STANDALONE_ALERT_TRUST_SCORE == pytest.approx(0.50)
    assert HARD_SKIP_TOP10_PCT == pytest.approx(70.0)
    assert SWEET_SPOT_TOP10_MAX_PCT == pytest.approx(35.0)
    assert SWEET_SPOT_HOLDERS_MIN == 200
    assert SWEET_SPOT_HOLDERS_MAX == 2000


def test_wallet_trust_bounds_and_standalone_alert_barring() -> None:
    """Verifies T_w in [0.0, 2.0] clamping and barring standalone alerts when T_w < 0.50."""
    orchestrator = ElizaCognitiveOrchestrator()
    assert orchestrator.set_wallet_trust_score("whale_high", 2.75) == pytest.approx(2.0)
    assert orchestrator.set_wallet_trust_score("bait_low", -0.45) == pytest.approx(0.0)
    assert orchestrator.set_wallet_trust_score("sub_threshold", 0.49) == pytest.approx(0.49)
    assert orchestrator.set_wallet_trust_score("at_threshold", 0.50) == pytest.approx(0.50)

    assert orchestrator.can_trigger_standalone_alert("whale_high") is True
    assert orchestrator.can_trigger_standalone_alert("at_threshold") is True
    assert orchestrator.can_trigger_standalone_alert("sub_threshold") is False
    assert orchestrator.can_trigger_standalone_alert("bait_low") is False

    # Standalone alert from a low-trust wallet (T_w < 0.50) is barred
    decision = orchestrator.evaluate_convergence(
        mint="LowTrustStandaloneMint11111111111111111111111",
        wallet_events=[
            {"wallet": "sub_threshold", "side": "BUY", "timestamp_sec": 1000.0},
        ],
        gmgn_security={"top10_pct": 25.0, "total_holders": 500, "prior_rug_count": 0},
        max_sol_allocation=10.0,
    )
    assert decision.standalone_alert_barred is True
    assert decision.should_enter is False
    assert decision.allocated_sol == pytest.approx(0.0)
    assert decision.action == "BARRED_LOW_TRUST_STANDALONE"


def test_dev_prior_rug_zero_score_and_top10_hard_skip() -> None:
    """Verifies automatic 0.0 dev score if prior_rug_count > 0 and hard skip if top10_pct > 70%."""
    orchestrator = ElizaCognitiveOrchestrator()

    # Case 1: prior_rug_count > 0 -> automatic 0.0 dev_history_score and hard skip
    dev_rug_decision = orchestrator.evaluate_convergence(
        mint="RuggerDevMint1111111111111111111111111111111",
        wallet_events=[
            {"wallet": "w1", "side": "BUY", "timestamp_sec": 100.0, "trust_score": 1.5},
            {"wallet": "w2", "side": "BUY", "timestamp_sec": 110.0, "trust_score": 1.5},
            {"wallet": "w3", "side": "BUY", "timestamp_sec": 120.0, "trust_score": 1.5},
        ],
        gmgn_security={"top10_pct": 25.0, "total_holders": 600, "prior_rug_count": 2},
        max_sol_allocation=10.0,
    )
    assert dev_rug_decision.dev_history_score == pytest.approx(0.0)
    assert dev_rug_decision.hard_skip is True
    assert dev_rug_decision.skip_reason == "DEV_PRIOR_RUG_HISTORY"
    assert dev_rug_decision.should_enter is False
    assert dev_rug_decision.allocated_sol == pytest.approx(0.0)

    # Case 2: top10_pct > 70.0% -> immediate hard skip
    top10_skip_decision = orchestrator.evaluate_convergence(
        mint="ConcentratedMint1111111111111111111111111111",
        wallet_events=[
            {"wallet": "w1", "side": "BUY", "timestamp_sec": 100.0, "trust_score": 1.5},
            {"wallet": "w2", "side": "BUY", "timestamp_sec": 110.0, "trust_score": 1.5},
            {"wallet": "w3", "side": "BUY", "timestamp_sec": 120.0, "trust_score": 1.5},
        ],
        gmgn_security={"top10_pct": 74.5, "total_holders": 600, "prior_rug_count": 0},
        max_sol_allocation=10.0,
    )
    assert top10_skip_decision.distribution_score == pytest.approx(0.0)
    assert top10_skip_decision.hard_skip is True
    assert top10_skip_decision.skip_reason == "TOP10_CONCENTRATION_ABOVE_70PCT"
    assert top10_skip_decision.should_enter is False
    assert top10_skip_decision.allocated_sol == pytest.approx(0.0)


def test_3wallet_60pct_and_5wallet_100pct_convergence_sizing() -> None:
    """Verifies optimal sweet spot (top10 <= 35%, 200 <= holders <= 2000) and
    60.0% SOL allocation on 3-wallet convergence vs. 100.0% SOL allocation on 5-wallet convergence.
    """
    orchestrator = ElizaCognitiveOrchestrator()

    # 3-Wallet High-Trust Convergence -> 60.0% of max SOL allocation
    dec_3 = orchestrator.evaluate_convergence(
        mint="SweetSpot3WalletMint111111111111111111111111",
        wallet_events=[
            {"wallet": "alpha_1", "side": "BUY", "timestamp_sec": 500.0, "trust_score": 1.3},
            {"wallet": "alpha_2", "side": "BUY", "timestamp_sec": 540.0, "trust_score": 1.5},
            {"wallet": "alpha_3", "side": "BUY", "timestamp_sec": 590.0, "trust_score": 1.7},
        ],
        gmgn_security={"top10_pct": 31.0, "total_holders": 750, "prior_rug_count": 0},
        dexscreener_liquidity={"liquidity_usd": 90_000.0, "volume_5m_usd": 70_000.0, "buy_sell_ratio": 2.0},
        grok_social={"mentions_per_min": 16.0, "unique_kol_authors": 6, "sentiment_polarity": 0.80},
        max_sol_allocation=12.0,
    )
    assert dec_3.should_enter is True
    assert dec_3.in_optimal_distribution_sweet_spot is True
    assert dec_3.distribution_score == pytest.approx(1.0)
    assert dec_3.converging_wallets == 3
    assert dec_3.allocation_pct == pytest.approx(CONVERGENCE_3WALLET_ALLOCATION_PCT)
    assert dec_3.allocated_sol == pytest.approx(12.0 * 0.60)
    assert dec_3.action == "EXECUTE_3WALLET_CONVERGENCE_60PCT"

    # 5-Wallet High-Trust Convergence -> 100.0% of max SOL allocation
    dec_5 = orchestrator.evaluate_convergence(
        mint="SweetSpot5WalletMint111111111111111111111111",
        wallet_events=[
            {"wallet": f"shark_{i}", "side": "BUY", "timestamp_sec": 800.0 + i * 10.0, "trust_score": 1.6}
            for i in range(1, 6)
        ],
        gmgn_security={"top10_pct": 22.0, "total_holders": 1200, "prior_rug_count": 0},
        dexscreener_liquidity={"liquidity_usd": 140_000.0, "volume_5m_usd": 110_000.0, "buy_sell_ratio": 2.5},
        grok_social={"mentions_per_min": 24.0, "unique_kol_authors": 9, "sentiment_polarity": 0.90},
        max_sol_allocation=12.0,
    )
    assert dec_5.should_enter is True
    assert dec_5.converging_wallets == 5
    assert dec_5.allocation_pct == pytest.approx(CONVERGENCE_5WALLET_ALLOCATION_PCT)
    assert dec_5.allocated_sol == pytest.approx(12.0)
    assert dec_5.action == "EXECUTE_5WALLET_MAX_CONVERGENCE_100PCT"


def test_melt_8model_deep_sequence_ensemble_and_weighted_bce_loss() -> None:
    """Verifies the 8-model MELT pipeline (`XGB+LGBM+RF+MLP` + `TCN+LSTM+GRU+Transformer`),
    `ts_collate`, bundle concentration Union-Find, exact Class-Weighted BCE Loss,
    and AUPRC threshold sweep across tau in [0.30, 0.60].
    """
    assert len(MELT_TABULAR_MODEL_NAMES) == 4
    assert len(MELT_DEEP_SEQUENCE_MODEL_NAMES) == 4
    assert len(MELT_8MODEL_NAMES) == 8

    # Verify Domain 1 Union-Find clustering over (user_account, identifier) tuples
    bundle_res = analyze_melt_bundle_concentration_domain(
        account_identifier_tuples=[
            ("sybil_a", "jito_bundle_99", 18.0),
            ("sybil_b", "jito_bundle_99", 17.0),
            ("sybil_c", "jito_bundle_99", 16.0),
            ("organic_1", "indep_1", 4.0),
        ]
    )
    assert bundle_res["multi_wallet_bundle_clusters"] == 1
    assert bundle_res["largest_cluster_pct"] == pytest.approx(51.0)

    # Verify Domain 2 ts_collate
    ts_res = ts_collate(
        temporal_windows=[
            [0.0010, 0.0015, 0.0012, 50.0],
            [0.0015, 0.0022, 0.0018, 85.0],
            [0.0022, 0.0006, 0.0014, 12.0],
        ],
        time_span_sec=60.0,
    )
    assert ts_res["num_windows"] == 3
    assert ts_res["drawdown_from_peak"] == pytest.approx((0.0022 - 0.0006) / 0.0022, rel=1e-4)

    # Verify exact Class-Weighted BCE Loss formula:
    # L(theta) = -1/N * sum_i [ w_1 * y_i * log p_i + w_0 * (1 - y_i) * log(1 - p_i) ]
    y_true = [1, 0, 0, 0]
    y_pred = [0.80, 0.20, 0.10, 0.25]
    w1, w0 = compute_class_weights_inverse_counts(y_true)
    # N=4, N1=1, N0=3 => w1 = 4/(2*1) = 2.0, w0 = 4/(2*3) = 2/3, so w1/w0 = 3.0 = N0/N1
    assert w1 / w0 == pytest.approx(3.0, rel=1e-4)

    expected_loss = -(
        w1 * math.log(0.80)
        + w0 * math.log(1.0 - 0.20)
        + w0 * math.log(1.0 - 0.10)
        + w0 * math.log(1.0 - 0.25)
    ) / 4.0
    computed_loss = compute_class_weighted_bce_loss(y_true, y_pred, w1=w1, w0=w0)
    assert computed_loss == pytest.approx(expected_loss, rel=1e-6)

    # Verify AUPRC sweep across tau in [0.30, 0.60]
    sweep = sweep_auprc_decision_thresholds(y_true, y_pred)
    assert sweep["tau_range"] == [AUPRC_SWEEP_TAU_MIN, AUPRC_SWEEP_TAU_MAX]
    assert AUPRC_SWEEP_TAU_MIN <= sweep["optimal_tau"] <= AUPRC_SWEEP_TAU_MAX
    assert sweep["benchmark_loss_reduction_pct_points"] == pytest.approx(
        MELT_8MODEL_LOSS_REDUCTION_PCT_POINTS
    )

    # Full 8-Model ensemble evaluation
    ensemble_report = evaluate_melt_8model_deep_sequence_ensemble(
        account_identifier_tuples=[
            ("cabal_1", "shared_id", 28.0),
            ("cabal_2", "shared_id", 26.0),
            ("cabal_3", "shared_id", 24.0),
        ],
        temporal_windows=[
            [0.0010, 0.0018, 0.0014, 90.0],
            [0.0018, 0.0003, 0.0009, 8.0],
        ],
        sale_duration_sec=25.0,
        buy_tx_count=45,
        sol_price_usd=92.0,
        migrate_weekday=6,
        migrate_hour=3,
        migrate_month=10,
    )
    for model_name in MELT_8MODEL_NAMES:
        assert model_name in ensemble_report["all_8_model_scores"]
        assert 0.0 <= ensemble_report["all_8_model_scores"][model_name] <= 1.0
    assert ensemble_report["is_high_risk_rug"] is True
    assert ensemble_report["verdict"] == "VETO_HIGH_RISK_RUG"


def test_closed_loop_rl_weight_and_wallet_trust_adaptation() -> None:
    """Verifies closed-loop RL weight adaptation requires >= 10 closed trades,
    normalizes weights to 1.0, boosts early winner wallets, and decays local-top/bait wallets.
    """
    assert MIN_CLOSED_TRADES_FOR_ADAPTATION == 10

    # Fewer than 10 trades -> does not adapt
    few_trades = [
        {"trade_id": f"t_{i}", "pnl_pct": 50.0, "won": True, "dev_history_score": 0.9}
        for i in range(5)
    ]
    no_adapt = run_closed_loop_weight_adaptation(closed_trades=few_trades)
    assert no_adapt["adapted"] is False
    assert no_adapt["reason"] == "INSUFFICIENT_CLOSED_TRADES_MIN_10"

    # 12 closed trades where dev_history and distribution strongly predict winners
    trades_12 = []
    for i in range(12):
        won = i < 8
        trades_12.append(
            {
                "trade_id": f"closed_{i}",
                "mint": f"Mint_{i}",
                "pnl_pct": 180.0 if won else -40.0,
                "pnl_sol": 1.8 if won else -0.4,
                "won": won,
                "dev_history_score": 0.95 if won else 0.20,
                "distribution_score": 0.90 if won else 0.25,
                "volume_score": 0.55 if won else 0.60,
                "ct_momentum_score": 0.50 if won else 0.58,
                "early_winner_wallets": ["sniper_alpha"] if won else [],
                "local_top_or_bait_wallets": ["copy_baiter"] if not won else [],
            }
        )

    adapted = run_closed_loop_weight_adaptation(
        closed_trades=trades_12,
        wallet_trust_scores={"sniper_alpha": 1.10, "copy_baiter": 0.85},
        learning_rate=0.30,
        early_winner_trust_boost=0.15,
        top_buyer_trust_decay=0.25,
    )
    assert adapted["adapted"] is True
    assert adapted["closed_trades_count"] == 12
    uw = adapted["updated_weights"]
    assert (
        uw["dev_history_w"]
        + uw["distribution_w"]
        + uw["volume_w"]
        + uw["ct_momentum_w"]
    ) == pytest.approx(1.0, abs=1e-5)
    # Dev history and distribution had strong positive edge so their weights increase
    assert uw["dev_history_w"] > DEFAULT_DEV_HISTORY_WEIGHT
    assert uw["distribution_w"] > DEFAULT_DISTRIBUTION_WEIGHT

    # Wallet trust score adaptation
    trust_map = adapted["updated_wallet_trust_scores"]
    assert trust_map["sniper_alpha"] > 1.10
    assert trust_map["sniper_alpha"] <= WALLET_TRUST_MAX
    assert trust_map["copy_baiter"] < MIN_STANDALONE_ALERT_TRUST_SCORE
    assert "copy_baiter" in adapted["barred_standalone_wallets"]


def test_mechanical_scale_out_and_three_emergency_tripwires() -> None:
    """Verifies the 3 Real-Time Emergency Exit Tripwires and 2x/3x/5x + Moonbag scale-out."""
    # Tripwire 1: >= 2 smart-money / dev-cluster wallets sell within 10m (600s) -> 80% liquidation
    tw_cluster = evaluate_rl_exit_and_tripwires(
        entry_price=1.0,
        current_price=1.30,
        cluster_sell_timestamps_sec=[1000.0, 1450.0],
        current_timestamp_sec=1500.0,
    )
    assert tw_cluster["emergency_tripwire_triggered"] is True
    assert tw_cluster["action"] == TRIPWIRE_ACTION_CLUSTER_SELL
    assert tw_cluster["liquidation_pct"] == pytest.approx(80.0)

    # Tripwire 2: 15m rolling volume drops by >= 70.0% -> 40% liquidation
    tw_vol = evaluate_rl_exit_and_tripwires(
        entry_price=1.0,
        current_price=1.10,
        prev_15m_volume_usd=200_000.0,
        curr_15m_volume_usd=50_000.0,  # 75% volume drop
    )
    assert tw_vol["emergency_tripwire_triggered"] is True
    assert tw_vol["action"] == TRIPWIRE_ACTION_VOLUME_DROP
    assert tw_vol["liquidation_pct"] == pytest.approx(40.0)

    # Tripwire 3: Hard Stop-Loss (pnl_pct <= -40.0%) -> atomic 100% liquidation via Jupiter + Jito
    tw_hard = evaluate_rl_exit_and_tripwires(
        entry_price=1.0,
        current_price=0.55,  # -45.0% PnL
    )
    assert tw_hard["emergency_tripwire_triggered"] is True
    assert tw_hard["action"] == TRIPWIRE_ACTION_HARD_STOP
    assert tw_hard["liquidation_pct"] == pytest.approx(100.0)
    assert tw_hard["execution_venue"] == "JUPITER_JITO_ATOMIC_BUNDLE"

    # Mechanical Scale-Out at 2x, 3x, 5x + Moonbag
    assert SCALE_OUT_MULTIPLIERS == (2.0, 3.0, 5.0)
    s2 = evaluate_rl_exit_and_tripwires(entry_price=1.0, current_price=2.1)
    assert s2["action"] == "SCALE_OUT_2X_TIER1"
    assert 2.0 in s2["scale_out_tiers_triggered"]

    s3 = evaluate_rl_exit_and_tripwires(
        entry_price=1.0,
        current_price=3.2,
        executed_scale_out_tiers=[2.0],
    )
    assert s3["action"] == "SCALE_OUT_3X_TIER2"
    assert 3.0 in s3["scale_out_tiers_triggered"]

    s5 = evaluate_rl_exit_and_tripwires(
        entry_price=1.0,
        current_price=5.4,
        executed_scale_out_tiers=[2.0, 3.0],
    )
    assert s5["action"] == "SCALE_OUT_5X_MOONBAG"
    assert 5.0 in s5["scale_out_tiers_triggered"]
    assert s5["retained_moonbag_pct"] == pytest.approx(15.0)


def test_eliza_rl_convergence_engine_facade_and_immutable_lock() -> None:
    """Verifies `ElizaRlConvergenceEngine` diagnostic, telemetry summary, and SHA-256 lock."""
    lock = verify_immutable_safety_files()
    assert lock["verified"] is True
    assert len(lock["sha256_digests"]) == 2

    engine = get_eliza_rl_convergence_engine()
    assert isinstance(engine, ElizaRlConvergenceEngine)

    diag = engine.run_full_eliza_rl_diagnostic()
    assert diag["ok"] is True
    assert diag["status"] == "SUBSYSTEM_3_ELIZA_RL_CONVERGENCE_HEALTHY"
    assert diag["three_wallet_convergence"]["allocation_pct"] == pytest.approx(60.0)
    assert diag["five_wallet_convergence"]["allocation_pct"] == pytest.approx(100.0)
    assert diag["closed_loop_rl_adaptation"]["adapted"] is True
    assert (
        diag["tripwires_and_scale_out"]["cluster_sell_80pct"]["action"]
        == "LIQUIDATE_80PCT_CLUSTER_SELL"
    )
    assert (
        diag["tripwires_and_scale_out"]["volume_drop_40pct"]["action"]
        == "LIQUIDATE_40PCT_VOLUME_DROP"
    )
    assert (
        diag["tripwires_and_scale_out"]["hard_stop_100pct"]["action"]
        == "LIQUIDATE_100PCT_HARD_STOP"
    )

    telemetry = engine.get_telemetry_summary()
    assert telemetry["status"] == "ONLINE"
    assert telemetry["diagnostics_run"] >= 1
    assert len(telemetry["melt_8model_names"]) == 8
