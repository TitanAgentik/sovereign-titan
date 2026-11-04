"""Tests for Quantitative On-Chain Intelligence, AI Wallet Forensics & Low-Latency Copy Execution Engine."""

from __future__ import annotations

from src.alpha.smart_money_copy_forensics_engine import (
    PLATFORM_2026_COMPARISON_MATRIX,
    RawRpcWalletTransaction,
    SOLANA_COPY_TRADING_EMPIRICAL_BENCHMARKS,
    SmartMoneyCopyForensicsEngine,
    VETTED_SMART_MONEY_ARCHETYPE_WALLETS,
    build_low_latency_copy_execution_plan,
    evaluate_5_anti_baiting_guardrails,
    evaluate_candidate_wallet_benchmarks,
    evaluate_discretionary_confluence_and_exit_ladder,
    evaluate_watchlist_and_cielo_signal_router,
    profile_wallet_6dimension_ai_rubric,
    run_onchain_sybil_bubblemaps_rugcheck_audit,
    sanitize_wallet_transactions_5rules,
)


def test_empirical_benchmarks_and_canonical_archetype_wallets() -> None:
    assert SOLANA_COPY_TRADING_EMPIRICAL_BENCHMARKS["pumpfun_graduation_ratio_1_in_n"] == 58
    assert SOLANA_COPY_TRADING_EMPIRICAL_BENCHMARKS["twenty_four_hour_token_collapse_rate_pct"] == 79.0
    assert SOLANA_COPY_TRADING_EMPIRICAL_BENCHMARKS["developer_multiwallet_bundle_extracted_usd"] == 579_000_000.0
    assert SOLANA_COPY_TRADING_EMPIRICAL_BENCHMARKS["external_automated_sniper_extracted_usd"] == 31_500_000.0
    assert SOLANA_COPY_TRADING_EMPIRICAL_BENCHMARKS["relayer_sponsored_feepayer_share_pct"] == 82.0
    assert SOLANA_COPY_TRADING_EMPIRICAL_BENCHMARKS["tripart_mm_filter_removed_swap_legs_pct"] == 48.7

    wallet_addrs = [w["wallet_address"] for w in VETTED_SMART_MONEY_ARCHETYPE_WALLETS]
    assert "AVAZvHLR2PcWpDf8BXY4rVxNHYRBytycHkcB5z5QNXYm" in wallet_addrs
    assert "4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t" in wallet_addrs
    assert "8zFZHuSRuDpuAR7J6FzwyF3vKNx4CVW3DFHJerQhc7Zd" in wallet_addrs
    assert "H72yLkhTnoBfhBTXXaj1RBXuirm8s8G5fcVh2XpQLggM" in wallet_addrs
    assert len(PLATFORM_2026_COMPARISON_MATRIX) == 6


def test_phase1_candidate_wallet_benchmarks_and_forensics() -> None:
    # Vetted wallet passes all 6 gates
    vetted = evaluate_candidate_wallet_benchmarks(
        wallet_address="AVAZvHLR2PcWpDf8BXY4rVxNHYRBytycHkcB5z5QNXYm",
        active_trading_days=64,
        rolling_7d_active=True,
        total_trades_30d=42,
        distinct_tokens_30d=18,
        realized_win_rate_net_pct=66.7,
        avg_position_size_sol=1.85,
        is_primary_initiator=True,
    )
    assert vetted.overall_promoted_to_watchlist is True
    assert vetted.rejection_reasons == []

    # Micro-tester / Honeypot >90% win-rate follower fails
    rejected = evaluate_candidate_wallet_benchmarks(
        wallet_address="FakeBundlerWallet11111111111111111111111111",
        active_trading_days=12,
        rolling_7d_active=True,
        total_trades_30d=8,
        distinct_tokens_30d=2,
        realized_win_rate_net_pct=96.5,
        avg_position_size_sol=0.12,
        is_primary_initiator=False,
        avg_slot_lag_behind_upstream=3,
    )
    assert rejected.overall_promoted_to_watchlist is False
    assert rejected.requires_honeypot_bundler_audit is True
    assert "AUTOMATED_MICRO_TESTER_BELOW_0_5_SOL" in rejected.rejection_reasons

    # Bubblemaps V2 + RugCheck clean vs 50% cluster monopoly
    clean_audit = run_onchain_sybil_bubblemaps_rugcheck_audit(
        wallet_address="4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t",
        token_mint="FartcoinMint",
        bubblemaps_largest_non_infra_cluster_pct=2.0,
        rugcheck_raw_score=310,
        rugcheck_score_normalised=8,
    )
    assert clean_audit.passed_forensic_audit is True
    assert clean_audit.rugcheck_rating_band == "GOOD_LOW_RISK"

    cabal_audit = run_onchain_sybil_bubblemaps_rugcheck_audit(
        wallet_address="SybilWallet",
        token_mint="CabalMint",
        funded_by_deployer_or_sybil_hub=True,
        bubblemaps_time_travel_slot0_bundle_wallets=30,
        bubblemaps_largest_non_infra_cluster_pct=50.0,
        rugcheck_raw_score=6500,
        rugcheck_score_normalised=65,
        rugcheck_trade_network_wash_ring=True,
    )
    assert cabal_audit.passed_forensic_audit is False
    assert cabal_audit.rugcheck_rating_band == "DANGER_HIGH_RISK"


