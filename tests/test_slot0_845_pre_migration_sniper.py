"""Comprehensive pytest suite for `src/execution/slot0_845_pre_migration_sniper.py`
verifying Subsystem 2: Sub-50ms Slot-0 Genesis Interception, Deterministic 80%/84.5 SOL
Pre-Migration Sniper, Dynamic Curve-Velocity Jito Tip Calibration, and 6-Relay Parallel Fan-Out.
"""

from __future__ import annotations

from pathlib import Path
import struct
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.execution.slot0_845_pre_migration_sniper import (
    ALL_FANOUT_RELAY_PATHS,
    APERTURE_INFLIGHT_CONFIDENCE_THRESHOLD_PCT,
    APERTURE_TXSTREAM_OVERHEAD_MS,
    APERTURE_TXSTREAM_OVERHEAD_US,
    APERTURE_TXSTREAM_PREDICTED_ACCURACY_PCT,
    COLOCATED_MAX_DETECTION_TO_SUBMISSION_MS,
    COLOCATED_SLOT0_LANDING_RATE_PCT,
    COLOCATED_VALIDATOR_HUBS,
    CoLocatedShredApertureLookaheadEngine,
    HOTPATH_MAX_DECISION_LOGIC_MS,
    HOTPATH_MAX_SIGNING_MS,
    HOTPATH_MAX_TEMPLATE_FILL_MS,
    HOTPATH_MAX_TOTAL_LATENCY_MS,
    JITO_DONT_FRONT_ACCOUNT_PUBKEY,
    JITO_SHREDSTREAM_MAX_LOOKAHEAD_MS,
    JITO_SHREDSTREAM_MIN_LOOKAHEAD_MS,
    LAMPORTS_PER_SOL,
    NON_COLOCATED_CLOUD_LANDING_RATE_PCT,
    NON_COLOCATED_CLOUD_MAX_LANDING_RATE_PCT,
    PRIMARY_6_RELAY_PATHS,
    PUMP_FUN_GRADUATION_SOL_TARGET,
    PUMP_FUN_MIGRATION_AUTHORITY,
    PUMP_FUN_PROGRAM_ID,
    PUMP_SWAP_AMM_PROGRAM_ID,
    PreMigration845Sniper,
    RELAY_NETWORK_TRANSIT_MAX_MS,
    RELAY_NETWORK_TRANSIT_MIN_MS,
    SLOT0_VS_SLOT2_PRICE_UPSIDE_RANGE_PCT,
    STAGE_A_PREWARM_CURVE_PCT_THRESHOLD,
    STAGE_B_HOTPATH_FIRE_SOL_THRESHOLD,
    SWQOS_VALIDATOR_TPU_PATH,
    Slot0And845PreMigrationSniperSuite,
    YELLOWSTONE_GRPC_MAX_LATENCY_MS,
    YELLOWSTONE_GRPC_MIN_LATENCY_MS,
    compute_dynamic_curve_velocity_jito_tip,
    derive_pumpswap_pool_pda_zero_rpc,
    dispatch_multi_relay_fanout_bundle,
    evaluate_shred_aperture_lookahead,
    fire_845_sol_pre_migration_hotpath,
    prewarm_at_80pct_curve,
)


