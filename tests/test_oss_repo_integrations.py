"""Comprehensive pytest suite for `src/execution/oss_repo_integrations.py`
verifying all 10 curated open-source Solana GitHub repository integrations.
"""

from __future__ import annotations

from pathlib import Path
import struct
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.execution.oss_repo_integrations import (
    ATA_RENT_RECLAIM_SOL,
    AutomatedExitAndDevSellEngine,
    BondingCurveState,
    CURATED_10_OSS_REPOS,
    ChainstackDualMigrationDetector,
    DEV_SELL_HOLDINGS_THRESHOLD_PCT,
    DEV_SELL_SUPPLY_THRESHOLD_PCT,
    HOUR_6_HARD_MAX_HOLD_STOP_SEC,
    INITIAL_REAL_TOKEN_RESERVES,
    INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS,
    INITIAL_VIRTUAL_TOKEN_RESERVES,
    LETSBONK_LAUNCHLAB_PROGRAM_ID,
    METEORA_DBC_PROGRAM_ID,
    MINUTE_45_PRINCIPAL_FREE_MOONBAG_SEC,
    ORCA_WHIRLPOOL_PROGRAM_ID,
    OssRepoIntegrationSuite,
    PUMP_FUN_BONDING_CURVE_DISCRIMINATOR,
    PUMP_FUN_MIGRATION_AUTHORITY,
    PUMP_FUN_PROGRAM_ID,
    PUMP_SWAP_AMM_PROGRAM_ID,
    PUMP_SWAP_MIN_EXTENDED_POOL_LEN,
    PumpFunBondingCurveMath,
    PumpSwapProtocolAdapter,
    ShredStreamIntraSlotSniper,
    SybilTransferTreeAndCohortAnalyzer,
    TOKEN_TOTAL_SUPPLY,
    build_fee_sharing_config_ix,
    check_and_build_extend_account_ix,
    decode_bonding_curve_account,
    quote_exact_sol_in,
    quote_exact_sol_to_sweep_graduation,
)


def test_pumpswap_protocol_adapter_constants_and_extend_account() -> None:
    """Verifies canonical Pump.fun / PumpSwap IDs and `<300` byte `extendAccount` rule."""
    adapter = PumpSwapProtocolAdapter()
    assert PUMP_FUN_PROGRAM_ID == "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
    assert PUMP_FUN_MIGRATION_AUTHORITY == "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
    assert PUMP_SWAP_AMM_PROGRAM_ID == "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
    assert PUMP_SWAP_MIN_EXTENDED_POOL_LEN == 300

    # Legacy 211-byte pool (< 300 bytes) MUST trigger extendAccount CPI
    legacy = adapter.check_and_build_extend_account_ix(
        pool_pubkey="LegacyPumpSwapPool1111111111111111111111111",
        pool_data_len=211,
    )
    assert legacy["requires_extension"] is True
    assert legacy["ix_built"] is True
    assert legacy["action"] == "EXTEND_ACCOUNT_REQUIRED"
    assert legacy["bytes_to_add"] == 89
    assert legacy["program_id"] == PUMP_SWAP_AMM_PROGRAM_ID
    assert legacy["ix_name"] == "extend_account"
    assert len(legacy["discriminator_hex"]) == 16
    assert legacy["instruction"] is not None
    assert len(legacy["accounts"]) == 5

    # Extended 300-byte pool (>= 300 bytes) must NOT trigger extendAccount
    extended = check_and_build_extend_account_ix(
        pool_pubkey="ExtendedPumpSwapPool11111111111111111111111",
        pool_data_len=300,
    )
    assert extended["requires_extension"] is False
    assert extended["ix_built"] is False
    assert extended["action"] == "NO_EXTENSION_NEEDED"
    assert extended["bytes_to_add"] == 0
    assert extended["instruction"] is None


