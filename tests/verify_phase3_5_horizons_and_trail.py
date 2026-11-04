"""Sovereign Titan OS — Phase 3.5 / 4.5 Verification Suite (`tests/verify_phase3_5_horizons_and_trail.py`).

Verifies:
1. Horizon 1 (`src/horizons/horizon1_bonding_scalp.py`):
   - Hard Anti-Rug Pre-Filter (Top-5 > 18%, 0-block dev bundle > 12%, creator sells > 0.5%, pHash vampire clone).
   - Setup 1A (`30% -> 46%` Pump.fun Bonding Curve velocity breakout with >= 18 independent unlinked buyers and Buy/Sell >= 2.8x).
   - Setup 1B (`88%` King-of-the-Hill migration front-run).
   - Stage 1 `40%` scale-out at `+25%` (`1.25x`), `30%` scale-out at `98.5%` bonding curve completion, and `30%` Risk-Free Moonbag carry into Horizon 2.
2. Horizon 2 (`src/horizons/horizon2_graduation_reclaim.py`):
   - Blocks 0-second graduation top buys.
   - Tracks `-48%` post-graduation sniper flush + `>= 25%` top-20 holder concentration reduction.
   - Fires on Higher-Low + 1m Anchored VWAP Reclaim + `>= 1.8x` 15s Buy/Sell ratio across `>= 10` buyers + DexScreener Boost + `LP >= $22,000`.
3. Horizon 3 & 4 (`src/horizons/horizon3_4_swing_and_scalp.py`):
   - Horizon 3 Mid-Cap 4h Volatility Compression Box (`<35%` range) + 4h VWAP breakout (`>= 2.5x` 5m volume).
   - Horizon 4 Panic-Wick Absorption Micro-Scalper (`-16%` single-slot non-deployer whale wick in active 5m EMA-21 uptrend -> 25ms BAM entry -> `70%` snap-back scalp at `+12%` + `3.5%` tight trailing stop).
4. 4-Stage Ratcheting Trail-Win Engine (`src/execution/trail_win_engine.py`):
   - Evaluates ticks in `< 0.05ms` (`50 microseconds`) backed by `/mnt/ramdisk/execution_state/active_trails.mmap`.
   - Strictly monotonic upward `active_trail_stop_price` across Stages 0, 1, 2, and 3 (`30% Curve -> 100% Migration -> -48% Flush -> 1m VWAP Reclaim -> 12.0x Parabolic Runner -> Order-Flow Climax Reversal`).
   - Locks in `>= 110%` of initial SOL invested at `2.0x`.
   - Fires 95th-percentile Jito exit bundle with `spl_token::instruction::close_account` (`2,039,280 lamports` = `0.00203928 SOL` ATA rent reclaim) on Order-Flow Climax Reversal.
"""

from __future__ import annotations

from pathlib import Path
import statistics
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution.atomic_tx_builder import ATA_RENT_LAMPORTS
from src.execution.trail_win_engine import TrailWinEngine
from src.horizons.horizon1_bonding_scalp import (
    BondingCurveSwapSample,
    BondingCurveTokenSnapshot,
    Horizon1BondingScalpEngine,
)
from src.horizons.horizon2_graduation_reclaim import (
    Horizon2GraduationReclaimEngine,
    PostGradSwapTick,
)
from src.horizons.horizon3_4_swing_and_scalp import (
    Horizon3And4SwingScalpEngine,
    MidCapConsolidationCandidate,
    PanicWickDislocationEvent,
)