def test_colocated_shred_aperture_lookahead_all_4_hubs() -> None:
    """Verifies bare-metal validator co-location in Frankfurt, Ashburn / NY, Amsterdam, and Tokyo
    (<35ms detection-to-submission latency, 89.0% Slot-0 landing rate vs <20.0% non-colocated cloud,
    20%-60% Slot-0 vs Slot-2 price upside, Yellowstone 5-20ms, ShredStream 50-200ms, Aperture +791us / 95% acc).
    """
    assert set(COLOCATED_VALIDATOR_HUBS) == {
        "Frankfurt",
        "Ashburn / NY",
        "Amsterdam",
        "Tokyo",
    }
    assert APERTURE_TXSTREAM_OVERHEAD_US == 791.0
    assert APERTURE_TXSTREAM_OVERHEAD_MS == pytest.approx(0.791, abs=1e-6)
    assert APERTURE_TXSTREAM_PREDICTED_ACCURACY_PCT == 95.0
    assert COLOCATED_SLOT0_LANDING_RATE_PCT == 89.0
    assert NON_COLOCATED_CLOUD_LANDING_RATE_PCT < NON_COLOCATED_CLOUD_MAX_LANDING_RATE_PCT
    assert SLOT0_VS_SLOT2_PRICE_UPSIDE_RANGE_PCT == (20.0, 60.0)

    for hub in COLOCATED_VALIDATOR_HUBS:
        for bundler in ("FrogLabs", "SolBundler"):
            decision = evaluate_shred_aperture_lookahead(
                token_mint="Slot0AlphaMint11111111111111111111111111111",
                datacenter_region=hub,
                yellowstone_grpc_latency_ms=9.2,
                shredstream_lookahead_ms=130.0,
                aperture_txstream_enabled=True,
                aperture_overhead_us=791.0,
                aperture_predicted_accuracy_pct=95.0,
                is_tier1_curated_dev=True,
                genesis_bundler_type=bundler,
                dev_genesis_bundle_detected=True,
            )
            assert decision.is_colocated is True
            assert decision.datacenter_region == hub
            assert decision.detection_to_submission_ms < COLOCATED_MAX_DETECTION_TO_SUBMISSION_MS
            assert decision.sub_35ms_colocated_sla_met is True
            assert decision.slot0_landing_rate_pct == 89.0
            assert decision.non_colocated_cloud_landing_rate_pct < 20.0
            assert decision.yellowstone_within_5_to_20ms is True
            assert decision.shredstream_within_50_to_200ms is True
            assert decision.aperture_overhead_us == 791.0
            assert decision.aperture_overhead_ms == pytest.approx(0.791, abs=1e-6)
            assert decision.aperture_predicted_accuracy_pct == 95.0
            assert 20.0 <= decision.expected_slot0_vs_slot2_upside_pct <= 60.0
            assert decision.should_snipe_slot0 is True
            assert bundler.upper() in decision.target_execution_position
            # Also verify dict-compatible access
            assert decision["should_snipe_slot0"] is True
            assert decision["slot0_landing_rate_pct"] == 89.0


def test_non_colocated_cloud_and_non_tier1_dev_rejected() -> None:
    """Verifies non-colocated cloud (<20% landing rate, >=35ms latency) and non-Tier-1 devs do not fire Slot-0 snipes."""
    engine = CoLocatedShredApertureLookaheadEngine()

    cloud_decision = engine.evaluate_shred_aperture_lookahead(
        token_mint="CloudMint1111111111111111111111111111111111",
        datacenter_region="AWS-US-West-Oregon",
        is_colocated=False,
    )
    assert cloud_decision.is_colocated is False
    assert cloud_decision.detection_to_submission_ms >= COLOCATED_MAX_DETECTION_TO_SUBMISSION_MS
    assert cloud_decision.slot0_landing_rate_pct < 20.0
    assert cloud_decision.should_snipe_slot0 is False
    assert engine.non_colocated_rejections == 1

    # Non-Tier-1 dev or low Aperture accuracy must also reject
    untrusted_dev = engine.evaluate_shred_aperture_lookahead(
        token_mint="UntrustedMint111111111111111111111111111111",
        datacenter_region="Frankfurt",
        is_tier1_curated_dev=False,
    )
    assert untrusted_dev.should_snipe_slot0 is False