def test_pumpswap_fee_sharing_config_v1_and_v2() -> None:
    """Tests `create_fee_sharing_config` and `update_fee_shares_v2` instruction builders."""
    mint = "FeeShareMint11111111111111111111111111111111"
    v1_ix = build_fee_sharing_config_ix(
        mint=mint,
        creator_shares_bps=[
            ("CreatorA11111111111111111111111111111111111", 6_000),
            ("CreatorB11111111111111111111111111111111111", 4_000),
        ],
        is_v2_update=False,
    )
    assert v1_ix["valid"] is True
    assert v1_ix["ix_name"] == "create_fee_sharing_config"
    assert v1_ix["is_v2_update"] is False
    assert v1_ix["total_bps"] == 10_000
    assert v1_ix["shareholder_count"] == 2

    v2_ix = build_fee_sharing_config_ix(
        mint=mint,
        creator_shares_bps=[
            ("CreatorA11111111111111111111111111111111111", 5_000),
            ("CreatorB11111111111111111111111111111111111", 3_000),
            ("CreatorC11111111111111111111111111111111111", 2_000),
        ],
        is_v2_update=True,
    )
    assert v2_ix["valid"] is True
    assert v2_ix["ix_name"] == "update_fee_shares_v2"
    assert v2_ix["is_v2_update"] is True
    assert v2_ix["total_bps"] == 10_000
    assert v2_ix["shareholder_count"] == 3
    assert v1_ix["discriminator_hex"] != v2_ix["discriminator_hex"]

    # Shares not summing to 10,000 bps must raise ValueError
    with pytest.raises(ValueError, match="10,000 bps"):
        build_fee_sharing_config_ix(
            mint=mint,
            creator_shares_bps=[("CreatorA11111111111111111111111111111111111", 8_000)],
        )


