#!/usr/bin/env python3
"""Sovereign Titan OS — Phase 3 Closed-Loop Verification & Latency Benchmark Suite.

Validates and benchmarks:
1. DuckDB Latency-Split Lead-Lag Matrix (`/mnt/ramdisk/alpha_graph/lead_lag_matrix.duckdb`)
   and 3-Tier Promotion (`MICRO_CAP_SHADOW_SHARK`, `MID_CAP_SHADOW_SHARK`, `CROWDED_WHALE_BAIT`).
2. Port 8002 Playbook Extractor (`profiles/{wallet}.json`) & Nightly Meta-Strategy Synthesizer
   (`profiles/autonomous_rules.json`).
3. `rustworkx` 3-Hop Burner Graph Rotation Inheritance (`fast_bot_followers=0`, `2.0x` priority)
   and `< 0.5ms` `is_bait_trade()` 3-hop traversal benchmark.
4. 100,000-Banner 64-bit `pHash` BK-Tree index and `< 0.3ms` `VAMPIRE_CLONE` (`Hamming <= 6`) benchmark.
5. End-to-end `preconfSubscribe` packet arrival -> 4 gates -> signed V0 bundle output in `< 2.0ms`
   for both Case A (100% Pre-Approved), Case B (25% Scout + 75% Conviction), and Asymmetric Exit
   Front-Running (`0.90 * first_tp_multiple` & `>=20%` master sell with `0.00203928 SOL` rent reclaim).
"""

from __future__ import annotations

import asyncio
import random
import statistics
import sys
import time
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw

WORKSPACE_ROOT = Path("/home/titanagentik/sovereign-titan")
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.discovery.discovery_lead_lag import (
    CandidateWalletMetrics,
    LeadLagDiscoveryEngine,
    SwapObservationRecord,
)
from src.execution.atomic_tx_builder import ATA_RENT_LAMPORTS
from src.execution.shadow_executor import PreconfShadowEvent, ShadowExecutor
from src.graph.burner_graph import BurnerGraph
from src.intelligence.playbook_extractor import (
    HistoricalTradeRecord,
    PlaybookExtractor,
    WalletProfile,
)
from src.intelligence.pre_scorer_cache import (
    BackgroundPreScorerCache,
    PreApprovedTokenState,
)
from src.intelligence.vision_scam_filter import FastPhashBKTreeIndex, VisionScamFilter


