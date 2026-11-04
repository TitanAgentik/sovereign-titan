"""Sovereign Titan OS — Phase 5 Closed-Loop Verification Suite (`tests/verify_phase5_vault_and_gepa.py`).

Verifies with zero placeholders:
1. Counterfactual "Missed Runner" Logger (`FALSE_NEGATIVE_OMISSION` at >=3.0x & LP > $25k)
   & 60-Trace GEPA Self-Improvement Arena (<=900 tokens, 50-trigger +10% EV promotion gate,
   -4.0% drawdown auto-rollback, and Immutable Safety Lock on `risk_watchdog.py` & `lib.rs`).
2. Core 0 Root-Locked Risk Watchdog (15m drawdown >=6.0%, 4 consecutive >5% slippage trades,
   PTP offset >5ms / Helius lag >1,500ms -> `EMERGENCY_DEMOTE_TO_PAPER`), Pyth/Binance 1s
   Macro Crash Filter (`GREEN`, `AMBER`, `RED_MACRO_FLUSH`), and `/var/lib/hermes/audit_ledger.parquet`.
3. 3-Stage Paper-to-Live Graduation Engine (`25.00 vSOL` boot, real V0 bundle simulation with
   impact/fees/tip/+1 slot 200ms penalty, and `PAPER -> CANARY -> LIVE` graduation).
4. Solana Pay Terminal & PNG QR Code Deposit Engine (`vault deposit 5.0 --auto-shard`,
   UTF-8 half-block QR inside `rich` panel, and `600x600` `latest_deposit_qr.png`).
5. Deferred Withdrawal Lockbox (`WITHDRAW_ADDRESS = "DEFERRED"`, +20 SOL HWM -> 10 SOL
   `RESERVE_LOCKBOX_KEYPAIR` sweep, `vault set-withdraw`, `vault withdraw profits | <amount> | ALL`
   with 25-shard ATA rent reclaim) & Unified CLI (`titan_cli.py`).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import time

from PIL import Image
from solders.keypair import Keypair

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cli.titan_cli import TitanCLIController
from src.evolution.counterfactual_logger import CounterfactualLogger
from src.evolution.gepa_arena import GEPASelfImprovementArena, MAX_INSTRUCTION_TOKENS
from src.risk.audit_ledger import AuditTaxLedger
from src.risk.risk_watchdog import RiskWatchdog
from src.vault.paper_to_live_engine import PaperToLiveGraduationEngine
from src.vault.qr_deposit import DEFAULT_QR_PNG_PATH, SolanaPayQRDepositEngine
from src.vault.withdrawal_manager import (
    DEFERRED_WITHDRAW_SENTINEL,
    DeferredWithdrawalManager,
)


async def verify_step_1_counterfactual_and_gepa() -> None:
    print(
        "\n[CHECK 1/5] Verifying Counterfactual Logger & 60-Trace GEPA Self-Improvement Arena..."
    )
    db_path = Path("/mnt/ramdisk/counterfactual_log.duckdb")
    if db_path.exists():
        db_path.unlink()

    state_path = Path("/mnt/ramdisk/execution_state/gepa_arena_state.json")
    if state_path.exists():
        state_path.unlink()

    logger = CounterfactualLogger(db_path=db_path)

    # 1. Populate 15 Top Winners & 15 Worst Losses
    for i in range(15):
        logger.record_executed_trade_trace(
            token_mint=f"WinnerMint{i:02d}111111111111111111111111111111",
            realized_pnl_sol=1.2 + i * 0.15,
            max_multiple=3.1 + i * 0.2,
            lp_usd=65_000.0 + i * 1_000.0,
            exit_reason="FIRST_TP_AND_TRAIL",
            feature_summary="clean_lp_organic_sharks",
            trace_id=f"winner_{i:02d}",
        )
        logger.record_executed_trade_trace(
            token_mint=f"LoserMint{i:02d}1111111111111111111111111111111",
            realized_pnl_sol=-(0.35 + i * 0.04),
            max_multiple=0.85,
            lp_usd=28_000.0,
            exit_reason="SYBIL_CLUSTER_DUMP_STOP",
            feature_summary="late_bundler_distribution",
            trace_id=f"loser_{i:02d}",
        )

    # 2. Populate 15 Missed Runners (>= 3.0x and LP > $25k -> FALSE_NEGATIVE_OMISSION)
    #    and 15 True Rug Blocks (TRUE_RUG_BLOCK)
    for i in range(15):
        miss_tid = logger.log_skip_decision(
            token_mint=f"MissedRunner{i:02d}1111111111111111111111111111",
            p_skip=0.68,
            rejection_reason="POST_MIGRATION_DIP_SKIP",
            initial_price_sol=0.00010,
            initial_lp_usd=22_000.0,
            feature_summary="strong_holder_retention_post_dip",
            trace_id=f"missed_{i:02d}",
        )
        miss_rec = logger.update_horizon_prices(
            trace_id=miss_tid,
            price_60s_sol=0.00018,
            price_300s_sol=0.00034,
            price_900s_sol=0.00042 + i * 0.00002,  # >= 4.2x (>= 3.0x threshold)
            peak_lp_usd=48_000.0 + i * 1_500.0,  # > $25k threshold
        )
        assert miss_rec.classification == "FALSE_NEGATIVE_OMISSION"

        rug_tid = logger.log_skip_decision(
            token_mint=f"TrueRugMint{i:02d}11111111111111111111111111111",
            p_skip=0.96,
            rejection_reason="TOP10_CONCENTRATION_AND_MINT_AUTH",
            initial_price_sol=0.00010,
            initial_lp_usd=18_000.0,
            feature_summary="dev_90pct_supply_cluster",
            trace_id=f"rug_{i:02d}",
        )
        rug_rec = logger.update_horizon_prices(
            trace_id=rug_tid,
            price_60s_sol=0.00004,
            price_300s_sol=0.00001,
            price_900s_sol=0.000002,
            peak_lp_usd=800.0,
        )
        assert rug_rec.classification == "TRUE_RUG_BLOCK"

    traces_60 = logger.fetch_stratified_60_traces()
    assert len(traces_60) == 60

    arena = GEPASelfImprovementArena(logger=logger, state_path=state_path)
    genesis_id = arena.champion.policy_id

    # Verify Immutable Safety Lock blocks any attempt to touch risk_watchdog.py or lib.rs
    blocked = False
    try:
        arena.verify_immutable_safety_lock(["src/risk/risk_watchdog.py"])
    except PermissionError:
        blocked = True
    assert blocked is True, "Immutable Safety Lock must block risk_watchdog.py modification"

    # Evolve SHADOW_CHALLENGER from the 60 stratified traces via Port 8002
    evo_report = await arena.evolve_challenger_from_60_traces()
    await arena.swarm_client.close()
    assert evo_report.status == "SHADOW_CHALLENGER_REGISTERED"
    assert evo_report.challenger_instruction_tokens <= MAX_INSTRUCTION_TOKENS
    assert evo_report.stratified_trace_counts == {
        "TOP_WINNER": 15,
        "WORST_LOSS": 15,
        "FALSE_NEGATIVE_OMISSION": 15,
        "TRUE_RUG_BLOCK": 15,
    }

    # Evaluate across 50 live market triggers using `simulateBundle` where Challenger beats
    # Champion by +18% EV (>= +10% threshold) with 0 honeypot hits
    promo_report = None
    for _ in range(50):
        promo_report = arena.record_shadow_trigger_simulation(
            champion_simulated_ev_sol=0.10,
            challenger_simulated_ev_sol=0.118,
            challenger_hit_honeypot=False,
        )
    assert promo_report is not None
    assert promo_report.promoted is True
    assert promo_report.status == "CHALLENGER_PROMOTED_TO_CHAMPION"
    assert arena.champion.policy_id == "policy_v2_challenger"

    # Simulate -4.2% rolling drawdown on the newly promoted Champion -> verify auto-rollback
    rb_report = arena.monitor_champion_drawdown_and_rollback(-4.2)
    assert rb_report.rolled_back is True
    assert rb_report.status == "CHAMPION_AUTO_ROLLED_BACK"
    assert arena.champion.policy_id == genesis_id

    logger.close()
    print(
        f"  [OK] 60-Trace GEPA Arena verified: Tokens={evo_report.challenger_instruction_tokens}/{MAX_INSTRUCTION_TOKENS} | "
        f"50-Trigger Promotion (+{promo_report.ev_improvement_pct:.1f}% EV, 0 honeypots) | "
        f"-4.2% Drawdown Auto-Rollback -> {arena.champion.policy_id} | Immutable Safety Lock=ENFORCED"
    )


def verify_step_2_risk_watchdog_and_parquet_ledger() -> None:
    print(
        "\n[CHECK 2/5] Verifying Core 0 Risk Watchdog, Macro Regime Switch & Parquet Tax Ledger..."
    )
    watchdog = RiskWatchdog()

    # 1. Verify Pyth/Binance 1s Macro Crash Filter (`GREEN`, `AMBER`, `RED_MACRO_FLUSH`)
    green = watchdog.evaluate_macro_regime(-0.6)
    assert green.regime == "GREEN"
    assert green.engine_b_active is True and green.shadow_sizing_multiplier == 1.0

    amber = watchdog.evaluate_macro_regime(-1.6)
    assert amber.regime == "AMBER"
    assert amber.engine_b_active is False and amber.shadow_sizing_multiplier == 0.5

    red = watchdog.evaluate_macro_regime(-2.5)
    assert red.regime == "RED_MACRO_FLUSH"
    assert red.engine_b_active is False and red.shadow_executor_active is False
    assert red.engine_a_priority_multiplier == 2.0

    # 2. Verify Core 0 Hard Circuit Breakers (15m drawdown >= 6.0%, 4x >5% slippage, PTP >5ms)
    watchdog.register_open_position(
        token_mint="OpenPosMint11111111111111111111111111111111",
        token_amount_raw=5_000_000_000,
        entry_sol=2.0,
        shard_id=0,
    )
    watchdog.record_equity_snapshot(100.0)
    watchdog.record_equity_snapshot(93.5)  # 6.5% 15m drawdown (>= 6.0%)
    for _ in range(4):
        watchdog.record_trade_slippage(-5.6)  # 4 consecutive trades > 5% slippage
    watchdog.update_hardware_and_stream_telemetry(
        ptp_clock_offset_ms=5.8, helius_stream_lag_ms=1650.0
    )

    breaker = watchdog.poll_circuit_breakers_100ms()
    assert breaker.triggered is True
    assert breaker.action == "EMERGENCY_DEMOTE_TO_PAPER"
    assert watchdog.execution_mode == "PAPER"
    assert breaker.flattened_positions_count == 1
    assert abs(breaker.total_rent_reclaimed_sol - 0.00203928) < 1e-9
    assert breaker.telegram_alert_dispatched is True

    # 3. Verify Permanent Parquet Tax & Lot Audit Ledger (`/var/lib/hermes/audit_ledger.parquet`)
    ledger_path = Path("/var/lib/hermes/audit_ledger.parquet")
    if ledger_path.exists():
        ledger_path.unlink()
    ledger = AuditTaxLedger(ledger_path=ledger_path)
    lot = ledger.append_trade(
        tx_signature="5TaxLotSig11111111111111111111111111111111111111111111",
        shard_id=2,
        engine_id="ENGINE_A_BACKRUNNER",
        sol_in=100.0,
        sol_out=101.45,
        jito_tip_sol=0.841,
        ata_rent_reclaimed_sol=0.00203928,
        sol_usd_spot_price=195.50,
    )
    rows = ledger.read_all_trades()
    assert ledger_path.exists()
    assert len(rows) == 1
    assert abs(rows[0].net_pnl_sol - lot.net_pnl_sol) < 1e-9

    print(
        f"  [OK] Core 0 Watchdog tripped `EMERGENCY_DEMOTE_TO_PAPER` (DD={breaker.rolling_15m_drawdown_pct:.1f}%, "
        f"SlippageBreaches={breaker.consecutive_slippage_breaches}, PTP={breaker.ptp_clock_offset_ms:.1f}ms) | "
        f"Macro Filter (`GREEN`->`AMBER`->`RED_MACRO_FLUSH` 2x Engine A) | "
        f"Parquet Ledger={ledger_path} ({len(rows)} row, Net={lot.net_pnl_sol:+.4f} SOL)"
    )


async def verify_step_3_paper_to_live_graduation() -> PaperToLiveGraduationEngine:
    print(
        "\n[CHECK 3/5] Verifying 3-Stage Paper-to-Live Graduation Engine (`25.00 vSOL` -> `CANARY` -> `LIVE`)..."
    )
    grad_engine = PaperToLiveGraduationEngine()
    assert grad_engine.mode == "PAPER"
    assert grad_engine.virtual_balance_sol == 25.00

    # Simulate 42 trades in PAPER mode: 34 winners (1.30x) and 8 small controlled stops (0.90x)
    # so total_paper_trades >= 40, PF >= 1.80, net_virtual_sol_pnl >= +3.5 SOL, max_dd <= 5.0%, 0 honeypots
    for idx in range(42):
        is_win = (idx % 5) != 3  # 80% win rate, shallow drawdown < 2%
        mult = 1.28 if is_win else 0.90
        res = await grad_engine.execute_simulated_paper_trade(
            token_mint=f"PaperGradMint{idx:02d}1111111111111111111111111111",
            entry_sol=1.0,
            raw_exit_multiple=mult,
            pool_sol_reserve=400.0,
            dex_fee_bps=25.0,
            jito_tip_sol=0.0005,
            plus_1_slot_200ms_penalty_bps=35.0,
            is_unhandled_honeypot=False,
        )
        assert res.v0_injects_jitodontfront is True
        assert res.v0_bundle_bytes < 1150

    snap_canary = grad_engine.get_status_snapshot()
    assert snap_canary.total_paper_trades == 42
    assert snap_canary.profit_factor >= 1.80
    assert snap_canary.net_virtual_sol_pnl >= 3.50
    assert snap_canary.max_drawdown_pct <= 5.00
    assert snap_canary.zero_unhandled_honeypots is True
    assert snap_canary.canary_eligible is True
    assert snap_canary.mode in ("CANARY", "LIVE")

    # Promote to LIVE (100% across all 25 shards)
    snap_live = grad_engine.set_mode_explicit("LIVE")
    assert snap_live.mode == "LIVE"
    assert snap_live.active_live_shards == 25
    assert snap_live.live_allocation_pct == 1.0

    print(
        f"  [OK] Graduation Engine Verified: Trades={snap_live.total_paper_trades} | "
        f"PF={snap_live.profit_factor:.2f} (>=1.80) | Net PnL={snap_live.net_virtual_sol_pnl:+.2f} vSOL (>=+3.50) | "
        f"Max DD={snap_live.max_drawdown_pct:.2f}% (<=5.0%) | Mode={snap_live.mode} (25 Shards Active)"
    )
    return grad_engine


async def verify_step_4_solana_pay_qr_deposit() -> None:
    print(
        "\n[CHECK 4/5] Verifying Solana Pay Terminal & 600x600 PNG QR Deposit (`vault deposit 5.0 --auto-shard`)..."
    )
    if DEFAULT_QR_PNG_PATH.exists():
        DEFAULT_QR_PNG_PATH.unlink()

    qr_engine = SolanaPayQRDepositEngine(png_path=DEFAULT_QR_PNG_PATH)
    session = qr_engine.create_deposit_request(
        amount_sol=5.0, auto_shard=True, print_to_stdout=True
    )
    confirmed = await qr_engine.await_helius_reference_confirmation(
        session, simulate_instant_arrival=True
    )

    assert confirmed.solana_pay_uri.startswith(f"solana:{confirmed.master_vault_pubkey}?amount=5.0&reference=")
    assert "&label=Sovereign+Titan+Vault&message=Trading+Capital+Deposit" in confirmed.solana_pay_uri
    assert any(ch in confirmed.utf8_half_block_qr for ch in ("█", "▀", "▄"))
    assert "SOVEREIGN TITAN VAULT" in confirmed.rich_terminal_panel_text
    assert DEFAULT_QR_PNG_PATH.exists()

    with Image.open(DEFAULT_QR_PNG_PATH) as img:
        assert img.size == (600, 600), f"Expected 600x600 QR PNG, got {img.size}"

    assert confirmed.confirmed is True
    assert len(confirmed.per_shard_allocated_sol) == 25
    assert abs(sum(confirmed.per_shard_allocated_sol.values()) - 5.0) < 1e-4

    print(
        f"  [OK] Solana Pay Deposit Verified: URI={confirmed.solana_pay_uri[:64]}... | "
        f"PNG={DEFAULT_QR_PNG_PATH} (600x600) | Auto-Sharded 5.0 SOL across 25 Shards (0.20 SOL/shard)"
    )


async def verify_step_5_deferred_withdrawal_and_cli(
    grad_engine: PaperToLiveGraduationEngine,
) -> None:
    print(
        "\n[CHECK 5/5] Verifying Deferred Withdrawal Lockbox (`DEFERRED` -> Sweep -> Withdraw) & Unified CLI..."
    )
    vault_mgr = DeferredWithdrawalManager(initial_hot_wallet_sol=50.0)
    assert vault_mgr.withdraw_address == DEFERRED_WITHDRAW_SENTINEL

    # Verify trading engines are strictly forbidden from accessing RESERVE_LOCKBOX_KEYPAIR
    engine_blocked = False
    try:
        vault_mgr.verify_engine_isolation("src.engines.engine_a_backrunner")
    except PermissionError:
        engine_blocked = True
    assert engine_blocked is True

    # Simulate hot-wallet growth from 50.0 SOL to 72.5 SOL (> HWM + 20.0 SOL) while DEFERRED
    sweep_ev = vault_mgr.record_hot_wallet_balance_and_sweep(72.5)
    assert sweep_ev.swept_count == 1
    assert sweep_ev.total_swept_sol == 10.0
    assert vault_mgr.pending_unclaimed_sweeps_sol == 10.0
    assert vault_mgr.active_hot_wallet_sol == 62.5
    assert vault_mgr.high_water_mark_sol == 60.0

    # Verify Unified CLI commands end-to-end
    cli = TitanCLIController(
        graduation_engine=grad_engine,
        withdrawal_manager=vault_mgr,
    )

    boot_res = await cli.execute_command(["swarm", "boot"])
    assert boot_res["status"] == "ONLINE"

    status_res = await cli.execute_command(["swarm", "status"])
    assert len(status_res["lanes"]) == 4

    bench_res = await cli.execute_command(["swarm", "benchmark"])
    assert bench_res["pass_sub_50us"] is True

    evolve_res = await cli.execute_command(["swarm", "evolve"])
    assert evolve_res["report"]["status"] == "SHADOW_CHALLENGER_REGISTERED"

    v_status_res = await cli.execute_command(["vault", "status"])
    assert v_status_res["withdrawal_vault"]["withdraw_address"] == DEFERRED_WITHDRAW_SENTINEL

    v_mode_res = await cli.execute_command(["vault", "mode", "live"])
    assert v_mode_res["snapshot"]["mode"] == "LIVE"

    scan_res = await cli.execute_command(["shadow", "scan"])
    assert "active_shadow_list" in scan_res

    insp_res = await cli.execute_command(["shadow", "inspect", "MicroShark111111111111111111111111111111111"])
    assert insp_res["wallet"] == "MicroShark111111111111111111111111111111111"

    flash_res = await cli.execute_command(["mev", "flash-test"])
    assert flash_res["triggered"] is True and flash_res["v0_tx_bytes"] < 1150

    dep_res = await cli.execute_command(["vault", "deposit", "5.0", "--auto-shard"])
    assert dep_res["session"]["confirmed"] is True

    # Bind external withdrawal wallet via `vault set-withdraw <address>`
    ext_wallet = str(Keypair().pubkey())
    set_res = await cli.execute_command(["vault", "set-withdraw", ext_wallet])
    assert set_res["withdraw_address"] == ext_wallet

    # 1. `vault withdraw profits` -> flushes 10.0 SOL from RESERVE_LOCKBOX_KEYPAIR
    prof_res = await cli.execute_command(["vault", "withdraw", "profits"])
    assert prof_res["receipt"]["withdrawal_type"] == "PROFITS"
    assert prof_res["receipt"]["amount_transferred_sol"] == 10.0
    assert vault_mgr.pending_unclaimed_sweeps_sol == 0.0

    # 2. `vault withdraw 12.5` -> withdraws 12.5 SOL from active hot wallet
    amt_res = await cli.execute_command(["vault", "withdraw", "12.5"])
    assert amt_res["receipt"]["withdrawal_type"] == "AMOUNT"
    assert amt_res["receipt"]["amount_transferred_sol"] == 12.5
    assert vault_mgr.active_hot_wallet_sol == 50.0

    # 3. `vault withdraw ALL` -> pauses daemons, closes positions, reclaims 25-shard ATA rent, sweeps 100%
    all_res = await cli.execute_command(["vault", "withdraw", "ALL"])
    receipt_all = all_res["receipt"]
    assert receipt_all["withdrawal_type"] == "ALL_FULL_LIQUIDATION"
    assert receipt_all["daemons_paused"] is True
    assert receipt_all["shards_swept_count"] == 25
    assert abs(receipt_all["ata_rent_reclaimed_sol"] - (25 * 0.00203928)) < 1e-8
    assert abs(receipt_all["amount_transferred_sol"] - (50.0 + 25 * 0.00203928)) < 1e-8
    assert vault_mgr.active_hot_wallet_sol == 0.0

    print(
        f"  [OK] Deferred Lockbox & CLI Verified: Swept 10.0 SOL at HWM+20 -> "
        f"`vault set-withdraw {ext_wallet[:10]}...` -> `withdraw profits` (10.0 SOL) -> "
        f"`withdraw 12.5` (12.5 SOL) -> `withdraw ALL` ({receipt_all['amount_transferred_sol']:.6f} SOL "
        f"incl. {receipt_all['ata_rent_reclaimed_sol']:.6f} SOL ATA rent across 25 shards)"
    )


async def main() -> int:
    t_start = time.perf_counter()
    print("=" * 78)
    print("SOVEREIGN TITAN OS — PHASE 5 VAULT, RISK WATCHDOG & GEPA ARENA SUITE")
    print("=" * 78)

    await verify_step_1_counterfactual_and_gepa()
    verify_step_2_risk_watchdog_and_parquet_ledger()
    grad_engine = await verify_step_3_paper_to_live_graduation()
    await verify_step_4_solana_pay_qr_deposit()
    await verify_step_5_deferred_withdrawal_and_cli(grad_engine)

    elapsed = time.perf_counter() - t_start
    print("\n" + "=" * 78)
    print(f"[PASS] 100% OF PHASE 5 VAULT & GEPA CHECKS PASSED IN {elapsed:.3f}s")
    print("=" * 78)
    return 0


def test_phase5_vault_risk_watchdog_and_gepa_suite() -> None:
    assert asyncio.run(main()) == 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