def test_nirholas_bonding_curve_math_and_graduation_sweep() -> None:
    """Verifies `nirholas/pump-fun-sdk` virtual reserve constants, binary layout decoding,
    constant-product quotes, and exact `~85.005359 SOL` graduation sweep math.
    """
    assert INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS == 30_000_000_000
    assert INITIAL_VIRTUAL_TOKEN_RESERVES == 1_073_000_000_000_000
    assert INITIAL_REAL_TOKEN_RESERVES == 793_100_000_000_000
    assert TOKEN_TOTAL_SUPPLY == 1_000_000_000_000_000

    # Pack 49-byte raw account data and decode via decode_bonding_curve_account
    raw_bytes = struct.pack(
        "<8sQQQQQB",
        PUMP_FUN_BONDING_CURVE_DISCRIMINATOR,
        INITIAL_VIRTUAL_TOKEN_RESERVES,
        INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS,
        INITIAL_REAL_TOKEN_RESERVES,
        0,
        TOKEN_TOTAL_SUPPLY,
        0,
    )
    assert len(raw_bytes) == 49
    state = decode_bonding_curve_account(raw_bytes)
    assert state.virtual_token_reserves == INITIAL_VIRTUAL_TOKEN_RESERVES
    assert state.virtual_sol_reserves == INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS
    assert state.real_token_reserves == INITIAL_REAL_TOKEN_RESERVES
    assert state.real_sol_reserves == 0
    assert state.token_total_supply == TOKEN_TOTAL_SUPPLY
    assert state.complete is False
    assert state.bonding_progress_pct == pytest.approx(0.0)
    assert state.market_cap_sol == pytest.approx(30.0 / 1.073, rel=1e-4)

    # Quote 1.0 SOL buy (1,000,000,000 lamports) with 100 bps (1%) fee
    quote_1sol = quote_exact_sol_in(state, sol_in_lamports=1_000_000_000, fee_bps=100)
    assert quote_1sol.fee_lamports == 10_000_000
    assert quote_1sol.net_sol_in_lamports == 990_000_000
    expected_tokens = (990_000_000 * INITIAL_VIRTUAL_TOKEN_RESERVES) // (
        INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS + 990_000_000
    )
    assert quote_1sol.tokens_out == expected_tokens
    assert quote_1sol.graduates_curve is False
    assert quote_1sol.spot_price_after_sol > quote_1sol.spot_price_before_sol

    # Quote exact SOL to sweep 100% graduation from initial state:
    # Net SOL = ceil(30_000_000_000 * 793_100_000_000_000 / 279_900_000_000_000) = 85_005_359_057 lamports (~85.005359 SOL)
    sweep = quote_exact_sol_to_sweep_graduation(state, fee_bps=100)
    assert sweep.net_sol_required_lamports == 85_005_359_057
    assert sweep.net_sol_required_sol == pytest.approx(85.005359057, rel=1e-9)
    assert sweep.final_virtual_token_reserves == 279_900_000_000_000
    assert sweep.already_complete is False

    # Near-graduation state (92% complete -> Strategy 1 ready)
    rem_tokens = int(INITIAL_REAL_TOKEN_RESERVES * 0.08)
    v_tok_92 = (INITIAL_VIRTUAL_TOKEN_RESERVES - INITIAL_REAL_TOKEN_RESERVES) + rem_tokens
    v_sol_92 = (
        INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS * INITIAL_VIRTUAL_TOKEN_RESERVES
    ) // v_tok_92
    state_92 = BondingCurveState(
        virtual_token_reserves=v_tok_92,
        virtual_sol_reserves=v_sol_92,
        real_token_reserves=rem_tokens,
        real_sol_reserves=v_sol_92 - INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS,
        token_total_supply=TOKEN_TOTAL_SUPPLY,
        complete=False,
    )
    sweep_92 = quote_exact_sol_to_sweep_graduation(state_92)
    assert sweep_92.current_progress_pct == pytest.approx(92.0, abs=0.05)
    assert sweep_92.strategy_1_ready is True
    assert sweep_92.net_sol_required_sol == pytest.approx(21.252082498, rel=1e-6)
    assert sweep_92.final_virtual_sol_reserves == 115_005_359_057

    # At 98% token progress, remaining sweep requires ~5.95 SOL (< 6.5 SOL)
    rem_tokens_98 = int(INITIAL_REAL_TOKEN_RESERVES * 0.02)
    v_tok_98 = (INITIAL_VIRTUAL_TOKEN_RESERVES - INITIAL_REAL_TOKEN_RESERVES) + rem_tokens_98
    v_sol_98 = (
        INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS * INITIAL_VIRTUAL_TOKEN_RESERVES
    ) // v_tok_98
    state_98 = BondingCurveState(
        virtual_token_reserves=v_tok_98,
        virtual_sol_reserves=v_sol_98,
        real_token_reserves=rem_tokens_98,
        real_sol_reserves=v_sol_98 - INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS,
        token_total_supply=TOKEN_TOTAL_SUPPLY,
        complete=False,
    )
    sweep_98 = quote_exact_sol_to_sweep_graduation(state_98)
    assert sweep_98.current_progress_pct == pytest.approx(98.0, abs=0.05)
    assert sweep_98.strategy_1_ready is True
    assert 0.0 < sweep_98.net_sol_required_sol < 6.5



def test_chainstack_dual_migration_detector() -> None:
    """Tests both `parse_logsubscribe_migrate_event` and `parse_programsubscribe_pamm_pool_init`."""
    detector = ChainstackDualMigrationDetector()
    mint = "GradMintDual11111111111111111111111111111111"
    pool = "GradPoolDual11111111111111111111111111111111"

    log_res = detector.parse_logsubscribe_migrate_event(
        logs=[
            f"Program {PUMP_FUN_PROGRAM_ID} invoke [1]",
            f"Program log: Migration authority {PUMP_FUN_MIGRATION_AUTHORITY}",
            "Program log: Instruction: Migrate",
            f"Program log: mint={mint} pool={pool}",
        ],
        signature="5DualMigSig1111111111111111111111111111111111111111111",
    )
    assert log_res["detected"] is True
    assert log_res["mentions_migration_authority"] is True
    assert log_res["has_migrate_instruction"] is True
    assert log_res["token_mint"] == mint
    assert log_res["pool_pubkey"] == pool

    # Legacy 211B pool init on PumpSwap AMM must be detected & flag extendAccount
    pamm_res = detector.parse_programsubscribe_pamm_pool_init(
        account_pubkey=pool,
        owner_program=PUMP_SWAP_AMM_PROGRAM_ID,
        data_len=211,
        token_mint=mint,
    )
    assert pamm_res["detected"] is True
    assert pamm_res["requires_extend_account"] is True
    assert pamm_res["dual_listener_ready"] is True
    assert pamm_res["extend_account_ix"]["bytes_to_add"] == 89


