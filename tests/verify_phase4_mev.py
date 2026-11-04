#!/usr/bin/env python3
"""Sovereign Titan OS — Phase 4 MEV Titan Triad, 2,000-Pool Mirror, Geo-Router & 25-Shard Verification Suite.

Validates and benchmarks:
1. In-Memory 2,000-Pool Reserve & Bin Mirror (`/mnt/ramdisk/mev_pool_mirror/pools_2000.mmap`)
   and `find_optimal_arb_size()` across 2,000 simulated pools (`< 0.05ms` per pair).
2. Engine A (`src/engines/engine_a_backrunner.py`): `<0.05ms` sibling pool recompute,
   `135,000 CU` limit, `58%` Jito tip / `42%` net profit split, `3–5ms` pre-BAM-tick release
   alignment, and Kamino Flash-Loan + Anchor `ProfitGuard` V0 transaction (`< 1,150 bytes`).
3. Engine B (`src/engines/engine_b_wide_sandwich.py`) Trigger 1 (Slow Copy-Herd Wave),
   Trigger 2 (Multi-Clip Whale TWAP), 4-condition Back-Leg Unwind (`+4% to +15%` spread,
   `>=60%` follower quorum, `8-slot / 1.6s` time-stop, emergency whale sell) + Engine C
   (`src/engines/engine_c_jit_dlmm.py`) 3-bin `SpotBalanced` JIT & `+100 SOL` safety lock.
4. 25ms BAM & Leader-Schedule Geographical Fan-Out Router (`src/network/network_geo_router.py`).
5. 25-Wallet Stealth Ring-Buffer (`AES-256-GCM` at `~/.hermes/skills/solana-mev-titan/.keystore.enc`
   pinned via `mlock`), 8–10 trade rotation, and Hourly Counter-Copy Self-Audit via `discovery_lead_lag.py`.
"""

from __future__ import annotations

import asyncio
import statistics
import sys
import time
from pathlib import Path
from typing import List

WORKSPACE_ROOT = Path("/home/titanagentik/sovereign-titan")
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.discovery.discovery_lead_lag import SwapObservationRecord
from src.engines.engine_a_backrunner import (
    EXACT_2HOP_COMPUTE_UNITS,
    EngineABackrunner,
)
from src.engines.engine_b_wide_sandwich import (
    CrowdedWhaleProfile,
    EngineBWideSandwich,
    WhaleClipObservation,
)
from src.engines.engine_c_jit_dlmm import (
    DLMMJitCandidatePool,
    EngineCJitDLMM,
)
from src.execution.atomic_tx_builder import ATA_RENT_LAMPORTS
from src.mirror.pool_state_mirror import (
    DEXVenue,
    PoolReserveState,
    PoolStateMirror,
    find_optimal_arb_size,
)
from src.network.network_geo_router import NetworkGeoRouter
from src.security.stealth_sharding import StealthShardRingManager