def verify_step_1_duckdb_lead_lag_matrix() -> List[str]:
    print("\n[CHECK 1/5] Benchmarking DuckDB Latency-Split Lead-Lag Matrix & 3-Tier Promotion...")
    engine = LeadLagDiscoveryEngine()

    shark_micro = "MicroShark111111111111111111111111111111111"
    shark_mid = "MidCapShark11111111111111111111111111111111"
    whale_bait = "CrowdedBaitWhale111111111111111111111111111"
    mev_0block = "ZeroBlockMevBot1111111111111111111111111111"

    candidates = [
        CandidateWalletMetrics(
            wallet=shark_micro,
            win_rate_30d=0.61,
            profit_factor_30d=3.4,
            realized_pnl_30d_usd=48_500.0,
            trades_30d=34,
            zero_to_two_slot_entry_ratio=0.18,
            median_entry_mc_usd=68_000.0,  # < $120k Micro-Cap
        ),
        CandidateWalletMetrics(
            wallet=shark_mid,
            win_rate_30d=0.56,
            profit_factor_30d=2.9,
            realized_pnl_30d_usd=92_000.0,
            trades_30d=42,
            zero_to_two_slot_entry_ratio=0.12,
            median_entry_mc_usd=210_000.0,  # >= $120k Mid-Cap
        ),
        CandidateWalletMetrics(
            wallet=whale_bait,
            win_rate_30d=0.52,
            profit_factor_30d=2.6,
            realized_pnl_30d_usd=135_000.0,
            trades_30d=28,
            zero_to_two_slot_entry_ratio=0.10,
            median_entry_mc_usd=180_000.0,
        ),
        CandidateWalletMetrics(
            wallet=mev_0block,
            win_rate_30d=0.65,
            profit_factor_30d=4.1,
            realized_pnl_30d_usd=80_000.0,
            trades_30d=150,
            zero_to_two_slot_entry_ratio=0.88,  # >75% 0-2 slot MEV bot -> discard
            median_entry_mc_usd=45_000.0,
        ),
    ]

    swaps: List[SwapObservationRecord] = []
    trade_id = 1

    # Generate 20 historical trades for each leader and their follower distributions
    for idx in range(20):
        base_slot = 310_000_000 + (idx * 500)

        # 1. Micro-Cap Shark: 1 fast bot (delta=1 slot, 1.5 SOL on 100 SOL pool = 1.5% < 4%) + 2 slow retail
        mint_micro = f"MintMicro{idx:02d}11111111111111111111111111111111"
        swaps.append(
            SwapObservationRecord(
                trade_id=trade_id,
                mint=mint_micro,
                wallet=shark_micro,
                slot=base_slot,
                mint_creation_slot=base_slot - 20,
                sol_amount=3.0,
                pool_sol_reserve=100.0,
                entry_mc_usd=68_000.0,
            )
        )
        trade_id += 1
        swaps.append(
            SwapObservationRecord(
                trade_id=trade_id,
                mint=mint_micro,
                wallet="FastBotA11111111111111111111111111111111111",
                slot=base_slot + 1,
                mint_creation_slot=base_slot - 20,
                sol_amount=1.5,
                pool_sol_reserve=100.0,
                entry_mc_usd=69_000.0,
            )
        )
        trade_id += 1
        for s_idx in range(2):
            swaps.append(
                SwapObservationRecord(
                    trade_id=trade_id,
                    mint=mint_micro,
                    wallet=f"SlowRetailMicro{s_idx}111111111111111111111111111",
                    slot=base_slot + 5 + s_idx,
                    mint_creation_slot=base_slot - 20,
                    sol_amount=0.8,
                    pool_sol_reserve=100.0,
                    entry_mc_usd=70_000.0,
                )
            )
            trade_id += 1

        # 2. Mid-Cap Shark: 2 fast bots (total 5.0 SOL on 120 SOL pool = 4.16% < 8%) + 4 slow retail
        mint_mid = f"MintMidCap{idx:02d}1111111111111111111111111111111"
        swaps.append(
            SwapObservationRecord(
                trade_id=trade_id,
                mint=mint_mid,
                wallet=shark_mid,
                slot=base_slot,
                mint_creation_slot=base_slot - 50,
                sol_amount=6.0,
                pool_sol_reserve=120.0,
                entry_mc_usd=210_000.0,
            )
        )
        trade_id += 1
        for f_idx in range(2):
            swaps.append(
                SwapObservationRecord(
                    trade_id=trade_id,
                    mint=mint_mid,
                    wallet=f"FastBotMid{f_idx}11111111111111111111111111111111",
                    slot=base_slot + 2,
                    mint_creation_slot=base_slot - 50,
                    sol_amount=2.5,
                    pool_sol_reserve=120.0,
                    entry_mc_usd=212_000.0,
                )
            )
            trade_id += 1
        for s_idx in range(4):
            swaps.append(
                SwapObservationRecord(
                    trade_id=trade_id,
                    mint=mint_mid,
                    wallet=f"SlowRetailMid{s_idx}11111111111111111111111111111",
                    slot=base_slot + 6 + s_idx,
                    mint_creation_slot=base_slot - 50,
                    sol_amount=1.0,
                    pool_sol_reserve=120.0,
                    entry_mc_usd=215_000.0,
                )
            )
            trade_id += 1

        # 3. Crowded Bait Whale: 2 fast bots + 16 slow retail followers moving pool price >= 6.5%
        mint_bait = f"MintBait{idx:02d}111111111111111111111111111111111"
        swaps.append(
            SwapObservationRecord(
                trade_id=trade_id,
                mint=mint_bait,
                wallet=whale_bait,
                slot=base_slot,
                mint_creation_slot=base_slot - 40,
                sol_amount=15.0,
                pool_sol_reserve=200.0,
                entry_mc_usd=180_000.0,
            )
        )
        trade_id += 1
        for f_idx in range(2):
            swaps.append(
                SwapObservationRecord(
                    trade_id=trade_id,
                    mint=mint_bait,
                    wallet=f"FastBotBait{f_idx}1111111111111111111111111111111",
                    slot=base_slot + 1,
                    mint_creation_slot=base_slot - 40,
                    sol_amount=1.5,
                    pool_sol_reserve=200.0,
                    entry_mc_usd=182_000.0,
                )
            )
            trade_id += 1
        for s_idx in range(16):
            swaps.append(
                SwapObservationRecord(
                    trade_id=trade_id,
                    mint=mint_bait,
                    wallet=f"SlowHerdFollower{s_idx:02d}111111111111111111111111",
                    slot=base_slot + 4 + (s_idx % 14),
                    mint_creation_slot=base_slot - 40,
                    sol_amount=1.2,  # 16 * 1.2 = 19.2 SOL on 200 SOL pool -> ~19.2% price impact (>= 6.5%)
                    pool_sol_reserve=200.0,
                    entry_mc_usd=188_000.0,
                )
            )
            trade_id += 1

    engine.ingest_candidates_and_swaps(candidates, swaps)
    t0 = time.perf_counter()
    audit_results = engine.run_latency_split_audit(candidates)
    total_audit_ms = (time.perf_counter() - t0) * 1000.0
    by_wallet = {r.wallet: r for r in audit_results}

    assert by_wallet[mev_0block].routed_to == "DISCARDED"
    assert by_wallet[mev_0block].discard_reason == "DISCARD_0_BLOCK_MEV_BOT_GT_75PCT"

    assert by_wallet[shark_micro].promotion_tier == "MICRO_CAP_SHADOW_SHARK"
    assert by_wallet[shark_micro].routed_to == "ACTIVE_SHADOW_LIST"
    assert by_wallet[shark_micro].fast_bot_followers == 1
    assert by_wallet[shark_micro].slow_retail_followers == 2
    assert by_wallet[shark_micro].follower_lp_impact_pct < 4.0

    assert by_wallet[shark_mid].promotion_tier == "MID_CAP_SHADOW_SHARK"
    assert by_wallet[shark_mid].routed_to == "ACTIVE_SHADOW_LIST"
    assert by_wallet[shark_mid].fast_bot_followers == 2
    assert by_wallet[shark_mid].slow_retail_followers == 4
    assert by_wallet[shark_mid].follower_lp_impact_pct < 8.0

    assert by_wallet[whale_bait].promotion_tier == "CROWDED_WHALE_BAIT"
    assert by_wallet[whale_bait].routed_to == "CROWDED_WHALE_BAIT_LIST"
    assert by_wallet[whale_bait].slow_retail_followers == 16
    assert by_wallet[whale_bait].slow_herd_price_impact_pct >= 6.5

    engine.close()
    print(
        f"  [OK] DuckDB Lead-Lag Audit across {len(swaps)} swaps completed in {total_audit_ms:.2f} ms: "
        f"Micro-Cap Shark->ACTIVE_SHADOW_LIST, Mid-Cap Shark->ACTIVE_SHADOW_LIST, "
        f"Crowded Whale->CROWDED_WHALE_BAIT_LIST, 0-Block Bot->DISCARDED."
    )
    return [shark_micro, shark_mid]


