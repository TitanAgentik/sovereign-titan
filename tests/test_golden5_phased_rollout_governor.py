"""Pytest verification suite for The "Golden 5" 3-Step Phased Profit Rollout Governor & House-Money Gatekeeper
(`src/execution/golden5_phased_rollout_governor.py` & `TitanIPCDaemon` integration).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution import (
    APPROVED_STEP2_LATE_CURVE_HOUSE_MONEY_SQUEEZE,
    BLOCKED_BY_STEP1_ZERO_PRINCIPAL_RISK_GATE,
    BLOCKED_BY_STEP2_LATE_CURVE_4SHIELD_GATE,
    DEFAULT_STEP2_UNLOCK_PROFIT_SOL,
    DEFAULT_STEP3_UNLOCK_PROFIT_SOL,
    GOLDEN_5_PLAYBOOK_MANIFEST,
    Golden5PhasedRolloutGovernor,
    Golden5RolloutStep,
    MAX_DIRECTIONAL_HOUSE_PROFIT_DRAWDOWN_PCT,
    STEP_1_ZERO_PRINCIPAL_RISK,
    STEP_2_LATE_CURVE_SQUEEZE,
    STEP_3_HOMERUN_HUNTERS_MANIFEST,
    STEP_3_HOUSE_MONEY_HOMERUN,
    evaluate_step2_late_curve_gate,
)
from src.ipc.titan_ipc_daemon import TitanIPCDaemon


def test_golden5_enum_constants_and_manifest() -> None:
    """Verifies the 3-step rollout enum, thresholds, and Golden 5 + 3 Home-Run manifests."""
    assert Golden5RolloutStep.STEP_1_ZERO_PRINCIPAL_RISK.value == "STEP_1_ZERO_PRINCIPAL_RISK"
    assert Golden5RolloutStep.STEP_2_LATE_CURVE_SQUEEZE.value == "STEP_2_LATE_CURVE_SQUEEZE"
    assert Golden5RolloutStep.STEP_3_HOUSE_MONEY_HOMERUN.value == "STEP_3_HOUSE_MONEY_HOMERUN"
    assert DEFAULT_STEP2_UNLOCK_PROFIT_SOL == 5.0
    assert DEFAULT_STEP3_UNLOCK_PROFIT_SOL == 15.0
    assert MAX_DIRECTIONAL_HOUSE_PROFIT_DRAWDOWN_PCT == 30.0
    assert len(GOLDEN_5_PLAYBOOK_MANIFEST) == 5
    assert len(STEP_3_HOMERUN_HUNTERS_MANIFEST) == 3
    for play in GOLDEN_5_PLAYBOOK_MANIFEST:
        assert play["principal_at_risk_sol"] == 0.0


def test_step1_zero_principal_risk_hard_blocks_directional_entries() -> None:
    """Verifies Step 1 hard-blocks any directional memecoin entry with BLOCKED_BY_STEP1_ZERO_PRINCIPAL_RISK_GATE."""
    gov = Golden5PhasedRolloutGovernor()
    assert gov.current_step == STEP_1_ZERO_PRINCIPAL_RISK
    assert gov.principal_risk_allowed_sol == 0.0

    decision = gov.evaluate_step2_late_curve_gate(
        curve_completion_pct=72.0,
        six_gate_firewall_passed=True,
        single_cluster_supply_pct=15.0,
        tarjan_scc_organic_passed=True,
        organic_volume_ratio=0.80,
        salmonella_fot_shield_passed=True,
        requested_sol=1.5,
    )
    assert decision.approved is False
    assert decision.verdict == BLOCKED_BY_STEP1_ZERO_PRINCIPAL_RISK_GATE
    assert decision.house_profit_allocated_sol == 0.0
    assert decision.principal_at_risk_sol == 0.0
    assert gov.step1_directional_blocks_count == 1


def test_step1_zero_risk_flash_stack_and_auto_promotion() -> None:
    """Verifies Step 1 executes all 4 risk-free flash groups and auto-promotes to Step 2 at >= 5.0 SOL."""
    gov = Golden5PhasedRolloutGovernor(
        initial_step=STEP_1_ZERO_PRINCIPAL_RISK,
        step2_unlock_profit_sol=5.0,
        step3_unlock_profit_sol=15.0,
        auto_progression_enabled=True,
    )
    res = gov.execute_step1_zero_risk_flash_stack()
    assert res["step_executed"] == STEP_1_ZERO_PRINCIPAL_RISK
    assert res["principal_at_risk_sol"] == 0.0
    assert res["overnight_memecoin_holding_sol"] == 0.0
    assert res["play1_engine_a_and_sanctum_lst_arb"]["combined_profit_sol"] > 0.0
    assert res["play2_buyback_crank_and_flash_liquidator"]["combined_profit_sol"] > 0.0
    assert (
        25.0
        <= res["play3_jito_5tx_superbundle_combiner"]["auction_win_rate_boost_pct"]
        <= 40.0
    )
    assert res["play4_delta_neutral_funding_harvester"]["net_price_delta_pct"] == 0.0
    assert res["play4_delta_neutral_funding_harvester"]["combined_total_apy_pct"] >= 25.0
    assert res["accumulated_house_profit_sol"] >= 5.0
    assert gov.current_step == STEP_2_LATE_CURVE_SQUEEZE
    assert res["auto_promoted_to"] == STEP_2_LATE_CURVE_SQUEEZE


def test_step2_late_curve_4shield_gate_and_house_money_sizing() -> None:
    """Verifies the 4-Shield Step 2 Late-Curve Gate (No 0% Gambles, 6-Gate Firewall, Tarjan SCC, Salmonella Shield)
    and House-Money sizing cap `min(requested_sol, max(0.5, accumulated_house_profit_sol * 0.25))`.
    """
    # Gate 1 failure: < 65.0% curve completion rejected
    early_gamble = evaluate_step2_late_curve_gate(
        curve_completion_pct=18.5,
        six_gate_firewall_passed=True,
        single_cluster_supply_pct=15.0,
        tarjan_scc_organic_passed=True,
        organic_volume_ratio=0.80,
        salmonella_fot_shield_passed=True,
        requested_sol=2.0,
        accumulated_house_profit_sol=10.0,
        rollout_step=STEP_2_LATE_CURVE_SQUEEZE,
    )
    assert early_gamble.approved is False
    assert early_gamble.gate1_no_zero_pct_gambles_passed is False
    assert early_gamble.verdict == BLOCKED_BY_STEP2_LATE_CURVE_4SHIELD_GATE
    assert early_gamble.house_profit_allocated_sol == 0.0

    # Gate 2 failure: single_cluster_supply_pct > 30.0%
    cabal_fail = evaluate_step2_late_curve_gate(
        curve_completion_pct=71.0,
        six_gate_firewall_passed=True,
        single_cluster_supply_pct=34.5,
        tarjan_scc_organic_passed=True,
        organic_volume_ratio=0.80,
        salmonella_fot_shield_passed=True,
        requested_sol=2.0,
        accumulated_house_profit_sol=10.0,
        rollout_step=STEP_2_LATE_CURVE_SQUEEZE,
    )
    assert cabal_fail.approved is False
    assert cabal_fail.gate2_six_gate_firewall_passed is False

    # Gate 3 failure: organic_volume_ratio < 0.65
    wash_fail = evaluate_step2_late_curve_gate(
        curve_completion_pct=71.0,
        six_gate_firewall_passed=True,
        single_cluster_supply_pct=18.0,
        tarjan_scc_organic_passed=True,
        organic_volume_ratio=0.42,
        salmonella_fot_shield_passed=True,
        requested_sol=2.0,
        accumulated_house_profit_sol=10.0,
        rollout_step=STEP_2_LATE_CURVE_SQUEEZE,
    )
    assert wash_fail.approved is False
    assert wash_fail.gate3_tarjan_scc_organic_passed is False

    # Gate 4 failure: salmonella_fot_shield_passed == False
    salmonella_fail = evaluate_step2_late_curve_gate(
        curve_completion_pct=71.0,
        six_gate_firewall_passed=True,
        single_cluster_supply_pct=18.0,
        tarjan_scc_organic_passed=True,
        organic_volume_ratio=0.78,
        salmonella_fot_shield_passed=False,
        requested_sol=2.0,
        accumulated_house_profit_sol=10.0,
        rollout_step=STEP_2_LATE_CURVE_SQUEEZE,
    )
    assert salmonella_fail.approved is False
    assert salmonella_fail.gate4_salmonella_fot_shield_passed is False

    # All 4 gates pass: verify House-Money sizing cap = min(requested_sol=5.0, max(0.5, 10.0 * 0.25)) = 2.5 SOL
    valid = evaluate_step2_late_curve_gate(
        curve_completion_pct=73.5,
        six_gate_firewall_passed=True,
        single_cluster_supply_pct=19.2,
        tarjan_scc_organic_passed=True,
        organic_volume_ratio=0.79,
        salmonella_fot_shield_passed=True,
        requested_sol=5.0,
        accumulated_house_profit_sol=10.0,
        rollout_step=STEP_2_LATE_CURVE_SQUEEZE,
    )
    assert valid.approved is True
    assert valid.verdict == APPROVED_STEP2_LATE_CURVE_HOUSE_MONEY_SQUEEZE
    assert valid.house_money_cap_sol == 2.5
    assert valid.house_profit_allocated_sol == 2.5
    assert valid.principal_at_risk_sol == 0.0
    assert valid.scale_out_fraction_pct == 75.0
    assert valid.slot0_prewarm_curve_pct == 80.0
    assert valid.slot0_migration_trigger_sol == 84.5
    assert valid.slot0_hotpath_latency_ms < 5.0


def test_step2_and_step3_stacks_plus_drawdown_step_down() -> None:
    """Verifies Step 2 execution, Step 3 Home-Run Hunters, and >30% Drawdown Auto Step-Down to Step 1."""
    gov = Golden5PhasedRolloutGovernor()

    s2 = gov.execute_step2_late_curve_squeeze_stack(requested_sol=2.0, curve_completion_pct=72.4)
    assert s2["principal_at_risk_sol"] == 0.0
    assert s2["house_profit_allocated_sol"] > 0.0
    assert s2["rejected_early_curve_gamble_gate1"]["approved"] is False
    assert s2["approved_late_curve_4shield_gate"]["approved"] is True
    assert s2["play5_late_curve_squeeze_and_slot0_sniper"]["slot0_under_5ms_verified"] is True

    s3 = gov.execute_step3_house_money_homerun_stack()
    assert s3["current_step"] == STEP_3_HOUSE_MONEY_HOMERUN
    assert s3["principal_at_risk_sol"] == 0.0
    assert s3["hunter1_agent30_crosschain_bridge_lookahead"]["inbound_amount_usd"] >= 25000.0
    assert s3["hunter2_agent31_gpu_vision_ca_sniper"]["sub_300ms_verified"] is True
    assert 25.0 <= s3["hunter2_agent31_gpu_vision_ca_sniper"]["human_speed_advantage_multiple"] <= 80.0
    assert s3["hunter3_agent13_cto_and_kol_shadow_inversion"]["kol_shadow_lead_blocks_range"] == [1, 15]

    # Simulate >30% directional drawdown of house profits -> must step back down to STEP_1_ZERO_PRINCIPAL_RISK
    peak = gov.peak_house_profit_sol
    dd = gov.evaluate_drawdown_step_down(
        current_house_profit_sol=peak * 0.60,  # 40% drawdown > 30% threshold
        peak_house_profit_sol=peak,
    )
    assert dd.triggered is True
    assert dd.previous_step == STEP_3_HOUSE_MONEY_HOMERUN
    assert dd.new_step == STEP_1_ZERO_PRINCIPAL_RISK
    assert gov.current_step == STEP_1_ZERO_PRINCIPAL_RISK


def test_titan_ipc_daemon_golden5_governor_wiring() -> None:
    """Verifies TitanIPCDaemon exposes golden5_governor in telemetry and handles all 5 IPC commands."""

    async def _run() -> None:
        daemon = TitanIPCDaemon()
        frame = daemon.build_telemetry_frame()
        assert "golden5_governor" in frame
        assert frame["golden5_governor"]["current_step"] == STEP_1_ZERO_PRINCIPAL_RISK
        assert frame["golden5_governor"]["principal_risk_allowed_sol"] == 0.0

        r_set = await daemon.handle_ipc_payload(
            {
                "action": "SET_GOLDEN5_ROLLOUT_STEP",
                "step": "STEP_2_LATE_CURVE_SQUEEZE",
                "auto_progression": True,
            }
        )
        assert r_set["ok"] is True
        assert r_set["current_step"] == STEP_2_LATE_CURVE_SQUEEZE

        r_s1 = await daemon.handle_ipc_payload({"action": "RUN_GOLDEN5_STEP1_FLASH_STACK"})
        assert r_s1["ok"] is True
        assert r_s1["principal_at_risk_sol"] == 0.0
        assert r_s1["cycle_risk_free_profit_sol"] > 0.0

        r_s2 = await daemon.handle_ipc_payload({"action": "RUN_GOLDEN5_STEP2_LATE_CURVE_STACK"})
        assert r_s2["ok"] is True
        assert r_s2["principal_at_risk_sol"] == 0.0
        assert r_s2["play5_late_curve_squeeze_and_slot0_sniper"]["slot0_under_5ms_verified"] is True

        r_s3 = await daemon.handle_ipc_payload({"action": "RUN_GOLDEN5_STEP3_HOMERUN_STACK"})
        assert r_s3["ok"] is True
        assert r_s3["current_step"] == STEP_3_HOUSE_MONEY_HOMERUN
        assert r_s3["principal_at_risk_sol"] == 0.0

        r_full = await daemon.handle_ipc_payload(
            {"action": "RUN_GOLDEN5_FULL_BLUEPRINT_DIAGNOSTIC"}
        )
        assert r_full["ok"] is True
        assert r_full["blueprint_status"] == "GOLDEN_5_PHASED_ROLLOUT_VERIFIED"
        assert r_full["starting_principal_at_risk_sol"] == 0.0
        assert r_full["drawdown_step_down_verification"]["triggered"] is True

        # Verify Autonomous Week Advance (Week 1) + Full 12-Week Autonomous Lifecycle (Steps 1 -> 2 -> 3)
        r_wk1 = await daemon.handle_ipc_payload({"action": "ADVANCE_AUTONOMOUS_WEEK"})
        assert r_wk1["ok"] is True
        assert r_wk1["week_executed"] == 1
        assert r_wk1["next_autonomous_week"] == 2
        assert r_wk1["weekly_record"]["principal_at_risk_sol"] == 0.0

        r_12wk = await daemon.handle_ipc_payload(
            {"action": "RUN_FULL_12WEEK_AUTONOMOUS_LIFECYCLE"}
        )
        assert r_12wk["ok"] is True
        assert r_12wk["final_step"] == STEP_3_HOUSE_MONEY_HOMERUN
        assert r_12wk["total_contributed_principal_usd"] > 2500.0
        assert r_12wk["capital_injections_count"] >= 1
        assert r_12wk["accumulated_house_profit_sol"] > 15.0

        # Verify Any-Random-Amount at Any-Random-Time capital injection
        prev_principal = r_12wk["total_contributed_principal_usd"]
        r_rand_inj = await daemon.handle_ipc_payload(
            {
                "action": "RECORD_CAPITAL_INJECTION",
                "params": {"random_amount": True},
            }
        )
        assert r_rand_inj["ok"] is True
        assert r_rand_inj["injection_mode"] == "RANDOM_ANYTIME"
        assert 100.0 <= r_rand_inj["injection_tranche"]["amount_usd"] <= 10000.0
        assert r_rand_inj["injection_tranche"]["elapsed_since_prev_injection_sec"] > 0.0
        assert r_rand_inj["principal_at_risk_sol"] == 0.0
        assert r_rand_inj["total_contributed_principal_usd"] > prev_principal

        # Verify Custom Arbitrary Amount at Any Arbitrary Timestamp
        r_custom_inj = await daemon.handle_ipc_payload(
            {
                "action": "RECORD_CAPITAL_INJECTION",
                "params": {"amount_usd": 743.82, "injected_at_ts_ms": 1893456000123},
            }
        )
        assert r_custom_inj["ok"] is True
        assert r_custom_inj["injection_mode"] == "CUSTOM_USD_ANYTIME"
        assert r_custom_inj["injection_tranche"]["amount_usd"] == 743.82
        assert r_custom_inj["injection_tranche"]["injected_at_ts_ms"] == 1893456000123
        assert r_custom_inj["principal_at_risk_sol"] == 0.0

        r_opt = await daemon.handle_ipc_payload(
            {"action": "APPLY_AI_AUTONOMOUS_OPTIMAL_SETTINGS"}
        )
        assert r_opt["ok"] is True
        assert r_opt["ai_autonomous_control_enabled"] is True
        assert r_opt["dual_control_mode"] == "AI_AUTONOMOUS_WITH_OPERATOR_OVERRIDE"

        # Verify TOGGLE_MODULE_STATE ON/OFF persistence in telemetry frame
        r_tog_off = await daemon.handle_ipc_payload(
            {
                "action": "TOGGLE_MODULE_STATE",
                "module_key": "RUN_SANCTUM_LST_FLASH_ARB",
                "enabled": False,
                "label": "Agent 25 Sanctum LST Flash Arb",
            }
        )
        assert r_tog_off["ok"] is True
        assert r_tog_off["enabled"] is False
        assert daemon.module_toggle_states["RUN_SANCTUM_LST_FLASH_ARB"] is False

        r_tog_on = await daemon.handle_ipc_payload(
            {
                "action": "TOGGLE_MODULE_STATE",
                "module_key": "RUN_SANCTUM_LST_FLASH_ARB",
                "enabled": True,
                "label": "Agent 25 Sanctum LST Flash Arb",
            }
        )
        assert r_tog_on["ok"] is True
        assert r_tog_on["enabled"] is True
        assert daemon.module_toggle_states["RUN_SANCTUM_LST_FLASH_ARB"] is True

    asyncio.run(_run())


def test_sovereign_original_edges_bayesian_ratchet_and_profit_amplifier() -> None:
    """Verifies the 3 Sovereign Original Edges in `golden5_phased_rollout_governor`:
    1. `evaluate_bayesian_win_probability_gate` (`>= 92.5%` posterior confluence gate + Quarter-Kelly).
    2. `evaluate_instant_breakeven_principal_ratchet` (`1.030x` trigger -> `1.0085x` stop floor).
    3. `execute_cross_engine_atomic_profit_amplifier` (Idle CU -> Kamino Flash Arb + 5-Tx Super-Bundle + ATA Rent Reclaim).
    """
    from src.execution.golden5_phased_rollout_governor import (
        ATA_RENT_RECLAIM_LAMPORTS,
        BAYESIAN_WIN_PROBABILITY_THRESHOLD,
        STEP_4_SOVEREIGN_ENDOWMENT,
        ZERO_LOSS_RATCHET_LOCK_MULTIPLE,
        ZERO_LOSS_RATCHET_TRIGGER_MULTIPLE,
        evaluate_bayesian_win_probability_gate,
        evaluate_instant_breakeven_principal_ratchet,
        execute_cross_engine_atomic_profit_amplifier,
    )

    gov = Golden5PhasedRolloutGovernor(
        initial_step=STEP_1_ZERO_PRINCIPAL_RISK,
        accumulated_house_profit_sol=12.0,
    )

    # Edge 1: High-confluence signal passes >= 92.5% Bayesian threshold
    approved_gate = gov.evaluate_bayesian_win_probability_gate(
        serial_runner_syndicate_confluence_score=0.92,
        cabal_hunter_x402_tier="TIER_1_WHALE",
        cabal_cluster_supply_pct=18.0,
        melt_122_feature_score=0.94,
        tarjan_scc_organic_ratio=0.85,
        six_gate_firewall_passed=True,
        salmonella_shield_passed=True,
        active_expel_rules_count=10,
        requested_sol=2.0,
    )
    assert approved_gate.approved is True
    assert approved_gate.posterior_win_probability >= BAYESIAN_WIN_PROBABILITY_THRESHOLD
    assert approved_gate.kelly_fraction > 0.0
    assert 0.0 < approved_gate.recommended_sol <= 2.0
    assert approved_gate.principal_at_risk_sol == 0.0

    # Edge 1: Weak signal or veto fails < 92.5% gate
    rejected_gate = evaluate_bayesian_win_probability_gate(
        serial_runner_syndicate_confluence_score=0.45,
        cabal_hunter_x402_tier="NEUTRAL",
        cabal_cluster_supply_pct=29.0,
        melt_122_feature_score=0.52,
        tarjan_scc_organic_ratio=0.66,
        six_gate_firewall_passed=True,
        salmonella_shield_passed=True,
        active_expel_rules_count=0,
        requested_sol=2.0,
    )
    assert rejected_gate.approved is False
    assert rejected_gate.posterior_win_probability < BAYESIAN_WIN_PROBABILITY_THRESHOLD
    assert rejected_gate.recommended_sol == 0.0

    # Edge 2: Instant Break-Even Principal Ratchet ("Zero-Loss Lock" at 1.030x -> 1.0085x)
    pre_lock = evaluate_instant_breakeven_principal_ratchet(
        entry_price_sol=1.0,
        current_price_sol=1.018,
        high_water_mark_price_sol=1.022,
        position_size_sol=2.0,
    )
    assert pre_lock.zero_loss_ratchet_locked is False
    assert pre_lock.downside_loss_probability > 0.0

    locked_res = gov.evaluate_instant_breakeven_principal_ratchet(
        entry_price_sol=1.0,
        current_price_sol=1.032,
        high_water_mark_price_sol=1.032,
        position_size_sol=2.0,
    )
    assert locked_res.zero_loss_ratchet_locked is True
    assert locked_res.newly_locked_this_tick is True
    assert locked_res.trigger_multiple == ZERO_LOSS_RATCHET_TRIGGER_MULTIPLE
    assert locked_res.lock_multiple == ZERO_LOSS_RATCHET_LOCK_MULTIPLE
    assert locked_res.zero_loss_stop_price_sol == 1.0085
    assert locked_res.downside_loss_probability == 0.0
    assert locked_res.locked_floor_net_profit_sol > 0.0

    # Edge 3: Cross-Engine Atomic Profit Amplifier
    amp_res = gov.execute_cross_engine_atomic_profit_amplifier(
        base_trade_profit_sol=1.50,
        slot_cu_limit=1_400_000,
        used_slot_cu=400_000,
        kamino_flash_principal_sol=300.0,
        sanctum_lst_spread_bps=15.0,
        jito_superbundle_secondary_profit_sol=0.45,
        closed_ata_accounts_count=5,
        jito_tip_rebate_sol=0.02,
    )
    assert amp_res.amplified is True
    assert amp_res.idle_slot_cu == 1_000_000
    assert amp_res.kamino_flash_arb_profit_sol > 0.0
    assert amp_res.superbundle_copack_profit_sol == 0.45
    assert amp_res.ata_rent_reclaimed_lamports == 5 * ATA_RENT_RECLAIM_LAMPORTS
    assert amp_res.total_realized_profit_sol > 1.50
    assert amp_res.profit_amplification_multiple > 1.0
    assert amp_res.principal_at_risk_sol == 0.0

    # Sequential auto-promotion Step 1 -> Step 4 when accumulated_house_profit_sol >= 50.0 SOL
    gov_seq = Golden5PhasedRolloutGovernor(
        initial_step=STEP_1_ZERO_PRINCIPAL_RISK,
        accumulated_house_profit_sol=55.0,
        auto_progression_enabled=True,
    )
    promoted = gov_seq._check_auto_promotion()
    assert promoted == STEP_4_SOVEREIGN_ENDOWMENT
    assert gov_seq.current_step == STEP_4_SOVEREIGN_ENDOWMENT
    assert gov_seq.auto_promotions_count == 3

    step4_state = gov_seq.set_rollout_step(STEP_4_SOVEREIGN_ENDOWMENT)
    assert step4_state["homerun_hunters_allowed"] is True


def test_trail_win_engine_and_bidirectional_scaler_zero_loss_ratchet_lock() -> None:
    """Verifies that `TrailWinEngine` and `BiDirectionalScaler` permanently lock the
    stop floor at `1.0085x` entry the instant price reaches `1.030x` (`+3.0%`), and execute
    a 100% full exit on retracement to `<= 1.0085x` instead of partial Stage-0 drawdown rungs.
    """
    from src.execution.bi_directional_scaler import BiDirectionalScaler
    from src.execution.trail_win_engine import (
        TrailWinEngine,
        ZERO_LOSS_LOCK_STOP_MULTIPLE,
        ZERO_LOSS_LOCK_TRIGGER_MULTIPLE,
    )

    trail = TrailWinEngine()
    mint = "ZeroLossRatchetMint1111111111111111111111111"
    entry_price = 0.00100000

    pos = trail.register_position(
        mint=mint,
        entry_price_sol=entry_price,
        initial_sol_invested=1.0,
        horizon="HORIZON_1_BONDING_SCALP",
    )
    assert pos.zero_loss_ratchet_locked is False

    # 1. Tick to +3.2% (1.032x >= 1.030x trigger) -> Zero-Loss Lock engages at 1.0085x
    tick_lock = trail.evaluate_tick(
        mint=mint,
        current_price_sol=entry_price * 1.032,
    )
    assert tick_lock is not None
    assert tick_lock.action == "HOLD"
    assert tick_lock.zero_loss_ratchet_locked is True
    assert pos.zero_loss_ratchet_locked is True
    assert pos.zero_loss_stop_price_sol == round(
        entry_price * ZERO_LOSS_LOCK_STOP_MULTIPLE, 12
    )
    assert pos.active_trail_stop_price >= pos.zero_loss_stop_price_sol

    # Manual override cannot lower the stop below the 1.0085x Zero-Loss floor
    override_pos = trail.set_manual_trail_override(
        mint=mint,
        trail_pct=0.25,
    )
    assert override_pos is not None
    assert override_pos.active_trail_stop_price >= pos.zero_loss_stop_price_sol

    # 2. BiDirectionalScaler skips Stage-0 partial drawdown rungs when Zero-Loss Lock is active
    scaler = BiDirectionalScaler()
    scaler_mint = "BiDirZeroLossMint111111111111111111111111111"
    scaler.register_position(
        token_mint=scaler_mint,
        entry_price_sol=entry_price,
        initial_sol_invested=1.0,
        horizon="HORIZON_1_BONDING_SCALP",
    )
    # First tick above 1.030x locks the Zero-Loss Ratchet
    step_up = scaler.evaluate_tick(
        token_mint=scaler_mint,
        current_price_sol=entry_price * 1.035,
        net_organic_buy_flow_sol_delta=8.5,
        elapsed_seconds=3.5,
    )
    assert step_up.remaining_bag_fraction == 1.0
    assert scaler.trail_engine.positions[scaler_mint].zero_loss_ratchet_locked is True

    # Retracement to 1.0080x (<= 1.0085x floor) skips partial D1/D2/D3 and executes 100% full exit via TrailWinEngine
    scale_exit = scaler.evaluate_tick(
        token_mint=scaler_mint,
        current_price_sol=entry_price * 1.0080,
        net_organic_buy_flow_sol_delta=1.0,
        elapsed_seconds=5.0,
    )
    assert scale_exit.decision_source == "TRAIL_WIN_ENGINE"
    assert scale_exit.fraction_sold == 1.0
    assert scale_exit.remaining_bag_fraction == 0.0
    assert scale_exit.trail_decision is not None
    assert "ZERO_LOSS_BREAKEVEN_RATCHET_STOP_HIT" in scale_exit.trail_decision.reason
    assert scaler.trail_engine.positions[scaler_mint].is_closed is True


def test_black_scholes_zero_tick_clamping_and_zero_slot_migration_slippage_cap() -> None:
    """Verifies `compute_black_scholes_digital_probability` clamps `<= 0` inputs to `1e-9`
    without raising `ValueError`, and `ZeroSlotMigrationArbEngine` formats `effective_slippage_bps`
    (`min(1200.0, blind_sniper_slippage_bps)`) in its reason string.
    """
    from src.engines.multimodal_vision_and_polymarket_sniper import (
        compute_black_scholes_digital_probability,
    )
    from src.engines.zero_slot_migration_arb import ZeroSlotMigrationArbEngine

    d2, p_yes, p_no = compute_black_scholes_digital_probability(
        spot_price=0.0,
        strike_price=0.0,
        annualized_volatility=0.0,
        time_to_expiry_years=0.0,
    )
    assert isinstance(d2, float)
    assert 0.0 <= p_yes <= 1.0
    assert abs((p_yes + p_no) - 1.0) < 1e-9

    arb_engine = ZeroSlotMigrationArbEngine()
    mig_res = arb_engine.evaluate_zero_slot_migration(
        token_mint="Slot0MigrationMint11111111111111111111111111",
        migration_venue="PUMPSWAP",
        seeded_lp_sol=85.0,
        sibling_dislocation_pct=0.0,
        blind_sniper_buy_sol=12.0,
        blind_sniper_slippage_bps=3500.0,
    )
    assert mig_res.triggered is True
    assert "(1200 bps slip)" in mig_res.reason


def test_daily_5k_velocity_preset_and_6_multipliers_activation() -> None:
    """Verifies the $5,000+/day (28.50 SOL/day) 5-Tier Velocity Preset & 6 Multipliers
    are enabled by default and can be configured via `activate_5k_daily_velocity_preset`.
    """
    gov = Golden5PhasedRolloutGovernor()
    assert gov.daily_5k_velocity_preset_enabled is True
    summary = gov.get_daily_5k_velocity_preset_summary()
    assert summary["enabled"] is True
    assert summary["status"] == "ARMED"
    assert summary["optimal_daily_target_sol"] >= 28.50
    assert summary["optimal_daily_target_usd"] >= 5415.0
    assert summary["uncapped_compounding_enabled"] is True
    assert summary["daily_profit_ceiling_usd"] == "UNCAPPED"
    assert summary["is_5k_only_a_floor"] is True
    assert summary["kamino_flash_cap_sol"] == 500.0
    assert summary["active_parallel_shards"] == 25
    assert summary["per_shard_entry_cap_sol"] == 2.0
    assert summary["meteora_dlmm_surge_pool_sol"] == 90.0
    assert len(summary["tiers"]) == 5
    assert len(summary["multipliers"]) == 6
    assert len(summary["capital_evolution_echelons"]) == 4

    res = gov.activate_5k_daily_velocity_preset()
    assert res["status"] == "ARMED"
    assert res["preset"]["enabled"] is True

    daemon = TitanIPCDaemon()
    ipc_res = asyncio.run(
        daemon.handle_ipc_payload(
            {
                "action": "ACTIVATE_5K_DAILY_VELOCITY_PRESET",
                "kamino_flash_cap_sol": 500.0,
                "active_parallel_shards": 25,
                "per_shard_entry_cap_sol": 2.0,
                "meteora_dlmm_surge_pool_sol": 90.0,
            }
        )
    )
    assert ipc_res["status"] in ("OK", "ARMED")
    assert ipc_res["daily_5k_preset"]["status"] == "ARMED"
    assert ipc_res["frame"]["daily_5k_preset"]["optimal_daily_target_sol"] >= 28.50


def test_uncapped_auto_compounding_and_4echelon_strategy_evolution() -> None:
    """Verifies that $5,000/day is strictly a FLOOR, never a ceiling, and that
    100% of realized profits auto-reinvest (50% DLMM/Funding, 30% Vault, 20% 25-Shard Waves)
    and evolve strategies across all 4 Capital Evolution Echelons up to $100,000+/day+.
    """
    gov = Golden5PhasedRolloutGovernor()
    assert gov.uncapped_compounding_enabled is True
    assert gov.daily_profit_ceiling_mode == "UNCAPPED_FLOOR_5K_ONLY"

    # Echelon 2 promotion (>= 500 SOL total equity)
    e2 = gov.run_uncapped_compound_and_evolve_cycle(additional_profit_sol=520.0)
    assert e2["active_capital_echelon_id"] == 2
    assert e2["kamino_flash_cap_sol"] >= 2500.0
    assert e2["meteora_dlmm_surge_pool_sol"] >= 300.0
    assert e2["active_simultaneous_token_waves"] == 3
    assert e2["scaled_optimal_daily_sol"] > 28.50

    # Echelon 3 promotion (>= 1,500 SOL total equity -> Local Cross-Chain Solver unlocked)
    e3 = gov.run_uncapped_compound_and_evolve_cycle(additional_profit_sol=1100.0)
    assert e3["active_capital_echelon_id"] == 3
    assert e3["kamino_flash_cap_sol"] >= 10000.0
    assert e3["meteora_dlmm_surge_pool_sol"] >= 1000.0
    assert e3["active_simultaneous_token_waves"] == 6
    assert e3["crosschain_solver_inventory_sol"] >= 500.0

    # Echelon 4 promotion (>= 5,000 SOL total equity -> $100,000+/day+ Uncapped Sovereign Whale)
    e4 = gov.run_uncapped_compound_and_evolve_cycle(additional_profit_sol=3600.0)
    assert e4["active_capital_echelon_id"] == 4
    assert e4["kamino_flash_cap_sol"] == 25000.0
    assert e4["meteora_dlmm_surge_pool_sol"] >= 3500.0
    assert e4["active_simultaneous_token_waves"] == 12
    assert e4["crosschain_solver_inventory_sol"] >= 2000.0
    assert e4["daily_profit_ceiling_usd"] == "UNCAPPED"

    daemon = TitanIPCDaemon()
    ipc_comp = asyncio.run(
        daemon.handle_ipc_payload(
            {
                "action": "RUN_UNCAPPED_COMPOUND_AND_EVOLVE_CYCLE",
                "additional_profit_sol": 28.5,
            }
        )
    )
    assert ipc_comp["ok"] is True
    assert ipc_comp["daily_5k_preset"]["daily_profit_ceiling_usd"] == "UNCAPPED"
    assert ipc_comp["daily_5k_preset"]["is_5k_only_a_floor"] is True
    assert ipc_comp["daily_5k_preset"]["compounding_reinvest_cycles"] >= 1


def test_autonomous_capital_adaptive_allocation_by_live_capital() -> None:
    """Verifies that `evaluate_capital_adaptive_allocation` automatically determines
    what strategies to run and how to size every engine strictly from live capital
    (initial $1,000-$2,000 seed + random capital injections + accumulated profit),
    with zero manual week or step switching required.
    """
    gov = Golden5PhasedRolloutGovernor(accumulated_house_profit_sol=0.0)

    # 1. Start at $2,000 initial seed
    seed_res = gov.set_initial_seed_capital(amount_usd=2000.0, sol_price_usd=185.0)
    assert seed_res["initial_seed_usd"] == 2000.0
    plan_2k = seed_res["capital_adaptive_plan"]
    assert plan_2k["mode"] == "AUTOMATIC_CAPITAL_ADAPTIVE"
    assert plan_2k["total_capital_sol"] == round(2000.0 / 185.0, 4)
    assert plan_2k["auto_per_shard_cap_sol"] >= 0.08
    assert plan_2k["auto_kamino_flash_cap_sol"] >= 100.0

    # 2. Inject $1,500 random capital -> automatically scales up per-shard, flash, DLMM, and waves
    inj_res = gov.record_capital_injection(
        amount_usd=1500.0, sol_price_usd=185.0, random_amount=False
    )
    plan_3500 = inj_res["capital_adaptive_plan"]
    assert plan_3500["total_capital_sol"] > plan_2k["total_capital_sol"]
    assert plan_3500["auto_per_shard_cap_sol"] > plan_2k["auto_per_shard_cap_sol"]
    assert plan_3500["auto_kamino_flash_cap_sol"] > plan_2k["auto_kamino_flash_cap_sol"]
    assert plan_3500["auto_dlmm_pool_sol"] > plan_2k["auto_dlmm_pool_sol"]
    assert plan_3500["active_engines_count"] >= 9

    # 3. Telemetry summary includes live capital_adaptive_plan
    telem = gov.get_telemetry_summary()
    assert "capital_adaptive_plan" in telem
    assert telem["capital_adaptive_plan"]["mode"] == "AUTOMATIC_CAPITAL_ADAPTIVE"