def test_phase2_cielo_router_and_negative_remaining_kol_dump() -> None:
    # Multi-wallet confluence (>=3 wallets within 15m) routes to Bot 4
    confluence = evaluate_watchlist_and_cielo_signal_router(
        event_type="NEW_SWAP_BUY",
        wallet_address="8zFZHuSRuDpuAR7J6FzwyF3vKNx4CVW3DFHJerQhc7Zd",
        token_mint="ConfluenceMint",
        usd_value=2400.0,
        multi_wallet_confluence_count=4,
        confluence_window_minutes=8.0,
    )
    assert confluence.routed_bot_assignment == "BOT_4_MULTI_WALLET_CONFLUENCE_CLUSTER_ENGINE"
    assert confluence.alert_fired is True

    # Negative percent_tokens_remaining exposes off-market promoted KOL dump
    kol_dump = evaluate_watchlist_and_cielo_signal_router(
        event_type="SELL_TRIM",
        wallet_address="PromotedKolWallet",
        token_mint="PromotedMint",
        usd_value=15_000.0,
        percent_sold=100.0,
        percent_tokens_remaining=-35.0,
    )
    assert kol_dump.promoted_kol_off_market_dump_detected is True
    assert kol_dump.operational_action == "HARD_BLOCK_PROMOTED_KOL_OFF_MARKET_TRANSFER_DUMP"