async def verify_step_2_playbook_extractor(
    promoted_sharks: List[str],
) -> List[WalletProfile]:
    print("\n[CHECK 2/5] Verifying Port 8002 Playbook Extractor & Nightly Meta-Strategy Synthesizer...")
    extractor = PlaybookExtractor()
    profiles: List[WalletProfile] = []

    for idx, wallet in enumerate(promoted_sharks):
        trades = [
            HistoricalTradeRecord(
                mint=f"HistMint{t:03d}11111111111111111111111111111111",
                sol_spent=1.5 + (t % 5) * 0.5,
                entry_mcap_usd=55_000.0 if idx == 0 else 195_000.0,
                entry_liquidity_usd=22_000.0 if idx == 0 else 48_000.0,
                had_dex_boost=(t % 2 == 0),
                hold_time_sec=95.0 + (t % 40),
                realized_multiple=2.5 if (t % 3 != 0) else 0.85,
                scale_out_pct=50.0,
                is_migrated_pool=(idx == 1 or t % 2 == 0),
            )
            for t in range(100)
        ]
        profile = await extractor.extract_wallet_playbook(
            wallet=wallet,
            last_100_trades=trades,
            fast_bot_followers=idx + 1,
        )
        assert (WORKSPACE_ROOT / "profiles" / f"{wallet}.json").exists()
        profiles.append(profile)
        print(
            f"  [OK] Extracted `profiles/{wallet[:14]}...json`: archetype={profile.archetype}, "
            f"lotto_threshold={profile.conviction_sizing.lotto_threshold_sol} SOL, "
            f"first_tp={profile.exit_signature.first_tp_multiple}x"
        )

    rules = await extractor.synthesize_autonomous_rules(profiles)
    await extractor.swarm_client.close()
    assert (WORKSPACE_ROOT / "profiles" / "autonomous_rules.json").exists()
    assert rules.consensus_frontrun_tp_factor == 0.90
    print("  [OK] Synthesized `profiles/autonomous_rules.json` across promoted sharks.")
    return profiles