def test_shredstream_intra_slot_sniper_5_venues() -> None:
    """Verifies `50ms–200ms` ShredStream parsing and atomic Jito bundle construction across
    Pump.fun, PumpSwap, Orca Whirlpool, LetsBonk / BonkFun, and Meteora DBC.
    """
    sniper = ShredStreamIntraSlotSniper()
    for venue_label, expected_prog in [
        ("Pump.fun", PUMP_FUN_PROGRAM_ID),
        ("PumpSwap", PUMP_SWAP_AMM_PROGRAM_ID),
        ("Orca Whirlpool", ORCA_WHIRLPOOL_PROGRAM_ID),
        ("LetsBonk / BonkFun", LETSBONK_LAUNCHLAB_PROGRAM_ID),
        ("Meteora Dynamic Bonding Curves (DBC)", METEORA_DBC_PROGRAM_ID),
    ]:
        ev = sniper.parse_shredstream_event(
            {
                "venue": venue_label,
                "intra_slot_latency_ms": 115.0,
                "slot": 342_815_500,
                "token_mint": "SnipeMint11111111111111111111111111111111111",
                "side": "BUY",
                "sol_amount": 1.5,
            }
        )
        assert ev["parsed"] is True
        assert ev["within_50_200ms_window"] is True
        assert ev["program_id"] == expected_prog

    bundle = sniper.build_multi_venue_atomic_jito_bundle(
        token_mint="SnipeMint11111111111111111111111111111111111",
        venues=[
            "Pump.fun",
            "PumpSwap",
            "Orca Whirlpool",
            "LetsBonk / BonkFun",
            "Meteora Dynamic Bonding Curves (DBC)",
        ],
        side="SELL",
        total_sol_amount=5.0,
        intra_slot_latency_ms=92.0,
        pumpswap_pool_data_len=211,
        close_ata_on_sell=True,
    )
    assert bundle["bundle_ready"] is True
    assert bundle["venue_count"] == 5
    assert bundle["within_50_200ms_window"] is True
    assert bundle["extend_account_injected"] is True
    assert bundle["ata_rent_reclaimed_sol"] == pytest.approx(ATA_RENT_RECLAIM_SOL)
    assert bundle["v0_tx_bytes"] < 1_232
    assert bundle["v0_size_valid"] is True


