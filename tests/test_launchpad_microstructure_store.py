"""Verification suite for `src/storage/launchpad_microstructure_store.py`
(arXiv:2512.11850 & arXiv:2609.18975 — Solana Launchpad Microstructure & On-Chain Data Coverage).
"""

from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT_DIR = Path("/home/titanagentik/sovereign-titan")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.storage.launchpad_microstructure_store import (
    ARXIV_2512_11850_CITATION,
    ARXIV_2609_18975_CITATION,
    DEX_SOLANA_TRADES_COLUMNS,
    H1_HIGH_SPAM_MIN_CURVE_PCT,
    H1_STANDARD_MIN_CURVE_PCT,
    NAIVE_INDEXER_BASELINE_COVERAGE_PCT,
    PEAK_DAILY_MINT_BENCHMARK,
    SOLANA_INSTRUCTION_CALLS_COLUMNS,
    TARGET_RECONCILED_COVERAGE_PCT,
    TOKENS_SOLANA_TRANSFERS_COLUMNS,
    DexTradeRecord,
    LaunchpadMicrostructureStore,
    SolanaInstructionCallRecord,
    TokenTransferRecord,
    evaluate_launchpad_spam_regime,
    reconcile_coverage_gaps,
)


def test_canonical_schemas_wal_and_dual_sql_access(tmp_path: Path) -> None:
    """Verifies WAL mode, ATTACH DATABASE schemas, exact columns, and dual SQL access."""
    db_file = tmp_path / "launchpad_test.sqlite3"
    store = LaunchpadMicrostructureStore(db_path=db_file)
    try:
        inspection = store.get_schema_inspection()
        assert inspection["journal_mode"] == "wal"
        assert inspection["schemas_valid"] is True
        for schema_name in ("tokens_solana", "dex_solana", "solana"):
            assert schema_name in inspection["attached_schemas"]

        assert tuple(inspection["tables"]["tokens_solana.transfers"]) == TOKENS_SOLANA_TRANSFERS_COLUMNS
        assert tuple(inspection["tables"]["dex_solana.trades"]) == DEX_SOLANA_TRADES_COLUMNS
        assert tuple(inspection["tables"]["solana.instruction_calls"]) == SOLANA_INSTRUCTION_CALLS_COLUMNS

        # Direct SQL INSERT via schema-qualified views (`tokens_solana.transfers`, `dex_solana.trades`, `solana.instruction_calls`)
        conn = store.connection
        conn.execute(
            """
            INSERT INTO tokens_solana.transfers VALUES (
                'tf_1', 'sig_1', 350000001, 1760000001000, 'MintA11111111111111111111111111111111111111',
                'Sender111', 'Receiver111', 'AtaSender111', 'AtaReceiver111',
                1000000000, 1000.0, 0.0001, 'BONDING_CURVE', 0
            );
            """
        )
        conn.execute(
            """
            INSERT INTO dex_solana.trades VALUES (
                'td_1', 'sig_1', 350000001, 3, 1760000001075, 'MintA11111111111111111111111111111111111111',
                '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P', 'Pump.fun', 'Pool111',
                'Receiver111', 'BUY', 0.05, 1000.0, 0.00005, 42.5, 0
            );
            """
        )
        conn.execute(
            """
            INSERT INTO solana.instruction_calls VALUES (
                'ix_1', 'sig_1', 350000001, 1760000001075, 'MintA11111111111111111111111111111111111111',
                '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P', '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
                'BONDING_BUY', 1, '66063d1201daebea', 12, '66063d1201daebea01', 0
            );
            """
        )

        # Verify rows are visible via BOTH schema-qualified and flat table queries
        assert len(store.query_transfers(use_schema_alias=True)) == 1
        assert len(store.query_transfers(use_schema_alias=False)) == 1
        assert len(store.query_trades(use_schema_alias=True)) == 1
        assert len(store.query_trades(use_schema_alias=False)) == 1
        assert len(store.query_instruction_calls(use_schema_alias=True)) == 1
        assert len(store.query_instruction_calls(use_schema_alias=False)) == 1
    finally:
        store.close()