def verify_step_3_burner_graph_and_bait_traversal(
    profiles: List[WalletProfile],
) -> BurnerGraph:
    print("\n[CHECK 3/5] Benchmarking `rustworkx` 3-Hop Burner Graph & <0.5ms `is_bait_trade()`...")
    graph = BurnerGraph()
    master_profile = profiles[0]
    master_wallet = master_profile.wallet
    graph.register_tracked_shark(master_wallet, master_profile)

    now_s = time.time()
    hop1_wallet = "BurnerHop1Wallet111111111111111111111111111"
    hop2_wallet = "BurnerHop2Wallet111111111111111111111111111"
    hop3_wallet = "BurnerHop3Wallet111111111111111111111111111"

    ev1 = graph.ingest_sol_transfer(
        master_wallet, hop1_wallet, 25.0, to_wallet_lifetime_txs=2, timestamp_s=now_s - 300
    )
    ev2 = graph.ingest_sol_transfer(
        hop1_wallet, hop2_wallet, 24.5, to_wallet_lifetime_txs=1, timestamp_s=now_s - 200
    )
    ev3 = graph.ingest_sol_transfer(
        hop2_wallet, hop3_wallet, 24.0, to_wallet_lifetime_txs=0, timestamp_s=now_s - 100
    )

    assert ev1 is not None and ev1.promoted_as_child_burner
    assert ev2 is not None and ev2.promoted_as_child_burner
    assert ev3 is not None and ev3.promoted_as_child_burner
    assert ev3.hop_distance == 3
    assert ev3.fast_bot_followers == 0
    assert ev3.priority_multiplier == 2.0

    # Populate 2,500 background nodes & edges to benchmark realistic cluster density
    for i in range(2500):
        w_a = f"ClusterNode{i:04d}11111111111111111111111111111"
        w_b = f"ClusterNode{(i + 1) % 2500:04d}1111111111111111111111111"
        graph.ingest_sol_transfer(w_a, w_b, 1.0, to_wallet_lifetime_txs=50, timestamp_s=now_s)

    # Record a bait token position on `hop3_wallet` (bought 10 minutes ago and holds 2.4% supply)
    bait_mint = "BaitTokenMint111111111111111111111111111111"
    clean_mint = "CleanTokenMint11111111111111111111111111111"
    graph.record_wallet_token_position(
        wallet=hop3_wallet,
        token_mint=bait_mint,
        supply_pct_held=2.4,
        buy_timestamp_s=now_s - 600,
    )

    latencies_ms: List[float] = []
    for _ in range(500):
        is_bait, lat_ms, reason = graph.is_bait_trade(master_wallet, bait_mint, now_s=now_s)
        assert is_bait is True and reason is not None
        latencies_ms.append(lat_ms)

        is_clean_bait, lat_clean_ms, _ = graph.is_bait_trade(
            master_wallet, clean_mint, now_s=now_s
        )
        assert is_clean_bait is False
        latencies_ms.append(lat_clean_ms)

    median_ms = statistics.median(latencies_ms)
    p99_ms = sorted(latencies_ms)[int(len(latencies_ms) * 0.99)]
    print(
        f"  [OK] 3-Hop Burner Graph (`is_bait_trade` across 1,000 traversals): "
        f"Median={median_ms:.5f} ms | P99={p99_ms:.5f} ms (Threshold: <0.50000 ms)"
    )
    assert median_ms < 0.5 and p99_ms < 0.5, f"is_bait_trade exceeded 0.5ms: p99={p99_ms:.5f}ms"
    graph.save_snapshot_to_ramdisk()
    return graph


