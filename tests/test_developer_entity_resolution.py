"""Comprehensive pytest verification suite for
`/home/titanagentik/sovereign-titan/src/alpha/developer_entity_resolution.py`
implementing Subsystem 4: Persistent Developer Entity Resolution (5-Vector Union-Find +
RED-COHORT-2026-v1 + TLSH/ssdeep/DLAM Transformer + KEENHash + Attention-GNN/PFT) &
Live Tier-1 Developer Registry.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.alpha.developer_entity_resolution import (
    ALL_FIVE_ONCHAIN_LINKAGE_VECTORS,
    ATTENTION_GNN_CLUSTER_ACCURACY_PCT,
    CEX_PREFUND_MAX_FRESH_WALLETS,
    CEX_PREFUND_MAX_TOTAL_SOL,
    CEX_PREFUND_MIN_FRESH_WALLETS,
    CEX_PREFUND_MIN_TOTAL_SOL,
    CURVE_MONITOR_DEFER_PCT,
    CURVE_MONITOR_DEFER_SOL,
    CURVE_PRE_MIGRATION_SNIPE_SOL,
    DLAM_PADDING_MODIFICATION_MAX_PCT,
    DLAM_PADDING_MODIFICATION_MIN_PCT,
    DLAM_SHARED_FRAGMENT_MAX_PCT,
    DLAM_SHARED_FRAGMENT_MIN_PCT,
    DeveloperEntityUnionFind,
    JITO_DONT_FRONT_PUBKEY,
    KEENHASH_BENCHMARK_EVALUATIONS,
    KEENHASH_BENCHMARK_RUNTIME_SEC,
    KEENHASH_SPEEDUP_MULTIPLIER,
    LiveDeveloperRegistryOrchestrator,
    PATH_A_GENESIS_ACTION,
    PATH_B_DEFER_ACTION,
    PEELING_CHAIN_MAX_FEE_TOLERANCE_PCT,
    PersistentDeveloperEntityResolutionSuite,
    RED_COHORT_EMPIRICAL_PERSISTENT_RINGS,
    RED_COHORT_EMPIRICAL_UNIQUE_ADDRESSES,
    RED_COHORT_FIRST_BUYER_WINDOW,
    RED_COHORT_MAX_SIZE,
    RED_COHORT_MIN_CO_OCCURRENCES,
    RED_COHORT_MIN_SIZE,
    RED_COHORT_RULE_ID,
    RED_COHORT_TOP100_EVENT_SHARE_MAX_PCT,
    RED_COHORT_TOP100_EVENT_SHARE_MIN_PCT,
    RED_COHORT_TOP_9WALLET_AVG_BUYER_RANK,
    RED_COHORT_TOP_9WALLET_DAYS,
    RED_COHORT_TOP_9WALLET_LAUNCHES,
    RED_COHORT_TOP_9WALLET_SIZE,
    RL_SCALE_OUT_MULTIPLIERS,
    SLOT0_FAST_MATCH_MAX_LATENCY_MS,
    STEALTH_CLUSTER_HAIR_TRIGGER_MAX_MS,
    TIER1_COHORT_MIN_30D_WIN_RATE_PCT,
    TIER1_COHORT_MIN_WIN_LOSS_RATIO,
    TIER1_MIN_GRADUATED_LAUNCHES,
    TLSH_DIGEST_HEX_LEN,
    TLSH_MAX_DISTANCE,
    TLSH_SLIDING_WINDOW_BYTES,
    VECTOR_ATOMIC_COSIGNING_AND_ALT_AUTHORITY,
    VECTOR_CEX_DEPOSIT_ADDRESS_BRIDGE,
    VECTOR_PEELING_CHAIN_RECONSOLIDATION,
    VECTOR_RED_COHORT_2026_V1_SNIPER_RINGS,
    VECTOR_UPSTREAM_FUNDER_AND_MAGIC_NODES,
    ZeroLinkReIdentifier,
    compute_ssdeep_ctph_similarity,
    compute_tlsh_72char_digest,
    compute_tlsh_distance,
    evaluate_behavioral_gnn_and_pft_fusion,
    evaluate_dlam_transformer_similarity,
)


def test_layer1_vector1_cex_deposit_bridge_and_correlated_withdrawal_prefunding() -> None:
    """Verifies Vector 1 (`CEX_DEPOSIT_ADDRESS_BRIDGE`):
      1. Unites burner deployers D1 and D2 routing multi-hop profits into the exact same
         persistent KYC exchange deposit address X_dep prior to hot-wallet sweep.
      2. Flags newly pre-funded burner D3 via correlated CEX withdrawal timing/denominations
         (`15.0–90.0 SOL` split across `5–10` fresh wallets).
    """
    assert CEX_PREFUND_MIN_TOTAL_SOL == pytest.approx(15.0)
    assert CEX_PREFUND_MAX_TOTAL_SOL == pytest.approx(90.0)
    assert CEX_PREFUND_MIN_FRESH_WALLETS == 5
    assert CEX_PREFUND_MAX_FRESH_WALLETS == 10

    uf = DeveloperEntityUnionFind()
    d1 = "DeployerBurnerD1_111111111111111111111111111"
    d2 = "DeployerBurnerD2_222222222222222222222222222"
    d3 = "DeployerBurnerD3_333333333333333333333333333"
    x_dep = "KycDepositAddrXdep_9999999999999999999999999"
    cex_hot = "BinanceHotSweep_8888888888888888888888888888"

    id1 = uf.ingest_cex_deposit_bridge(
        deployer_wallet=d1,
        intermediary_hops=["Hop1A", "Hop1B"],
        cex_deposit_address=x_dep,
        cex_hot_wallet=cex_hot,
        profit_sol=38.0,
    )
    id2 = uf.ingest_cex_deposit_bridge(
        deployer_wallet=d2,
        intermediary_hops=["Hop2A", "Hop2B", "Hop2C"],
        cex_deposit_address=x_dep,
        cex_hot_wallet=cex_hot,
        profit_sol=54.2,
    )
    assert id1 == id2
    assert uf.are_co_controlled(d1, d2) is True

    # Correlated CEX withdrawal: 48.0 SOL split across 6 fresh wallets within 60 seconds
    alert = uf.detect_correlated_cex_withdrawal_prefunding(
        cex_hot_wallet=cex_hot,
        withdrawals=[
            (d3, 8.0, 5000.0),
            ("FreshSybil_2", 8.5, 5010.0),
            ("FreshSybil_3", 7.5, 5022.0),
            ("FreshSybil_4", 8.0, 5035.0),
            ("FreshSybil_5", 8.0, 5048.0),
            ("FreshSybil_6", 8.0, 5059.0),
        ],
    )
    assert alert.is_correlated_cex_prefund is True
    assert alert.within_15_to_90_sol_band is True
    assert alert.within_5_to_10_wallet_band is True
    assert alert.total_withdrawn_sol == pytest.approx(48.0)
    assert alert.wallet_count == 6
    assert uf.are_co_controlled(d1, d3) is True

    cluster = uf.resolve_developer_entity(d3)
    assert x_dep in cluster.cex_deposit_addresses
    assert VECTOR_CEX_DEPOSIT_ADDRESS_BRIDGE in cluster.active_vectors
    assert len(cluster.prefunded_burner_alerts) == 1


def test_layer1_vector3_red_cohort_2026_v1_persistent_sniper_rings() -> None:
    """Verifies Vector 3 (`RED_COHORT_2026_V1_SNIPER_RINGS`):
      - Two-stage `RED-COHORT-2026-v1` detector over first-10 buyer window
        (`co_occurrences >= 3`, cohort sizes `2 <= size <= 12`).
      - Empirical benchmarks: `1,012` persistent rings, `2,965` unique addresses,
        top 9-wallet cohort with avg buyer rank `2.29` across `42` launches in `11` days,
        and top 100 cohorts = `27%–35%` of cohort-touch events.
    """
    assert RED_COHORT_RULE_ID == "RED-COHORT-2026-v1"
    assert RED_COHORT_FIRST_BUYER_WINDOW == 10
    assert RED_COHORT_MIN_CO_OCCURRENCES == 3
    assert RED_COHORT_MIN_SIZE == 2
    assert RED_COHORT_MAX_SIZE == 12
    assert RED_COHORT_EMPIRICAL_PERSISTENT_RINGS == 1_012
    assert RED_COHORT_EMPIRICAL_UNIQUE_ADDRESSES == 2_965
    assert RED_COHORT_TOP_9WALLET_SIZE == 9
    assert RED_COHORT_TOP_9WALLET_AVG_BUYER_RANK == pytest.approx(2.29)
    assert RED_COHORT_TOP_9WALLET_LAUNCHES == 42
    assert RED_COHORT_TOP_9WALLET_DAYS == 11
    assert RED_COHORT_TOP100_EVENT_SHARE_MIN_PCT == pytest.approx(27.0)
    assert RED_COHORT_TOP100_EVENT_SHARE_MAX_PCT == pytest.approx(35.0)

    uf = DeveloperEntityUnionFind()
    top9_wallets = [f"Top9InsiderSniper_{i}" for i in range(1, 10)]
    # Construct 42 launches across 11 days where the 9-wallet ring snipes in the first-10 window
    # with ranks averaging ~2.29
    rank_pattern = [1, 1, 2, 2, 2, 3, 3, 3, 4]  # mean = 21 / 9 = 2.33
    launches = []
    for l_idx in range(42):
        ts = 1_700_000_000.0 + (l_idx / 41.0) * (11.0 * 86400.0)
        deployer = "RotatedDev_Alpha" if l_idx % 2 == 0 else "RotatedDev_Beta"
        launches.append(
            {
                "token_mint": f"CohortMint_{l_idx:02d}",
                "deployer_wallet": deployer,
                "timestamp_sec": ts,
                "first_10_buyers": list(zip(top9_wallets, rank_pattern)),
            }
        )

    report = uf.ingest_red_cohort_2026_v1_sniper_rings(launches)
    assert report.rule_id == "RED-COHORT-2026-v1"
    assert report.persistent_ring_count == 1
    assert report.unique_ring_addresses == 9
    assert RED_COHORT_TOP100_EVENT_SHARE_MIN_PCT <= report.top_100_event_share_pct <= RED_COHORT_TOP100_EVENT_SHARE_MAX_PCT

    ring = report.detected_rings[0]
    assert ring.cohort_size == 9
    assert ring.co_occurrence_launches == 42
    assert ring.observation_span_days == pytest.approx(11.0, abs=0.1)
    assert 2.0 <= ring.avg_buyer_rank <= 2.5
    assert uf.are_co_controlled("RotatedDev_Alpha", "RotatedDev_Beta") is True


def test_layer1_all_five_vectors_and_peeling_chain_tolerance() -> None:
    """Verifies that all 5 linkage vectors merge distinct burner deployers into a single
    persistent `Developer_Entity_ID`, and that Vector 5 (`PEELING_CHAIN_RECONSOLIDATION`)
    enforces the `<= 1.5%` fee tolerance.
    """
    assert len(ALL_FIVE_ONCHAIN_LINKAGE_VECTORS) == 5
    assert PEELING_CHAIN_MAX_FEE_TOLERANCE_PCT == pytest.approx(1.5)

    uf = DeveloperEntityUnionFind()
    d1, d2, d3, d4, d5 = "DevW1", "DevW2", "DevW3", "DevW4", "DevW5"

    # Vector 1: CEX bridge (d1 <-> d2)
    uf.ingest_cex_deposit_bridge(d1, ["HopX"], "SharedCexDep")
    uf.ingest_cex_deposit_bridge(d2, ["HopY"], "SharedCexDep")

    # Vector 2: Upstream funder + Magic Nodes (d2 <-> d3)
    uf.ingest_upstream_funder_and_magic_nodes(
        deployer_wallets=[d2, d3],
        upstream_funder="UpstreamFunder99",
        magic_node_sink="MagicNodeSink99",
    )

    # Vector 3: RED-COHORT-2026-v1 (d3 <-> d4)
    uf.ingest_red_cohort_2026_v1_sniper_rings(
        [
            {
                "token_mint": f"M_{i}",
                "deployer_wallet": d3 if i < 2 else d4,
                "first_10_buyers": ["SniperA", "SniperB", "SniperC"],
            }
            for i in range(4)
        ]
    )

    # Vector 4: Atomic Co-Signing & ALT Authority (d4 <-> d5)
    uf.ingest_atomic_cosigning_and_alt_authority(
        deployer_wallets=[d4, d5],
        co_signers=["CoSignerZ"],
        shared_alt_creator="SharedALTCreatorZ",
        program_upgrade_authority="SharedUpgradeAuthZ",
        jito_bundle_id="Bundle_777",
    )

    # Vector 5: Peeling chain within <= 1.5% tolerance (100.0 SOL -> 99.1 SOL = 0.9% fee leakage)
    peel_ok = uf.ingest_peeling_chain_reconsolidation(
        source_wallet=d5,
        upstream_inflow_sol=100.0,
        peel_transfers=[
            ("Peel_1", 49.5, 100.0),
            ("Peel_2", 49.6, 105.0),
        ],
        reconsolidation_sink_wallet="FinalDevSinkWallet",
    )
    assert peel_ok.within_1_5_pct_tolerance is True
    assert peel_ok.fee_leakage_pct == pytest.approx(0.9)

    # Verify non-qualifying peeling chain (> 1.5% fee difference) does NOT merge unrelated wallet
    peel_reject = uf.ingest_peeling_chain_reconsolidation(
        source_wallet="UnrelatedSourceWallet",
        upstream_inflow_sol=100.0,
        peel_transfers=[("UnrelatedPeel", 90.0, 200.0)],  # 10.0% leakage > 1.5%
        reconsolidation_sink_wallet="UnrelatedSinkWallet",
    )
    assert peel_reject.within_1_5_pct_tolerance is False
    assert uf.are_co_controlled("UnrelatedSourceWallet", "UnrelatedSinkWallet") is False

    # Verify D1..D5 and FinalDevSinkWallet all resolve to the exact same Developer Entity
    cluster = uf.resolve_developer_entity(d1)
    for w in (d1, d2, d3, d4, d5, "FinalDevSinkWallet"):
        assert uf.are_co_controlled(d1, w) is True
        assert w in cluster.member_wallets
    assert cluster.vector_count == 5
    assert set(cluster.active_vectors) == set(ALL_FIVE_ONCHAIN_LINKAGE_VECTORS)


def test_layer2_ssdeep_ctph_tlsh_72char_and_dlam_transformer_obfuscation_recovery() -> None:
    """Verifies Layer 2 Zero-Link Re-Identification primitives:
      1. `compute_ssdeep_ctph_similarity`: rolling-hash CTPH + ensemble mean of
         Levenshtein, Jaccard, and Sorensen similarity metrics.
      2. `compute_tlsh_72char_digest` & `compute_tlsh_distance`: 5-byte sliding window,
         Pearson hash, quartile buckets, exact 72-char hex digest, distance in `[0, 1000]`.
      3. `evaluate_dlam_transformer_similarity`: zero-padding, positional encoding, and
         masked self-attention recovering `1%–13%` conserved developer fragment even when
         `87%–91%` of the payload is padded/modified, plus `KEENHash` (`215x` speedup:
         `5.3B` evaluations in `395.83s`).
    """
    assert TLSH_DIGEST_HEX_LEN == 72
    assert TLSH_SLIDING_WINDOW_BYTES == 5
    assert TLSH_MAX_DISTANCE == 1000
    assert DLAM_PADDING_MODIFICATION_MIN_PCT == pytest.approx(87.0)
    assert DLAM_PADDING_MODIFICATION_MAX_PCT == pytest.approx(91.0)
    assert DLAM_SHARED_FRAGMENT_MIN_PCT == pytest.approx(1.0)
    assert DLAM_SHARED_FRAGMENT_MAX_PCT == pytest.approx(13.0)
    assert KEENHASH_SPEEDUP_MULTIPLIER == pytest.approx(215.0)
    assert KEENHASH_BENCHMARK_EVALUATIONS == 5_300_000_000
    assert KEENHASH_BENCHMARK_RUNTIME_SEC == pytest.approx(395.83)

    base_code = (
        b"AnchorInstruction::InitializeMint2|ComputeUnitLimit=187420|"
        b"PumpFunBondingCurveSetup_v3|CustomFeeVaultRoute_9918273645!"
    )
    payload_a = base_code + bytes((i * 37 + 13) & 0xFF for i in range(300))
    payload_a_near = base_code + bytes((i * 37 + 13) & 0xFF for i in range(290)) + b"MODIFIED10"
    payload_unrelated = bytes((i * 109 + 211) & 0xFF for i in range(400))

    # 1. ssdeep CTPH similarity
    ss_same = compute_ssdeep_ctph_similarity(payload_a, payload_a_near)
    ss_diff = compute_ssdeep_ctph_similarity(payload_a, payload_unrelated)
    expected_mean = (
        ss_same.levenshtein_similarity
        + ss_same.jaccard_similarity
        + ss_same.sorensen_similarity
    ) / 3.0
    assert ss_same.ensemble_mean_similarity == pytest.approx(expected_mean, abs=1e-5)
    assert ss_same.is_match is True
    assert ss_same.ensemble_mean_similarity > ss_diff.ensemble_mean_similarity

    # 2. TLSH 72-char hex digest & distance in [0, 1000]
    digest_a = compute_tlsh_72char_digest(payload_a)
    digest_near = compute_tlsh_72char_digest(payload_a_near)
    digest_unrel = compute_tlsh_72char_digest(payload_unrelated)

    assert len(digest_a) == 72
    assert len(digest_near) == 72
    assert all(c in "0123456789ABCDEF" for c in digest_a)
    assert compute_tlsh_distance(digest_a, digest_a) == 0

    dist_near = compute_tlsh_distance(digest_a, digest_near)
    dist_unrel = compute_tlsh_distance(digest_a, digest_unrel)
    assert 0 <= dist_near <= 1000
    assert 0 <= dist_unrel <= 1000
    assert dist_near < dist_unrel

    # 3. DLAM Transformer under 89% padding/modification (11% conserved fragment)
    # Total length = 1000 bytes; conserved base_code = ~112 bytes (~11%), padding = 888 bytes (~89%)
    heavily_padded_b = (b"\x00" * 444) + base_code + (b"\xff" * 444)
    digest_padded_b = compute_tlsh_72char_digest(heavily_padded_b)

    dlam_res = evaluate_dlam_transformer_similarity(
        digest_a=digest_a,
        digest_b=digest_padded_b,
        raw_a=payload_a,
        raw_b=heavily_padded_b,
    )
    assert dlam_res.positional_encoding_applied is True
    assert dlam_res.masked_self_attention_applied is True
    assert DLAM_SHARED_FRAGMENT_MIN_PCT <= dlam_res.shared_fragment_recovery_pct <= DLAM_SHARED_FRAGMENT_MAX_PCT
    assert DLAM_PADDING_MODIFICATION_MIN_PCT <= dlam_res.estimated_padding_modification_pct <= DLAM_PADDING_MODIFICATION_MAX_PCT
    assert dlam_res.survives_87_to_91_pct_obfuscation is True
    assert dlam_res.is_same_developer_codebase is True
    assert dlam_res.keenhash_speedup_multiplier == pytest.approx(215.0)
    assert dlam_res.keenhash_lookup_latency_ms < SLOT0_FAST_MATCH_MAX_LATENCY_MS


def test_layer2_behavioral_gnn_91_7_pct_and_pft_fusion() -> None:
    """Verifies `evaluate_behavioral_gnn_and_pft_fusion` across involuntary software
    fingerprints (instruction sequence, exact CU limit integer, priority fee rounding habit,
    `pump` vanity suffix, funding-to-deploy ms cadence), Attention-GNN (`91.7%` cluster
    accuracy), PFT LLM account matching, X/Twitter handle rename history, and Metaplex
    image embeddings.
    """
    assert ATTENTION_GNN_CLUSTER_ACCURACY_PCT == pytest.approx(91.7)

    ref_profile = {
        "entity_id": "DEV_ENTITY_SERIAL_WINNER_77",
        "instruction_sequence": (
            "ComputeBudget::SetComputeUnitLimit",
            "ComputeBudget::SetComputeUnitPrice",
            "PumpFun::Create",
            "PumpFun::Buy",
        ),
        "exact_cu_limit": 194320,
        "priority_fee_micro_lamports": 412888,
        "vanity_suffix": "pump",
        "funding_to_deploy_ms": 3850.0,
        "gnn_behavior_vector": [0.91, 0.42, 0.18, 0.77],
        "metadata_style_signature": "ticker_upper|desc_meme_2lines|tg_portal_link",
        "twitter_numeric_id": "998877665544",
        "twitter_handle_history": ["@sol_builder_old", "@sol_builder_v2"],
        "metaplex_image_embedding": [0.75, 0.61, 0.22, 0.11],
    }

    cand_profile = {
        "instruction_sequence": (
            "ComputeBudget::SetComputeUnitLimit",
            "ComputeBudget::SetComputeUnitPrice",
            "PumpFun::Create",
            "PumpFun::Buy",
        ),
        "exact_cu_limit": 194320,
        "priority_fee_micro_lamports": 912888,  # Same quirky modulo-1000 habit (888)
        "vanity_suffix": "pump",
        "funding_to_deploy_ms": 3890.0,
        "gnn_behavior_vector": [0.90, 0.43, 0.19, 0.76],
        "metadata_style_signature": "ticker_upper|desc_meme_2lines|tg_portal_link",
        "twitter_numeric_id": "998877665544",  # Same immutable Twitter ID despite handle rename
        "twitter_handle_history": ["@sol_builder_rebranded"],
        "metaplex_image_embedding": [0.74, 0.62, 0.21, 0.12],
    }

    res = evaluate_behavioral_gnn_and_pft_fusion(cand_profile, ref_profile)
    assert res.is_reidentified is True
    assert res.matched_entity_id == "DEV_ENTITY_SERIAL_WINNER_77"
    assert res.attention_gnn_benchmark_accuracy_pct == pytest.approx(91.7)
    assert res.involuntary_fingerprint_score >= 0.90
    assert res.attention_gnn_cluster_score >= 0.95
    assert res.pft_llm_account_score >= 0.95
    assert res.social_and_image_fusion_score >= 0.95
    assert "EXACT_INSTRUCTION_SEQUENCE" in res.matched_signals
    assert "EXACT_CU_LIMIT_194320" in res.matched_signals
    assert "IMMUTABLE_TWITTER_ID_RENAME_MATCH" in res.matched_signals


def test_operational_blueprint_live_tier1_registry_and_path_a_vs_path_b_router() -> None:
    """Verifies `LiveDeveloperRegistryOrchestrator`:
      - Curates `Tier-1 Serial Winner Developers` (`graduated_launches >= 2`, high ATH,
        zero Slot-1 rug drain or clean CTO catalyst, Cielo/Kolscan/uwuu `30d_win_rate >= 35.0%`
        and `win_loss_ratio >= 2.0`).
      - Path A (Known Tier-1 Developer at Slot 0 via Graph, Watch Wallet, `RED-COHORT-2026-v1`,
        or `<5ms` DLAM/TLSH): Immediately triggers `"SLOT0_OR_SLOT1_GENESIS_JITO_SNIPE"` with
        `jitodontfront` and multi-relay fan-out.
      - Path B (Unknown Developer at Slot 0): Defers entry (`"DEFER_TO_80PCT_CURVE_PDA_MONITOR"`),
        monitors curve PDA to `80%`, runs 122-feature MELT + Tarjan SCC wash filter, pre-warms
        PumpSwap tx at `80%`, fires Slot-0 pre-migration snipe at `84.5 SOL`, and hands off to
        ElizaOS + RL exit engine (`2x, 3x, 5x` scale-out + `<50ms` stealth-cluster hair-trigger).
    """
    assert TIER1_MIN_GRADUATED_LAUNCHES == 2
    assert TIER1_COHORT_MIN_30D_WIN_RATE_PCT == pytest.approx(35.0)
    assert TIER1_COHORT_MIN_WIN_LOSS_RATIO == pytest.approx(2.0)

    orchestrator = LiveDeveloperRegistryOrchestrator()

    # Register a qualifying Tier-1 Serial Winner Developer
    core_bytes = b"Tier1WinnerCustomDeployerPayload_v9_Signature_ComputeUnitLimit_212000" * 5
    rec = orchestrator.evaluate_and_register_developer(
        entity_id="DEV_TIER1_WINNER_01",
        graduated_launches=3,
        peak_ath_usd=950_000.0,
        slot1_rug_drains=0,
        clean_cto_catalyst=True,
        cielo_kolscan_uwuu_30d_win_rate_pct=41.2,
        cielo_kolscan_uwuu_win_loss_ratio=2.6,
        associated_watch_wallets=["KolscanAlphaWatchWallet_1"],
        associated_red_cohort_ids=["RED_COHORT_ALPHA1"],
        reference_payload_bytes=core_bytes,
    )
    assert rec.qualifies_as_tier1_serial_winner is True

    # Path A via Watch Wallet / Zero-Link at Slot 0
    decision_a = orchestrator.route_live_token_launch(
        token_mint="Slot0Tier1Mint11111111111111111111111111111",
        deployer_wallet="FreshZeroLinkBurnerDeployer1111111111111111",
        slot0_buyer_wallets=["KolscanAlphaWatchWallet_1"],
        candidate_payload_bytes=core_bytes,
    )
    assert decision_a.is_known_tier1_developer is True
    assert decision_a.recommended_action == PATH_A_GENESIS_ACTION
    assert decision_a.jito_dont_front_AccountMeta == JITO_DONT_FRONT_PUBKEY
    assert len(decision_a.multi_relay_fanout) >= 4
    assert decision_a.slot0_lookup_latency_ms < SLOT0_FAST_MATCH_MAX_LATENCY_MS

    # Path B for Unknown Developer at Slot 0
    decision_b = orchestrator.route_live_token_launch(
        token_mint="UnknownDevMint22222222222222222222222222222",
        deployer_wallet="CompletelyUnknownWallet22222222222222222222",
        observed_curve_sol=84.55,
        melt_122_pred_score=0.15,
        tarjan_scc_wash_trade_ratio=0.05,
    )
    assert decision_b.is_known_tier1_developer is False
    assert decision_b.recommended_action == PATH_B_DEFER_ACTION
    assert decision_b.defer_to_curve_pct == pytest.approx(CURVE_MONITOR_DEFER_PCT)
    assert decision_b.curve_pda_80pct_sol_threshold == pytest.approx(CURVE_MONITOR_DEFER_SOL)
    assert decision_b.melt_and_tarjan_passed is True
    assert decision_b.pumpswap_tx_prewarmed_at_80pct is True
    assert decision_b.pre_migration_snipe_trigger_sol == pytest.approx(CURVE_PRE_MIGRATION_SNIPE_SOL)
    assert decision_b.pre_migration_snipe_fired is True
    assert decision_b.elizaos_rl_exit_handoff is True
    assert decision_b.rl_scale_out_multipliers == RL_SCALE_OUT_MULTIPLIERS
    assert decision_b.stealth_cluster_hair_trigger_ms < STEALTH_CLUSTER_HAIR_TRIGGER_MAX_MS


def test_persistent_developer_entity_resolution_suite_facade() -> None:
    """Verifies `PersistentDeveloperEntityResolutionSuite.run_full_entity_resolution_diagnostic`
    and `get_telemetry_summary`.
    """
    suite = PersistentDeveloperEntityResolutionSuite()
    diag = suite.run_full_entity_resolution_diagnostic()

    assert diag["layer1_union_find_cluster"]["vector_count"] == 5
    assert diag["layer1_prefund_alert"]["is_correlated_cex_prefund"] is True
    assert diag["layer1_red_cohort_report"]["rule_id"] == "RED-COHORT-2026-v1"
    assert diag["layer1_peeling_chain"]["within_1_5_pct_tolerance"] is True
    assert diag["tier1_developer_record"]["qualifies_as_tier1_serial_winner"] is True
    assert (
        diag["path_a_genesis_snipe_decision"]["recommended_action"]
        == "SLOT0_OR_SLOT1_GENESIS_JITO_SNIPE"
    )
    assert (
        diag["path_b_defer_80pct_decision"]["recommended_action"]
        == "DEFER_TO_80PCT_CURVE_PDA_MONITOR"
    )

    telemetry = suite.get_telemetry_summary()
    assert telemetry["subsystem"] == "PersistentDeveloperEntityResolutionSuite"
    assert telemetry["diagnostic_runs"] == 1
    assert len(telemetry["supported_onchain_vectors"]) == 5
    assert telemetry["tlsh_digest_hex_len"] == 72
    assert telemetry["keenhash_speedup_multiplier"] == pytest.approx(215.0)
    assert telemetry["attention_gnn_cluster_accuracy_pct"] == pytest.approx(91.7)
    assert telemetry["last_diagnostic_available"] is True