def test_record_validation_and_bam_tick_bounds() -> None:
    """Verifies strict domain validation on lifecycle stages, trade sides, and instruction types."""
    with pytest.raises(ValueError, match="Invalid lifecycle_stage"):
        TokenTransferRecord(
            transfer_id="bad_tf",
            tx_signature="sig",
            slot=1,
            block_time_ms=1000,
            token_mint="Mint1",
            sender_wallet="w1",
            receiver_wallet="w2",
            sender_ata="a1",
            receiver_ata="a2",
            amount_raw=100,
            amount_ui=0.1,
            supply_share_pct=0.01,
            lifecycle_stage="INVALID_STAGE",
        )

    with pytest.raises(ValueError, match="Invalid trade side"):
        DexTradeRecord(
            trade_id="bad_td",
            tx_signature="sig",
            slot=1,
            bam_tick_index=0,
            block_time_ms=1000,
            token_mint="Mint1",
            dex_program_id="prog",
            venue_name="Pump.fun",
            pool_address="pool",
            trader_wallet="trader",
            side="HOLD",
            sol_amount=1.0,
            token_amount=100.0,
            execution_price_sol=0.01,
            bonding_curve_progress_pct=50.0,
        )

    with pytest.raises(ValueError, match="Invalid instruction_type"):
        SolanaInstructionCallRecord(
            ix_id="bad_ix",
            tx_signature="sig",
            slot=1,
            block_time_ms=1000,
            token_mint="Mint1",
            program_id="prog",
            outer_program_id="prog",
            instruction_type="UNKNOWN_IX",
        )

    # BAM tick index is clamped into [0, 7] (8 ticks per 200ms Alpenglow slot)
    clamped = DexTradeRecord(
        trade_id="ok_td",
        tx_signature="sig",
        slot=1,
        bam_tick_index=19,
        block_time_ms=1000,
        token_mint="Mint1",
        dex_program_id="prog",
        venue_name="Pump.fun",
        pool_address="pool",
        trader_wallet="trader",
        side="buy",
        sol_amount=1.0,
        token_amount=100.0,
        execution_price_sol=0.01,
        bonding_curve_progress_pct=50.0,
    )
    assert clamped.bam_tick_index == 7
    assert clamped.side == "BUY"


def test_evaluate_launchpad_spam_regime_high_spam_and_normal() -> None:
    """Verifies arXiv:2512.11850 high-spam regime & sub-2% graduation rate detector."""
    # Peak retail mania: 69,046 mints/day, 980 graduations (~1.419% graduation rate), 58.2% DEX tx share
    mania = evaluate_launchpad_spam_regime(
        total_mints=PEAK_DAILY_MINT_BENCHMARK,
        graduated_mints=980,
        observation_window_hours=24.0,
        launchpad_dex_tx_count=5_820_000,
        total_solana_dex_tx_count=10_000_000,
    )
    assert mania.daily_mint_rate == pytest.approx(69_046.0)
    assert mania.annualized_or_daily_mint_rate == pytest.approx(69_046.0)
    assert mania.launchpad_dex_tx_share_pct == pytest.approx(58.2)
    assert mania.dex_share_within_empirical_band is True
    assert mania.raw_graduation_rate_pct == pytest.approx((980 / 69_046) * 100.0, rel=1e-3)
    assert mania.raw_graduation_rate_pct < 2.0
    assert mania.is_high_spam_sub_2pct_regime is True
    assert mania.recommended_h1_min_curve_pct == pytest.approx(H1_HIGH_SPAM_MIN_CURVE_PCT)
    assert mania["recommended_h1_min_curve_pct"] == pytest.approx(92.5)
    assert mania.paper_citation == ARXIV_2512_11850_CITATION

    # Normal selective regime: 12,000 mints/day, 360 graduations (3.0% graduation rate)
    normal = evaluate_launchpad_spam_regime(
        total_mints=12_000,
        graduated_mints=360,
        observation_window_hours=24.0,
        launchpad_dex_tx_count=1_500_000,
        total_solana_dex_tx_count=5_000_000,
    )
    assert normal.raw_graduation_rate_pct == pytest.approx(3.0)
    assert normal.is_high_spam_sub_2pct_regime is False
    assert normal.recommended_h1_min_curve_pct == pytest.approx(H1_STANDARD_MIN_CURVE_PCT)
    assert normal["recommended_h1_min_curve_pct"] == pytest.approx(88.0)