def verify_step_4_phash_100k_bktree_benchmark() -> VisionScamFilter:
    print(
        "\n[CHECK 4/5] Benchmarking 100,000-Banner 64-Bit `pHash` BK-Tree (<0.3ms Vampire Detection)..."
    )
    vision_filter = VisionScamFilter()

    # Verify PIL Image perceptual hash computation via `imagehash.phash`
    img = Image.new("RGB", (64, 64), color=(20, 40, 80))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 54, 54], fill=(220, 180, 40))
    pil_phash_u64 = FastPhashBKTreeIndex.compute_pil_phash_u64(img)
    assert isinstance(pil_phash_u64, int) and pil_phash_u64 > 0

    # Populate 100,000 distinct 64-bit banner hashes
    rng = random.Random(42)
    target_original_mint = "OriginalIconMint111111111111111111111111111"
    target_original_hash = 0xF0E1D2C3B4A59687

    vision_filter.bktree.insert(target_original_mint, target_original_hash)
    for idx in range(99_999):
        h = rng.getrandbits(64)
        vision_filter.bktree.insert(f"HistMint{idx:06d}", h)

    assert vision_filter.bktree.size == 100_000

    # Mutate 4 bits (Hamming distance = 4 <= 6) to simulate a vampire clone banner
    vampire_hash = target_original_hash ^ 0b101101
    assert FastPhashBKTreeIndex.hamming_distance_u64(target_original_hash, vampire_hash) == 4

    lookup_latencies_ms: List[float] = []
    for i in range(200):
        res_vamp = vision_filter.bktree.query_vampire_clone(
            mint=f"VampireCloneMint{i:03d}",
            phash_u64=vampire_hash,
        )
        assert res_vamp.status == "VAMPIRE_CLONE"
        assert res_vamp.matched_older_mint == target_original_mint
        assert res_vamp.hamming_distance is not None and res_vamp.hamming_distance <= 6
        lookup_latencies_ms.append(res_vamp.lookup_latency_ms)

    median_lookup_ms = statistics.median(lookup_latencies_ms)
    avg_lookup_ms = statistics.mean(lookup_latencies_ms)
    print(
        f"  [OK] 100,000-Banner `pHash` BK-Tree Vampire Lookup: "
        f"Median={median_lookup_ms:.4f} ms | Mean={avg_lookup_ms:.4f} ms (Threshold: <0.3000 ms)"
    )
    assert median_lookup_ms < 0.3, (
        f"pHash lookup exceeded 0.3ms threshold: {median_lookup_ms:.4f}ms"
    )
    vision_filter.save_index_metadata()
    return vision_filter


