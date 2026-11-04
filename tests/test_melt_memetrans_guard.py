"""Comprehensive pytest suite for `src/alpha/melt_memetrans_guard.py`
implementing arXiv:2602.13480 — MELT (MemeTrans): A Behavioral Trace Dataset
for High-Risk Memecoin Launch Detection (Hu et al., 2026).
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.alpha.melt_memetrans_guard import (
    MELT_122_FEATURE_NAMES,
    MELT_DETECTION_ACCURACY_BENCHMARK_PCT,
    MELT_EMPIRICAL_CO_PURCHASE_SUPPLY_PCT,
    MELT_EMPIRICAL_FUND_FLOW_SUPPLY_PCT,
    MELT_EMPIRICAL_JITO_BUNDLE_SUPPLY_PCT,
    MELT_EMPIRICAL_WASH_TRADE_TX_PCT,
    MELT_ESTIMATED_LOSS_REDUCTION_PCT,
    MELT_FEATURE_CATEGORY_SLICES,
    MELT_FEATURE_VECTOR_DIM,
    MeltHolderSlice,
    MeltMemeTransGuard,
    MeltRawTransaction,
    PAPER_CITATION,
    TupleUnionFind,
    build_melt_122_feature_vector,
    classify_behavioral_traces,
    decluster_tuple_bundles,
    evaluate_melt_122_ensemble,
)


def test_empirical_constants_and_feature_schema() -> None:
    """Verifies Hu et al. (2026) empirical benchmarks and the 122-feature schema."""
    assert "arXiv:2602.13480" in PAPER_CITATION
    assert MELT_EMPIRICAL_WASH_TRADE_TX_PCT == pytest.approx(21.4)
    assert MELT_EMPIRICAL_CO_PURCHASE_SUPPLY_PCT == pytest.approx(9.16)
    assert MELT_EMPIRICAL_JITO_BUNDLE_SUPPLY_PCT == pytest.approx(15.96)
    assert MELT_EMPIRICAL_FUND_FLOW_SUPPLY_PCT == pytest.approx(28.22)
    assert MELT_DETECTION_ACCURACY_BENCHMARK_PCT == pytest.approx(90.2)
    assert MELT_ESTIMATED_LOSS_REDUCTION_PCT == pytest.approx(56.1)
    assert MELT_FEATURE_VECTOR_DIM == 122
    assert len(MELT_122_FEATURE_NAMES) == 122
    assert len(set(MELT_122_FEATURE_NAMES)) == 122

    # Verify exact 24 + 24 + 24 + 26 + 24 = 122 split
    expected_counts = {
        "launchpad_trading_velocity_and_sale_duration": 24,
        "buyer_breadth_and_per_buyer_accumulation": 24,
        "holding_concentration_raw_vs_declustered": 24,
        "multi_wallet_bundle_traces": 26,
        "price_trajectory_and_stability": 24,
    }
    total = 0
    for cat, (start, end) in MELT_FEATURE_CATEGORY_SLICES.items():
        assert (end - start) == expected_counts[cat]
        total += end - start
    assert total == 122


def test_classify_behavioral_traces_wash_and_transfers() -> None:
    """Tests classification of NORMAL_SWAP, TOKEN_TRANSFER, and CIRCULAR_WASH_TRADE."""
    txs = [
        # 3 normal organic buys
        {
            "tx_signature": "org_1",
            "slot": 100,
            "timestamp_sec": 1000.0,
            "signer": "alice",
            "tx_kind": "SWAP",
            "side": "BUY",
            "amount_sol": 1.5,
            "supply_pct_delta": 1.2,
            "price_sol": 0.00010,
        },
        {
            "tx_signature": "org_2",
            "slot": 105,
            "timestamp_sec": 1060.0,
            "signer": "bob",
            "tx_kind": "SWAP",
            "side": "BUY",
            "amount_sol": 2.0,
            "supply_pct_delta": 1.8,
            "price_sol": 0.00011,
        },
        {
            "tx_signature": "org_3",
            "slot": 110,
            "timestamp_sec": 1120.0,
            "signer": "charlie",
            "tx_kind": "SWAP",
            "side": "BUY",
            "amount_sol": 1.0,
            "supply_pct_delta": 0.9,
            "price_sol": 0.00012,
        },
        # 1 explicit SPL token transfer
        {
            "tx_signature": "xfer_1",
            "slot": 111,
            "timestamp_sec": 1125.0,
            "signer": "ping_a",
            "counterparty": "pong_b",
            "tx_kind": "TOKEN_TRANSFER",
            "side": "TRANSFER",
            "amount_sol": 0.0,
            "supply_pct_delta": 1.0,
            "price_sol": 0.00012,
        },
        # Self-swap circular roundtrip (same signer buys and sells within 45s)
        {
            "tx_signature": "wash_self_buy",
            "slot": 112,
            "timestamp_sec": 1130.0,
            "signer": "self_washer",
            "tx_kind": "SWAP",
            "side": "BUY",
            "amount_sol": 3.0,
            "supply_pct_delta": 2.0,
            "price_sol": 0.00013,
        },
        {
            "tx_signature": "wash_self_sell",
            "slot": 113,
            "timestamp_sec": 1140.0,
            "signer": "self_washer",
            "tx_kind": "SWAP",
            "side": "SELL",
            "amount_sol": 3.0,
            "supply_pct_delta": 2.0,
            "price_sol": 0.00013,
        },
        # A <-> B ping-pong wash trade (ping_a buys, transfers to pong_b, pong_b sells within window)
        {
            "tx_signature": "wash_ping_buy",
            "slot": 111,
            "timestamp_sec": 1122.0,
            "signer": "ping_a",
            "tx_kind": "SWAP",
            "side": "BUY",
            "amount_sol": 2.5,
            "supply_pct_delta": 1.0,
            "price_sol": 0.00012,
        },
        {
            "tx_signature": "wash_pong_sell",
            "slot": 112,
            "timestamp_sec": 1128.0,
            "signer": "pong_b",
            "tx_kind": "SWAP",
            "side": "SELL",
            "amount_sol": 2.5,
            "supply_pct_delta": 1.0,
            "price_sol": 0.00012,
        },
        # Shared fee-payer wash loop
        {
            "tx_signature": "wash_fp_buy",
            "slot": 120,
            "timestamp_sec": 1180.0,
            "signer": "sybil_x",
            "fee_payer": "cabal_fee_payer_1",
            "tx_kind": "SWAP",
            "side": "BUY",
            "amount_sol": 4.0,
            "supply_pct_delta": 2.5,
            "price_sol": 0.00014,
        },
        {
            "tx_signature": "wash_fp_sell",
            "slot": 121,
            "timestamp_sec": 1185.0,
            "signer": "sybil_y",
            "fee_payer": "cabal_fee_payer_1",
            "tx_kind": "SWAP",
            "side": "SELL",
            "amount_sol": 4.0,
            "supply_pct_delta": 2.5,
            "price_sol": 0.00014,
        },
    ]

    summary = classify_behavioral_traces(txs, circular_window_sec=45.0)
    assert summary.total_tx_count == 10
    assert summary.organic_swap_count == 3
    assert summary.normal_swap_count == 3
    assert summary.token_transfer_count == 1
    assert summary.circular_wash_trade_count == 6
    assert summary.wash_trade_tx_ratio == pytest.approx(0.6)
    assert summary.unique_organic_buyers == 3
    assert summary.sale_duration_sec == pytest.approx(185.0)
    assert summary.mean_buyer_accumulation_pct == pytest.approx((1.2 + 1.8 + 0.9) / 3.0)

    by_sig = {r.tx_signature: r for r in summary.records}
    assert by_sig["org_1"].trace_type == "NORMAL_SWAP"
    assert by_sig["xfer_1"].trace_type == "TOKEN_TRANSFER"
    assert by_sig["wash_self_buy"].trace_type == "CIRCULAR_WASH_TRADE"
    assert by_sig["wash_ping_buy"].trace_type == "CIRCULAR_WASH_TRADE"
    assert by_sig["wash_fp_buy"].trace_type == "CIRCULAR_WASH_TRADE"


def test_decluster_tuple_bundles_risk_tiers_and_channels() -> None:
    """Tests Union-Find tuple declustering across CO_PURCHASE, JITO_BUNDLE, and FUND_FLOW
    and verifies LOW_RISK_ORGANIC (<=6pp), MODERATE_CAUTION (6-24pp), and HIGH_RISK_REJECT (>=24pp).
    """
    # Case 1: High-Risk Bundled Cabal (20 accounts each holding 2.5% -> raw Top-10 = 25.0%,
    # all linked into a single cluster of 50.0% + 9 independent 1.0% holders -> declustered Top-10 = 59.0%,
    # delta = +34.0pp >= 24.0pp -> HIGH_RISK_REJECT)
    cabal_holders = []
    for i in range(20):
        cabal_holders.append(
            MeltHolderSlice(
                user_account=f"sybil_{i:02d}",
                supply_pct=2.5,
                entry_slot=500 if i < 6 else (501 if i < 12 else 502 + i),
                jito_bundle_id="bundle_alpha" if i < 10 else None,
                funder="root_cabal_funder",
            )
        )
    for j in range(9):
        cabal_holders.append(
            MeltHolderSlice(
                user_account=f"retail_{j:02d}",
                supply_pct=1.0,
                entry_slot=600 + j,
                funder=f"independent_funder_{j}",
            )
        )

    high_res = decluster_tuple_bundles(cabal_holders)
    assert high_res.raw_top10_share_pct == pytest.approx(25.0)
    assert high_res.declustered_top10_share_pct == pytest.approx(59.0)
    assert high_res.top10_share_delta_pp == pytest.approx(34.0)
    assert high_res.cluster_risk_tier == "HIGH_RISK_REJECT"
    assert high_res.co_purchase_supply_pct == pytest.approx(30.0)  # 12 sybils in slots 500 & 501
    assert high_res.jito_bundle_supply_pct == pytest.approx(25.0)  # 10 sybils in bundle_alpha
    assert high_res.fund_flow_supply_pct == pytest.approx(50.0)  # all 20 sybils share root_cabal_funder
    assert high_res.total_bundled_supply_pct == pytest.approx(50.0)

    # Case 2: Low-Risk Organic Launch (12 independent holders, only 2 small holders share a slot -> delta <= 6.0pp)
    low_holders = [
        MeltHolderSlice(
            user_account=f"org_{i:02d}",
            supply_pct=2.0,
            entry_slot=700 + i,
            funder=f"funder_{i:02d}",
        )
        for i in range(12)
    ]
    # Link org_10 and org_11 in the same slot (each 2.0% -> merged 4.0%, raw top 10 was 20.0%,
    # declustered top 10 is 4.0 + 9*2.0 = 22.0%, delta = 2.0pp <= 6.0pp)
    low_holders[10].entry_slot = 999
    low_holders[11].entry_slot = 999
    low_res = decluster_tuple_bundles(low_holders)
    assert low_res.raw_top10_share_pct == pytest.approx(20.0)
    assert low_res.declustered_top10_share_pct == pytest.approx(22.0)
    assert low_res.top10_share_delta_pp == pytest.approx(2.0)
    assert low_res.cluster_risk_tier == "LOW_RISK_ORGANIC"

    # Case 3: Moderate Caution (6.0 < top10_share_delta_pp < 24.0)
    # 15 holders at 2.5% each (raw top 10 = 25.0%). Merge 6 of them via shared Jito tip payer
    # so 5 extra accounts enter the top-10 cluster -> delta = 5 * 2.5 = 12.5pp
    mod_holders = [
        MeltHolderSlice(
            user_account=f"mod_{i:02d}",
            supply_pct=2.5,
            entry_slot=800 + i,
            jito_tip_payer="shared_tip_1" if i < 6 else None,
        )
        for i in range(15)
    ]
    mod_res = decluster_tuple_bundles(mod_holders)
    assert mod_res.raw_top10_share_pct == pytest.approx(25.0)
    assert mod_res.declustered_top10_share_pct == pytest.approx(37.5)
    assert mod_res.top10_share_delta_pp == pytest.approx(12.5)
    assert mod_res.cluster_risk_tier == "MODERATE_CAUTION"


def test_strategy_5_hard_stability_threshold_and_122_ensemble() -> None:
    """Tests 122-feature generation, 4-model ensemble scoring, and Strategy 5 gating."""
    guard = MeltMemeTransGuard()
    sim = guard.simulate_clean_vs_cabal_launch()

    clean = sim["clean_launch"]
    cabal = sim["cabal_launch"]

    # Clean launch must pass all 3 Strategy 5 gates:
    # min_price_ratio >= 0.70, pred_score < 0.30, top10_share_delta_pp < 24.0
    assert clean["smart_money_confluence_allowed"] is True
    assert clean["decision"] == "ALLOW_SMART_MONEY_CONFLUENCE"
    assert clean["min_price_ratio"] >= 0.70
    assert clean["pred_score"] < 0.30
    assert clean["top10_share_delta_pp"] < 24.0
    assert clean["cluster_risk_tier"] == "LOW_RISK_ORGANIC"
    assert len(clean["ensemble_result"]["feature_vector"]) == 122

    # Cabal launch must be rejected by Strategy 5:
    assert cabal["smart_money_confluence_allowed"] is False
    assert cabal["decision"] == "BLOCK_HIGH_RISK_MEMECOIN_LAUNCH"
    assert cabal["cluster_risk_tier"] == "HIGH_RISK_REJECT"
    assert cabal["top10_share_delta_pp"] >= 24.0
    assert cabal["pred_score"] >= 0.30
    assert cabal["min_price_ratio"] < 0.70
    assert len(cabal["rejection_reasons"]) == 3
    assert cabal["estimated_loss_reduction_pct"] == pytest.approx(56.1)
    assert cabal["detection_accuracy_benchmark_pct"] == pytest.approx(90.2)

    # Verify all 4 sub-model scores are bounded in [0.0, 1.0]
    for model_key in ("mlp_score", "rf_score", "lgbm_score", "lstm_temporal_score", "pred_score"):
        assert 0.0 <= clean["ensemble_result"][model_key] <= 1.0
        assert 0.0 <= cabal["ensemble_result"][model_key] <= 1.0
        assert cabal["ensemble_result"][model_key] > clean["ensemble_result"][model_key]


def test_strategy_5_individual_gate_rejections() -> None:
    """Verifies that violating even a single Strategy 5 threshold blocks smart-money confluence."""
    guard = MeltMemeTransGuard()
    txs = [
        {
            "tx_signature": f"s_{i}",
            "slot": 1000 + i * 2,
            "timestamp_sec": 1000.0 + i * 20.0,
            "signer": f"buyer_{i}",
            "tx_kind": "SWAP",
            "side": "BUY",
            "amount_sol": 1.0,
            "supply_pct_delta": 1.0,
            "price_sol": 0.001,
        }
        for i in range(25)
    ]
    holders = [
        {"user_account": f"buyer_{i}", "supply_pct": 1.0, "entry_slot": 1000 + i * 2}
        for i in range(25)
    ]

    # Clean baseline with min_price_ratio = 0.65 (< 0.70 floor) must be blocked
    low_price_eval = guard.evaluate_token_launch(
        token_mint="LOW_PRICE_RATIO_MINT",
        transactions=txs,
        holders=holders,
        min_price_ratio=0.65,
    )
    assert low_price_eval.smart_money_confluence_allowed is False
    assert any("MIN_PRICE_RATIO_BELOW_0.70" in r for r in low_price_eval.rejection_reasons)

    # Telemetry summary check
    telemetry = guard.get_telemetry_summary()
    assert telemetry["feature_vector_dim"] == 122
    assert telemetry["counters"]["total_evaluations"] >= 1
    assert telemetry["last_evaluation"]["token_mint"] == "LOW_PRICE_RATIO_MINT"


def test_transitive_multi_channel_tuple_union_find() -> None:
    """Verifies transitive closure across CO_PURCHASE -> JITO_BUNDLE -> FUND_FLOW tuples."""
    holders = [
        {"user_account": "w1", "supply_pct": 7.0},
        {"user_account": "w2", "supply_pct": 7.0},
        {"user_account": "w3", "supply_pct": 7.0},
        {"user_account": "w4", "supply_pct": 7.0},
        {"user_account": "w5", "supply_pct": 7.0},
    ]
    # Pass explicit (user_account, channel, identifier) and (user_account, identifier) tuples
    tuples = [
        ("w1", "CO_PURCHASE", "slot_777"),
        ("w2", "CO_PURCHASE", "slot_777"),
        ("w2", "JITO_BUNDLE", "bundle_xyz"),
        ("w3", "JITO_BUNDLE", "bundle_xyz"),
        ("w3", "FUND_FLOW:root_shark_99"),
        ("w4", "FUND_FLOW:root_shark_99"),
    ]
    res = decluster_tuple_bundles(holders=holders, tuples=tuples)
    # w1, w2, w3, w4 all merge into a single 28.0% cluster; w5 remains a 7.0% singleton
    assert res.declustered_cluster_count == 2
    assert res.bundled_cluster_count == 1
    assert res.largest_cluster_supply_pct == pytest.approx(28.0)
    assert res.second_largest_cluster_supply_pct == pytest.approx(7.0)
    top_cluster = res.clusters[0]
    assert top_cluster.accounts == ["w1", "w2", "w3", "w4"]
    assert set(top_cluster.channels_triggered) == {"CO_PURCHASE", "JITO_BUNDLE", "FUND_FLOW"}
    assert res.co_purchase_supply_pct == pytest.approx(14.0)
    assert res.jito_bundle_supply_pct == pytest.approx(14.0)
    assert res.fund_flow_supply_pct == pytest.approx(14.0)
    assert res.total_bundled_supply_pct == pytest.approx(28.0)


def test_empty_and_edge_case_traces_and_serialization() -> None:
    """Verifies empty trace safety and full dictionary serialization."""
    empty_trace = classify_behavioral_traces([])
    assert empty_trace.total_tx_count == 0
    assert empty_trace.wash_trade_tx_ratio == 0.0
    assert empty_trace.organic_swap_count == 0
    assert empty_trace.unique_organic_buyers == 0
    assert empty_trace.sale_duration_sec == 0.0
    assert empty_trace.mean_buyer_accumulation_pct == 0.0

    guard = MeltMemeTransGuard()
    sim = guard.simulate_clean_vs_cabal_launch()
    assert sim["comparison"]["clean_allowed"] is True
    assert sim["comparison"]["cabal_blocked"] is True
    assert guard.last_evaluation is not None
    serialized = guard.last_evaluation.to_dict()
    assert serialized["paper_citation"] == PAPER_CITATION
    assert "trace_summary" in serialized
    assert "bundle_result" in serialized
    assert "ensemble_result" in serialized
    assert len(serialized["ensemble_result"]["feature_names"]) == 122
