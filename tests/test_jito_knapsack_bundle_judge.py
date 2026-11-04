"""Comprehensive pytest verification suite for `src/execution/jito_knapsack_bundle_judge.py`
testing Agent C & Agent D of `AlphaExploit-Solana`:
1. Two-Stage Jito Block Engine Conflict-Set & Global Knapsack Optimizer (`solve_two_stage_jito_auction`)
2. Dynamic 70/30 vs 50–70% Edge Tip Calibrator (`calibrate_dynamic_jito_tip_and_priority_split`)
3. Strict `jitodontfront` Index-0, Sparse Compaction & Multi-Signer Contiguity Validator
   (`validate_and_compact_jitodontfront_bundle`)
4. `< 80ms` End-to-End Execution Budget & 5-Region Jito + Astralane + Lil-JIT Fan-Out
   (`execute_sub80ms_multi_region_bundle`)
5. `JitoKnapsackBundleJudge` Facade & `TitanIPCDaemon` Telemetry
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.execution.jito_knapsack_bundle_judge import (
    ADDITIONAL_BUNDLE_RELAYS,
    ALL_7_FANOUT_TARGETS,
    BundleInstructionSpec,
    BundleTransactionSpec,
    IPC_COMMAND_RUN_JITO_KNAPSACK_DONTFRONT_JUDGE,
    JITO_5_REGIONS,
    JITO_AUCTION_TICK_MS,
    JITO_DONT_FRONT_PUBKEY,
    JitoCandidateBundle,
    JitoKnapsackBundleJudge,
    MAX_END_TO_END_EXECUTION_BUDGET_MS,
    MAX_PARALLEL_SUBMIT_BUDGET_MS,
    MAX_PATH_SEARCH_BUDGET_MS,
    MAX_SIMULATE_BUNDLE_BUDGET_MS,
    MAX_TX_BUILD_BUDGET_MS,
    OFFICIAL_JITO_TIP_ACCOUNTS,
    REJECTED_BUNDLE_EXCEEDS_5_TX_LIMIT,
    REJECTED_DISCONTIGUOUS_OVERLAPPING_SIGNERS,
    REJECTED_DUPLICATE_JITODONTFRONT_IN_TX,
    REJECTED_EMPTY_BUNDLE,
    REJECTED_INVALID_JITO_TIP_ACCOUNT,
    REJECTED_MISSING_INLINE_FINAL_TIP_INSTRUCTION,
    REJECTED_NON_PREFIX_JITODONTFRONT_INDEX,
    VALID_JITODONTFRONT_BUNDLE,
    calibrate_dynamic_jito_tip_and_priority_split,
    execute_sub80ms_multi_region_bundle,
    get_jito_knapsack_bundle_judge,
    is_jitodontfront_pubkey,
    solve_two_stage_jito_auction,
    validate_and_compact_jitodontfront_bundle,
)


def test_canonical_constants_and_jitodontfront_prefix_sentinel() -> None:
    """Verifies canonical Jito sentinel pubkey, 8 tip accounts, and 5+2 fan-out targets."""
    assert JITO_DONT_FRONT_PUBKEY == "jitodontfront111111111111111111111111111111"
    assert is_jitodontfront_pubkey(JITO_DONT_FRONT_PUBKEY) is True
    assert is_jitodontfront_pubkey("jitodontfrontCustomSuffix999999999999999999") is True
    assert is_jitodontfront_pubkey("11111111111111111111111111111111") is False

    assert len(OFFICIAL_JITO_TIP_ACCOUNTS) == 8
    assert len(set(OFFICIAL_JITO_TIP_ACCOUNTS)) == 8

    assert JITO_5_REGIONS == (
        "NEW_YORK",
        "FRANKFURT",
        "TOKYO",
        "AMSTERDAM",
        "SALT_LAKE_CITY",
    )
    assert ADDITIONAL_BUNDLE_RELAYS == ("ASTRALANE", "LIL_JIT")
    assert len(ALL_7_FANOUT_TARGETS) == 7
    assert JITO_AUCTION_TICK_MS == 200.0


def test_stage1_conflict_partitioning_union_find_and_local_efficiency_scoring() -> None:
    """Verifies Stage 1 Union-Find conflict partitioning across transitive write-account
    overlaps and local `score(b) = tip(b) / c(b)` winner selection.
    """
    candidates = [
        # Conflict Set C_1: transitive chain b1 (AcctA, AcctB) <-> b2 (AcctB, AcctC) <-> b3 (AcctC)
        # b1 has highest raw tip (10M) but bloated CU (1,000,000) -> score = 10.0
        # b2 has 6M tip and 200,000 CU -> score = 30.0 (Stage 1 winner!)
        # b3 has 4M tip and 250,000 CU -> score = 16.0
        JitoCandidateBundle(
            bundle_id="c1_bloated_high_raw_tip",
            tip_lamports=10_000_000,
            compute_units=1_000_000,
            write_accounts=("AcctA", "AcctB"),
        ),
        JitoCandidateBundle(
            bundle_id="c1_compact_high_score_winner",
            tip_lamports=6_000_000,
            compute_units=200_000,
            write_accounts=("AcctB", "AcctC"),
            is_our_bundle=True,
        ),
        JitoCandidateBundle(
            bundle_id="c1_transitive_overlap",
            tip_lamports=4_000_000,
            compute_units=250_000,
            write_accounts=("AcctC", "AcctD"),
        ),
        # Conflict Set C_2: disjoint write account AcctX
        JitoCandidateBundle(
            bundle_id="c2_winner",
            tip_lamports=5_000_000,
            compute_units=250_000,
            write_accounts=("AcctX",),
        ),
        JitoCandidateBundle(
            bundle_id="c2_loser",
            tip_lamports=3_000_000,
            compute_units=300_000,
            write_accounts=("AcctX",),
        ),
    ]

    result = solve_two_stage_jito_auction(candidates, cu_limit=1_000_000)
    assert result.total_candidate_bundles == 5
    assert result.conflict_sets_count == 2

    c1, c2 = result.conflict_sets[0], result.conflict_sets[1]
    assert set(c1.bundle_ids) == {
        "c1_bloated_high_raw_tip",
        "c1_compact_high_score_winner",
        "c1_transitive_overlap",
    }
    assert c1.winner_bundle_id == "c1_compact_high_score_winner"
    assert c1.winner_score == pytest.approx(30.0)
    assert set(c1.evicted_bundle_ids) == {
        "c1_bloated_high_raw_tip",
        "c1_transitive_overlap",
    }

    assert c2.winner_bundle_id == "c2_winner"
    assert c2.winner_score == pytest.approx(20.0)
    assert result.stage1_winner_ids == ["c1_compact_high_score_winner", "c2_winner"]
    assert result.selected_bundle_ids == ["c1_compact_high_score_winner", "c2_winner"]
    assert result.total_selected_tip_lamports == 11_000_000
    assert result.total_selected_compute_units == 450_000
    assert result.our_bundle_selected is True


def test_stage2_global_01_knapsack_exact_optimization_under_cu_limit() -> None:
    """Verifies Stage 2 solves the exact 0/1 knapsack problem `max sum tip(b)` subject to
    `sum c(b) <= CU_limit`, outperforming naive greedy when packing two medium bundles
    beats a single slightly higher-density bundle.
    """
    # 3 disjoint conflict sets -> all 3 enter W:
    # w1: tip = 10_000_000, cu = 600_000 (score = 16.67)
    # w2: tip = 9_000_000,  cu = 500_000 (score = 18.00)
    # w3: tip = 9_000_000,  cu = 500_000 (score = 18.00)
    # Wait: let's also test classic knapsack where w1 has highest score (20.0) at cu=600k (tip=12M)
    # vs w2 (cu=500k, tip=9.5M, score=19.0) + w3 (cu=500k, tip=9.5M, score=19.0) = 19M total tip at cu=1,000k!
    candidates = [
        {
            "bundle_id": "w1_greedy_trap",
            "tip_lamports": 12_000_000,
            "compute_units": 600_000,
            "write_accounts": ["Pool_1"],
        },
        {
            "bundle_id": "w2_optimal_pair_a",
            "tip_lamports": 9_500_000,
            "compute_units": 500_000,
            "write_accounts": ["Pool_2"],
            "is_our_bundle": True,
        },
        {
            "bundle_id": "w3_optimal_pair_b",
            "tip_lamports": 9_500_000,
            "compute_units": 500_000,
            "write_accounts": ["Pool_3"],
        },
    ]

    result = solve_two_stage_jito_auction(candidates, cu_limit=1_000_000)
    assert result.conflict_sets_count == 3
    assert set(result.selected_bundle_ids) == {"w2_optimal_pair_a", "w3_optimal_pair_b"}
    assert result.evicted_stage2_bundle_ids == ["w1_greedy_trap"]
    assert result.total_selected_tip_lamports == 19_000_000
    assert result.total_selected_compute_units == 1_000_000
    assert result.cu_utilization_pct == pytest.approx(100.0)
    assert result.exact_knapsack_optimal is True
    assert result.our_bundle_selected is True


def test_dynamic_tip_calibrator_standard_70_30_split_and_edge_50_to_70_pct() -> None:
    """Verifies standard 70/30 priority-fee/Jito-tip split above P75 and competitive
    Block-0 / Emergency Cabal-Dump 50%–70% (default 60%) expected profit scaling.
    """
    conflict_tips = [1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]
    std_res = calibrate_dynamic_jito_tip_and_priority_split(
        expected_profit_lamports=50_000_000,
        recent_conflict_set_winning_tips_lamports=conflict_tips,
        mode="STANDARD",
    )
    assert std_res.mode == "STANDARD"
    assert std_res.is_competitive_edge_mode is False
    assert std_res.p75_conflict_set_lamports == 4_000_000
    assert std_res.priority_fee_fraction == pytest.approx(0.70)
    assert std_res.jito_tip_fraction == pytest.approx(0.30)
    assert (
        std_res.priority_fee_lamports / std_res.total_fee_budget_lamports
    ) == pytest.approx(0.70, abs=1e-6)
    assert (
        std_res.tip_lamports / std_res.total_fee_budget_lamports
    ) == pytest.approx(0.30, abs=1e-6)
    assert std_res.tip_lamports == std_res.jito_tip_lamports
    assert std_res.tip_lamports > std_res.p75_conflict_set_lamports
    assert std_res.exceeds_conflict_set_p75 is True

    # Competitive Block-0 Migration Snipe (default 60% of expected profit V)
    snipe_default = calibrate_dynamic_jito_tip_and_priority_split(
        expected_profit_lamports=100_000_000,
        is_block0_snipe=True,
    )
    assert snipe_default.mode == "BLOCK0_MIGRATION_SNIPE"
    assert snipe_default.is_competitive_edge_mode is True
    assert snipe_default.is_block0_snipe is True
    assert snipe_default.edge_tip_fraction == pytest.approx(0.60)
    assert snipe_default.tip_lamports == 60_000_000

    # Competitive Emergency Cabal-Dump Front-Run at 50% and 70% bounds (and clamping)
    cabal_50 = calibrate_dynamic_jito_tip_and_priority_split(
        expected_profit_lamports=80_000_000,
        is_emergency_cabal_frontrun=True,
        edge_tip_fraction=0.40,  # Clamped up to 0.50
    )
    assert cabal_50.mode == "EMERGENCY_CABAL_DUMP_FRONTRUN"
    assert cabal_50.edge_tip_fraction == pytest.approx(0.50)
    assert cabal_50.tip_lamports == 40_000_000

    cabal_70 = calibrate_dynamic_jito_tip_and_priority_split(
        expected_profit_lamports=80_000_000,
        is_emergency_cabal_frontrun=True,
        edge_tip_fraction=0.85,  # Clamped down to 0.70
    )
    assert cabal_70.edge_tip_fraction == pytest.approx(0.70)
    assert cabal_70.tip_lamports == int(80_000_000 * 0.70)


def test_jitodontfront_validator_all_5_structural_invariants() -> None:
    """Verifies all 5 strict Jito Block Engine `jitodontfront` bundle structural invariants."""
    # 1. Sparse Slot Compaction: [tx1, None, tx2] -> [tx1, tx2] + inline final tip appended
    sparse_res = validate_and_compact_jitodontfront_bundle(
        transactions=[
            {
                "tx_id": "tx0_front",
                "signers": ["signer_1"],
                "accounts": [JITO_DONT_FRONT_PUBKEY, "PoolA"],
            },
            None,
            None,
            {
                "tx_id": "tx1_back",
                "signers": ["signer_1"],
                "accounts": ["PoolA"],
            },
        ],
        tip_lamports=2_500_000,
    )
    assert sparse_res.valid is True
    assert sparse_res.status == VALID_JITODONTFRONT_BUNDLE
    assert sparse_res.original_slot_count == 4
    assert sparse_res.compacted_tx_count == 2
    assert sparse_res.sparse_nulls_removed == 2
    assert sparse_res.index0_has_jitodontfront is True
    assert sparse_res.inline_final_tip_verified is True
    assert sparse_res.inline_final_tip_appended is True
    assert sparse_res.selected_jito_tip_account in OFFICIAL_JITO_TIP_ACCOUNTS
    last_tx_final_ix = sparse_res.compacted_transactions[-1].instructions[-1]
    assert last_tx_final_ix.is_jito_tip_transfer is True
    assert last_tx_final_ix.tip_account in OFFICIAL_JITO_TIP_ACCOUNTS
    assert last_tx_final_ix.tip_lamports == 2_500_000

    # 1b. Empty bundle and > 5 compacted transactions rejected
    empty_res = validate_and_compact_jitodontfront_bundle([None, None])
    assert empty_res.valid is False
    assert empty_res.rejection_reason == REJECTED_EMPTY_BUNDLE

    too_many_res = validate_and_compact_jitodontfront_bundle(
        [
            {"tx_id": f"tx_{i}", "signers": ["s1"], "accounts": [JITO_DONT_FRONT_PUBKEY] if i == 0 else ["Acct"]}
            for i in range(6)
        ]
    )
    assert too_many_res.valid is False
    assert too_many_res.rejection_reason == REJECTED_BUNDLE_EXCEEDS_5_TX_LIMIT

    # 2. No Duplicate `jitodontfront` Accounts in a Single Tx
    dup_res = validate_and_compact_jitodontfront_bundle(
        [
            {
                "tx_id": "tx0_dup",
                "signers": ["signer_1"],
                "accounts": [
                    JITO_DONT_FRONT_PUBKEY,
                    "jitodontfrontSecondarySentinel11111111111111",
                ],
            }
        ]
    )
    assert dup_res.valid is False
    assert dup_res.rejection_reason == REJECTED_DUPLICATE_JITODONTFRONT_IN_TX

    # 3. Strict Index-0 & Contiguous Front-of-Bundle Rule: reject [tip_tx, tx_with_dont_front]
    non_prefix_res = validate_and_compact_jitodontfront_bundle(
        [
            {
                "tx_id": "tx0_tip_without_dont_front",
                "signers": ["signer_1"],
                "accounts": [OFFICIAL_JITO_TIP_ACCOUNTS[0]],
            },
            {
                "tx_id": "tx1_with_dont_front_at_index1",
                "signers": ["signer_1"],
                "accounts": [JITO_DONT_FRONT_PUBKEY, "PoolA"],
            },
        ]
    )
    assert non_prefix_res.valid is False
    assert non_prefix_res.rejection_reason == REJECTED_NON_PREFIX_JITODONTFRONT_INDEX

    # Also reject gap in `jitodontfront` indices [0, 2]
    gapped_prefix_res = validate_and_compact_jitodontfront_bundle(
        [
            {"tx_id": "tx0_df", "signers": ["s1"], "accounts": [JITO_DONT_FRONT_PUBKEY]},
            {"tx_id": "tx1_no_df", "signers": ["s1"], "accounts": ["PoolA"]},
            {"tx_id": "tx2_df", "signers": ["s1"], "accounts": [JITO_DONT_FRONT_PUBKEY]},
        ]
    )
    assert gapped_prefix_res.valid is False
    assert gapped_prefix_res.rejection_reason == REJECTED_NON_PREFIX_JITODONTFRONT_INDEX

    # 4. Overlapping Cryptographic Signer Contiguity:
    # Valid contiguous overlapping signers in prefix [Tx0(A), Tx1(A,B), Tx2(B)]
    valid_multi_signer_res = validate_and_compact_jitodontfront_bundle(
        [
            {"tx_id": "tx0", "signers": ["signer_A"], "accounts": [JITO_DONT_FRONT_PUBKEY]},
            {"tx_id": "tx1", "signers": ["signer_A", "signer_B"], "accounts": [JITO_DONT_FRONT_PUBKEY]},
            {"tx_id": "tx2", "signers": ["signer_B"], "accounts": ["PoolA"]},
        ]
    )
    assert valid_multi_signer_res.valid is True
    assert valid_multi_signer_res.dont_front_tx_indices == [0, 1]

    # Invalid discontiguous overlapping signers [Tx0(A), Tx1(B), Tx2(A)]
    discontiguous_signer_res = validate_and_compact_jitodontfront_bundle(
        [
            {"tx_id": "tx0", "signers": ["signer_A"], "accounts": [JITO_DONT_FRONT_PUBKEY]},
            {"tx_id": "tx1", "signers": ["signer_B"], "accounts": [JITO_DONT_FRONT_PUBKEY]},
            {"tx_id": "tx2", "signers": ["signer_A"], "accounts": [JITO_DONT_FRONT_PUBKEY]},
        ]
    )
    assert discontiguous_signer_res.valid is False
    assert (
        discontiguous_signer_res.rejection_reason
        == REJECTED_DISCONTIGUOUS_OVERLAPPING_SIGNERS
    )

    # 5. Invalid tip account or missing final tip when auto_append_inline_final_tip=False
    bad_tip_acct_res = validate_and_compact_jitodontfront_bundle(
        [{"tx_id": "tx0", "signers": ["s1"], "accounts": [JITO_DONT_FRONT_PUBKEY]}],
        preferred_tip_account="NotAnOfficialJitoTipAccount1111111111111111",
    )
    assert bad_tip_acct_res.valid is False
    assert bad_tip_acct_res.rejection_reason == REJECTED_INVALID_JITO_TIP_ACCOUNT

    missing_tip_res = validate_and_compact_jitodontfront_bundle(
        [{"tx_id": "tx0", "signers": ["s1"], "accounts": [JITO_DONT_FRONT_PUBKEY]}],
        auto_append_inline_final_tip=False,
    )
    assert missing_tip_res.valid is False
    assert missing_tip_res.rejection_reason == REJECTED_MISSING_INLINE_FINAL_TIP_INSTRUCTION


def test_sub80ms_execution_budget_and_5_region_jito_astralane_lil_jit_fanout() -> None:
    """Verifies `< 80ms` end-to-end budget (`<20ms` path search, `<10ms` build,
    `<20ms` simulateBundle, `<30ms` parallel submit) and 50–100ms pre-slot-transition
    fan-out across all 5 Jito regions + Astralane + Lil-JIT.
    """
    assert (
        MAX_PATH_SEARCH_BUDGET_MS
        + MAX_TX_BUILD_BUDGET_MS
        + MAX_SIMULATE_BUNDLE_BUDGET_MS
        + MAX_PARALLEL_SUBMIT_BUDGET_MS
        == MAX_END_TO_END_EXECUTION_BUDGET_MS
    )

    res = execute_sub80ms_multi_region_bundle(
        bundle_id="test_sub80ms_bundle",
        tip_lamports=4_200_000,
        path_search_ms=14.5,
        tx_build_ms=6.2,
        simulate_bundle_ms=15.1,
        parallel_submit_ms=22.4,
        simulate_bundle_passed=True,
        time_until_slot_transition_ms=68.0,
    )
    assert res.dispatched is True
    assert res.simulate_bundle_passed is True
    assert res.path_search_within_20ms is True
    assert res.tx_build_within_10ms is True
    assert res.simulate_bundle_within_20ms is True
    assert res.parallel_submit_within_30ms is True
    assert res.total_execution_ms == pytest.approx(58.2)
    assert res.within_80ms_total_budget is True
    assert res.all_stage_budgets_met is True
    assert res.within_50_to_100ms_slot_window is True

    assert res.jito_regions_dispatched == list(JITO_5_REGIONS)
    assert res.additional_relays_dispatched == ["ASTRALANE", "LIL_JIT"]
    assert res.all_5_jito_regions_covered is True
    assert res.astralane_included is True
    assert res.lil_jit_included is True
    assert len(res.target_receipts) == 7
    assert res.selected_jito_tip_account in OFFICIAL_JITO_TIP_ACCOUNTS

    # Verify pre-flight simulateBundle failure aborts submission and saves tips
    aborted = execute_sub80ms_multi_region_bundle(
        bundle_id="test_reverted_bundle",
        tip_lamports=4_200_000,
        simulate_bundle_passed=False,
    )
    assert aborted.dispatched is False
    assert aborted.status == "ABORTED_SIMULATE_BUNDLE_FAILED"
    assert aborted.tips_saved_on_abort_lamports == 4_200_000
    assert aborted.target_receipts == []


def test_jito_knapsack_bundle_judge_facade_and_ipc_telemetry() -> None:
    """Verifies `JitoKnapsackBundleJudge.run_full_jito_judge_diagnostic()` and
    `get_telemetry_summary()` for `TitanIPCDaemon` (`RUN_JITO_KNAPSACK_DONTFRONT_JUDGE`).
    """
    judge = get_jito_knapsack_bundle_judge()
    assert isinstance(judge, JitoKnapsackBundleJudge)

    diag = judge.run_full_jito_judge_diagnostic()
    assert diag["status"] == "PASS"
    assert diag["ok"] is True
    assert diag["ipc_command"] == IPC_COMMAND_RUN_JITO_KNAPSACK_DONTFRONT_JUDGE
    assert diag["all_invariants_verified"] is True

    telemetry = judge.get_telemetry_summary()
    assert telemetry["ipc_command"] == IPC_COMMAND_RUN_JITO_KNAPSACK_DONTFRONT_JUDGE
    assert telemetry["official_jito_tip_accounts_count"] == 8
    assert telemetry["jito_5_regions"] == list(JITO_5_REGIONS)
    assert telemetry["additional_relays"] == ["ASTRALANE", "LIL_JIT"]
    assert telemetry["counters"]["diagnostics_run"] >= 1
    assert telemetry["counters"]["auctions_solved"] >= 1
    assert telemetry["counters"]["tip_calibrations_run"] >= 3
    assert telemetry["counters"]["bundles_validated"] >= 4
    assert telemetry["counters"]["bundles_rejected"] >= 3
    assert telemetry["counters"]["multi_region_dispatches"] >= 1
    assert telemetry["last_diagnostic_available"] is True