def test_phase3_5rule_sanitization_and_6d_ai_rubric() -> None:
    wallet = "4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t"
    raw_txs = [
        RawRpcWalletTransaction(
            signature="buy_1",
            slot=100,
            timestamp=1000,
            fee_payer="GaslessRelayer82Pct",
            token_account_owner=wallet,
            token_mint="Mint1",
            dex_program_id="RaydiumV4",
            token_balance_delta=1000.0,
            sol_balance_delta=-2.0,
            sol_usd_at_trade_hour=150.0,
            sol_usd_current_spot=220.0,
        ),
        RawRpcWalletTransaction(
            signature="sell_1",
            slot=150,
            timestamp=2800,
            fee_payer="GaslessRelayer82Pct",
            token_account_owner=wallet,
            token_mint="Mint1",
            dex_program_id="RaydiumV4",
            token_balance_delta=-1000.0,
            sol_balance_delta=6.0,
            sol_usd_at_trade_hour=155.0,
            sol_usd_current_spot=220.0,
        ),
        RawRpcWalletTransaction(
            signature="unmatched_airdrop_sell",
            slot=160,
            timestamp=2900,
            fee_payer="GaslessRelayer82Pct",
            token_account_owner=wallet,
            token_mint="AirdropMint",
            dex_program_id="RaydiumV4",
            token_balance_delta=-5000.0,
            sol_balance_delta=10.0,
            sol_usd_at_trade_hour=155.0,
            sol_usd_current_spot=220.0,
            matched_prior_buy_in_30d_window=False,
            acquired_via_offmarket_transfer=True,
        ),
    ]
    report = sanitize_wallet_transactions_5rules(wallet, raw_txs)
    assert report.sanitized_valid_swap_legs == 2
    assert report.relayer_feepayer_overridden_count == 3
    assert report.unmatched_or_transfer_sells_dropped == 1
    assert report.excluded_as_automated_market_maker is False
    # Net PnL at trade hour: (-2 * 150) + (6 * 155) = -300 + 930 = +630 USD
    assert report.total_net_pnl_usd_trade_hour_priced == 630.0

    # Test 6D AI Strategy Rubric on a sub-second sniper / baiter vs swing trader
    baiter_profile = profile_wallet_6dimension_ai_rubric(
        wallet_address="BaiterWhale",
        pct_buys_first_5_blocks=85.0,
        pct_buys_above_95pct_curve_or_raydium=5.0,
        median_hold_duration_minutes=0.4,
        entry_sol_amounts=[1.0, 2.0, 100.0],
        max_post_loss_entry_sol=100.0,
        avg_sell_legs_per_trade=1.0,
        single_clip_100pct_dump_ratio=0.95,
        trade_pnl_usd_list=[50000.0, -4000.0, -5000.0],
        trade_roi_pct_list=[5000.0, -99.0, -99.0],
        loss_cut_floor_pct=-99.0,
        unmatched_or_negative_remaining_count=3,
        low_liquidity_below_30k_entries=4,
    )
    assert baiter_profile.dim1_entry_venue_timing_class == "SUB_SECOND_LAUNCH_SNIPER_DO_NOT_COPY"
    assert baiter_profile.dim2_holding_velocity_class == "ULTRA_SHORT_SCALPER_UNCOPYABLE"
    assert baiter_profile.dim3_sizing_discipline_class == "ERRATIC_REVENGE_TILT_SIZER"
    assert baiter_profile.dim4_exit_laddering_class == "SINGLE_CLIP_DUMPER"
    assert baiter_profile.dim6_adversarial_red_flag_class == "INSIDER_COPY_BAITER_BLACKLIST"
    assert baiter_profile.copy_viability_verdict == "BLACKLIST_IMMEDIATELY_ADVERSARIAL_BAITER"


def test_phase4_execution_plan_guardrails_and_exit_ladder() -> None:
    plan = build_low_latency_copy_execution_plan(
        venue_regime="BONDING_CURVE_MIGRATION_SNIPE",
        position_size_sol=2.0,
        requested_slippage_pct=10.0,
        use_jito_bundle_tip=True,
    )
    assert plan.yellowstone_grpc_proto_version == "12.6.0"
    assert plan.dynamic_compute_unit_limit is True
    assert plan.skip_preflight is True
    assert plan.jito_tip_lamports is not None
    assert plan.prioritization_fee_lamports is None
    assert plan.slippage_cap_valid is True

    # 100 SOL whale bait in $12,000 illiquid pool is blocked by Guardrails
    bait_eval = evaluate_5_anti_baiting_guardrails(
        target_whale_trade_sol=100.0,
        bankroll_sol=20.0,
        proportional_copy_pct=5.0,
        hard_sol_ceiling=1.0,
        token_market_cap_usd=85_000.0,
        pool_liquidity_usd=12_000.0,
        jupiter_dry_run_sell_quote_succeeded=False,
    )
    assert bait_eval.capped_follower_size_sol == 1.0
    assert bait_eval.bait_trap_detected is True
    assert bait_eval.all_guardrails_passed is False
    assert bait_eval.execution_decision == "ABORT_COPY_BAIT_OR_GUARDRAIL_VIOLATION"

    # 4-Tranche exit ladder at 5.2x multiple
    exit_plan = evaluate_discretionary_confluence_and_exit_ladder(current_price_multiple=5.2)
    assert exit_plan.realized_fraction_sold == 0.75
    assert exit_plan.moonbag_fraction_retained == 0.25
    assert len(exit_plan.tranche_ladder) == 5

    # Full Engine facade diagnostic
    engine = SmartMoneyCopyForensicsEngine()
    diag = engine.run_full_4phase_copy_intelligence_diagnostic()
    assert diag["status"] == "PHASE_1_TO_4_SMART_MONEY_COPY_INTELLIGENCE_READY"
    assert engine.get_telemetry_summary()["cielo_bots_online"] == 4
