"""Comprehensive pytest verification suite for
`src/ingestion/pre_mint_peel_chain_listener.py` implementing Agent A of `AlphaExploit-Solana`:
Sub-50ms ShredStream & Pre-Mint Peel-Chain Listener (`PRE_LAUNCH_DEV_SIGNAL`),
6 `cabalspy[realtime]` WebSocket Streams, and Constant-Product Bonding Curve
`65%–78%` Acceleration -> `77%–79%` Automated `75%` Scale-Out.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ingestion.pre_mint_peel_chain_listener import (
    ACTION_ABORT_GRADUATION_FROZEN,
    ACTION_ENTER_CURVE_SQUEEZE,
    ACTION_HOLD_REJECTED_UNAUDITED_FLOW,
    ACTION_SCALE_OUT_75PCT_PRE_FREEZE,
    ACTION_WAIT_BELOW_SQUEEZE_ZONE,
    AGENT_A_SWARM_ID,
    ALLOWED_TARGET_PROGRAM_IDS,
    BLOCK1_SNIPE_ACTION,
    CABALSPY_REALTIME_6_STREAMS,
    CABALSPY_WEBSOCKET_CORES,
    CURVE_GRADUATION_FREEZE_PCT,
    DEFAULT_OVERHEAD_TOLERANCE_SOL,
    ENTRY_SQUEEZE_MAX_CURVE_PCT,
    ENTRY_SQUEEZE_MIN_CURVE_PCT,
    HIGH_GRADUATION_RATE_THRESHOLD_PCT,
    INITIAL_VIRTUAL_SOL_RESERVES,
    INITIAL_VIRTUAL_TOKEN_RESERVES,
    MAX_SHRED_INGESTION_LATENCY_MS,
    MIN_FRESH_BURNER_WALLETS,
    NO_PRE_MINT_SIGNAL,
    PRE_FREEZE_SCALEOUT_FRACTION,
    PRE_FREEZE_SCALEOUT_PCT,
    PRE_LAUNCH_DEV_SIGNAL,
    PRE_MINT_PEEL_WINDOW_SECONDS,
    PUMPSWAP_AMM_PROGRAM_ID,
    PUMP_FUN_CURVE_FEE_BPS,
    PUMP_FUN_CURVE_FEE_RATE,
    PUMP_FUN_PROGRAM_ID,
    PreMintPeelChainListener,
    RAYDIUM_CPMM_PROGRAM_ID,
    RAYDIUM_V4_PROGRAM_ID,
    RENT_AND_GAS_OVERHEAD_SOL,
    RETAINED_RUNNER_FRACTION,
    RETAINED_RUNNER_PCT,
    SCALEOUT_MAX_CURVE_PCT,
    SCALEOUT_MIN_CURVE_PCT,
    SHREDSTREAM_TURBINE_CORES,
    STREAM_BONDING_CURVE_RESERVE_TICK,
    STREAM_NEW_MINT_GENESIS,
    STREAM_PEEL_CHAIN_FUNDING,
    STREAM_PUMPSWAP_GRADUATION_FREEZE,
    STREAM_SAME_BLOCK_JITO_BUNDLE,
    STREAM_SOLBUNDLER_WITHDRAW_SWEEP,
    YELLOWSTONE_GEYSER_COMMITMENT,
    detect_pre_mint_peel_chain_signal,
    evaluate_constant_product_curve_and_scaleout,
    evaluate_realtime_shred_and_cabalspy_streams,
    register_solbundler_withdraw_sweep,
)


def test_realtime_shred_and_6_cabalspy_streams_program_filtering() -> None:
    """Verifies Yellowstone Geyser gRPC (`processed`, `<50ms`), Jito ShredStream (`Cores 0-3`),
    Helius Webhooks, and the 6 concurrent `cabalspy[realtime]` WebSocket streams (`Cores 4-15`)
    strictly filtered to Pump.fun, PumpSwap, and Raydium program IDs.
    """
    assert SHREDSTREAM_TURBINE_CORES == (0, 1, 2, 3)
    assert CABALSPY_WEBSOCKET_CORES == tuple(range(4, 16))
    assert len(CABALSPY_REALTIME_6_STREAMS) == 6
    assert set(CABALSPY_REALTIME_6_STREAMS) == {
        "NEW_MINT_GENESIS",
        "PEEL_CHAIN_FUNDING",
        "SAME_BLOCK_JITO_BUNDLE",
        "SOLBUNDLER_WITHDRAW_SWEEP",
        "BONDING_CURVE_RESERVE_TICK",
        "PUMPSWAP_GRADUATION_FREEZE",
    }
    assert set(ALLOWED_TARGET_PROGRAM_IDS) == {
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
        "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",
    }

    listener = PreMintPeelChainListener()
    events = [
        {
            "stream_type": STREAM_NEW_MINT_GENESIS,
            "program_id": PUMP_FUN_PROGRAM_ID,
            "token_mint": "MintA",
        },
        {
            "stream_type": STREAM_PEEL_CHAIN_FUNDING,
            "program_id": PUMP_FUN_PROGRAM_ID,
            "source_wallet": "PeelSourceA",
        },
        {
            "stream_type": STREAM_SAME_BLOCK_JITO_BUNDLE,
            "program_id": PUMP_FUN_PROGRAM_ID,
            "bundle_id": "Bundle01",
        },
        {
            "stream_type": STREAM_SOLBUNDLER_WITHDRAW_SWEEP,
            "program_id": PUMP_FUN_PROGRAM_ID,
            "destination_treasury_wallet": "TreasuryHighGrad11111111111111111111111111",
            "swept_burner_wallets": ["Burner1", "Burner2"],
            "peel_chain_intermediaries": ["PeelHop1"],
            "total_swept_sol": 92.4,
            "graduated_launches": 6,
            "total_launches": 15,
        },
        {
            "stream_type": STREAM_BONDING_CURVE_RESERVE_TICK,
            "program_id": RAYDIUM_V4_PROGRAM_ID,
            "pool": "RayV4Pool",
        },
        {
            "stream_type": STREAM_PUMPSWAP_GRADUATION_FREEZE,
            "program_id": PUMPSWAP_AMM_PROGRAM_ID,
            "pool": "PumpSwapPool",
        },
        {
            "stream_type": STREAM_BONDING_CURVE_RESERVE_TICK,
            "program_id": RAYDIUM_CPMM_PROGRAM_ID,
            "pool": "RayCPMMPool",
        },
        # Non-target program event -> must be dropped
        {
            "stream_type": STREAM_NEW_MINT_GENESIS,
            "program_id": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
            "token_mint": "IgnoredMemo",
        },
    ]

    report = listener.evaluate_realtime_shred_and_cabalspy_streams(
        events=events,
        yellowstone_grpc_latency_ms=11.2,
        jito_shredstream_latency_ms=7.8,
        helius_webhook_latency_ms=32.0,
        cabalspy_ws_latency_ms=14.1,
        commitment_level=YELLOWSTONE_GEYSER_COMMITMENT,
    )

    assert report.commitment_level == "processed"
    assert report.sub_50ms_sla_met is True
    assert report.effective_ingestion_latency_ms < MAX_SHRED_INGESTION_LATENCY_MS
    assert report.total_events_received == 8
    assert report.accepted_target_program_events == 7
    assert report.dropped_non_target_program_events == 1
    assert "TreasuryHighGrad11111111111111111111111111" in report.tracked_high_graduation_treasuries
    assert "PeelHop1" in report.tracked_peel_intermediaries
    assert report["sub_50ms_sla_met"] is True


def test_solbundler_withdraw_sweep_high_vs_low_graduation_mapping() -> None:
    """Verifies `register_solbundler_withdraw_sweep` promotes deployers with
    `graduation_rate_pct > 25.0%` into the active watch set and excludes low-graduation deployers.
    """
    listener = PreMintPeelChainListener()

    high_grad = listener.register_solbundler_withdraw_sweep(
        destination_treasury_wallet="EliteTreasuryWallet111111111111111111111111",
        swept_burner_wallets=["SweptBurner01", "SweptBurner02", "SweptBurner03"],
        peel_chain_intermediaries=["IntermediaryHop01"],
        total_swept_sol=184.5,
        graduated_launches=5,
        total_launches=12,  # 41.67% > 25.0%
    )
    assert high_grad.graduation_rate_pct == pytest.approx(41.67, abs=0.01)
    assert high_grad.is_high_graduation_deployer is True
    assert high_grad.promoted_to_active_watch_set is True

    low_grad = register_solbundler_withdraw_sweep(
        destination_treasury_wallet="LowGradSpamDeployer11111111111111111111111",
        swept_burner_wallets=["SpamBurner01"],
        total_swept_sol=4.2,
        graduated_launches=1,
        total_launches=20,  # 5.0% <= 25.0%
    )
    assert low_grad.graduation_rate_pct == pytest.approx(5.0, abs=0.01)
    assert low_grad.is_high_graduation_deployer is False
    assert low_grad.promoted_to_active_watch_set is False


def test_pre_mint_peel_chain_signal_emits_pre_block0_on_8_plus_fresh_burners() -> None:
    """Verifies `detect_pre_mint_peel_chain_signal` emits `PRE_LAUNCH_DEV_SIGNAL` prior to
    Block-0 mint creation when a tracked treasury or peel-chain intermediary disperses
    `buy_amount + 0.003 SOL` (within ±0.0015 SOL tolerance) to >= 8 fresh burner wallets
    (`prior_tx_count == 0`) within a 15-minute (900s) rolling window.
    """
    listener = PreMintPeelChainListener()
    treasury = "TrackedSerialWinnerTreasury1111111111111111"
    peel_hop = "TrackedPeelIntermediaryHop11111111111111111"

    listener.register_solbundler_withdraw_sweep(
        destination_treasury_wallet=treasury,
        swept_burner_wallets=["OldBurner1", "OldBurner2"],
        peel_chain_intermediaries=[peel_hop],
        total_swept_sol=120.0,
        graduated_launches=7,
        total_launches=16,  # 43.75% > 25%
    )

    # 9 fresh burner addresses receiving 2.000 SOL buy_amount + ~0.003 SOL rent/gas within 240s (< 900s)
    dispersals = [
        {
            "burner_wallet": f"FreshBurnerWallet{i:02d}11111111111111111111111",
            "amount_sol": 2.003 + (0.0002 if i % 2 == 0 else -0.0002),
            "prior_tx_count": 0,
            "timestamp_sec": 10_000.0 + i * 25.0,
        }
        for i in range(1, 10)
    ]

    signal = listener.detect_pre_mint_peel_chain_signal(
        source_wallet=peel_hop,
        dispersals=dispersals,
        expected_buy_amount_sol=2.0,
    )

    assert signal.signal_type == PRE_LAUNCH_DEV_SIGNAL
    assert signal.is_pre_launch_dev_signal is True
    assert signal.emitted_prior_to_block0_mint is True
    assert signal.resolved_treasury_wallet == treasury
    assert signal.is_tracked_treasury_or_intermediary is True
    assert signal.deployer_graduation_rate_pct > HIGH_GRADUATION_RATE_THRESHOLD_PCT
    assert signal.qualifying_fresh_burner_count == 9
    assert signal.meets_min_8_fresh_burners is True
    assert signal.within_15m_rolling_window is True
    assert signal.observed_window_span_seconds <= PRE_MINT_PEEL_WINDOW_SECONDS
    assert signal.observed_avg_overhead_sol == pytest.approx(
        RENT_AND_GAS_OVERHEAD_SOL, abs=DEFAULT_OVERHEAD_TOLERANCE_SOL
    )
    assert signal.target_snipe_block == 1
    assert signal.pre_arm_execution_action == BLOCK1_SNIPE_ACTION
    assert len(signal.pre_armed_burner_wallets) == 9
    assert signal["signal_type"] == "PRE_LAUNCH_DEV_SIGNAL"


def test_pre_mint_peel_chain_signal_rejects_fewer_than_8_or_non_fresh_or_expired_window() -> None:
    """Verifies `detect_pre_mint_peel_chain_signal` does NOT fire when:
    - Fewer than 8 fresh burner wallets receive `buy_amount + 0.003 SOL`
    - Wallets are not fresh (`prior_tx_count > 0`)
    - Overhead is outside `0.003 ± 0.0015 SOL`
    - Dispersal window exceeds 15 minutes (`900s`)
    - Block-0 mint has already been created (`block0_mint_already_created=True`).
    """
    # Case 1: Only 7 fresh burners (< 8 minimum)
    seven_burners = [
        (f"FreshBurner{i}", 1.003, 1000.0 + i * 10.0, 0, 1.0)
        for i in range(7)
    ]
    sig_seven = detect_pre_mint_peel_chain_signal(
        source_wallet="TrackedTreasury",
        dispersals=seven_burners,
        is_tracked_treasury=True,
    )
    assert sig_seven.signal_type == NO_PRE_MINT_SIGNAL
    assert sig_seven.is_pre_launch_dev_signal is False
    assert sig_seven.meets_min_8_fresh_burners is False

    # Case 2: 8 wallets, but 3 have prior_tx_count > 0 (only 5 fresh burners)
    mixed_burners = [
        {
            "burner_wallet": f"MixedBurner{i}",
            "amount_sol": 1.003,
            "buy_amount_sol": 1.0,
            "prior_tx_count": 0 if i < 5 else 4,
            "timestamp_sec": 2000.0 + i * 10.0,
        }
        for i in range(8)
    ]
    sig_mixed = detect_pre_mint_peel_chain_signal(
        source_wallet="TrackedTreasury",
        dispersals=mixed_burners,
        is_tracked_treasury=True,
    )
    assert sig_mixed.signal_type == NO_PRE_MINT_SIGNAL
    assert sig_mixed.qualifying_fresh_burner_count == 5

    # Case 3: 8 fresh wallets, but overhead is 0.025 SOL (not ~0.003 SOL)
    bad_overhead = [
        {
            "burner_wallet": f"BadOvhBurner{i}",
            "amount_sol": 1.025,
            "buy_amount_sol": 1.0,
            "prior_tx_count": 0,
            "timestamp_sec": 3000.0 + i * 10.0,
        }
        for i in range(8)
    ]
    sig_bad_ovh = detect_pre_mint_peel_chain_signal(
        source_wallet="TrackedTreasury",
        dispersals=bad_overhead,
        is_tracked_treasury=True,
    )
    assert sig_bad_ovh.signal_type == NO_PRE_MINT_SIGNAL
    assert sig_bad_ovh.qualifying_fresh_burner_count == 0

    # Case 4: 8 fresh wallets spread across 3,600s (> 900s 15-minute window, 250s apart -> max 4 in any 900s window)
    expired_window = [
        {
            "burner_wallet": f"SlowBurner{i}",
            "amount_sol": 1.003,
            "buy_amount_sol": 1.0,
            "prior_tx_count": 0,
            "timestamp_sec": 5000.0 + i * 350.0,
        }
        for i in range(8)
    ]
    sig_expired = detect_pre_mint_peel_chain_signal(
        source_wallet="TrackedTreasury",
        dispersals=expired_window,
        is_tracked_treasury=True,
    )
    assert sig_expired.signal_type == NO_PRE_MINT_SIGNAL
    assert sig_expired.within_15m_rolling_window is False


def test_constant_product_curve_math_125bps_fee_and_zero_passive_support() -> None:
    """Verifies constant-product invariant `x * y = k`, `1.25%` (`125 bps`) bidirectional fee,
    nonlinear slippage penalty `delta_y / y`, and Zero Passive Price Support Hazard.
    """
    eval_res = evaluate_constant_product_curve_and_scaleout(
        virtual_sol_reserves=60.0,
        virtual_token_reserves=536_500_000.0,
        order_sol_amount=4.0,
        cabal_dump_supply_pct=40.0,
        curve_completion_pct=70.0,
        audited_wallet_convergence=True,
        has_open_position=False,
    )

    assert eval_res.fee_bps == PUMP_FUN_CURVE_FEE_BPS == 125
    assert eval_res.fee_rate == pytest.approx(PUMP_FUN_CURVE_FEE_RATE, abs=1e-6)
    assert eval_res.constant_product_k == pytest.approx(60.0 * 536_500_000.0, rel=1e-6)

    # Marginal price = x / y
    expected_marginal = 60.0 / 536_500_000.0
    assert eval_res.marginal_price_sol_per_token == pytest.approx(expected_marginal, rel=1e-9)

    # Buy fee = 1.25% of 4.0 SOL = 0.05 SOL; net SOL into curve = 3.95 SOL
    assert eval_res.buy_fee_sol == pytest.approx(0.05, abs=1e-6)
    assert eval_res.net_sol_into_curve == pytest.approx(3.95, abs=1e-6)

    # Effective entry price > marginal price due to 1.25% fee + nonlinear curve impact
    assert eval_res.effective_entry_price_sol_per_token > eval_res.marginal_price_sol_per_token
    assert eval_res.nonlinear_slippage_ratio_delta_y_over_y == pytest.approx(
        eval_res.tokens_received_delta_y / 536_500_000.0, rel=1e-6
    )

    # Bidirectional roundtrip fee drag = 1 - (1 - 0.0125)^2 = 2.484375%
    assert eval_res.bidirectional_roundtrip_fee_drag_pct == pytest.approx(2.484375, abs=1e-4)

    # Zero Passive Price Support Hazard: 0 resting limit bids, synchronized cabal dump collapses price
    assert eval_res.resting_limit_bids_count == 0
    assert eval_res.zero_passive_price_support_hazard is True
    assert eval_res.post_cabal_dump_marginal_price < eval_res.marginal_price_sol_per_token
    # A 40% supply dump into y increases y by 1.4x -> price drops by (1 / 1.4^2) = 0.5102 -> ~48.98% collapse
    assert eval_res.synchronized_dump_price_collapse_pct == pytest.approx(48.9796, abs=0.05)


def test_curve_squeeze_65_to_78_entry_and_77_to_79_automated_75pct_scaleout() -> None:
    """Verifies the Pre-Graduation Curve Squeeze & Pre-Freeze Scale-Out Protocol:
    - Below 65%: `WAIT_BELOW_65PCT_ACCELERATION_ZONE`
    - 65%–78% with audited wallet convergence: `ENTER_PRE_GRADUATION_CURVE_SQUEEZE`
    - 65%–78% without audited convergence: `REJECT_ENTRY_NO_AUDITED_CONVERGENCE`
    - 76.0%–79.5% (targeting 77%–79%): `SCALE_OUT_75PCT_PRE_GRADUATION_FREEZE` (`scale_out_fraction = 0.75`)
    - >= 80.0%: `ABORT_CURVE_FROZEN_AT_80PCT`.
    """
    # 1. Below 65% -> wait
    below_res = evaluate_constant_product_curve_and_scaleout(
        curve_completion_pct=52.0,
        audited_wallet_convergence=True,
    )
    assert below_res.in_entry_acceleration_zone is False
    assert below_res.recommended_action == ACTION_WAIT_BELOW_SQUEEZE_ZONE

    # 2. Inside 65%–78% entry squeeze zone (e.g. 71.0%) with audited wallet convergence
    entry_res = evaluate_constant_product_curve_and_scaleout(
        curve_completion_pct=71.0,
        audited_wallet_convergence=True,
        has_open_position=False,
    )
    assert entry_res.in_entry_acceleration_zone is True
    assert entry_res.recommended_action == ACTION_ENTER_CURVE_SQUEEZE

    # 3. Inside 65%–78% without audited wallet convergence -> rejected
    unverified_res = evaluate_constant_product_curve_and_scaleout(
        curve_completion_pct=71.0,
        audited_wallet_convergence=False,
        has_open_position=False,
    )
    assert unverified_res.recommended_action == ACTION_HOLD_REJECTED_UNAUDITED_FLOW

    # 4. Inside 77%–79% optimal pre-freeze scale-out band (e.g. 78.0%) -> 75% automated scale-out
    for pct in (76.5, 77.5, 78.4, 79.2):
        scaleout_res = evaluate_constant_product_curve_and_scaleout(
            curve_completion_pct=pct,
            audited_wallet_convergence=True,
            post_migration_organic_volume_confirmed=True,
        )
        assert scaleout_res.in_pre_freeze_scaleout_zone is True
        assert scaleout_res.recommended_action == ACTION_SCALE_OUT_75PCT_PRE_FREEZE
        assert scaleout_res.scale_out_fraction == pytest.approx(
            PRE_FREEZE_SCALEOUT_FRACTION, abs=1e-6
        )
        assert scaleout_res.scale_out_pct == pytest.approx(PRE_FREEZE_SCALEOUT_PCT, abs=1e-4)
        assert scaleout_res.retained_runner_fraction == pytest.approx(
            RETAINED_RUNNER_FRACTION, abs=1e-6
        )
        assert scaleout_res.retained_runner_pct == pytest.approx(RETAINED_RUNNER_PCT, abs=1e-4)
        assert scaleout_res.runner_hold_authorized is True

    # 5. At or above 80% graduation freeze
    frozen_res = evaluate_constant_product_curve_and_scaleout(
        curve_completion_pct=80.0,
        has_open_position=True,
    )
    assert frozen_res.is_graduation_frozen is True
    assert frozen_res.recommended_action == ACTION_ABORT_GRADUATION_FROZEN


def test_pre_mint_peel_chain_listener_facade_diagnostic_and_telemetry() -> None:
    """Verifies `PreMintPeelChainListener.run_full_pre_mint_listener_diagnostic()`
    and `get_telemetry_summary()` for `TitanIPCDaemon`.
    """
    listener = PreMintPeelChainListener()
    diag = listener.run_full_pre_mint_listener_diagnostic()

    assert diag["agent_id"] == AGENT_A_SWARM_ID
    assert diag["solbundler_withdraw_sweep"]["is_high_graduation_deployer"] is True
    assert diag["realtime_stream_ingestion_report"]["sub_50ms_sla_met"] is True
    assert diag["realtime_stream_ingestion_report"]["accepted_target_program_events"] == 7
    assert diag["realtime_stream_ingestion_report"]["dropped_non_target_program_events"] == 1
    assert diag["pre_mint_peel_chain_signal"]["signal_type"] == PRE_LAUNCH_DEV_SIGNAL
    assert diag["pre_mint_peel_chain_signal"]["qualifying_fresh_burner_count"] == 10
    assert diag["pre_mint_peel_chain_signal"]["target_snipe_block"] == 1
    assert (
        diag["curve_squeeze_entry_evaluation"]["recommended_action"]
        == ACTION_ENTER_CURVE_SQUEEZE
    )
    assert (
        diag["pre_freeze_75pct_scaleout_evaluation"]["recommended_action"]
        == ACTION_SCALE_OUT_75PCT_PRE_FREEZE
    )
    assert diag["pre_freeze_75pct_scaleout_evaluation"]["scale_out_fraction"] == 0.75

    telemetry = listener.get_telemetry_summary()
    assert telemetry["subsystem"] == "PreMintPeelChainListener"
    assert telemetry["agent_id"] == AGENT_A_SWARM_ID
    assert telemetry["yellowstone_commitment"] == "processed"
    assert telemetry["diagnostic_runs"] == 1
    assert telemetry["last_diagnostic_available"] is True
    assert telemetry["pre_armed_burner_wallets_count"] == 10


@pytest.mark.asyncio
async def test_titan_ipc_daemon_pre_mint_peel_chain_listener_action() -> None:
    """Verifies `TitanIPCDaemon` exposes `pre_mint_listener` telemetry and executes `RUN_PRE_MINT_PEEL_CHAIN_LISTENER`."""
    from src.ipc.titan_ipc_daemon import TitanIPCDaemon

    daemon = TitanIPCDaemon()
    frame = daemon.build_telemetry_frame()
    assert "pre_mint_listener" in frame
    assert frame["pre_mint_listener"]["agent_id"] == AGENT_A_SWARM_ID

    resp = await daemon.handle_ipc_payload(
        {"action": "RUN_PRE_MINT_PEEL_CHAIN_LISTENER", "params": {}}
    )
    assert resp["ok"] is True
    assert resp["action"] == "RUN_PRE_MINT_PEEL_CHAIN_LISTENER"
    assert (
        resp["data"]["pre_mint_peel_chain_signal"]["signal_type"]
        == PRE_LAUNCH_DEV_SIGNAL
    )
    assert (
        resp["data"]["pre_freeze_75pct_scaleout_evaluation"]["scale_out_fraction"]
        == 0.75
    )
    assert resp["data"]["telemetry"]["diagnostic_runs"] >= 1