def verify_step_1_2000_pool_mirror_and_arb_benchmark() -> PoolStateMirror:
    print(
        "\n[CHECK 1/5] Benchmarking 2,000-Pool Zero-Copy Mirror & `find_optimal_arb_size()` (<0.05ms/pair)..."
    )
    mirror = PoolStateMirror()
    venues: List[DEXVenue] = [
        "RAYDIUM_AMM_V4",
        "RAYDIUM_CPMM",
        "METEORA_DYNAMIC_AMM",
        "PUMPSWAP",
        "METEORA_DLMM",
        "RAYDIUM_CLMM",
        "ORCA_WHIRLPOOL",
    ]

    pair_pools: List[tuple[PoolReserveState, PoolReserveState]] = []

    # Populate 2,000 pools across 1,000 token mints (2 venues per mint)
    for mint_idx in range(1_000):
        mint_addr = f"MirrorMint{mint_idx:04d}111111111111111111111111111111"
        v_a = venues[mint_idx % 4]  # CPMM venue
        v_b = venues[(mint_idx + 1) % 4]  # Sibling CPMM venue

        pool_a = PoolReserveState(
            pool_address=f"PoolA{mint_idx:04d}111111111111111111111111111111111",
            token_mint=mint_addr,
            venue=v_a,
            pool_type="CPMM",
            r_sol=250.0 + (mint_idx % 100),
            r_token=10_000_000.0,
            fee_bps=25.0,
        )
        # Dislocate sibling pool B by +4.5% so optimal arbitrage exists
        pool_b = PoolReserveState(
            pool_address=f"PoolB{mint_idx:04d}111111111111111111111111111111111",
            token_mint=mint_addr,
            venue=v_b,
            pool_type="CPMM",
            r_sol=(250.0 + (mint_idx % 100)) * 1.045,
            r_token=10_000_000.0,
            fee_bps=25.0,
        )
        mirror.upsert_pool(pool_a)
        mirror.upsert_pool(pool_b)
        pair_pools.append((pool_a, pool_b))

    assert len(mirror.pools_by_address) == 2_000
    unpacked = mirror.read_mmap_slot(0)
    assert unpacked[2] == pair_pools[0][0].r_sol

    # Benchmark `find_optimal_arb_size()` across all 1,000 pairs (2,000 pools)
    latencies_ms: List[float] = []
    profitable_count = 0
    for p_a, p_b in pair_pools:
        t0 = time.perf_counter()
        res = find_optimal_arb_size(p_a, p_b)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        if res.profitable:
            profitable_count += 1

    # Also test DLMM/CLMM active bin-walking arbitrage
    dlmm_pool = PoolReserveState(
        pool_address="DlmmPool11111111111111111111111111111111111",
        token_mint="MirrorMint000011111111111111111111111111",
        venue="METEORA_DLMM",
        pool_type="DLMM_CLMM",
        r_sol=300.0,
        r_token=10_000_000.0,
        fee_bps=20.0,
        active_bin_id=100,
        bin_liquidity_map={
            100 - k: (500_000.0, 0.000033 * (1.0 - k * 0.002)) for k in range(12)
        },
    )
    bin_arb = find_optimal_arb_size(pair_pools[0][0], dlmm_pool)
    assert bin_arb.compute_latency_ms < 0.05

    median_ms = statistics.median(latencies_ms)
    mean_ms = statistics.mean(latencies_ms)
    p99_ms = sorted(latencies_ms)[int(len(latencies_ms) * 0.99)]
    print(
        f"  [OK] 2,000-Pool Mirror (`find_optimal_arb_size` across 1,000 pairs): "
        f"Median={median_ms:.5f} ms | Mean={mean_ms:.5f} ms | P99={p99_ms:.5f} ms "
        f"(Threshold: <0.05000 ms | Profitable={profitable_count}/1,000)"
    )
    assert median_ms < 0.05 and mean_ms < 0.05, (
        f"find_optimal_arb_size exceeded 0.05ms: mean={mean_ms:.5f}ms"
    )
    return mirror


def verify_step_2_engine_a_backrunner(mirror: PoolStateMirror) -> None:
    print(
        "\n[CHECK 2/5] Verifying Engine A (Flash-Loan Cross-DEX Back-Runner & 25ms BAM Alignment)..."
    )
    engine_a = EngineABackrunner(mirror=mirror)
    target_mint = f"MirrorMint{1:04d}111111111111111111111111111111"
    engine_a.prewarm_mint_ata(target_mint)

    # Simulate a whale swap shred on PoolB0001 pushing its SOL reserve up by +18%
    shred_update = PoolReserveState(
        pool_address=f"PoolB{1:04d}111111111111111111111111111111111",
        token_mint=target_mint,
        venue="RAYDIUM_CPMM",
        pool_type="CPMM",
        r_sol=315.0,
        r_token=8_600_000.0,
        fee_bps=25.0,
    )

    # Benchmark recompute latency first (without V0 compilation overhead)
    fast_res = engine_a.on_pool_shred_update(shred_update, build_v0_tx=False)
    assert fast_res.recompute_latency_ms < 0.05, (
        f"Engine A sibling recompute took {fast_res.recompute_latency_ms:.5f}ms (>0.05ms)"
    )

    # Full execution with Kamino Flash-Loan + ProfitGuard V0 compilation
    res = engine_a.on_pool_shred_update(shred_update, build_v0_tx=True)
    assert res.triggered is True
    assert res.net_ev_lamports > 500_000
    assert res.exact_compute_units == EXACT_2HOP_COMPUTE_UNITS  # 135,000 CU
    assert res.jito_tip_lamports == int(res.net_ev_lamports * 0.58)
    assert res.retained_net_profit_lamports == res.net_ev_lamports - res.jito_tip_lamports
    assert 3.0 <= res.bam_lead_before_boundary_ms <= 5.0
    assert res.v0_transaction is not None
    assert res.v0_transaction.serialized_size_bytes < 1150

    print(
        f"  [OK] Engine A Triggered: Recompute={fast_res.recompute_latency_ms:.5f} ms (<0.05ms) | "
        f"Net EV={res.net_ev_lamports / 1e9:.4f} SOL | Jito Tip (58%)={res.jito_tip_lamports / 1e9:.4f} SOL | "
        f"CU={res.exact_compute_units} | Pre-BAM Lead={res.bam_lead_before_boundary_ms:.1f}ms | "
        f"V0 Tx={res.v0_transaction.serialized_size_bytes}B"
    )