def test_reconcile_coverage_gaps_all_three_gap_classes() -> None:
    """Verifies arXiv:2609.18975 coverage gap detector & backfiller across all 3 primary gap classes."""
    store = LaunchpadMicrostructureStore(db_path=":memory:")
    try:
        mint_1 = "MintGap1CPI11111111111111111111111111111111"
        mint_2 = "MintGap2Mig11111111111111111111111111111111"
        mint_3 = "MintGap3Gen11111111111111111111111111111111"
        pump_prog = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        jup_prog = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

        # Mint 1 has genesis records + an inner CPI BONDING_BUY via Jupiter missing from dex_solana.trades (Gap 1)
        store.insert_instruction_call(
            {
                "ix_id": "m1_create_ix",
                "tx_signature": "m1_tx_create",
                "slot": 100,
                "block_time_ms": 100_000,
                "token_mint": mint_1,
                "program_id": pump_prog,
                "outer_program_id": pump_prog,
                "instruction_type": "CREATE_MINT",
                "ix_depth": 1,
            }
        )
        store.insert_transfer(
            {
                "transfer_id": "m1_gen_tf",
                "tx_signature": "m1_tx_create",
                "slot": 100,
                "block_time_ms": 100_000,
                "token_mint": mint_1,
                "sender_wallet": "MintAuth",
                "receiver_wallet": "CurveVault1",
                "amount_ui": 1_000_000_000.0,
                "supply_share_pct": 100.0,
                "lifecycle_stage": "MINT_GENESIS",
            }
        )
        store.insert_instruction_call(
            {
                "ix_id": "m1_cpi_buy_ix",
                "tx_signature": "m1_tx_cpi_buy",
                "slot": 102,
                "block_time_ms": 100_400,
                "token_mint": mint_1,
                "program_id": pump_prog,
                "outer_program_id": jup_prog,
                "instruction_type": "BONDING_BUY",
                "ix_depth": 2,
            }
        )
        store.insert_transfer(
            {
                "transfer_id": "m1_cpi_buy_tf",
                "tx_signature": "m1_tx_cpi_buy",
                "slot": 102,
                "block_time_ms": 100_400,
                "token_mint": mint_1,
                "sender_wallet": "CurveVault1",
                "receiver_wallet": "WhaleBuyer1",
                "amount_ui": 50_000_000.0,
                "supply_share_pct": 5.0,
                "lifecycle_stage": "BONDING_CURVE",
                "is_inner_cpi": 1,
            }
        )

        # Mint 2 has genesis records + WITHDRAW_MIGRATION instruction & MIGRATION_LOCK transfer without a graduation trade (Gap 2)
        store.insert_instruction_call(
            {
                "ix_id": "m2_create_ix",
                "tx_signature": "m2_tx_create",
                "slot": 200,
                "block_time_ms": 200_000,
                "token_mint": mint_2,
                "program_id": pump_prog,
                "outer_program_id": pump_prog,
                "instruction_type": "CREATE_MINT",
                "ix_depth": 1,
            }
        )
        store.insert_transfer(
            {
                "transfer_id": "m2_gen_tf",
                "tx_signature": "m2_tx_create",
                "slot": 200,
                "block_time_ms": 200_000,
                "token_mint": mint_2,
                "sender_wallet": "MintAuth",
                "receiver_wallet": "CurveVault2",
                "amount_ui": 1_000_000_000.0,
                "supply_share_pct": 100.0,
                "lifecycle_stage": "MINT_GENESIS",
            }
        )
        store.insert_instruction_call(
            {
                "ix_id": "m2_mig_ix",
                "tx_signature": "m2_tx_mig",
                "slot": 250,
                "block_time_ms": 210_000,
                "token_mint": mint_2,
                "program_id": pump_prog,
                "outer_program_id": pump_prog,
                "instruction_type": "WITHDRAW_MIGRATION",
                "ix_depth": 1,
            }
        )
        store.insert_transfer(
            {
                "transfer_id": "m2_mig_tf",
                "tx_signature": "m2_tx_mig",
                "slot": 250,
                "block_time_ms": 210_000,
                "token_mint": mint_2,
                "sender_wallet": "CurveVault2",
                "receiver_wallet": "PumpSwapPool2",
                "amount_ui": 206_900_000.0,
                "supply_share_pct": 20.69,
                "lifecycle_stage": "MIGRATION_LOCK",
            }
        )

        # Mint 3 has a trade in dex_solana.trades but is missing CREATE_MINT and MINT_GENESIS (Gap 3)
        store.insert_trade(
            {
                "trade_id": "m3_td_1",
                "tx_signature": "m3_tx_buy",
                "slot": 305,
                "bam_tick_index": 2,
                "block_time_ms": 301_000,
                "token_mint": mint_3,
                "dex_program_id": pump_prog,
                "venue_name": "Pump.fun",
                "pool_address": "CurveVault3",
                "trader_wallet": "Trader3",
                "side": "BUY",
                "sol_amount": 2.0,
                "token_amount": 40_000_000.0,
                "execution_price_sol": 0.00000005,
                "bonding_curve_progress_pct": 65.0,
            }
        )

        report = reconcile_coverage_gaps(store)
        assert report.paper_citation == ARXIV_2609_18975_CITATION
        assert report.naive_indexer_baseline_pct == pytest.approx(NAIVE_INDEXER_BASELINE_COVERAGE_PCT)
        assert report.inner_cpi_swaps_reconciled == 1
        assert report.migration_orphans_reconciled == 1
        assert report.genesis_mints_reconciled == 1
        assert report.total_gaps_reconciled == 3
        assert report.unreconciled_gaps_remaining == 0
        assert report.coverage_completeness_pct == pytest.approx(TARGET_RECONCILED_COVERAGE_PCT)

        # Verify Mint 1 now has a reconciled inner CPI trade in dex_solana.trades
        m1_trades = store.query_trades(token_mint=mint_1)
        assert len(m1_trades) == 1
        assert m1_trades[0]["is_inner_cpi"] == 1
        assert m1_trades[0]["trader_wallet"] == "WhaleBuyer1"
        assert m1_trades[0]["token_amount"] == pytest.approx(50_000_000.0)

        # Verify Mint 2 now has a graduation trade with bonding_curve_progress_pct == 100.0
        m2_trades = store.query_trades(token_mint=mint_2)
        assert len(m2_trades) == 1
        assert m2_trades[0]["bonding_curve_progress_pct"] == pytest.approx(100.0)

        # Verify Mint 3 now has both MINT_GENESIS transfer and CREATE_MINT instruction call
        m3_genesis_tfs = store.query_transfers(token_mint=mint_3, lifecycle_stage="MINT_GENESIS")
        m3_create_ixs = store.query_instruction_calls(token_mint=mint_3, instruction_type="CREATE_MINT")
        assert len(m3_genesis_tfs) == 1
        assert len(m3_create_ixs) == 1
    finally:
        store.close()


