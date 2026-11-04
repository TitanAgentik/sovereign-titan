#!/usr/bin/env python3
"""
Phase 7 Verification Suite: Sovereign Titan Zero-Loss Institutional Hardening Shields
=====================================================================================
Verifies all 6 Zero-Loss Hardening Modules & AGENTS.md Section 5 invariants:
  1. Module 1 (`LocalSvmRoundtripGuard`): <0.5ms Atomic Buy+Sell Roundtrip Honeypot & Tax Sim
  2. Module 2 (`SybilWashAuditor`): 45s Self-Churn + 3-Hop Ancestor Wash Stripper & 14% Cabal Cap
  3. Module 3 (`VelocityScratchGuard` & `BiDirectionalScaler`): 3.0s (15-Slot) Green-or-Scratch + ATA Rent Reclaim
  4. Module 4 (`HouseMoneyGovernor`): 0.35x Scout Start -> +1.0 SOL Full Unlock -> 55% Daily HWM Profit Floor
  5. Module 5 (`ExpectedValueTipGate`): >=3.5x Total Friction Coverage & <=28% Tip-to-EV Ratio Gate
  6. Module 6 (`DriftPerpHedger`): [OFF / 50% / 100%] 1x Short SOL-PERP Delta-Neutral USD Equity Lock
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT_DIR = Path("/home/titanagentik/sovereign-titan")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
for skill_dir in (
    ROOT_DIR / "hermes-skills" / "alpha-wallet-shadow",
    ROOT_DIR / "hermes-skills" / "solana-mev-titan",
    ROOT_DIR / "hermes-skills" / "sovereign-orchestrator",
):
    if str(skill_dir) not in sys.path:
        sys.path.insert(0, str(skill_dir))

from src.security.svm_roundtrip_guard import (
    LocalSvmRoundtripGuard,
    RoundtripSimulationInput,
)
from src.security.sybil_wash_auditor import (
    PoolSwapRecord,
    SybilWashAuditor,
    TokenHolderRecord,
)
from src.execution.velocity_scratch_guard import VelocityScratchGuard
from src.execution.bi_directional_scaler import BiDirectionalScaler
from src.risk.house_money_governor import HouseMoneyGovernor
from src.execution.ev_tip_gate import ExpectedValueTipGate
from src.vault.drift_perp_hedger import DriftPerpHedger


def verify_step_1_local_svm_roundtrip_honeypot_guard() -> None:
    print("\n[TEST 1/6] LocalSvmRoundtripGuard (<0.5ms Atomic Buy+Sell Roundtrip & Tax Sim)...")
    guard = LocalSvmRoundtripGuard()
    guard.blocked_mints.clear()
    guard.blocks_today = 0

    # 1. Clean token with 25 bps pool fee and 0% hidden tax
    latencies_ms = []
    clean_result = None
    for _ in range(50):
        res = guard.verify_atomic_roundtrip(
            RoundtripSimulationInput(
                token_mint="CleanMeme1111111111111111111111111111111111",
                amount_sol=1.5,
                pool_r_sol=250.0,
                pool_r_token=250_000_000.0,
                pool_fee_bps=25.0,
                simulated_sell_tax_bps=0.0,
            )
        )
        latencies_ms.append(res.latency_ms)
        clean_result = res

    median_lat_ms = statistics.median(latencies_ms)
    assert clean_result is not None and clean_result.passed, "Clean token must pass roundtrip guard"
    assert median_lat_ms < 0.5, f"Roundtrip simulation exceeded 0.5ms SLA: {median_lat_ms:.4f}ms"

    # 2. Hidden 15% sell tax hook -> must block as HIDDEN_HONEYPOT_OR_TAX_HOOK
    tax_trap = guard.verify_atomic_roundtrip(
        RoundtripSimulationInput(
            token_mint="TaxTrap222222222222222222222222222222222222",
            amount_sol=1.5,
            pool_r_sol=250.0,
            pool_r_token=250_000_000.0,
            pool_fee_bps=25.0,
            simulated_sell_tax_bps=1500.0,
        )
    )
    assert not tax_trap.passed, "15% hidden sell tax must be blocked"
    assert tax_trap.status_code == "HIDDEN_HONEYPOT_OR_TAX_HOOK"
    assert guard.is_token_blocked("TaxTrap222222222222222222222222222222222222")

    # 3. Delayed sell revert hook -> must block
    revert_trap = guard.verify_atomic_roundtrip(
        RoundtripSimulationInput(
            token_mint="RevertTrap333333333333333333333333333333333",
            amount_sol=1.5,
            pool_r_sol=250.0,
            pool_r_token=250_000_000.0,
            pool_fee_bps=25.0,
            simulated_sell_revert_err="InstructionError(1, Custom(6001))",
        )
    )
    assert not revert_trap.passed and revert_trap.status_code == "HIDDEN_HONEYPOT_OR_TAX_HOOK"

    # 4. Unauthorized CPI hook -> must block
    cpi_trap = guard.verify_atomic_roundtrip(
        RoundtripSimulationInput(
            token_mint="MaliciousCpi4444444444444444444444444444444",
            amount_sol=1.5,
            pool_r_sol=250.0,
            pool_r_token=250_000_000.0,
            pool_fee_bps=25.0,
            invoked_cpi_hook_program="ScamHook999999999999999999999999999999999999",
        )
    )
    assert not cpi_trap.passed and cpi_trap.status_code == "HIDDEN_HONEYPOT_OR_TAX_HOOK"

    bundle_payload = guard.build_simulate_bundle_payload()
    assert bundle_payload["method"] == "simulateBundle"
    assert bundle_payload["params"][1]["replaceRecentBlockhash"] is True

    print(
        f"  -> PASS: Clean Roundtrip={clean_result.actual_simulated_sol_out_tx2:.4f}/{clean_result.amount_sol_in:.4f} SOL | "
        f"Median Latency={median_lat_ms:.4f}ms (<0.5ms SLA) | Blocked Traps={guard.blocks_today}"
    )


def verify_step_2_sybil_wash_and_cabal_auditor() -> None:
    print("\n[TEST 2/6] SybilWashAuditor (45s Wash Stripper + 3-Hop Ancestor + 14% Cabal Ceiling)...")
    auditor = SybilWashAuditor()

    now = time.time()
    # Register a 3-hop shared ancestor cluster in burner_graph for Sybil wash wallets
    auditor.burner_graph.ingest_sol_transfer("CabalRootFunder111", "MidHopA", 25.0)
    auditor.burner_graph.ingest_sol_transfer("MidHopA", "SybilWasherA", 12.0)
    auditor.burner_graph.ingest_sol_transfer("CabalRootFunder111", "MidHopB", 25.0)
    auditor.burner_graph.ingest_sol_transfer("MidHopB", "SybilWasherB", 12.0)

    swaps = [
        # Self-churning wallet (bought and sold within 45s) -> 40 SOL fake buy + 39.5 SOL sell
        PoolSwapRecord(signer="SelfChurnBot1", side="BUY", amount_sol=40.0, timestamp_s=now - 20.0),
        PoolSwapRecord(signer="SelfChurnBot1", side="SELL", amount_sol=39.5, timestamp_s=now - 5.0),
        # 3-hop shared ancestor wash pair (SybilWasherA buys, SybilWasherB sells) -> 30 SOL fake buy
        PoolSwapRecord(signer="SybilWasherA", side="BUY", amount_sol=30.0, timestamp_s=now - 12.0),
        PoolSwapRecord(signer="SybilWasherB", side="SELL", amount_sol=5.0, timestamp_s=now - 10.0),
        # Genuine organic flow: 4 SOL buy vs 6 SOL sell (true organic ratio = 0.67x, raw ratio = 74 / 50.5 = 1.47x)
        PoolSwapRecord(signer="OrganicBuyer1", side="BUY", amount_sol=2.5, timestamp_s=now - 8.0),
        PoolSwapRecord(signer="OrganicBuyer2", side="BUY", amount_sol=1.5, timestamp_s=now - 4.0),
        PoolSwapRecord(signer="OrganicSeller1", side="SELL", amount_sol=6.0, timestamp_s=now - 3.0),
    ]

    vol_report = auditor.compute_organic_volume("WashToken111111111111111111111111111111111", swaps)
    assert vol_report.raw_buy_sell_ratio > 1.4, "Raw wash ratio should look artificially bullish"
    assert vol_report.organic_buy_sell_ratio < 0.70, "Stripped organic ratio must expose weak <0.70x real demand"
    assert vol_report.wash_volume_stripped_sol >= 110.0

    # Test Top-50 Holder Cabal Supply Ceiling (14.0% cap across 2-hop funder + slots [Mint, Mint+2])
    mint_slot = 398_500_000
    cabal_holders = [
        TokenHolderRecord("CabalWallet1", supply_pct=4.5, entry_slot=mint_slot, explicit_funder="GenesisCabalMaster"),
        TokenHolderRecord("CabalWallet2", supply_pct=4.2, entry_slot=mint_slot + 1, explicit_funder="GenesisCabalMaster"),
        TokenHolderRecord("CabalWallet3", supply_pct=3.8, entry_slot=mint_slot + 2, explicit_funder="GenesisCabalMaster"),
        TokenHolderRecord("CabalWallet4", supply_pct=3.1, entry_slot=mint_slot + 10, explicit_funder="GenesisCabalMaster"),
        TokenHolderRecord("OrganicHolder1", supply_pct=1.8, entry_slot=mint_slot + 45, explicit_funder="CoinbaseHotWallet"),
    ]
    cabal_audit = auditor.audit_token_holder_cabal(
        token_mint="BundledCabalToken22222222222222222222222222",
        holders=cabal_holders,
        mint_slot=mint_slot,
    )
    assert not cabal_audit.passed, "Cluster controlling >=14.0% supply must be blocked"
    assert cabal_audit.status_code == "CABAL_BUNDLED_SUPPLY_TRAP"
    assert cabal_audit.max_cluster_supply_pct >= 14.0

    print(
        f"  -> PASS: Raw Ratio={vol_report.raw_buy_sell_ratio:.2f}x -> Organic Ratio={vol_report.organic_buy_sell_ratio:.2f}x "
        f"(Stripped {vol_report.wash_volume_stripped_sol:.1f} SOL wash) | Cabal Cluster={cabal_audit.max_cluster_supply_pct:.2f}% BLOCKED"
    )


def verify_step_3_velocity_scratch_guard_and_bi_directional_scaler() -> None:
    print("\n[TEST 3/6] VelocityScratchGuard & BiDirectionalScaler (15-Slot / 3.0s Green-or-Scratch)...")
    scratch_guard = VelocityScratchGuard()
    scaler = BiDirectionalScaler(scratch_guard=scratch_guard)

    token_mint = "StagnantMeme1111111111111111111111111111111"
    entry_slot = 398_550_000
    scaler.register_position(
        token_mint=token_mint,
        entry_price_sol=0.000100,
        initial_sol_invested=1.0,
        horizon="HORIZON_1_CURVE_SCALP",
        entry_slot=entry_slot,
    )

    # Simulate 14 slots (2.8s) with weak organic flow (0.30 SOL < 1.20 SOL) and +0.6% MFE (< +1.8%)
    early_decision = scaler.evaluate_tick(
        token_mint=token_mint,
        current_price_sol=0.0001006,
        net_organic_buy_flow_sol_delta=0.30,
        elapsed_seconds=2.8,
        current_slot=entry_slot + 14,
    )
    assert early_decision.decision_source != "VELOCITY_SCRATCH_3S", (
        "Should wait until 15 Alpenglow slots (3.0s) before scratching"
    )

    # At Slot +15 (3.0s), price is flat (-0.2%) and net organic buy flow is 0.35 SOL (< 1.20 SOL required)
    scratch_decision = scaler.evaluate_tick(
        token_mint=token_mint,
        current_price_sol=0.0000998,
        net_organic_buy_flow_sol_delta=0.05,
        elapsed_seconds=3.0,
        current_slot=entry_slot + 15,
    )
    assert scratch_decision.decision_source == "VELOCITY_SCRATCH_3S"
    assert scratch_decision.action == "SCRATCH_EXIT_100PCT_WITH_RENT"
    assert scratch_decision.fraction_sold == 1.0
    assert scratch_decision.reclaimed_rent_lamports == 2_039_280
    assert scratch_decision.signed_v0_tx is not None

    print(
        f"  -> PASS: Fired {scratch_decision.action} at Slot +{scratch_decision.scratch_decision.slots_elapsed} "
        f"(MFE={scratch_decision.scratch_decision.max_favorable_excursion_pct:.2f}%, "
        f"NetBuy={scratch_decision.scratch_decision.net_organic_buy_flow_after_entry_sol:.2f} SOL) + "
        f"Reclaimed {scratch_decision.reclaimed_rent_lamports:,} lamports ATA rent"
    )


def verify_step_4_house_money_ratchet_governor() -> None:
    print("\n[TEST 4/6] HouseMoneyGovernor (0.35x Scout -> +1.0 SOL Full Size -> 55% HWM Floor)...")
    gov = HouseMoneyGovernor(
        state_path=Path("/mnt/ramdisk/test_house_money_state.json")
    )
    gov.set_daily_pnl_state(daily_realized_net_sol=0.0, daily_high_water_mark_pnl_sol=0.0)

    # 1. Start of UTC Day (0.0 SOL realized PnL): Phase 0 Conservative Scout
    snap0 = gov.get_status_snapshot()
    assert snap0.phase == "PHASE_0_CONSERVATIVE_SCOUT"
    assert abs(snap0.directional_sizing_multiplier - 0.35) < 1e-9
    assert snap0.min_required_confidence == 88.0
    assert snap0.engine_a_max_borrow_sol == 5000.0

    low_conf_eval = gov.evaluate_directional_entry(
        requested_size_sol=2.0,
        token_confidence_score=82.0,
    )
    assert not low_conf_eval["allowed"], "Confidence 82 must be rejected in Phase 0 (requires >=88)"

    high_conf_eval = gov.evaluate_directional_entry(
        requested_size_sol=2.0,
        token_confidence_score=91.0,
    )
    assert high_conf_eval["allowed"]
    assert abs(high_conf_eval["approved_size_sol"] - 0.70) < 1e-9, "2.0 SOL * 0.35x Scout = 0.70 SOL"

    # 2. Realize +1.2 SOL profit -> Unlocks Phase 1 (1.0x full size)
    snap1 = gov.record_realized_pnl_delta(1.2)
    assert snap1.phase == "PHASE_1_HOUSE_MONEY_UNLOCKED"
    assert abs(snap1.directional_sizing_multiplier - 1.0) < 1e-9

    # 3. Realize another +8.8 SOL -> Daily HWM hits +10.0 SOL (55% Floor = +5.50 SOL)
    snap_peak = gov.record_realized_pnl_delta(8.8)
    assert abs(snap_peak.daily_high_water_mark_pnl_sol - 10.0) < 1e-9
    assert abs(snap_peak.locked_daily_profit_floor_sol - 5.50) < 1e-9

    # 4. Pull back -4.55 SOL (Realized PnL = +5.45 SOL <= +5.50 SOL floor) -> Locks Floor for rest of UTC day
    snap_locked = gov.record_realized_pnl_delta(-4.55)
    assert snap_locked.phase == "DAILY_PROFIT_FLOOR_LOCKED_ARB_ONLY"
    assert snap_locked.directional_paused_for_day is True
    assert snap_locked.directional_sizing_multiplier == 0.0
    assert snap_locked.engine_a_flash_arb_allowed is True

    # Verify directional trade is blocked while Engine A Flash-Arb remains 100% active at 5,000 SOL
    dir_blocked = gov.evaluate_directional_entry(1.0, 95.0)
    assert not dir_blocked["allowed"]

    print(
        f"  -> PASS: Phase 0 (0.35x Scout) -> Phase 1 (+10.0 SOL HWM / +5.50 SOL Floor) -> "
        f"Floor Lock Paused Directional at +{snap_locked.daily_realized_net_sol:.2f} SOL while Engine A active at {snap_locked.engine_a_max_borrow_sol:.0f} SOL"
    )


def verify_step_5_ev_tip_gate() -> None:
    print("\n[TEST 5/6] ExpectedValueTipGate (>=3.5x Friction Coverage & <=28% Tip-to-EV Ratio)...")
    gate = ExpectedValueTipGate()

    # 1. Congested slot micro-scalp: 0.25 SOL size, +2.0% expected move (5,000,000 lamports EV),
    #    entry+exit Jito tips = 2,400,000 lamports (48% of EV -> must block)
    blocked = gate.evaluate_trade_ev(
        position_size_sol=0.25,
        expected_gain_pct=2.0,
        entry_jito_tip_lamports=1_200_000,
        estimated_exit_jito_tip_lamports=1_200_000,
        pool_fee_bps=25.0,
    )
    assert not blocked.passed
    assert blocked.status_code == "JITO_TIP_EXCEEDS_28PCT_EV_GATE"
    assert blocked.min_viable_position_sol > 0.25

    # 2. Institutional sizing or higher expected move: 1.5 SOL size, +4.5% expected move,
    #    entry+exit Jito tips = 1,000,000 lamports -> passes >=3.5x and <=28% tip-to-EV
    passed = gate.evaluate_trade_ev(
        position_size_sol=1.50,
        expected_gain_pct=4.5,
        entry_jito_tip_lamports=500_000,
        estimated_exit_jito_tip_lamports=500_000,
        pool_fee_bps=25.0,
    )
    assert passed.passed
    assert passed.ev_to_friction_multiple >= 3.5
    assert passed.tip_to_ev_ratio_pct <= 28.0

    print(
        f"  -> PASS: Blocked Micro-Scalp (Tip/EV={blocked.tip_to_ev_ratio_pct:.1f}%, MinViable={blocked.min_viable_position_sol:.3f} SOL) | "
        f"Approved Institutional Trade (Coverage={passed.ev_to_friction_multiple:.2f}x, Tip/EV={passed.tip_to_ev_ratio_pct:.1f}%)"
    )


def verify_step_6_drift_perp_delta_neutral_hedger() -> None:
    print("\n[TEST 6/6] DriftPerpHedger ([OFF / 50% / 100%] 1x Short SOL-PERP Delta-Neutral Hedge)...")
    hedger = DriftPerpHedger(
        state_path=Path("/mnt/ramdisk/test_drift_perp_hedge.json")
    )

    # Set 100% Delta-Neutral Hedge on 100 SOL vault at $188.40/SOL ($18,840 USD locked)
    state_100 = hedger.set_hedge_mode("100%", idle_treasury_sol=100.0, current_sol_usd=188.40)
    assert state_100.mode == "FULL_100PCT"
    assert abs(state_100.short_perp_notional_sol - 100.0) < 1e-9
    assert abs(state_100.locked_usd_value - 18_840.0) < 1e-2
    assert state_100.last_rebalance_v0_tx_bytes > 0

    # Simulate a -20% SOL flash crash and verify $0.00 USD drawdown on hedged equity
    crash_sim = hedger.simulate_sol_crash_usd_impact(sol_price_drop_pct=-20.0)
    assert abs(crash_sim["net_portfolio_pnl_usd"]) < 1e-6, (
        f"100% Drift SOL-PERP hedge must yield $0.00 USD drawdown, got {crash_sim['net_portfolio_pnl_usd']}"
    )
    assert crash_sim["spot_pnl_usd"] < -3700.0

    # Reset to OFF for default runtime state
    hedger.set_hedge_mode("OFF", idle_treasury_sol=100.0, current_sol_usd=188.40)

    print(
        f"  -> PASS: 100% Hedge Locked ${state_100.locked_usd_value:,.2f} USD via {state_100.drift_program_id[:10]}... | "
        f"-20% SOL Crash Unhedged={crash_sim['spot_pnl_usd']:,.2f} USD vs Hedged={crash_sim['net_portfolio_pnl_usd']:,.2f} USD"
    )


def main() -> int:
    print("=" * 88)
    print("SOVEREIGN TITAN OS — PHASE 7 ZERO-LOSS INSTITUTIONAL HARDENING VERIFICATION SUITE")
    print("=" * 88)
    t0 = time.perf_counter()

    verify_step_1_local_svm_roundtrip_honeypot_guard()
    verify_step_2_sybil_wash_and_cabal_auditor()
    verify_step_3_velocity_scratch_guard_and_bi_directional_scaler()
    verify_step_4_house_money_ratchet_governor()
    verify_step_5_ev_tip_gate()
    verify_step_6_drift_perp_delta_neutral_hedger()

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    print("\n" + "=" * 88)
    print(f"ALL 6/6 PHASE 7 ZERO-LOSS HARDENING TESTS PASSED IN {elapsed_ms:.2f}ms")
    print("=" * 88)
    return 0


def test_phase7_zero_loss_shields_suite() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