def verify_step_3_engine_b_and_engine_c() -> None:
    print(
        "\n[CHECK 3/5] Verifying Engine B (Wide-Sandwich & TWAP) & Engine C (DLMM JIT +100 SOL Lock)..."
    )
    engine_b = EngineBWideSandwich()
    bait_whale = "CrowdedBaitWhale111111111111111111111111111"
    engine_b.register_crowded_bait_whale(
        CrowdedWhaleProfile(
            wallet=bait_whale,
            slow_retail_followers=18,  # >= 15
            fast_bot_followers=2,  # <= 3
            expected_herd_price_impact_pct=8.4,  # >= 6.5%
        )
    )

    now_s = time.time()
    base_slot = 310_010_000
    mint_herd = "HerdWaveMint1111111111111111111111111111111"

    # 1. Trigger 1: Slow Copy-Herd Wave
    trig1 = engine_b.evaluate_crowded_whale_buy(
        whale_wallet=bait_whale,
        token_mint=mint_herd,
        pool_lp_usd=95_000.0,  # Within [$15k, $350k]
        entry_price=0.00100,
        current_slot=base_slot,
        front_leg_sol=4.0,
        target_spread_pct=6.5,
        now_s=now_s,
    )
    assert trig1.triggered is True
    assert trig1.trigger_type == "TRIGGER_1_SLOW_COPY_HERD"
    assert trig1.front_leg_slot == base_slot + 1
    assert trig1.max_hold_until_slot == base_slot + 8
    assert trig1.front_leg_v0_tx is not None
    assert trig1.front_leg_v0_tx.has_jito_dont_front_in_ix0 is True

    # Unwind via >= 60% follower quorum at Slot N+4 (0.8s)
    unwind1 = engine_b.evaluate_back_leg_unwind(
        token_mint=mint_herd,
        current_price=0.00105,
        completed_followers=12,  # 12/18 = 66.7% >= 60%
        current_slot=base_slot + 4,
        current_time_s=now_s + 0.80,
    )
    assert unwind1.should_unwind is True
    assert unwind1.new_state == "UNWOUND_FOLLOWER_QUORUM_60PCT"
    assert unwind1.reclaimed_rent_lamports == ATA_RENT_LAMPORTS
    assert unwind1.back_leg_v0_tx is not None
    assert unwind1.back_leg_v0_tx.has_close_account_rent_reclaim is True
    print(
        f"  [OK] Engine B Trigger 1 (Slow Copy-Herd): Front-Leg at Slot N+1 (`jitodontfront`) -> "
        f"Unwound at Slot N+4 ({unwind1.follower_completion_ratio * 100:.1f}% follower quorum) + 0.00203928 SOL rent reclaim."
    )

    # 2. Trigger 2: Multi-Clip Whale TWAP (>100 SOL wallet, 2 identical clips within 2-10s, >=40 SOL liquid)
    twap_whale = "TwapAccumulatorWhale11111111111111111111111"
    mint_twap = "TwapTargetMint11111111111111111111111111111"
    clip1 = WhaleClipObservation(
        wallet=twap_whale,
        token_mint=mint_twap,
        clip_sol=20.0,
        wallet_total_sol_balance=110.0,  # Initial 130 SOL > 100 SOL
        timestamp_s=now_s,
        slot=base_slot + 10,
    )
    clip2 = WhaleClipObservation(
        wallet=twap_whale,
        token_mint=mint_twap,
        clip_sol=20.0,  # Identical clip
        wallet_total_sol_balance=90.0,  # >= 40 SOL remaining liquid
        timestamp_s=now_s + 4.5,  # Within [2s, 10s]
        slot=base_slot + 32,
    )
    res_clip1 = engine_b.observe_whale_twap_clip(clip1)
    assert res_clip1.triggered is False
    res_clip2 = engine_b.observe_whale_twap_clip(clip2)
    assert res_clip2.triggered is True
    assert res_clip2.trigger_type == "TRIGGER_2_MULTI_CLIP_TWAP"

    # Test Hard 8-Slot (1.6s Alpenglow) Time-Stop Unwind on TWAP position
    unwind_twap = engine_b.evaluate_back_leg_unwind(
        token_mint=mint_twap,
        current_price=0.00102,
        completed_followers=0,
        current_slot=base_slot + 32 + 8,  # 8 slots elapsed (1.6s)
        current_time_s=now_s + 4.5 + 1.60,
    )
    assert unwind_twap.should_unwind is True
    assert unwind_twap.new_state == "UNWOUND_TIME_STOP_8_SLOTS"
    print(
        "  [OK] Engine B Trigger 2 (Multi-Clip TWAP): Detected Clip #1 & #2 (20 SOL, 4.5s delta) -> "
        "Verified 8-slot (1.6s Alpenglow) hard time-stop unwind."
    )

    # 3. Engine C: Meteora DLMM 3-Bin JIT Fee Harvester & +100 SOL Safety Gate
    engine_c = EngineCJitDLMM()
    assert engine_c.effective_execution_mode == "PAPER_SIM"

    # Record +95 SOL profit (still < +100 SOL threshold -> must remain PAPER_SIM)
    engine_c.record_realized_vault_profit(
        engine_a_profit_sol=40.0, engine_b_profit_sol=30.0, shadow_profit_sol=25.0
    )
    assert engine_c.effective_execution_mode == "PAPER_SIM"

    dlmm_candidate = DLMMJitCandidatePool(
        pool_address="MeteoraDlmmPool1111111111111111111111111111",
        token_mint="DlmmHotMint11111111111111111111111111111111",
        active_bin_id=420,
        tvl_usd=50_000.0,
        volume_1m_usd=95_000.0,  # 1.9x > 1.5x Vol/TVL
        dynamic_fee_bps=185.0,  # > 150 bps
    )
    bundle_paper = engine_c.evaluate_dlmm_pool_entry(dlmm_candidate, now_s=now_s)
    assert bundle_paper is not None
    assert bundle_paper.execution_mode == "PAPER_SIM"
    assert bundle_paper.bins == (419, 420, 421)
    assert bundle_paper.strategy_type == "SpotBalanced"

    # Now add +10 SOL profit (total +105 SOL >= +100 SOL) -> unlocks LIVE_UNLOCKED
    engine_c.record_realized_vault_profit(engine_a_profit_sol=10.0)
    assert engine_c.effective_execution_mode == "LIVE_UNLOCKED"

    # Verify -35% volume velocity drop exit trigger
    should_exit, exit_reason = engine_c.should_burn_and_exit_lp(
        bundle_paper, current_volume_1m_usd=55_000.0, current_time_s=now_s + 30.0
    )
    assert should_exit is True and exit_reason is not None
    print(
        f"  [OK] Engine C (Meteora DLMM 3-Bin `SpotBalanced` JIT): Enforced `PAPER_SIM` at +95 SOL, "
        f"unlocked `LIVE_UNLOCKED` at +105 SOL, and verified -35% velocity drop exit."
    )