def test_automated_exit_and_dev_sell_engine() -> None:
    """Tests Hour-6 Hard Max-Hold Stop (`21,600s`), 45-Minute Principal-Free Moonbag (`2,700s`),
    and Instant Dev-Sell Exit Trigger (`>=0.5%` supply or `>=25%` dev holdings).
    """
    engine = AutomatedExitAndDevSellEngine()
    assert HOUR_6_HARD_MAX_HOLD_STOP_SEC == 21_600.0
    assert MINUTE_45_PRINCIPAL_FREE_MOONBAG_SEC == 2_700.0
    assert DEV_SELL_SUPPLY_THRESHOLD_PCT == pytest.approx(0.5)
    assert DEV_SELL_HOLDINGS_THRESHOLD_PCT == pytest.approx(25.0)

    # 1. Dev sells >= 0.5% of total supply -> instant 100% front-run exit + ATA rent reclaim
    dev_supply_exit = engine.evaluate_position_exit(
        token_mint="DevRugMint1111111111111111111111111111111111",
        hold_duration_sec=45.0,
        dev_sold_supply_pct=0.55,
        dev_sold_holdings_pct=10.0,
    )
    assert dev_supply_exit.should_exit is True
    assert dev_supply_exit.exit_pct == pytest.approx(100.0)
    assert dev_supply_exit.trigger_reason == "INSTANT_DEV_SELL_FRONTRUN_EXIT"
    assert dev_supply_exit.frontrun_jito_bundle is True
    assert dev_supply_exit.reclaim_ata_rent is True
    assert dev_supply_exit.ata_rent_reclaimed_sol == pytest.approx(ATA_RENT_RECLAIM_SOL)

    # 2. Dev sells >= 25% of dev holdings -> instant 100% front-run exit + ATA rent reclaim
    dev_holdings_exit = engine.evaluate_position_exit(
        token_mint="DevRugMint2222222222222222222222222222222222",
        hold_duration_sec=120.0,
        dev_sold_supply_pct=0.20,
        dev_sold_holdings_pct=26.0,
    )
    assert dev_holdings_exit.should_exit is True
    assert dev_holdings_exit.exit_pct == pytest.approx(100.0)
    assert dev_holdings_exit.trigger_reason == "INSTANT_DEV_SELL_FRONTRUN_EXIT"

    # 3. Hour-6 Hard Max-Hold Stop (>= 21,600s) -> 100% exit + ATA rent reclaim
    hour_6_exit = engine.evaluate_position_exit(
        token_mint="StaleMoonbagMint1111111111111111111111111111",
        hold_duration_sec=21_600.0,
        principal_extracted=True,
    )
    assert hour_6_exit.should_exit is True
    assert hour_6_exit.exit_pct == pytest.approx(100.0)
    assert hour_6_exit.trigger_reason == "HOUR_6_HARD_MAX_HOLD_STOP"
    assert hour_6_exit.reclaim_ata_rent is True

    # 4. 45-Minute Principal-Free Moonbag Gate (>= 2,700s, principal not yet extracted, +100% PnL)
    moonbag_exit = engine.evaluate_position_exit(
        token_mint="SwingMint11111111111111111111111111111111111",
        hold_duration_sec=2_700.0,
        principal_extracted=False,
        unrealized_pnl_pct=100.0,
        position_sol=2.0,
    )
    assert moonbag_exit.should_exit is True
    assert moonbag_exit.trigger_reason == "MINUTE_45_PRINCIPAL_FREE_MOONBAG_GATE"
    assert moonbag_exit.exit_pct == pytest.approx(50.0)  # Sells 50% at 2x to withdraw 100% principal
    assert moonbag_exit.sol_returned_estimate == pytest.approx(2.0)


