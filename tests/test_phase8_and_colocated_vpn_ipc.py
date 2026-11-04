"""Comprehensive unit and integration test suite for:
  1. Phase 8 Apex Predator 7-Module Suite + NVMe Checkpoint Manager (8 modules):
     - `AtomicFlashLiquidator` (`src/engines/atomic_flash_liquidator.py`)
     - `CexDexLeadLagEngine` / `CEXDEXLeadLagEngine` (`src/engines/cex_dex_lead_lag.py`)
     - `ZeroSlotMigrationArbEngine` (`src/engines/zero_slot_migration_arb.py`)
     - `DynamicContentionTipOptimizer` (`src/execution/dynamic_contention_tip_optimizer.py`)
     - `MultiVenueSplitRouter` (`src/execution/multi_venue_split_router.py`)
     - `AlphaConsensusQuorumGate` (`src/intelligence/alpha_consensus_quorum.py`)
     - `ShredExitFrontRunner` (`src/security/shred_exit_frontrunner.py`)
     - `NVMeCheckpointManager` (`src/memory/nvme_checkpoint_manager.py`)
  2. `TitanIPCDaemon` Co-Located VPN Mesh, Memory Checkpoint, Drift Hedge, Shard & Position Lock actions:
     - `SWITCH_COLOCATED_VPN_MODE`
     - `TOGGLE_COLOCATED_TUNNEL`
     - `PROBE_COLOCATED_VPN_MESH`
     - `CHECKPOINT_MEMORY_NOW`
     - `SET_DRIFT_HEDGE_MODE`
     - `RECLAIM_SHARD_RENT`
     - `ROTATE_SHARD`
     - `TOGGLE_POSITION_LOCK`
  3. `TitanCLIController` unified CLI subcommands (`swarm boot`, `swarm status`, `swarm agents`, `vpn [status|probe|mode]`).
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cli.titan_cli import TitanCLIController
from src.engines.atomic_flash_liquidator import (
    AtomicFlashLiquidator,
    UnderwaterObligationCandidate,
)
from src.engines.cex_dex_lead_lag import CexDexLeadLagEngine
from src.engines.zero_slot_migration_arb import ZeroSlotMigrationArbEngine
from src.execution.dynamic_contention_tip_optimizer import DynamicContentionTipOptimizer
from src.execution.multi_venue_split_router import MultiVenueSplitRouter
from src.intelligence.alpha_consensus_quorum import AlphaConsensusQuorumGate
from src.ipc.titan_ipc_daemon import TitanIPCDaemon
from src.memory.nvme_checkpoint_manager import NVMeCheckpointManager
from src.security.shred_exit_frontrunner import (
    ShredExitFrontRunner,
    ShredThreatObservation,
)
from src.security.sybil_wash_auditor import SybilWashAuditor

# Canonical alias requested by audit specification
CEXDEXLeadLagEngine = CexDexLeadLagEngine


def test_atomic_flash_liquidator_safe_and_underwater_obligations() -> None:
    """Verifies `AtomicFlashLiquidator` rejects healthy obligations (`HF >= 1.0`)
    and compiles <1,150B Kamino Flash-Loan + ProfitGuard V0 liquidation bundles for underwater obligations.
    """
    liquidator = AtomicFlashLiquidator()
    initial_landed = liquidator.liquidations_landed_today

    safe_candidate = UnderwaterObligationCandidate(
        obligation_address="SafeOblig111111111111111111111111111111111",
        venue="KAMINO_KLEND",
        collateral_mint="SafeCollateralMint1111111111111111111111111",
        debt_sol=350.0,
        health_factor=1.08,
    )
    safe_res = liquidator.execute_flash_liquidation(safe_candidate)
    assert safe_res.triggered is False
    assert safe_res.flash_borrowed_sol == 0.0
    assert safe_res.net_retained_profit_sol == 0.0
    assert "HEALTH_FACTOR_SAFE" in safe_res.reason

    for venue in ("KAMINO_KLEND", "MARGINFI_V2", "DRIFT_MARGIN"):
        underwater = UnderwaterObligationCandidate(
            obligation_address=f"Underwater{venue[:6]}11111111111111111111111111",
            venue=venue,  # type: ignore[arg-type]
            collateral_mint=f"Collateral{venue[:6]}1111111111111111111111111",
            debt_sol=600.0,
            health_factor=0.89,
            liquidation_bonus_bps=680.0,
            dex_slippage_bps=80.0,
        )
        res = liquidator.execute_flash_liquidation(underwater, jito_tip_share_pct=30.0)
        assert res.triggered is True
        assert res.venue == venue
        assert res.flash_borrowed_sol == pytest.approx(600.0)
        assert res.gross_liquidation_bonus_sol == pytest.approx(36.0)  # 600 * 6.0%
        assert res.jito_tip_sol == pytest.approx(10.8)
        assert res.net_retained_profit_sol == pytest.approx(25.2)
        assert 0 < res.v0_tx_bytes < 1150
        assert res.to_dict()["triggered"] is True

    assert liquidator.liquidations_landed_today == initial_landed + 3


def test_cex_dex_lead_lag_engine_bull_bear_and_neutral_regimes() -> None:
    """Verifies `CEXDEXLeadLagEngine` (`CexDexLeadLagEngine`) across bullish impulse,
    bearish flush stop-tightening, and neutral equilibrium ticks.
    """
    engine = CEXDEXLeadLagEngine()
    base_snipes = engine.lead_lag_snipes_today

    # 1. Bullish CEX impulse (>= +0.35%) -> Flash-Loan stale CLMM bin snipe
    bull = engine.evaluate_cex_perp_tick(
        cex_sol_price_usd=198.20,
        dex_sol_price_usd=196.80,
        cex_100ms_return_pct=0.58,
        open_positions_count=3,
        cex_venue="BINANCE_PERP_WS",
    )
    assert bull.triggered is True
    assert bull.action == "FLASH_SNIPE_STALE_CLMM_BINS"
    assert bull.flash_borrow_sol == pytest.approx(1500.0)
    assert bull.net_arb_profit_sol > 0.0
    assert engine.lead_lag_snipes_today == base_snipes + 1

    # 2. Bearish CEX flush (<= -0.40%) -> Pre-emptive 1.5% Trail-Win stop tighten
    bear = engine.evaluate_cex_perp_tick(
        cex_sol_price_usd=194.50,
        dex_sol_price_usd=196.10,
        cex_100ms_return_pct=-0.62,
        open_positions_count=4,
        cex_venue="BYBIT_PERP_WS",
    )
    assert bear.triggered is True
    assert bear.action == "PREEMPTIVE_TRAIL_STOP_TIGHTEN_1_5PCT"
    assert bear.trail_stops_tightened_count == 4
    assert bear.flash_borrow_sol == 0.0

    # 3. Neutral equilibrium
    neutral = engine.evaluate_cex_perp_tick(
        cex_sol_price_usd=196.50,
        dex_sol_price_usd=196.45,
        cex_100ms_return_pct=0.05,
        open_positions_count=2,
    )
    assert neutral.triggered is False
    assert neutral.action == "NEUTRAL_NO_IMPULSE"
    assert neutral.to_dict()["reason"] == "CEX_DEX_EQUILIBRIUM"


def test_zero_slot_migration_arb_engine_twin_pool_and_blind_sniper() -> None:
    """Verifies `ZeroSlotMigrationArbEngine` Strategy M1 (`ZERO_SLOT_TWIN_POOL_FLASH_ARB`)
    and Strategy M2 (`ZERO_SLOT_BLIND_SNIPER_SANDWICH`).
    """
    mig_engine = ZeroSlotMigrationArbEngine()
    initial_count = mig_engine.migrations_captured_today

    # Strategy M1: Sibling dislocation >= 6.0% -> Kamino 0-Fee Flash-Loan Arb
    res_m1 = mig_engine.evaluate_zero_slot_migration(
        token_mint="GradTwinArbMint1111111111111111111111111111",
        migration_venue="PUMPSWAP_CPMM",
        seeded_lp_sol=85.0,
        sibling_dislocation_pct=12.5,
    )
    assert res_m1.triggered is True
    assert res_m1.strategy == "ZERO_SLOT_TWIN_POOL_FLASH_ARB"
    assert res_m1.net_profit_sol > 0.0
    assert 0 < res_m1.v0_tx_bytes < 1150

    # Strategy M2: Blind Slot-0 sniper sandwich (dislocation < 6.0%)
    res_m2 = mig_engine.evaluate_zero_slot_migration(
        token_mint="GradSniperMint11111111111111111111111111111",
        migration_venue="RAYDIUM_CPMM",
        seeded_lp_sol=85.0,
        sibling_dislocation_pct=2.0,
        blind_sniper_buy_sol=30.0,
        blind_sniper_slippage_bps=1800.0,
    )
    assert res_m2.triggered is True
    assert res_m2.strategy == "ZERO_SLOT_BLIND_SNIPER_SANDWICH"
    assert res_m2.net_profit_sol > 0.0
    assert 0 < res_m2.v0_tx_bytes < 1150
    assert mig_engine.migrations_captured_today == initial_count + 2


def test_dynamic_contention_tip_optimizer_all_regimes() -> None:
    """Verifies `DynamicContentionTipOptimizer` across uncontested (14%), moderate (36%),
    and high contention auction war (62%) regimes.
    """
    optimizer = DynamicContentionTipOptimizer()

    uncontested = optimizer.optimize_jito_tip(gross_ev_sol=2.0, rival_bundles_detected=0)
    assert uncontested.regime == "UNCONTESTED_POOL_86PCT_RETAINED"
    assert uncontested.optimized_tip_pct == pytest.approx(14.0)
    assert uncontested.optimized_tip_sol == pytest.approx(0.28)
    assert uncontested.retained_net_profit_sol == pytest.approx(1.72)
    assert uncontested.tip_rebate_saved_sol == pytest.approx(0.88)  # 1.16 - 0.28

    moderate = optimizer.optimize_jito_tip(gross_ev_sol=2.0, rival_bundles_detected=2)
    assert moderate.regime == "MODERATE_CONTENTION_64PCT_RETAINED"
    assert moderate.optimized_tip_pct == pytest.approx(36.0)
    assert moderate.retained_net_profit_sol == pytest.approx(1.28)
    assert moderate.tip_rebate_saved_sol == pytest.approx(0.44)

    high = optimizer.optimize_jito_tip(gross_ev_sol=2.0, rival_bundles_detected=5)
    assert high.regime == "HIGH_CONTENTION_AUCTION_WAR"
    assert high.optimized_tip_pct == pytest.approx(62.0)
    assert high.retained_net_profit_sol == pytest.approx(0.76)
    assert high.tip_rebate_saved_sol == pytest.approx(0.0)


def test_multi_venue_split_router_reduces_price_impact() -> None:
    """Verifies `MultiVenueSplitRouter` splits orders across sibling pools and reduces slippage."""
    router = MultiVenueSplitRouter()
    res = router.compute_optimal_split(
        token_mint="SplitRouteMint11111111111111111111111111111",
        total_order_sol=24.0,
    )
    assert res.venues_used == 3
    assert len(res.allocations) == 3
    assert res.split_order_price_impact_pct < res.single_pool_price_impact_pct
    assert res.slippage_saved_bps > 0.0
    assert res.slippage_saved_sol > 0.0
    total_allocated = sum(float(a["allocated_sol"]) for a in res.allocations)
    assert total_allocated == pytest.approx(24.0, abs=0.05)


def test_alpha_consensus_quorum_gate_solo_super_and_sybil_block() -> None:
    """Verifies `AlphaConsensusQuorumGate` VPIN calculation, 0.5x solo scout,
    2.0x non-Sybil multi-shark super-signal, and 0.0x Sybil fake quorum block.
    """
    auditor = SybilWashAuditor()
    gate = AlphaConsensusQuorumGate(sybil_auditor=auditor)

    vpin = gate.compute_vpin_score(buy_volume_sol=50.0, sell_volume_sol=5.0)
    assert 0.80 <= vpin <= 0.99

    mint_clean = "ConsensusGemMint111111111111111111111111111"
    now_s = 1_700_000_000.0

    # 1. Single shark -> 0.5x Scout
    solo = gate.record_shark_buy_and_evaluate(
        token_mint=mint_clean,
        shark_wallet="IndependentSharkA1111111111111111111111111",
        buy_sol=8.0,
        window_buy_vol_sol=20.0,
        window_sell_vol_sol=12.0,
        now_s=now_s,
    )
    assert solo.approved is True
    assert solo.tier == "SOLO_SHARK_SCOUT_0_5X"
    assert solo.sizing_multiplier == pytest.approx(0.5)

    # 2. Second independent shark within 15s -> 2.0x Super-Signal
    super_sig = gate.record_shark_buy_and_evaluate(
        token_mint=mint_clean,
        shark_wallet="IndependentSharkB2222222222222222222222222",
        buy_sol=14.0,
        window_buy_vol_sol=55.0,
        window_sell_vol_sol=6.0,
        now_s=now_s + 3.0,
    )
    assert super_sig.approved is True
    assert super_sig.tier == "CONSENSUS_SUPER_SIGNAL_2_0X"
    assert super_sig.independent_non_sybil_sharks == 2
    assert super_sig.sizing_multiplier == pytest.approx(2.0)

    # 3. Sybil Fake Quorum: two burner wallets funded by the same root ancestor
    sybil_root = "CabalMasterFunder11111111111111111111111111"
    sybil_b1 = "CabalPuppetBurnerA111111111111111111111111"
    sybil_b2 = "CabalPuppetBurnerB222222222222222222222222"
    auditor.burner_graph.ingest_sol_transfer(sybil_root, sybil_b1, 15.0, timestamp_s=now_s)
    auditor.burner_graph.ingest_sol_transfer(sybil_root, sybil_b2, 15.0, timestamp_s=now_s)

    mint_sybil = "SybilTrapMint111111111111111111111111111111"
    gate.record_shark_buy_and_evaluate(
        token_mint=mint_sybil,
        shark_wallet=sybil_b1,
        buy_sol=5.0,
        now_s=now_s,
    )
    sybil_eval = gate.record_shark_buy_and_evaluate(
        token_mint=mint_sybil,
        shark_wallet=sybil_b2,
        buy_sol=5.0,
        now_s=now_s + 1.5,
    )
    assert sybil_eval.approved is False
    assert sybil_eval.tier == "SYBIL_FAKE_QUORUM_BLOCKED"
    assert sybil_eval.sizing_multiplier == pytest.approx(0.0)


def test_shred_exit_frontrunner_all_threat_types(tmp_path: Path) -> None:
    """Verifies `ShredExitFrontRunner` detects LP pulls, authority mutations, and whale mega-dumps,
    compiling a 95th-percentile Jito V0 exit bundle with `0.00203928 SOL` ATA rent reclaim.
    """
    runner = ShredExitFrontRunner(state_path=tmp_path / "shred_exit_state.json")

    # 1. Benign small swap shred -> no exit
    benign = runner.evaluate_incoming_shred(
        ShredThreatObservation(
            token_mint="CleanHoldMint111111111111111111111111111111",
            pool_address="PoolClean111111111111111111111111111111111",
            signer_wallet="RetailTrader111111111111111111111111111111",
            instruction_name="swap_exact_in",
            sell_sol_equivalent=1.5,
            pool_r_sol=250.0,
            is_deployer_or_top_holder=False,
        )
    )
    assert benign.frontrun_triggered is False
    assert benign.threat_type == "NONE"

    # 2. LP pull shred -> emergency front-run exit
    lp_pull = runner.evaluate_incoming_shred(
        ShredThreatObservation(
            token_mint="RugPullMint11111111111111111111111111111111",
            pool_address="PoolRug11111111111111111111111111111111111",
            signer_wallet="DeployerRugger1111111111111111111111111111",
            instruction_name="remove_liquidity",
            sell_sol_equivalent=180.0,
            pool_r_sol=200.0,
            is_deployer_or_top_holder=True,
            our_position_sol=3.0,
            our_unrealized_pnl_pct=20.0,
        )
    )
    assert lp_pull.frontrun_triggered is True
    assert lp_pull.threat_type == "LP_PULL_SHRED_DETECTED"
    assert lp_pull.ata_rent_reclaimed_sol == pytest.approx(0.00203928)
    assert 0 < lp_pull.v0_tx_bytes < 1150

    # 3. Authority mutation shred -> emergency front-run exit
    auth_mut = runner.evaluate_incoming_shred(
        ShredThreatObservation(
            token_mint="FreezeAuthMint11111111111111111111111111111",
            pool_address="PoolFreeze11111111111111111111111111111111",
            signer_wallet="MaliciousAuth11111111111111111111111111111",
            instruction_name="freeze_account",
            sell_sol_equivalent=0.0,
            pool_r_sol=180.0,
        )
    )
    assert auth_mut.frontrun_triggered is True
    assert auth_mut.threat_type == "AUTHORITY_MUTATION_SHRED"

    # 4. Whale mega-dump (>= 12% of pool SOL reserve)
    whale_dump = runner.evaluate_incoming_shred(
        ShredThreatObservation(
            token_mint="WhaleDumpMint111111111111111111111111111111",
            pool_address="PoolWhale111111111111111111111111111111111",
            signer_wallet="TopHolderWhale1111111111111111111111111111",
            instruction_name="swap_exact_in_sell",
            sell_sol_equivalent=45.0,
            pool_r_sol=250.0,  # 18% >= 12%
            is_deployer_or_top_holder=True,
        )
    )
    assert whale_dump.frontrun_triggered is True
    assert whale_dump.threat_type == "DEV_OR_WHALE_MEGA_DUMP"


def test_nvme_checkpoint_manager_atomic_sync_and_cold_restore(tmp_path: Path) -> None:
    """Verifies `NVMeCheckpointManager` atomic file sync, manifest persistence,
    cold-boot detection, and restore from NVMe snapshot.
    """
    ramdisk_dir = tmp_path / "mock_ramdisk"
    snapshot_dir = tmp_path / "mock_nvme_snapshot"
    (ramdisk_dir / "execution_state").mkdir(parents=True, exist_ok=True)
    (ramdisk_dir / "alpha_profiles").mkdir(parents=True, exist_ok=True)

    mgr = NVMeCheckpointManager(ramdisk_root=ramdisk_dir, snapshot_dir=snapshot_dir)
    assert mgr.is_ramdisk_cold() is True
    assert mgr.has_nvme_snapshot() is False

    # Populate persistent RAMDisk files
    gepa_file = ramdisk_dir / "execution_state" / "gepa_arena_state.json"
    gepa_file.write_text('{"champion": "policy_v2"}', encoding="utf-8")
    profile_file = ramdisk_dir / "alpha_profiles" / "Shark1.json"
    profile_file.write_text('{"wallet": "Shark1"}', encoding="utf-8")

    assert mgr.is_ramdisk_cold() is False
    ckpt = mgr.checkpoint_now(reason="unit_test")
    assert ckpt.operation == "CHECKPOINT_TO_NVME"
    assert ckpt.files_synced >= 2
    assert ckpt.total_bytes_synced > 0
    assert mgr.has_nvme_snapshot() is True

    # Simulate warm RAMDisk noop
    noop = mgr.restore_if_ramdisk_cold()
    assert noop.operation == "NOOP_WARM_RAMDISK"

    # Simulate cold reboot by wiping RAMDisk files
    gepa_file.unlink()
    profile_file.unlink()
    assert mgr.is_ramdisk_cold() is True

    restored = mgr.restore_if_ramdisk_cold()
    assert restored.operation == "RESTORE_TO_RAMDISK"
    assert restored.files_synced >= 2
    assert gepa_file.exists()
    assert profile_file.exists()

    st = mgr.status()
    assert st["has_nvme_snapshot"] is True
    assert st["ramdisk_warm"] is True


@pytest.mark.asyncio
async def test_titan_ipc_daemon_colocated_vpn_and_operational_actions() -> None:
    """Verifies `TitanIPCDaemon` actions:
    - `SWITCH_COLOCATED_VPN_MODE`
    - `TOGGLE_COLOCATED_TUNNEL`
    - `PROBE_COLOCATED_VPN_MESH`
    - `CHECKPOINT_MEMORY_NOW`
    - `SET_DRIFT_HEDGE_MODE`
    - `RECLAIM_SHARD_RENT`
    - `ROTATE_SHARD`
    - `TOGGLE_POSITION_LOCK`
    plus CLI `swarm boot`, `swarm status`, `swarm agents`, and `vpn [status|probe|mode]`.
    """
    daemon = TitanIPCDaemon()

    # 1. SWITCH_COLOCATED_VPN_MODE
    r_vpn_mode = await daemon.handle_ipc_payload(
        {
            "action": "SWITCH_COLOCATED_VPN_MODE",
            "params": {"routing_mode": "PINNED_SINGLE_POP", "tunnel_id": "nyc-wg1"},
        }
    )
    assert r_vpn_mode["ok"] is True
    assert (
        r_vpn_mode["data"]["colocated_vpn_mesh"]["routing_mode"]
        == "PINNED_SINGLE_POP"
    )
    assert (
        r_vpn_mode["data"]["colocated_vpn_mesh"]["active_primary_tunnel_id"]
        == "nyc-wg1"
    )

    # 2. TOGGLE_COLOCATED_TUNNEL
    r_toggle = await daemon.handle_ipc_payload(
        {"action": "TOGGLE_COLOCATED_TUNNEL", "params": {"tunnel_id": "slc-wg4"}}
    )
    assert r_toggle["ok"] is True
    assert r_toggle["data"]["tunnel_id"] == "slc-wg4"
    assert r_toggle["data"]["enabled"] is False

    # Re-enable slc-wg4
    r_toggle_on = await daemon.handle_ipc_payload(
        {"action": "TOGGLE_COLOCATED_TUNNEL", "params": {"tunnel_id": "slc-wg4"}}
    )
    assert r_toggle_on["data"]["enabled"] is True

    # 3. PROBE_COLOCATED_VPN_MESH
    r_probe = await daemon.handle_ipc_payload(
        {"action": "PROBE_COLOCATED_VPN_MESH", "params": {}}
    )
    assert r_probe["ok"] is True
    assert r_probe["data"]["enabled_tunnels"] == 5
    assert 0.1 <= r_probe["data"]["best_rtt_ms"] <= 500.0
    assert r_probe["data"]["colocated_vpn_mesh"]["mtu_safe_verified"] is True
    assert "enp210s0f0np0" in r_probe["data"]["colocated_vpn_mesh"].get("nic_interfaces", {})

    # 4. CHECKPOINT_MEMORY_NOW
    r_ckpt = await daemon.handle_ipc_payload(
        {"action": "CHECKPOINT_MEMORY_NOW", "params": {}}
    )
    assert r_ckpt["ok"] is True
    assert r_ckpt["data"]["operation"] == "CHECKPOINT_TO_NVME"
    assert r_ckpt["data"]["files_synced"] >= 1

    # 5. SET_DRIFT_HEDGE_MODE
    r_hedge = await daemon.handle_ipc_payload(
        {"action": "SET_DRIFT_HEDGE_MODE", "params": {"mode": "100", "idle_treasury_sol": 50.0}}
    )
    assert r_hedge["ok"] is True
    assert r_hedge["data"]["hedge_ratio_pct"] == pytest.approx(100.0)
    assert r_hedge["data"]["short_perp_notional_sol"] == pytest.approx(50.0)

    # 6. RECLAIM_SHARD_RENT
    r_rent = await daemon.handle_ipc_payload(
        {"action": "RECLAIM_SHARD_RENT", "params": {"shard_index": 0}}
    )
    assert r_rent["ok"] is True
    assert r_rent["data"]["reclaimed"] is True
    assert r_rent["data"]["rent_reclaimed_sol"] == pytest.approx(0.00203928)

    # 7. ROTATE_SHARD
    r_rot = await daemon.handle_ipc_payload(
        {"action": "ROTATE_SHARD", "params": {"shard_index": 1}}
    )
    assert r_rot["ok"] is True
    assert r_rot["data"]["rotated"] is True

    # 8. TOGGLE_POSITION_LOCK
    if not daemon.open_positions:
        daemon.open_positions.append(
            {
                "position_id": "pos_test_01",
                "symbol": "TEST / SOL",
                "mint": "TestLockMint1111111111111111111111111111111",
                "size_sol": 1.0,
                "locked_manual": False,
            }
        )
    target_mint = daemon.open_positions[0]["mint"]
    r_lock = await daemon.handle_ipc_payload(
        {"action": "TOGGLE_POSITION_LOCK", "params": {"mint": target_mint}}
    )
    assert r_lock["ok"] is True
    assert isinstance(r_lock["data"]["locked_manual"], bool)

    # 9. Verify CLI `swarm boot`, `swarm status`, `swarm agents`, and `vpn [status|probe|mode]`
    cli = TitanCLIController()
    boot_out = await cli.execute_command(["swarm", "boot"])
    assert boot_out["primary_nic"] in ("enp210s0f0np0", "enp65s0f0")
    assert boot_out["agent_swarm"]["total_primary_agents"] == 32
    assert boot_out["agent_swarm"]["total_subagents"] == 96
    assert boot_out["colocated_vpn_mesh"]["mtu_safe_verified"] is True

    status_out = await cli.execute_command(["swarm", "status"])
    assert status_out["primary_nic"] in ("enp210s0f0np0", "enp65s0f0")
    assert status_out["agent_swarm"]["total_primary_agents"] == 32
    assert status_out["colocated_vpn_mesh"]["enabled_tunnels"] == 5

    agents_out = await cli.execute_command(["swarm", "agents"])
    assert agents_out["audit"]["total_primary_agents"] == 32
    assert agents_out["audit"]["total_subagents"] == 96

    vpn_status = await cli.execute_command(["vpn", "status"])
    assert vpn_status["summary"]["enabled_tunnels"] == 5

    vpn_probe = await cli.execute_command(["vpn", "probe"])
    assert vpn_probe["mtu_safe_verified"] is True

    vpn_mode = await cli.execute_command(
        ["vpn", "mode", "MULTI_POP_FANOUT_6X", "--tunnel", "fra-wg0"]
    )
    assert vpn_mode["routing_mode"] == "MULTI_POP_FANOUT_6X"
    assert vpn_mode["active_primary_tunnel_id"] == "fra-wg0"