async def verify_step_4_network_geo_router() -> None:
    print(
        "\n[CHECK 4/5] Verifying 25ms BAM & Leader-Schedule Geographical Fan-Out Router..."
    )
    router = NetworkGeoRouter()
    schedule_file = router.populate_leader_schedule(base_slot=310_000_000, num_slots=32)
    assert schedule_file.exists()

    receipt = await router.dispatch_simultaneous_fanout(
        signed_tx_bytes=b"\x01" * 512,
        current_slot=310_000_000,
        live_network_send=False,
    )
    await router.close()
    assert receipt.dispatch_completed_hw_ns >= receipt.dispatch_started_hw_ns
    assert "helius_sender" in receipt.dispatched_endpoints
    assert "jito_ny" in receipt.dispatched_endpoints
    assert "jito_frankfurt" in receipt.dispatched_endpoints
    assert "jito_amsterdam" in receipt.dispatched_endpoints
    assert "jito_tokyo" in receipt.dispatched_endpoints
    assert "astralane" in receipt.dispatched_endpoints
    print(
        f"  [OK] Geo-Router Fan-Out across {len(receipt.dispatched_endpoints)} endpoints "
        f"(Leader={receipt.current_leader_region} -> Next={receipt.next_leader_region}) "
        f"logged in {receipt.fanout_latency_us:.2f} us."
    )