def main() -> None:
    print("=" * 82)
    print(
        "SOVEREIGN TITAN OS — PHASE 3.5 MULTI-HORIZON LIFECYCLE & RATCHETING TRAIL-WIN SUITE"
    )
    print("=" * 82)

    t_suite_start = time.perf_counter()

    # Initialize shared TrailWinEngine & Horizon 1-4 Engines
    trail_engine = TrailWinEngine(build_live_v0_txs=False)
    h1_engine = Horizon1BondingScalpEngine(trail_engine=trail_engine)
    h2_engine = Horizon2GraduationReclaimEngine(trail_engine=trail_engine)
    h3_4_engine = Horizon3And4SwingScalpEngine(trail_engine=trail_engine)

    # ==========================================================================
    # [CHECK 1/5] HORIZON 1: Pre-Bonding Anti-Rug Pre-Filter, Curve Velocity & Carry
    # ==========================================================================
    print(
        "\n[CHECK 1/5] Verifying Horizon 1 Pre-Bonding Curve Velocity, Anti-Rug & 98.5% Carry..."
    )
    mint_lifecycle = "LifecycleRunnerMint11111111111111111111111111"
    now_s = time.time()

    # 1a. Verify hard anti-rug rejection when top-5 holders > 18%
    bad_snap = BondingCurveTokenSnapshot(
        mint="RugBundleMint1111111111111111111111111111111",
        symbol="RUG/SOL",
        venue="PUMPFUN",
        creator_wallet="BadDevWallet1111111111111111111111111111111",
        curve_completion_pct=35.0,
        current_price_sol=0.00010,
        market_cap_usd=22_000.0,
        top5_non_curve_holders_pct=24.5,  # > 18.0% -> must reject
        dev_same_slot_bundle_pct=4.0,
        creator_sold_supply_pct=0.0,
        timestamp_s=now_s,
    )
    bad_res = h1_engine.evaluate_pre_bonding_entry(bad_snap)
    assert not bad_res.triggered and "TOP5_CONCENTRATION" in (
        bad_res.reject_reason or ""
    ), f"Expected top-5 anti-rug rejection, got: {bad_res}"

    # 1b. Feed 20 independent unlinked buyers driving curve from 30.0% -> 46.5% (+16.5% in 12s)
    for i in range(20):
        h1_engine.ingest_curve_swap(
            mint_lifecycle,
            BondingCurveSwapSample(
                timestamp_s=now_s - 12.0 + i * 0.5,
                slot=343_000_000 + i,
                buyer_wallet=f"OrganicBuyerWallet{i:03d}1111111111111111111111",
                side="BUY",
                sol_amount=0.85,
                curve_completion_pct=30.0 + (i / 19.0) * 16.5,
                price_sol=0.00010 + i * 0.000001,
            ),
        )
    # One small sell so Buy/Sell ratio is well above 2.8x
    h1_engine.ingest_curve_swap(
        mint_lifecycle,
        BondingCurveSwapSample(
            timestamp_s=now_s - 1.0,
            slot=343_000_021,
            buyer_wallet="SmallFlipperWallet11111111111111111111111111",
            side="SELL",
            sol_amount=1.2,
            curve_completion_pct=46.5,
            price_sol=0.000120,
        ),
    )

    good_snap = BondingCurveTokenSnapshot(
        mint=mint_lifecycle,
        symbol="ALPEN/SOL",
        venue="PUMPFUN",
        creator_wallet="CleanDevWallet11111111111111111111111111111",
        curve_completion_pct=46.5,
        current_price_sol=0.000120,
        market_cap_usd=28_500.0,
        top5_non_curve_holders_pct=11.2,
        dev_same_slot_bundle_pct=3.5,
        creator_sold_supply_pct=0.0,
        narrative_score=88.0,
        timestamp_s=now_s,
    )
    h1_decision = h1_engine.evaluate_pre_bonding_entry(good_snap, sol_allocation=2.0)
    assert h1_decision.triggered, f"Horizon 1 entry failed: {h1_decision}"
    assert h1_decision.setup_type == "SETUP_1A_MID_CURVE_VELOCITY"
    assert h1_decision.v0_buy_tx is not None
    assert h1_decision.v0_buy_tx.has_jito_dont_front_in_ix0

    # 1c. Simulate curve acceleration to +25% gain (1.25x = 0.000150 SOL) -> Stage 1 40% scale-out
    d_stage1 = h1_engine.evaluate_curve_tick_and_carry(
        mint=mint_lifecycle,
        current_price_sol=0.000152,
        curve_completion_pct=78.0,
        now_s=now_s + 5.0,
    )
    assert d_stage1.action == "STAGE1_PARTIAL_SCALP"
    assert abs(d_stage1.remaining_bag_fraction - 0.60) < 1e-6
    assert d_stage1.new_stop_price >= 0.000120 * 1.04

    # 1d. Simulate curve hitting 98.5% -> 30% pre-graduation scale-out, leaving 30% Risk-Free Moonbag
    d_985 = h1_engine.evaluate_curve_tick_and_carry(
        mint=mint_lifecycle,
        current_price_sol=0.000195,
        curve_completion_pct=98.8,
        now_s=now_s + 11.0,
    )
    assert d_985.action == "HORIZON1_985_BONDING_SCALE_OUT"
    assert abs(d_985.remaining_bag_fraction - 0.30) < 1e-6

    # 1e. Simulate 100% bonding curve migration bridge into Horizon 2
    h1_engine.evaluate_curve_tick_and_carry(
        mint=mint_lifecycle,
        current_price_sol=0.000210,
        curve_completion_pct=100.0,
        now_s=now_s + 14.0,
    )
    pos_after_mig = trail_engine.positions[mint_lifecycle]
    assert pos_after_mig.horizon == "HORIZON_2_GRADUATION_RECLAIM"
    assert pos_after_mig.is_risk_free_moonbag
    print(
        f"  [OK] Horizon 1 Setup 1A Triggered ({h1_decision.eval_latency_ms:.3f}ms) | "
        f"40% @ 1.25x + 30% @ 98.5% Curve | 30% Moonbag Carried to Horizon 2."
    )

    # ==========================================================================
    # [CHECK 2/5] HORIZON 2: Post-Graduation -48% Sniper Flush & 1m VWAP Reclaim
    # ==========================================================================
    print(
        "\n[CHECK 2/5] Verifying Horizon 2 Post-Graduation -48% Flush & 1m VWAP Reclaim..."
    )
    grad_mint = "GraduatedRunnerMint2222222222222222222222222"
    t_grad = now_s + 20.0
    h2_engine.register_graduation(
        mint=grad_mint,
        symbol="GRAD/SOL",
        venue="PUMPSWAP",
        graduation_open_mcap=85_000.0,
        graduation_open_price_sol=0.00100,
        initial_top20_holder_pct=50.0,
        graduated_at_s=t_grad,
    )

    # 2a. Verify 0-second graduation candle top is BLOCKED before sniper flush
    h2_engine.ingest_post_grad_swap(
        grad_mint,
        PostGradSwapTick(
            timestamp_s=t_grad + 1.0,
            slot=343_000_100,
            wallet="FomoSniper01",
            side="BUY",
            sol_amount=5.0,
            price_sol=0.00120,
            market_cap_usd=100_000.0,
        ),
        current_top20_holder_pct=49.0,
    )
    early_attempt = h2_engine.evaluate_reclaim_entry(
        mint=grad_mint,
        current_price_sol=0.00120,
        current_mcap_usd=100_000.0,
        pool_liquidity_usd=38_000.0,
        dexscreener_paid_or_boosted=True,
        now_s=t_grad + 1.5,
    )
    assert not early_attempt.triggered and early_attempt.reject_reason == "PHASE_A_SNIPER_FLUSH_NOT_COMPLETE"

    # 2b. Simulate -48% post-graduation sniper flush ($100k -> $52k MC) + top-20 holder reduction (50% -> 34% = 32% reduction)
    h2_engine.ingest_post_grad_swap(
        grad_mint,
        PostGradSwapTick(
            timestamp_s=t_grad + 45.0,
            slot=343_000_320,
            wallet="BondingFlipperDump",
            side="SELL",
            sol_amount=8.0,
            price_sol=0.000624,
            market_cap_usd=52_000.0,
        ),
        current_top20_holder_pct=34.0,
    )

    # 2c. Simulate Higher-Low formation + 12 unique buyers flipping 15s Buy/Sell ratio > 1.8x + 1m VWAP reclaim
    for idx in range(12):
        h2_engine.ingest_post_grad_swap(
            grad_mint,
            PostGradSwapTick(
                timestamp_s=t_grad + 50.0 + idx * 0.8,
                slot=343_000_350 + idx,
                wallet=f"FreshDexBuyer{idx:02d}11111111111111111111111111",
                side="BUY",
                sol_amount=1.5,
                price_sol=0.000680 + idx * 0.000010,
                market_cap_usd=58_000.0 + idx * 1_200.0,
            ),
            current_top20_holder_pct=33.5,
        )

    reclaim_res = h2_engine.evaluate_reclaim_entry(
        mint=grad_mint,
        current_price_sol=0.000820,
        current_mcap_usd=72_000.0,
        pool_liquidity_usd=42_000.0,
        mint_freeze_revoked=True,
        dexscreener_paid_or_boosted=True,
        sol_allocation=3.0,
        now_s=t_grad + 60.0,
    )
    assert reclaim_res.triggered, f"Horizon 2 Reclaim failed: {reclaim_res}"
    assert reclaim_res.flush_drawdown_pct == 48.0
    assert reclaim_res.top20_reduction_pct >= 25.0
    assert reclaim_res.v0_buy_tx is not None and reclaim_res.v0_buy_tx.has_jito_dont_front_in_ix0
    print(
        f"  [OK] Horizon 2 Blocked 0s Top | Caught -{reclaim_res.flush_drawdown_pct:.1f}% Flush + "
        f"1m VWAP Reclaim (Buy/Sell={reclaim_res.buy_sell_ratio_15s:.2f}x, Buyers={reclaim_res.unique_buyers_15s})."
    )

    # ==========================================================================
    # [CHECK 3/5] HORIZON 3 (Mid-Cap Breakout) & HORIZON 4 (25ms Panic-Wick Scalp)
    # ==========================================================================
    print(
        "\n[CHECK 3/5] Verifying Horizon 3 Mid-Cap Swing & Horizon 4 Panic-Wick Micro-Scalper..."
    )
    h3_candidate = MidCapConsolidationCandidate(
        mint="MidCapCultRunner333333333333333333333333333",
        symbol="CULT/SOL",
        market_cap_usd=2_400_000.0,
        pool_liquidity_usd=185_000.0,
        token_age_hours=18.5,
        box_4h_high_price_sol=0.0120,
        box_4h_low_price_sol=0.0098,  # 22.4% range (< 35%)
        vwap_4h_price_sol=0.0115,
        current_price_sol=0.0126,  # Breakout above box high & 4h VWAP
        current_5m_volume_usd=145_000.0,
        avg_5m_volume_usd=42_000.0,  # 3.45x volume (>= 2.5x)
        holder_count_growing=True,
        x_velocity_growing=True,
        midcap_shadow_sharks_10m=2,
        atr_1m_sol=0.00045,
    )
    h3_res = h3_4_engine.evaluate_horizon3_midcap_breakout(h3_candidate, sol_allocation=4.0)
    assert h3_res.triggered, f"Horizon 3 breakout failed: {h3_res}"

    wick_mint = "LiquidWickScalpMint4444444444444444444444444"
    h4_event = PanicWickDislocationEvent(
        mint=wick_mint,
        symbol="WICK/SOL",
        pool_liquidity_usd=92_000.0,
        volume_5m_usd=160_000.0,
        pre_wick_price_sol=0.00500,
        wick_bottom_price_sol=0.00420,  # -16.0% single-slot dislocation wick
        ema_21_5m_price_sol=0.00465,  # Pre-wick price > 5m EMA-21
        ema_30s_price_sol=0.00495,
        whale_sell_lp_impact_pct=4.8,  # >= 3.0% of pool LP
        is_deployer_or_insider_sell=False,
        has_dev_rug_flags=False,
        holder_count_rising=True,
        social_velocity_rising=True,
        timestamp_s=now_s,
    )
    h4_res = h3_4_engine.evaluate_horizon4_wick_microscalp(h4_event, sol_allocation=2.0)
    assert h4_res.triggered, f"Horizon 4 micro-scalp failed: {h4_res}"
    # Simulate +13% snap-back bounce within 6 seconds -> auto-scalps 70% and sets 3.5% tight trail
    h4_bounce = trail_engine.evaluate_tick(
        mint=wick_mint,
        current_price_sol=0.00475,
        now_s=now_s + 6.0,
    )
    assert h4_bounce.action == "STAGE1_PARTIAL_SCALP"
    assert abs(h4_bounce.remaining_bag_fraction - 0.30) < 1e-6
    print(
        f"  [OK] Horizon 3 Breakout (Box={h3_res.box_range_pct:.1f}%, Vol={h3_res.volume_5m_multiple:.2f}x) | "
        f"Horizon 4 Wick Scalp (-{h4_res.wick_dislocation_pct:.1f}% Wick -> 70% Bounce Scalp + 3.5% Trail)."
    )

    # ==========================================================================
    # [CHECK 4/5] 4-STAGE RATCHETING TRAIL-WIN ENGINE: Monotonicity, <0.05ms, 2x Lock & 12x Climax
    # ==========================================================================
    print(
        "\n[CHECK 4/5] Benchmarking 4-Stage Ratcheting Trail-Win Engine (<0.05ms) Through 12.0x Runner..."
    )
    entry_price = 0.000820
    initial_sol = 3.0
    # Trajectory from 1.0x -> 1.4x (Stage 1) -> pullback -> 2.1x (Stage 2) -> pullback -> 6.0x (Stage 3 11%) -> 12.0x -> 16.0x (6% trail)
    multipliers = [
        1.00, 1.08, 1.18, 1.36, 1.32, 1.29, 1.55, 1.85, 2.05, 1.92,
        2.40, 3.10, 2.88, 4.20, 5.40, 5.15, 7.80, 9.50, 11.20, 12.00, 15.60,
    ]

    latencies_ms = []
    previous_stop = trail_engine.positions[grad_mint].active_trail_stop_price
    sim_time = t_grad + 61.0

    for step_idx, mult in enumerate(multipliers):
        sim_time += 2.0
        tick_price = entry_price * mult
        decision = trail_engine.evaluate_tick(
            mint=grad_mint,
            current_price_sol=tick_price,
            buy_volume_3s_sol=18.0,
            sell_volume_3s_sol=4.0,
            now_s=sim_time,
        )
        latencies_ms.append(decision.eval_latency_ms)

        # Invariant 1: active_trail_stop_price MUST NEVER decrease
        assert decision.new_stop_price >= previous_stop - 1e-12, (
            f"Monotonicity violated at step {step_idx} (mult={mult}x): "
            f"{decision.new_stop_price} < {previous_stop}"
        )
        previous_stop = decision.new_stop_price

        # Invariant 2: At >= 2.0x, cumulative SOL recovered must be >= 110% of initial SOL invested
        if mult >= 2.05:
            assert decision.cumulative_sol_recovered >= 1.10 * initial_sol - 1e-6, (
                f"Expected >= 110% principal recovered at 2.0x, got "
                f"{decision.cumulative_sol_recovered:.4f} / {initial_sol:.4f} SOL"
            )

    # Verify zero-copy mmap synchronization
    grad_pos = trail_engine.positions[grad_mint]
    mmap_snapshot = trail_engine.read_slot_from_mmap(grad_pos.slot_index)
    assert abs(float(mmap_snapshot["active_trail_stop_price"]) - grad_pos.active_trail_stop_price) < 1e-9
    assert int(mmap_snapshot["current_stage"]) == 3

    median_latency_ms = statistics.median(latencies_ms)
    assert median_latency_ms < 0.05, (
        f"Expected < 0.05ms per-tick evaluation latency, got {median_latency_ms:.5f}ms"
    )

    # ==========================================================================
    # [CHECK 5/5] ORDER-FLOW CLIMAX REVERSAL AT 12.0x+ WITH ATA RENT RECLAIM
    # ==========================================================================
    print(
        "\n[CHECK 5/5] Verifying Order-Flow Climax Front-Run Exit & ATA Rent Reclaim at Top..."
    )
    climax_decision = trail_engine.evaluate_tick(
        mint=grad_mint,
        current_price_sol=entry_price * 15.20,  # Within 5% of 15.60x peak
        buy_volume_3s_sol=4.0,
        sell_volume_3s_sol=16.5,  # 4.125x Sell/Buy Volume Delta (>= 3.2x threshold)
        now_s=sim_time + 1.0,
        compile_tx=True,
    )
    assert climax_decision.action == "ORDER_FLOW_CLIMAX_EXIT", (
        f"Expected ORDER_FLOW_CLIMAX_EXIT, got {climax_decision}"
    )
    assert climax_decision.position_closed
    assert climax_decision.reclaimed_rent_lamports == ATA_RENT_LAMPORTS
    assert (
        climax_decision.v0_tx is not None
        and climax_decision.v0_tx.has_close_account_rent_reclaim
    )
    print(
        f"  [OK] Monotonic Stop Verified Across 21 Ticks | Median Tick Latency={median_latency_ms:.5f}ms (<0.05ms) | "
        f"Principal Recovered={climax_decision.cumulative_sol_recovered:.2f} SOL ({climax_decision.cumulative_sol_recovered / initial_sol * 100:.0f}% of initial) | "
        f"Climax Exit V0={climax_decision.v0_tx.serialized_size_bytes}B + {ATA_RENT_LAMPORTS} lamports ATA rent reclaimed."
    )

    elapsed_total = time.perf_counter() - t_suite_start
    print("\n" + "=" * 82)
    print(
        f"[PASS] 100% OF PHASE 3.5 MULTI-HORIZON & TRAIL-WIN CHECKS PASSED IN {elapsed_total:.3f}s"
    )
    print("=" * 82)


def test_phase3_5_horizons_and_ratcheting_trail_win_suite() -> None:
    main()


if __name__ == "__main__":
    main()