def test_zero_rpc_deterministic_pumpswap_pool_pda_derivation() -> None:
    """Verifies 0.0ms zero-RPC deterministic PumpSwap AMM pool PDA derivation from token_mint."""
    mint_a = "PumpGradMintA111111111111111111111111111111"
    mint_b = "PumpGradMintB222222222222222222222222222222"

    pda_a1 = derive_pumpswap_pool_pda_zero_rpc(token_mint=mint_a)
    pda_a2 = derive_pumpswap_pool_pda_zero_rpc(token_mint=mint_a)
    pda_b = derive_pumpswap_pool_pda_zero_rpc(token_mint=mint_b)

    assert pda_a1.zero_rpc is True
    assert pda_a1.rpc_calls_made == 0
    assert pda_a1.network_latency_ms == 0.0
    assert pda_a1.program_id == PUMP_SWAP_AMM_PROGRAM_ID
    assert pda_a1.migration_authority == PUMP_FUN_MIGRATION_AUTHORITY
    # Deterministic across repeated calls
    assert pda_a1.pool_pda == pda_a2.pool_pda
    assert pda_a1.pool_base_vault_pda == pda_a2.pool_base_vault_pda
    assert pda_a1.pool_quote_vault_pda == pda_a2.pool_quote_vault_pda
    assert pda_a1.lp_mint_pda == pda_a2.lp_mint_pda
    # Distinct mints produce distinct deterministic PDAs
    assert pda_a1.pool_pda != pda_b.pool_pda
    assert len(pda_a1.pool_pda) >= 32


def test_stage_a_prewarm_at_80pct_curve() -> None:
    """Verifies Stage A template pre-warming in RAM at >= 80.0% bonding curve completion."""
    sniper = PreMigration845Sniper()
    mint = "StageAPrewarmMint11111111111111111111111111"

    # Below 80% (e.g. 74.0%) must NOT prewarm
    below_80 = sniper.prewarm_at_80pct_curve(
        token_mint=mint,
        curve_completion_pct=74.0,
    )
    assert below_80.prewarmed is False
    assert below_80.status == "BELOW_80PCT_PREWARM_THRESHOLD"

    # At >= 80.0% (e.g. 80.0% = 68.0 SOL) MUST prewarm in RAM
    at_80 = sniper.prewarm_at_80pct_curve(
        token_mint=mint,
        curve_completion_pct=80.0,
        sol_deposited_curve=68.0,
        compute_unit_limit=135_000,
        compute_unit_price_micro_lamports=250_000,
    )
    assert at_80.prewarmed is True
    assert at_80.status == "STAGE_A_RAM_TEMPLATE_PREWARMED"
    assert at_80.curve_completion_pct == 80.0
    assert at_80.sol_deposited_curve == 68.0
    assert at_80.compute_budget_ix["compute_unit_limit"] == 135_000
    assert at_80.compute_budget_ix["compute_unit_price_micro_lamports"] == 250_000
    assert PUMP_SWAP_AMM_PROGRAM_ID in at_80.alt_accounts
    assert PUMP_FUN_PROGRAM_ID in at_80.alt_accounts
    assert at_80.pumpswap_pool_pda in at_80.alt_accounts
    assert at_80.template_size_bytes == 128
    assert set(at_80.byte_offset_map.keys()) >= {
        "token_mint",
        "pumpswap_pool_pda",
        "buy_amount_lamports",
        "min_tokens_out_raw",
        "slippage_bps",
        "jito_tip_lamports",
    }
    assert at_80.ed25519_single_op_payload["single_op_ed25519_ready"] is True
    assert len(at_80.presigned_jito_tip_wrappers) == 4
    assert all(w["ready_in_ram"] for w in at_80.presigned_jito_tip_wrappers)