def verify_step_5_stealth_sharding_and_self_audit() -> None:
    print(
        "\n[CHECK 5/5] Verifying 25-Wallet AES-256-GCM Stealth Ring-Buffer (`mlock`) & Hourly Self-Audit..."
    )
    mgr = StealthShardRingManager()
    keystore_file = mgr.initialize_and_encrypt_keystore()
    assert keystore_file.exists()
    assert len(mgr.shards) == 25

    # Reload and decrypt from `~/.hermes/skills/solana-mev-titan/.keystore.enc`
    mgr.load_and_decrypt_keystore()
    assert len(mgr.shards) == 25
    assert mgr.mlock_active is True

    # Simulate 10 profitable directional trades to trigger automatic 8-10 trade shard rotation
    rotation_ev = None
    for _ in range(10):
        ev = mgr.record_profitable_directional_trade(profit_sol=0.15)
        if ev is not None:
            rotation_ev = ev
            break

    assert rotation_ev is not None
    assert rotation_ev.reason == "TRADE_COUNT_ROTATION_8_TO_10"
    assert len(rotation_ev.hop_splits_sol) == 3

    # Simulate Hourly Counter-Copy Self-Audit where shard #3 has picked up 2 external copy-bots
    compromised_candidate_pubkey = mgr.shards[3].pubkey
    swaps: List[SwapObservationRecord] = []
    tid = 1
    for i in range(20):
        slot = 310_500_000 + (i * 200)
        mint = f"AuditMint{i:02d}11111111111111111111111111111111"
        swaps.append(
            SwapObservationRecord(
                trade_id=tid,
                mint=mint,
                wallet=compromised_candidate_pubkey,
                slot=slot,
                mint_creation_slot=slot - 30,
                sol_amount=1.0,
                pool_sol_reserve=100.0,
                entry_mc_usd=85_000.0,
            )
        )
        tid += 1
        # 2 external copy-bots following shard #3 within 1-2 slots
        for b_idx in range(2):
            swaps.append(
                SwapObservationRecord(
                    trade_id=tid,
                    mint=mint,
                    wallet=f"ExternalCopyBot{b_idx}111111111111111111111111111",
                    slot=slot + 1 + b_idx,
                    mint_creation_slot=slot - 30,
                    sol_amount=0.8,
                    pool_sol_reserve=100.0,
                    entry_mc_usd=86_000.0,
                )
            )
            tid += 1

    audit_report = mgr.run_hourly_counter_copy_self_audit(
        swap_observations=swaps, flag_as_counter_bait=True
    )
    assert compromised_candidate_pubkey in audit_report.compromised_shards
    assert compromised_candidate_pubkey in audit_report.counter_bait_wallets
    assert mgr.shards[3].pubkey != compromised_candidate_pubkey
    assert mgr.shards[3].status == "ACTIVE"
    print(
        f"  [OK] 25-Shard AES-256-GCM Keyring (`mlock={mgr.mlock_active}`) verified: "
        f"Rotated Shard 0->1 after {rotation_ev.old_shard_index + 8} trades; "
        f"Self-Audit detected 2 copy-bots on Shard 3 ({compromised_candidate_pubkey[:10]}...), "
        f"flagged as COUNTER_BAIT_WALLET, and swept SOL to fresh keypair ({mgr.shards[3].pubkey[:10]}...)."
    )


async def main() -> int:
    print("==============================================================================")
    print("SOVEREIGN TITAN OS — PHASE 4 MEV TITAN TRIAD & STEALTH SHARDING SUITE")
    print("==============================================================================")
    t_start = time.perf_counter()
    mirror = verify_step_1_2000_pool_mirror_and_arb_benchmark()
    try:
        verify_step_2_engine_a_backrunner(mirror)
        verify_step_3_engine_b_and_engine_c()
        await verify_step_4_network_geo_router()
        verify_step_5_stealth_sharding_and_self_audit()
    finally:
        mirror.close()
    elapsed_s = time.perf_counter() - t_start
    print("\n==============================================================================")
    print(f"[PASS] 100% OF PHASE 4 MEV TITAN CHECKS PASSED IN {elapsed_s:.3f}s")
    print("==============================================================================")
    return 0


def test_phase4_mev_triad_and_stealth_sharding_suite() -> None:
    assert asyncio.run(main()) == 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