def test_synthetic_batch_coverage_audit_and_duckdb_sync() -> None:
    """Verifies synthetic batch ingestion, full coverage audit, telemetry summary, and DuckDB sync."""
    store = LaunchpadMicrostructureStore(db_path=":memory:")
    try:
        batch_res = store.ingest_synthetic_or_live_batch(
            synthetic_mint_count=60,
            synthetic_graduated_count=1,
            include_coverage_gaps=True,
            auto_reconcile=False,
        )
        assert batch_res["synthetic_mint_count"] == 60
        assert batch_res["synthetic_graduated_count"] == 1

        audit = store.run_coverage_audit()
        assert audit["status"] == "OK"
        assert audit["schema_inspection"]["schemas_valid"] is True
        assert audit["coverage_reconciliation"]["total_gaps_reconciled"] >= 4
        assert audit["coverage_reconciliation"]["coverage_completeness_pct"] == pytest.approx(99.98)
        assert audit["spam_regime"]["is_high_spam_sub_2pct_regime"] is True
        assert audit["spam_regime"]["recommended_h1_min_curve_pct"] == pytest.approx(92.5)

        telemetry = store.get_telemetry_summary()
        assert telemetry["journal_mode"] == "wal"
        assert telemetry["row_counts"]["tokens_solana.transfers"] > 60
        assert telemetry["row_counts"]["dex_solana.trades"] > 60
        assert telemetry["row_counts"]["solana.instruction_calls"] > 60
        assert telemetry["recommended_h1_min_curve_pct"] == pytest.approx(92.5)

        duck_res = store.sync_to_duckdb()
        assert duck_res["synced"] is True
        assert duck_res["tokens_solana_transfers_rows"] == telemetry["row_counts"]["tokens_solana.transfers"]
        assert duck_res["dex_solana_trades_rows"] == telemetry["row_counts"]["dex_solana.trades"]
        assert duck_res["solana_instruction_calls_rows"] == telemetry["row_counts"]["solana.instruction_calls"]
    finally:
        store.close()