def test_stage_b_fire_845_sol_and_aperture_95pct_inflight_hotpath() -> None:
    """Verifies Stage B <5ms hot-path fire trigger at >= 84.5 SOL deposited OR >= 95.0%
    Aperture TxStream in-flight crossing 85.0 SOL.
    """
    sniper = PreMigration845Sniper()
    mint = "StageBHotpathMint11111111111111111111111111"

    # Pre-warm Stage A at 82% curve completion
    prewarm_res = sniper.prewarm_at_80pct_curve(token_mint=mint, curve_completion_pct=82.0)
    assert prewarm_res.prewarmed is True

    # Below 84.5 SOL and without in-flight crossing 85.0 SOL -> does not fire
    hold_res = sniper.fire_845_sol_pre_migration_hotpath(
        token_mint=mint,
        sol_deposited_curve=83.2,
        aperture_inflight_sol_delta=0.5,
        aperture_inflight_confidence_pct=96.0,
    )
    assert hold_res.fired is False
    assert hold_res.lands_in_pumpswap_slot0 is False

    # Trigger 1: Direct >= 84.5 SOL deposited on bonding curve
    fire_845 = sniper.fire_845_sol_pre_migration_hotpath(
        token_mint=mint,
        sol_deposited_curve=84.5,
        buy_amount_sol=2.5,
        slippage_bps=150,
        jito_tip_sol=0.02,
    )
    assert fire_845.fired is True
    assert fire_845.was_stage_a_prewarmed is True
    assert fire_845.trigger_mode == "DIRECT_845_SOL_CURVE_THRESHOLD"
    assert fire_845.pumpswap_pool_pda == prewarm_res.pumpswap_pool_pda
    assert fire_845.decision_logic_ms < HOTPATH_MAX_DECISION_LOGIC_MS
    assert fire_845.template_fill_ms < HOTPATH_MAX_TEMPLATE_FILL_MS
    assert fire_845.signing_ms < HOTPATH_MAX_SIGNING_MS
    assert fire_845.total_hotpath_latency_ms < HOTPATH_MAX_TOTAL_LATENCY_MS
    assert fire_845.sub_5ms_sla_met is True
    assert fire_845.target_migration_slot == 0
    assert fire_845.lands_in_pumpswap_slot0 is True
    assert fire_845.v0_under_1232_mtu is True
    assert len(bytes.fromhex(fire_845.ed25519_signature_hex)) == 64

    # Verify populated byte offsets inside instruction buffer
    raw_ix = bytes.fromhex(fire_845.populated_instruction_hex)
    unpacked_buy_lamports = struct.unpack_from("<Q", raw_ix, 80)[0]
    unpacked_slippage_bps = struct.unpack_from("<H", raw_ix, 96)[0]
    unpacked_tip_lamports = struct.unpack_from("<Q", raw_ix, 98)[0]
    assert unpacked_buy_lamports == int(2.5 * LAMPORTS_PER_SOL)
    assert unpacked_slippage_bps == 150
    assert unpacked_tip_lamports == int(0.02 * LAMPORTS_PER_SOL)

    # Trigger 2: Aperture TxStream >= 95.0% accuracy in-flight tx crossing 85.0 SOL (from 83.8 SOL + 1.5 SOL in-flight)
    fire_aperture = fire_845_sol_pre_migration_hotpath(
        token_mint=mint,
        sol_deposited_curve=83.8,
        aperture_inflight_sol_delta=1.5,
        aperture_inflight_confidence_pct=95.0,
        buy_amount_sol=3.0,
        slippage_bps=100,
    )
    assert fire_aperture.fired is True
    assert fire_aperture.trigger_mode == "APERTURE_95PCT_INFLIGHT_85_SOL_CROSSING"
    assert fire_aperture.predicted_total_curve_sol == pytest.approx(85.3, abs=1e-4)
    assert fire_aperture.sub_5ms_sla_met is True
    assert fire_aperture.lands_in_pumpswap_slot0 is True