def test_sybil_transfer_tree_and_smart_wallet_cohort_analyzer() -> None:
    """Tests recursive transfer tree `delta_h10_pp` calculation and Strategy 5 cohort gating."""
    analyzer = SybilTransferTreeAndCohortAnalyzer()

    # Build a 3-hop Sybil cabal: RootCabal -> Mid1/Mid2 -> 20 leaf wallets each holding 2.5% (50% total)
    # Plus 10 independent retail holders at 1.0% each.
    # Raw Top-10 = 10 * 2.5% = 25.0%.
    # Declustered Top-10 = 50.0% (RootCabal) + 9 * 1.0% = 59.0% -> delta_h10_pp = +34.0pp (>= 24.0pp -> REJECT)
    transfers = [
        {"from": "RootCabal", "to": "Mid1"},
        {"from": "RootCabal", "to": "Mid2"},
    ]
    holdings = {}
    for i in range(20):
        parent = "Mid1" if i < 10 else "Mid2"
        leaf = f"SybilLeaf_{i:02d}"
        transfers.append({"from": parent, "to": leaf})
        holdings[leaf] = 2.5
    for j in range(10):
        holdings[f"Retail_{j:02d}"] = 1.0

    cabal_tree = analyzer.build_hierarchical_transfer_tree(transfers, holdings)
    assert cabal_tree["raw_h10_pct"] == pytest.approx(25.0)
    assert cabal_tree["declustered_h10_pct"] == pytest.approx(59.0)
    assert cabal_tree["delta_h10_pp"] == pytest.approx(34.0)
    assert cabal_tree["risk_tier"] == "HIGH_RISK_SYBIL_CABAL"
    assert cabal_tree["strategy_5_tree_pass"] is False
    assert cabal_tree["max_tree_depth"] == 2

    # Strategy 5 cohort evaluation must block when delta_h10_pp >= 24.0
    wallets = [
        {
            "wallet": "AlphaShark1",
            "win_rate_pct": 66.0,
            "profit_factor": 4.2,
            "realized_pnl_sol": 350.0,
            "trades_30d": 40,
            "fast_bot_followers": 1,
        },
        {
            "wallet": "AlphaShark2",
            "win_rate_pct": 61.0,
            "profit_factor": 3.5,
            "realized_pnl_sol": 210.0,
            "trades_30d": 32,
            "fast_bot_followers": 1,
        },
    ]
    blocked_cohort = analyzer.evaluate_smart_wallet_cohort(
        wallet_profiles=wallets,
        delta_h10_pp=cabal_tree["delta_h10_pp"],
        min_price_ratio=0.85,
        melt_pred_score=0.10,
    )
    assert blocked_cohort["strategy_5_confluence_allowed"] is False
    assert any("DELTA_H10_SYBIL_EXCEEDED" in r for r in blocked_cohort["rejection_reasons"])

    # Clean tree (delta_h10_pp = 2.5pp < 24.0pp) must allow Strategy 5 confluence with 2.0x super-sizing
    allowed_cohort = analyzer.evaluate_smart_wallet_cohort(
        wallet_profiles=wallets,
        delta_h10_pp=2.5,
        min_price_ratio=0.85,
        melt_pred_score=0.10,
    )
    assert allowed_cohort["strategy_5_confluence_allowed"] is True
    assert allowed_cohort["qualified_smart_wallets_count"] == 2
    assert allowed_cohort["recommended_sizing_multiplier"] == pytest.approx(2.0)


def test_oss_repo_integration_suite_facade_and_telemetry() -> None:
    """Tests `OssRepoIntegrationSuite.run_full_10_repo_diagnostic()` and `get_telemetry_summary()`."""
    suite = OssRepoIntegrationSuite()
    diag = suite.run_full_10_repo_diagnostic()

    assert diag["all_10_repos_verified"] is True
    assert diag["repos_count"] == 10
    assert len(CURATED_10_OSS_REPOS) == 10
    assert diag["pumpswap_protocol"]["legacy_211b_check"]["requires_extension"] is True
    assert diag["pumpswap_protocol"]["extended_300b_check"]["requires_extension"] is False
    assert diag["bonding_curve_math"]["graduation_sweep_quote"]["net_sol_required_lamports"] == 85_005_359_057
    assert diag["dual_migration_detector"]["logsubscribe_migrate"]["detected"] is True
    assert diag["dual_migration_detector"]["programsubscribe_pamm_init"]["detected"] is True
    assert diag["shredstream_sniper"]["multi_venue_jito_bundle"]["venue_count"] == 5
    assert diag["automated_exit_and_dev_sell"]["dev_sell_frontrun_exit"]["should_exit"] is True
    assert diag["automated_exit_and_dev_sell"]["hour_6_hard_stop_exit"]["should_exit"] is True
    assert diag["sybil_tree_and_cohort"]["smart_wallet_cohort"]["strategy_5_confluence_allowed"] is True

    telemetry = suite.get_telemetry_summary()
    assert telemetry["repos_integrated"] == 10
    assert telemetry["last_diagnostic_available"] is True
    assert telemetry["counters"]["diagnostics_run"] == 1