def verify_step_5_sub2ms_shadow_executor(
    profiles: List[WalletProfile],
    burner_graph: BurnerGraph,
    vision_filter: VisionScamFilter,
) -> None:
    print(
        "\n[CHECK 5/5] Benchmarking Sub-2ms Two-Tranche Shadow Executor (`preconfSubscribe` -> Signed V0 Bundle)..."
    )
    pre_cache = BackgroundPreScorerCache(vision_filter=vision_filter)
    executor = ShadowExecutor(
        burner_graph=burner_graph,
        pre_scorer_cache=pre_cache,
        vision_filter=vision_filter,
    )

    master_profile = profiles[0]
    executor.register_shadow_wallet(master_profile)

    # Pre-approve a token in `/mnt/ramdisk/pre_approved_tokens` for Case A
    case_a_mint = "CaseAPreApprovedMint11111111111111111111111"
    case_b_mint = "CaseBUncachedMint11111111111111111111111111"
    executor.prewarm_token_accounts(case_a_mint)
    executor.prewarm_token_accounts(case_b_mint)

    pre_cache.put_state(
        PreApprovedTokenState(
            mint=case_a_mint,
            status="PRE_APPROVED",
            composite_score=0.93,
            phash_hex="1122334455667788",
            phash_status="CLEAN",
            recommended_slippage_bps=125,
            jito_tip_lamports=150_000,
            ttl_sec=120,
        )
    )

    clean_banner_hash = 0x0102030405060708  # Distinct from 100k random hashes
    case_a_latencies_ms: List[float] = []

    # Warmup
    warmup_ev = PreconfShadowEvent(
        master_wallet=master_profile.wallet,
        token_mint=case_a_mint,
        side="BUY",
        master_sol_spent=3.5,
        master_fill_price=0.00100,
        live_pool_price=0.00103,  # +3.0% <= +8.0% max drift
        banner_phash_u64=clean_banner_hash,
    )
    _ = executor.process_preconf_event_fast_path(warmup_ev, target_allocation_sol=2.0)

    # Benchmark 200 iterations of Case A (100% Pre-Approved Fast Path)
    for _ in range(200):
        dec_a = executor.process_preconf_event_fast_path(
            warmup_ev, target_allocation_sol=2.0
        )
        assert dec_a.accepted is True
        assert dec_a.case_type == "CASE_A_PRE_APPROVED_100PCT"
        assert dec_a.immediate_sol_dispatched == 2.0
        assert dec_a.signed_v0_tx is not None
        assert dec_a.signed_v0_tx.has_jito_dont_front_in_ix0 is True
        assert dec_a.signed_v0_tx.serialized_size_bytes < 1150
        case_a_latencies_ms.append(dec_a.hot_path_latency_ms)

    median_a_ms = statistics.median(case_a_latencies_ms)
    p99_a_ms = sorted(case_a_latencies_ms)[int(len(case_a_latencies_ms) * 0.99)]
    print(
        f"  [OK] Case A (100% Pre-Approved Zero-LLM Hot Path -> Signed V0 Bundle): "
        f"Median={median_a_ms:.4f} ms | P99={p99_a_ms:.4f} ms (Threshold: <2.0000 ms)"
    )
    assert median_a_ms < 2.0 and p99_a_ms < 2.0, (
        f"Case A hot path exceeded 2.0ms: p99={p99_a_ms:.4f}ms"
    )

    # Benchmark Case B (Uncached 0-Second Launch -> 25% Scout Tranche in <2.0ms)
    case_b_ev = PreconfShadowEvent(
        master_wallet=master_profile.wallet,
        token_mint=case_b_mint,
        side="BUY",
        master_sol_spent=4.0,
        master_fill_price=0.00200,
        live_pool_price=0.00210,  # +5.0% <= +8.0% max drift
        banner_phash_u64=clean_banner_hash ^ 0xFF00FF00FF00FF00,
    )
    dec_b = executor.process_preconf_event_fast_path(case_b_ev, target_allocation_sol=2.0)
    assert dec_b.accepted is True
    assert dec_b.case_type == "CASE_B_UNCACHED_SCOUT_25PCT"
    assert dec_b.immediate_sol_dispatched == 0.5  # 25% of 2.0 SOL
    assert dec_b.pending_conviction_sol == 1.5  # 75% of 2.0 SOL
    assert dec_b.hot_path_latency_ms < 2.0
    assert dec_b.signed_v0_tx is not None and dec_b.signed_v0_tx.has_jito_dont_front_in_ix0
    print(
        f"  [OK] Case B (25% Scout Tranche Signed V0 Bundle): {dec_b.hot_path_latency_ms:.4f} ms (<2.0ms) | "
        f"Scout={dec_b.immediate_sol_dispatched} SOL, Pending Conviction={dec_b.pending_conviction_sol} SOL"
    )

    # Verify Asymmetric Exit Front-Running (0.90 * first_tp_multiple & >=20% master bag dump)
    expected_frontrun_tp = round(
        0.90 * master_profile.exit_signature.first_tp_multiple, 4
    )
    assert dec_a.frontrun_tp_multiple == expected_frontrun_tp

    sell_ev = PreconfShadowEvent(
        master_wallet=master_profile.wallet,
        token_mint=case_a_mint,
        side="SELL",
        master_sol_spent=0.0,
        master_fill_price=0.00220,
        live_pool_price=0.00220,
        banner_phash_u64=clean_banner_hash,
        master_sell_fraction=0.25,  # Master sold 25% (>= 20% threshold)
    )
    exit_dec = executor.process_preconf_event_fast_path(sell_ev)
    assert exit_dec.accepted is True
    assert exit_dec.case_type == "ASYMMETRIC_EXIT_95TH_JITO"
    assert exit_dec.reclaimed_rent_lamports == ATA_RENT_LAMPORTS
    assert exit_dec.signed_v0_tx is not None
    assert exit_dec.signed_v0_tx.has_close_account_rent_reclaim is True
    assert exit_dec.hot_path_latency_ms < 2.0
    print(
        f"  [OK] Asymmetric Exit Front-Runner (Target={expected_frontrun_tp}x | Master >=20% Dump): "
        f"95th-Pct Jito Exit V0 Bundle + `close_account` (0.00203928 SOL) built in {exit_dec.hot_path_latency_ms:.4f} ms."
    )


async def main() -> int:
    print("==============================================================================")
    print("SOVEREIGN TITAN OS — PHASE 3 SHADOW EXECUTOR & ALPHA GRAPH VERIFICATION SUITE")
    print("==============================================================================")
    t_start = time.perf_counter()
    promoted_sharks = verify_step_1_duckdb_lead_lag_matrix()
    profiles = await verify_step_2_playbook_extractor(promoted_sharks)
    burner_graph = verify_step_3_burner_graph_and_bait_traversal(profiles)
    vision_filter = verify_step_4_phash_100k_bktree_benchmark()
    verify_step_5_sub2ms_shadow_executor(profiles, burner_graph, vision_filter)
    elapsed_s = time.perf_counter() - t_start
    print("\n==============================================================================")
    print(f"[PASS] 100% OF PHASE 3 SHADOW EXECUTOR BENCHMARKS PASSED IN {elapsed_s:.3f}s")
    print("==============================================================================")
    return 0


def test_phase3_shadow_executor_and_alpha_graph_suite() -> None:
    assert asyncio.run(main()) == 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