def test_dynamic_curve_velocity_jito_tip_exact_formula() -> None:
    """Verifies exact formula:
    B_tip(t) = P_q(Tips_{t-50:t}) * (1 + alpha * (Delta_SOL_curve / Delta_t)).
    """
    # Construct a deterministic 50-block trailing tip array where P_90 is known exactly
    trailing_50 = [round(0.001 * (i + 1), 6) for i in range(50)]  # 0.001 .. 0.050 SOL
    # For 50 elements (indices 0..49), pos at q=90 is 0.90 * 49 = 44.1 -> 0.0451 SOL
    res_90 = compute_dynamic_curve_velocity_jito_tip(
        trailing_50_block_tips_sol=trailing_50,
        percentile_q=90.0,
        delta_sol_curve=15.0,
        delta_t_sec=3.0,
        alpha=0.20,
    )
    expected_p90 = 0.0451
    expected_velocity = 15.0 / 3.0  # 5.0 SOL/sec
    expected_multiplier = 1.0 + 0.20 * 5.0  # 2.0
    expected_b_tip = expected_p90 * expected_multiplier  # 0.0902 SOL

    assert res_90.trailing_window_blocks == 50
    assert res_90.percentile_q == 90.0
    assert res_90.p_q_base_tip_sol == pytest.approx(expected_p90, abs=1e-8)
    assert res_90.curve_velocity_sol_per_sec == pytest.approx(expected_velocity, abs=1e-8)
    assert res_90.velocity_multiplier == pytest.approx(expected_multiplier, abs=1e-8)
    assert res_90.b_tip_sol == pytest.approx(expected_b_tip, abs=1e-8)
    assert res_90.b_tip_lamports == int(round(expected_b_tip * LAMPORTS_PER_SOL))

    # Fractional q=0.75 vs q=75.0 must yield identical results
    res_frac = compute_dynamic_curve_velocity_jito_tip(
        trailing_50_block_tips_sol=trailing_50,
        percentile_q=0.75,
        delta_sol_curve=10.0,
        delta_t_sec=2.0,
        alpha=0.25,
    )
    res_pct = compute_dynamic_curve_velocity_jito_tip(
        trailing_50_block_tips_sol=trailing_50,
        percentile_q=75.0,
        delta_sol_curve=10.0,
        delta_t_sec=2.0,
        alpha=0.25,
    )
    assert res_frac.b_tip_sol == res_pct.b_tip_sol
    assert res_frac.b_tip_sol < res_90.b_tip_sol

    # Invalid delta_t_sec <= 0 must raise ValueError
    with pytest.raises(ValueError):
        compute_dynamic_curve_velocity_jito_tip(
            trailing_50_block_tips_sol=trailing_50,
            delta_sol_curve=5.0,
            delta_t_sec=0.0,
        )


def test_preflight_simulate_bundle_jitodontfront_and_6_relay_fanout() -> None:
    """Verifies free `simulateBundle` pre-flight check, `jitodontfront` injection into Tx[0],
    and parallel 6-relay (`JITO_NY`, `JITO_FRANKFURT`, `JITO_TOKYO`, `JITO_AMSTERDAM`,
    `ASTRALANE`, `QUICKNODE_LIL_JIT`) + `SWQOS_VALIDATOR_TPU` fan-out within 5-30ms.
    """
    assert set(PRIMARY_6_RELAY_PATHS) == {
        "JITO_NY",
        "JITO_FRANKFURT",
        "JITO_TOKYO",
        "JITO_AMSTERDAM",
        "ASTRALANE",
        "QUICKNODE_LIL_JIT",
    }
    assert SWQOS_VALIDATOR_TPU_PATH == "SWQOS_VALIDATOR_TPU"
    assert len(ALL_FANOUT_RELAY_PATHS) == 7

    # Case 1: Pre-flight simulateBundle passes -> dispatches across all 6 relays + SWQoS TPU
    ok_dispatch = dispatch_multi_relay_fanout_bundle(
        token_mint="FanoutMint111111111111111111111111111111111",
        jito_tip_sol=0.025,
        simulate_bundle_success=True,
    )
    assert ok_dispatch.simulation_passed is True
    assert ok_dispatch.simulate_bundle_preflight_free is True
    assert ok_dispatch.jitodontfront_injected_in_tx0 is True
    assert ok_dispatch.jitodontfront_pubkey == JITO_DONT_FRONT_ACCOUNT_PUBKEY
    assert ok_dispatch.jitodontfront_pubkey.startswith("jitodontfront")
    assert JITO_DONT_FRONT_ACCOUNT_PUBKEY in ok_dispatch.tx0_accounts
    assert ok_dispatch.frontrun_backrun_protection_active is True
    assert ok_dispatch.dispatched is True
    assert ok_dispatch.tip_paid_sol == pytest.approx(0.025, abs=1e-8)
    assert ok_dispatch.tip_saved_by_simulation_sol == 0.0
    assert set(ok_dispatch.primary_6_relays) == set(PRIMARY_6_RELAY_PATHS)
    assert set(ok_dispatch.all_dispatched_paths) == set(ALL_FANOUT_RELAY_PATHS)
    assert ok_dispatch.all_relays_within_5_to_30ms is True
    for relay_name in ALL_FANOUT_RELAY_PATHS:
        leg = ok_dispatch.relay_results[relay_name]
        assert RELAY_NETWORK_TRANSIT_MIN_MS <= leg["network_transit_ms"] <= RELAY_NETWORK_TRANSIT_MAX_MS
        assert leg["within_5_to_30ms_sla"] is True
        assert leg["dispatched"] is True

    # Case 2: Pre-flight simulateBundle fails -> aborts fan-out and saves 100% of Jito tip
    failed_sim = dispatch_multi_relay_fanout_bundle(
        token_mint="FanoutMint111111111111111111111111111111111",
        jito_tip_sol=0.042,
        simulate_bundle_success=False,
        simulation_error="InstructionError: Custom(6001) SlippageExceeded",
    )
    assert failed_sim.simulation_passed is False
    assert failed_sim.dispatched is False
    assert failed_sim.tip_paid_sol == 0.0
    assert failed_sim.tip_saved_by_simulation_sol == pytest.approx(0.042, abs=1e-8)
    assert failed_sim.all_dispatched_paths == []

    # Invalid jitodontfront prefix must raise ValueError
    with pytest.raises(ValueError):
        dispatch_multi_relay_fanout_bundle(
            jitodontfront_pubkey="invalidprefix111111111111111111111111111111"
        )


def test_slot0_and_845_pre_migration_sniper_suite_facade() -> None:
    """Verifies `Slot0And845PreMigrationSniperSuite` diagnostic and telemetry summary for `TitanIPCDaemon`."""
    suite = Slot0And845PreMigrationSniperSuite()
    diag = suite.run_full_sniper_pipeline_diagnostic()

    assert diag["subsystem"] == "SUBSYSTEM_2_SLOT0_AND_845_SOL_PRE_MIGRATION_SNIPER"
    assert diag["all_checks_passed"] is True
    assert diag["lookahead"]["colocated_frankfurt"]["should_snipe_slot0"] is True
    assert diag["lookahead"]["non_colocated_cloud"]["should_snipe_slot0"] is False
    assert diag["pre_migration_845_sniper"]["zero_rpc_pda"]["zero_rpc"] is True
    assert diag["pre_migration_845_sniper"]["stage_a_80pct_prewarm"]["prewarmed"] is True
    assert diag["pre_migration_845_sniper"]["stage_b_845_hotpath_fire"]["fired"] is True
    assert diag["pre_migration_845_sniper"]["stage_b_845_hotpath_fire"]["sub_5ms_sla_met"] is True
    assert (
        diag["dynamic_curve_velocity_tips"]["p90_surge"]["b_tip_sol"]
        > diag["dynamic_curve_velocity_tips"]["p75_calm"]["b_tip_sol"]
    )
    assert diag["multi_relay_fanout"]["dispatched_bundle"]["dispatched"] is True
    assert diag["multi_relay_fanout"]["blocked_by_simulate_bundle"]["dispatched"] is False

    telemetry = suite.get_telemetry_summary()
    assert telemetry["subsystem"] == "SUBSYSTEM_2_SLOT0_AND_845_SOL_PRE_MIGRATION_SNIPER"
    assert telemetry["colocated_slot0_landing_rate_pct"] == 89.0
    assert telemetry["non_colocated_cloud_landing_rate_pct"] < 20.0
    assert telemetry["aperture_txstream_overhead_us"] == 791.0
    assert telemetry["aperture_txstream_accuracy_pct"] == 95.0
    assert telemetry["stage_a_prewarm_threshold_pct"] == 80.0
    assert telemetry["stage_b_fire_threshold_sol"] == 84.5
    assert set(telemetry["primary_6_relays"]) == set(PRIMARY_6_RELAY_PATHS)
    assert telemetry["counters"]["diagnostics_run"] == 1
    assert telemetry["counters"]["preflight_simulations_blocked"] == 1
    assert telemetry["last_diagnostic_available"] is True
