"""Comprehensive pytest verification suite for `src/execution/four_stage_zero_loss_pipeline.py`
implementing Part 3: The 4-Stage Zero/Low-Loss Execution Pipeline.
"""

from __future__ import annotations

from pathlib import Path
import struct
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.execution.four_stage_zero_loss_pipeline import (
    FourStageZeroLossPipeline,
    GOLDILOCKS_MAX_EARLY_BUYERS,
    GOLDILOCKS_MIN_EARLY_BUYERS,
    GRADUATION_SQUEEZE_PCT_MAX,
    GRADUATION_SQUEEZE_PCT_MIN,
    JITO_DONT_FRONT_PUBKEY,
    METEORA_DLMM_PROGRAM_ID,
    PUMP_FUN_MIGRATION_AUTHORITY,
    PUMP_FUN_PROGRAM_ID,
    PUMP_SWAP_AMM_PROGRAM_ID,
    STAGE1_CURVE_COMPLETION_TARGET_SOL,
    STAGE1_CURVE_SOL_BAND_MAX,
    STAGE1_CURVE_SOL_BAND_MIN,
    STAGE1_MAX_SHRED_LATENCY_MS,
    STAGE1_MIN_SHRED_LATENCY_MS,
    STAGE2_HISTORICAL_LOSS_ELIMINATION_PCT,
    STAGE2_MAX_DELTA_H10_PP,
    STAGE2_MAX_PRED_SCORE,
    STAGE3_EXTEND_ACCOUNT_MIN_POOL_LEN,
    STAGE3_MAX_ATOMIC_BUNDLE_TXS,
    STAGE3_MAX_SLIPPAGE_BPS,
    STAGE3_MIN_SLIPPAGE_BPS,
    STAGE4_DEFAULT_MAX_IDLE_DELTA_T_SEC,
    STAGE4_DEFAULT_MDD_THETA,
    STAGE4_HARD_UNGRADUATED_TIME_STOP_SEC,
    STAGE4_SAME_SLOT_EXIT_LATENCY_MS,
    WSOL_MINT_PUBKEY,
    derive_coin_creator_vault_ata,
    pumpfun_listen_migrations_logsubscribe,
    pumpfun_read_curve,
    run_stage1_subslot_ingestion,
    run_stage2_sybil_melt_firewall,
    run_stage3_atomic_jito_execution,
    run_stage4_automated_exit_and_dlmm_migration,
)
from src.execution.oss_repo_integrations import (
    INITIAL_REAL_TOKEN_RESERVES,
    INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS,
    INITIAL_VIRTUAL_TOKEN_RESERVES,
    PUMP_FUN_BONDING_CURVE_DISCRIMINATOR,
    TOKEN_TOTAL_SUPPLY,
)


def test_stage1_subslot_ingestion_goldilocks_and_curve_bands() -> None:
    """Verifies Stage 1 (`sol-parser-sdk` + `pumpfun-bonkfun-bot`):
      - 50ms-200ms sub-slot ShredStream capture for Block-0 creations, whale swaps, creator sells
      - `pumpfun_listen_migrations_logsubscribe` on `39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg`
      - `pumpfun_read_curve` approaching 85.0 SOL completion threshold
      - Goldilocks bundler tier (`11 <= early_buyers <= 50`), `62.0 <= curve_sol <= 75.0 SOL` band,
        and `88.0%–99.5%` graduation squeeze band.
    """
    assert STAGE1_MIN_SHRED_LATENCY_MS == pytest.approx(50.0)
    assert STAGE1_MAX_SHRED_LATENCY_MS == pytest.approx(200.0)
    assert STAGE1_CURVE_COMPLETION_TARGET_SOL == pytest.approx(85.0)
    assert GOLDILOCKS_MIN_EARLY_BUYERS == 11
    assert GOLDILOCKS_MAX_EARLY_BUYERS == 50
    assert STAGE1_CURVE_SOL_BAND_MIN == pytest.approx(62.0)
    assert STAGE1_CURVE_SOL_BAND_MAX == pytest.approx(75.0)
    assert GRADUATION_SQUEEZE_PCT_MIN == pytest.approx(88.0)
    assert GRADUATION_SQUEEZE_PCT_MAX == pytest.approx(99.5)

    # 1. Goldilocks bundler tier (28 early buyers) + 68.4 SOL curve completion band
    s1 = run_stage1_subslot_ingestion(
        token_mint="GoldilocksMint11111111111111111111111111111",
        early_buyers=28,
        curve_sol=68.4,
        shred_lead_time_ms=115.0,
        event_type="BLOCK0_TOKEN_CREATION",
    )
    assert s1.within_50_200ms_subslot_window is True
    assert s1.block_0_token_creation_captured is True
    assert s1.in_goldilocks_bundler_tier is True
    assert s1.in_62_to_75_sol_curve_band is True
    assert s1.approaching_85_sol_threshold is True
    assert s1.triggers_stage2_firewall is True
    assert s1["triggers_stage2_firewall"] is True
    assert "stage" in s1

    # 2. Graduation squeeze band (88.0% - 99.5%) with early_buyers outside Goldilocks
    s1_squeeze = run_stage1_subslot_ingestion(
        token_mint="GradSqueezeMint1111111111111111111111111111",
        early_buyers=64,
        curve_sol=78.5,
        shred_lead_time_ms=82.0,
        event_type="WHALE_SWAP",
        sol_amount=8.5,
    )
    assert s1_squeeze.in_goldilocks_bundler_tier is False
    assert s1_squeeze.in_62_to_75_sol_curve_band is False
    assert s1_squeeze.in_88_to_99_5_graduation_squeeze_band is True
    assert s1_squeeze.whale_swap_captured is True
    assert s1_squeeze.triggers_stage2_firewall is True

    # 3. Migration logSubscribe on 39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg
    mig_res = pumpfun_listen_migrations_logsubscribe(
        logs=[
            f"Program {PUMP_FUN_PROGRAM_ID} invoke [1]",
            f"Program log: Migration Authority {PUMP_FUN_MIGRATION_AUTHORITY}",
            "Program log: Instruction: Migrate",
            "Program log: mint=MigMint111111111111111111111111111111111111 pool=MigPool111111111111111111111111111111111111",
        ],
        signature="5MigSigTest1111111111111111111111111111111111111111111",
    )
    assert mig_res["detected"] is True
    assert mig_res["migration_authority"] == PUMP_FUN_MIGRATION_AUTHORITY

    # 4. Creator sell captured in Stage 1 must NOT trigger a new Stage 2 buy entry
    s1_creator_sell = run_stage1_subslot_ingestion(
        token_mint="CreatorDumpMint1111111111111111111111111111",
        early_buyers=25,
        curve_sol=66.0,
        shred_lead_time_ms=75.0,
        event_type="CREATOR_SELL",
    )
    assert s1_creator_sell.creator_sell_captured is True
    assert s1_creator_sell.triggers_stage2_firewall is False

    # 5. Direct `pumpfun_read_curve` check approaching 85.0 SOL & raw 49-byte decoding
    curve_70 = pumpfun_read_curve(curve_sol=70.0)
    assert curve_70["curve_sol"] == pytest.approx(70.0, abs=1e-4)
    assert curve_70["in_62_to_75_sol_curve_band"] is True
    assert curve_70["remaining_sol_to_85_graduation"] == pytest.approx(15.0, abs=1e-4)

    raw_49b = struct.pack(
        "<8sQQQQQB",
        PUMP_FUN_BONDING_CURVE_DISCRIMINATOR,
        INITIAL_VIRTUAL_TOKEN_RESERVES,
        INITIAL_VIRTUAL_SOL_RESERVES_LAMPORTS,
        INITIAL_REAL_TOKEN_RESERVES,
        0,
        TOKEN_TOTAL_SUPPLY,
        0,
    )
    decoded_curve = pumpfun_read_curve(raw_curve_bytes=raw_49b)
    assert decoded_curve["curve_sol"] == pytest.approx(0.0)
    assert decoded_curve["complete"] is False


def test_stage2_pre_trade_sybil_and_melt_122_firewall() -> None:
    """Verifies Stage 2 (`gtg7784/bot-solana-wallet-tracker` + `arXiv:2602.13480`):
      - Recursive parent funding tree crawl (`SybilTransferTreeAndCohortAnalyzer`)
      - 122-feature `MLP+LSTM` / `MLP+RF` ensemble (`MeltMemeTransGuard`)
      - Hard-blocks any trade where `delta_h10_pp > 6.0` OR `pred_score >= 0.30`
      - Eliminates 56.1% of historical loss events upfront.
    """
    assert STAGE2_MAX_DELTA_H10_PP == pytest.approx(6.0)
    assert STAGE2_MAX_PRED_SCORE == pytest.approx(0.30)
    assert STAGE2_HISTORICAL_LOSS_ELIMINATION_PCT == pytest.approx(56.1)

    # 1. Clean organic launch (delta_h10_pp = 0.0 <= 6.0, pred_score < 0.30) -> APPROVED
    clean = run_stage2_sybil_melt_firewall(
        token_mint="CleanStage2Mint1111111111111111111111111111",
        early_buyers=28,
        is_sybil_cabal=False,
    )
    assert clean.firewall_passed is True
    assert clean.hard_blocked is False
    assert clean.delta_h10_pp <= 6.0
    assert clean.pred_score < 0.30
    assert clean.feature_vector_dim == 122
    assert len(clean.feature_vector) == 122
    assert 0.0 <= clean.mlp_lstm_score <= 1.0
    assert 0.0 <= clean.mlp_rf_score <= 1.0
    assert clean.historical_loss_elimination_pct == pytest.approx(56.1)
    assert clean.block_reasons == []

    # 2. High-risk Sybil cabal funding tree + bundled wash launch -> HARD BLOCKED
    cabal = run_stage2_sybil_melt_firewall(
        token_mint="CabalStage2Mint9999999999999999999999999999",
        early_buyers=24,
        is_sybil_cabal=True,
    )
    assert cabal.firewall_passed is False
    assert cabal.hard_blocked is True
    assert cabal.delta_h10_pp > 6.0
    assert cabal.delta_h10_breached is True
    assert cabal.pred_score >= 0.30
    assert cabal.pred_score_breached is True
    assert cabal.max_funding_tree_depth >= 2
    assert len(cabal.block_reasons) == 2

    # 3. Custom parent funding tree where 4 sybil leaves share `CabalRoot` -> delta_h10_pp = 7.5 > 6.0
    custom_tree_res = run_stage2_sybil_melt_firewall(
        token_mint="CustomTreeSybilMint111111111111111111111111",
        transfers=[
            {"from": "CabalRoot", "to": "RelayA"},
            {"from": "RelayA", "to": "Sybil1"},
            {"from": "RelayA", "to": "Sybil2"},
            {"from": "RelayA", "to": "Sybil3"},
            {"from": "RelayA", "to": "Sybil4"},
        ],
        wallet_holdings_pct={
            "Sybil1": 2.5,
            "Sybil2": 2.5,
            "Sybil3": 2.5,
            "Sybil4": 2.5,
            **{f"Organic_{i}": 2.5 for i in range(1, 11)},
        },
        pred_score_override=0.14,
    )
    assert custom_tree_res.delta_h10_pp == pytest.approx(7.5)
    assert custom_tree_res.delta_h10_breached is True
    assert custom_tree_res.hard_blocked is True

    # 4. Exact boundary tests:
    # 4a. delta_h10_pp = 6.00 (<= 6.0) and pred_score = 0.299 (< 0.30) -> PASSES
    edge_pass = run_stage2_sybil_melt_firewall(
        token_mint="EdgePassMint1111111111111111111111111111111",
        delta_h10_pp_override=6.0,
        pred_score_override=0.299,
    )
    assert edge_pass.firewall_passed is True
    assert edge_pass.hard_blocked is False

    # 4b. delta_h10_pp = 6.01 (> 6.0) with low pred_score = 0.12 -> HARD BLOCKED
    edge_delta_block = run_stage2_sybil_melt_firewall(
        token_mint="EdgeDeltaBlockMint1111111111111111111111111",
        delta_h10_pp_override=6.01,
        pred_score_override=0.12,
    )
    assert edge_delta_block.hard_blocked is True
    assert edge_delta_block.delta_h10_breached is True
    assert edge_delta_block.pred_score_breached is False

    # 4c. delta_h10_pp = 2.0 (<= 6.0) with pred_score = 0.30 (>= 0.30) -> HARD BLOCKED
    edge_pred_block = run_stage2_sybil_melt_firewall(
        token_mint="EdgePredBlockMint11111111111111111111111111",
        delta_h10_pp_override=2.0,
        pred_score_override=0.30,
    )
    assert edge_pred_block.hard_blocked is True
    assert edge_pred_block.delta_h10_breached is False
    assert edge_pred_block.pred_score_breached is True


def test_stage3_atomic_jito_execution_extend_account_and_creator_vault_pda() -> None:
    """Verifies Stage 3 (`dexoryn-solana/pumpfun-sniper-bot` + `@pump-fun/pump-swap-sdk`):
      - Automatic `extendAccount(pool)` prepending when `pool_data_len < 300`
      - Deterministic `coin_creator_vault_ata` PDA derivation (`coin_creator` + `creator_vault` + `wSOL`)
      - 5-Tx atomic Jito bundle vs single signed tx with `mev_only_buy_protection = True`
        (`jitodontfront111111111111111111111111111111`)
      - Tight 8.0%–15.0% (`800 <= max_slippage_bps <= 1500`) slippage enforcement.
    """
    assert STAGE3_EXTEND_ACCOUNT_MIN_POOL_LEN == 300
    assert STAGE3_MIN_SLIPPAGE_BPS == 800
    assert STAGE3_MAX_SLIPPAGE_BPS == 1500
    assert STAGE3_MAX_ATOMIC_BUNDLE_TXS == 5
    assert JITO_DONT_FRONT_PUBKEY == "jitodontfront111111111111111111111111111111"

    # 1. Deterministic `coin_creator_vault_ata` PDA derivation
    creator_a = "CoinCreatorAlpha111111111111111111111111111"
    creator_b = "CoinCreatorBeta2222222222222222222222222222"
    pda_a1 = derive_coin_creator_vault_ata(creator_a)
    pda_a2 = derive_coin_creator_vault_ata(creator_a)
    pda_b = derive_coin_creator_vault_ata(creator_b)
    assert pda_a1["coin_creator_vault_ata"] == pda_a2["coin_creator_vault_ata"]
    assert pda_a1["coin_creator_vault_authority_pda"] == pda_a2["coin_creator_vault_authority_pda"]
    assert pda_a1["coin_creator_vault_ata"] != pda_b["coin_creator_vault_ata"]
    assert pda_a1["creator_vault_seed"] == "creator_vault"
    assert pda_a1["wsol_mint"] == WSOL_MINT_PUBKEY

    # 2. Legacy 211-byte pool (< 300 bytes) -> auto-prepends `extend_account` + 5-Tx atomic Jito bundle
    s3_legacy = run_stage3_atomic_jito_execution(
        token_mint="Stage3LegacyMint111111111111111111111111111",
        pool_pubkey="Stage3Legacy211BPool11111111111111111111111",
        coin_creator=creator_a,
        pool_data_len=211,
        sol_amount=3.0,
        max_slippage_bps=1000,
        mev_only_buy_protection=True,
        dispatch_as_5tx_atomic_bundle=True,
    )
    assert s3_legacy.executed is True
    assert s3_legacy.extend_account_prepended is True
    assert s3_legacy.extend_account_bytes_added == 89
    assert s3_legacy.instructions[0]["ix_name"] == "extend_account"
    assert s3_legacy.instructions[1]["ix_name"] == "pumpswap_buy_exact_quote_in"
    assert s3_legacy.coin_creator_vault_ata == pda_a1["coin_creator_vault_ata"]
    assert s3_legacy.mev_only_buy_protection is True
    assert s3_legacy.jito_dont_front_pubkey == JITO_DONT_FRONT_PUBKEY
    assert s3_legacy.max_slippage_bps == 1000
    assert s3_legacy.max_slippage_pct == pytest.approx(10.0)
    assert s3_legacy.slippage_within_8_to_15_pct_bounds is True
    assert s3_legacy.dispatch_mode == "ATOMIC_5TX_JITO_BUNDLE"
    assert s3_legacy.bundle_tx_count == 5

    # 3. Already-extended 300-byte pool (>= 300 bytes) + single signed tx
    s3_extended = run_stage3_atomic_jito_execution(
        token_mint="Stage3ExtendedMint1111111111111111111111111",
        pool_pubkey="Stage3Extended300BPool111111111111111111111",
        coin_creator=creator_a,
        pool_data_len=300,
        sol_amount=1.5,
        max_slippage_bps=800,
        dispatch_as_5tx_atomic_bundle=False,
    )
    assert s3_extended.extend_account_prepended is False
    assert s3_extended.extend_account_bytes_added == 0
    assert len(s3_extended.instructions) == 1
    assert s3_extended.dispatch_mode == "SINGLE_SIGNED_JITO_TX"
    assert s3_extended.bundle_tx_count == 1

    # 4. Slippage outside [800, 1500] bps must raise ValueError when strict validation is enabled
    with pytest.raises(ValueError, match="800"):
        run_stage3_atomic_jito_execution(
            token_mint="BadSlippageMint1111111111111111111111111111",
            pool_pubkey="BadSlippagePool1111111111111111111111111111",
            max_slippage_bps=500,
            enforce_strict_slippage_bounds=True,
        )
    with pytest.raises(ValueError, match="1500"):
        run_stage3_atomic_jito_execution(
            token_mint="BadSlippageMint2222222222222222222222222222",
            pool_pubkey="BadSlippagePool2222222222222222222222222222",
            max_slippage_bps=2000,
            enforce_strict_slippage_bounds=True,
        )


def test_stage4_automated_exit_triggers_and_dlmm_pro_migration() -> None:
    """Verifies Stage 4 (`slightlyuseless/memecoin-trading-bot` + `arXiv:2608.20271`) with
    Dual-Broadcast (`mev_off_dual_broadcast = True`) across all 3 exit/scale triggers:
      1. Same-slot Dev/Whale-Sell Trigger (`200ms`, creator sell OR smart-wallet cohort exit)
      2. 5-Minute Microstructure Stop (`arXiv:2608.20271`: `MDD_t < -theta` or `Idle_t > delta_t`)
      3. Take-Profit Ladder & Single-Sided Meteora DLMM Pro Bin Migration + hard 6-hour (`21,600s`)
         time stop on ungraduated curves.
    """
    assert STAGE4_SAME_SLOT_EXIT_LATENCY_MS == pytest.approx(200.0)
    assert STAGE4_HARD_UNGRADUATED_TIME_STOP_SEC == pytest.approx(21_600.0)
    assert STAGE4_DEFAULT_MDD_THETA == pytest.approx(0.28)
    assert STAGE4_DEFAULT_MAX_IDLE_DELTA_T_SEC == pytest.approx(150.0)

    # Trigger 1a: Creator sell detected via ShredStream -> 100% same-slot exit (<= 200ms)
    t1_creator = run_stage4_automated_exit_and_dlmm_migration(
        token_mint="Trigger1CreatorSellMint11111111111111111111",
        hold_duration_sec=80.0,
        position_sol=2.0,
        unrealized_pnl_pct=15.0,
        creator_sell_detected=True,
        mev_off_dual_broadcast=True,
    )
    assert t1_creator.mev_off_dual_broadcast is True
    assert "JITO_BLOCK_ENGINE_MEV_OFF" in t1_creator.broadcast_channels
    assert "SWQOS_LEADER_TPU_DIRECT_QUIC" in t1_creator.broadcast_channels
    assert t1_creator.trigger1_dev_or_whale_sell_fired is True
    assert t1_creator.creator_sell_detected is True
    assert t1_creator.trigger_fired == "TRIGGER_1_SAME_SLOT_DEV_OR_WHALE_SELL_EXIT"
    assert t1_creator.exit_pct == pytest.approx(100.0)
    assert t1_creator.same_slot_200ms_exit is True
    assert t1_creator.exit_latency_ms <= 200.0
    assert t1_creator.reclaim_ata_rent is True

    # Trigger 1b: Smart-wallet cohort exit (`abstradeapi/solana-smart-wallet-analyzer`) -> 100% same-slot exit
    t1_whale = run_stage4_automated_exit_and_dlmm_migration(
        token_mint="Trigger1WhaleCohortMint11111111111111111111",
        hold_duration_sec=110.0,
        position_sol=2.0,
        unrealized_pnl_pct=30.0,
        smart_wallet_cohort_sell_detected=True,
        smart_wallets_exiting_count=2,
    )
    assert t1_whale.trigger1_dev_or_whale_sell_fired is True
    assert t1_whale.smart_wallet_cohort_sell_detected is True
    assert t1_whale.trigger_fired == "TRIGGER_1_SAME_SLOT_DEV_OR_WHALE_SELL_EXIT"
    assert t1_whale.exit_pct == pytest.approx(100.0)

    # Trigger 2a: 5-Minute Microstructure Stop (`arXiv:2608.20271`) — Liquidity Drawdown `MDD_t < -theta`
    t2_mdd = run_stage4_automated_exit_and_dlmm_migration(
        token_mint="Trigger2MddStopMint111111111111111111111111",
        hold_duration_sec=210.0,
        position_sol=2.5,
        unrealized_pnl_pct=-8.0,
        current_tvl_sol=65.0,
        peak_tvl_sol=100.0,  # MDD_t = -0.35 < -0.28
        idle_t_sec=15.0,
    )
    assert t2_mdd.trigger2_5min_microstructure_fired is True
    assert t2_mdd.mdd_breached is True
    assert t2_mdd.mdd_t == pytest.approx(-0.35)
    assert t2_mdd.rug_t_indicator == 1
    assert t2_mdd.trigger_fired == "TRIGGER_2_5MIN_MICROSTRUCTURE_STOP_ARXIV_2608_20271"
    assert t2_mdd.exit_pct == pytest.approx(100.0)
    assert t2_mdd.reclaim_ata_rent is True

    # Trigger 2b: 5-Minute Microstructure Stop (`arXiv:2608.20271`) — Inactivity Spike `Idle_t > delta_t`
    t2_idle = run_stage4_automated_exit_and_dlmm_migration(
        token_mint="Trigger2IdleStopMint11111111111111111111111",
        hold_duration_sec=250.0,
        position_sol=2.5,
        unrealized_pnl_pct=-2.0,
        current_tvl_sol=95.0,
        peak_tvl_sol=100.0,
        idle_t_sec=165.0,  # > 150.0s delta_t
    )
    assert t2_idle.trigger2_5min_microstructure_fired is True
    assert t2_idle.idle_breached is True
    assert t2_idle.rug_t_indicator == 1
    assert t2_idle.trigger_fired == "TRIGGER_2_5MIN_MICROSTRUCTURE_STOP_ARXIV_2608_20271"
    assert t2_idle.exit_pct == pytest.approx(100.0)

    # Trigger 3a: Take-Profit Ladder + Single-Sided Meteora DLMM Pro Bin Migration
    t3_dlmm = run_stage4_automated_exit_and_dlmm_migration(
        token_mint="Trigger3DlmmRunnerMint111111111111111111111",
        hold_duration_sec=400.0,
        position_sol=3.0,
        unrealized_pnl_pct=140.0,
        curve_graduated=True,
        current_tvl_sol=160.0,
        peak_tvl_sol=165.0,
        idle_t_sec=8.0,
    )
    assert t3_dlmm.trigger3_tp_dlmm_or_6h_stop_fired is True
    assert t3_dlmm.single_sided_meteora_dlmm_migrated is True
    assert t3_dlmm.trigger_fired == "TRIGGER_3_TAKE_PROFIT_AND_SINGLE_SIDED_METEORA_DLMM_MIGRATION"
    assert t3_dlmm.exit_pct == pytest.approx(50.0)
    assert t3_dlmm.runner_dlmm_migrated_pct == pytest.approx(50.0)
    assert t3_dlmm.meteora_dlmm_plan is not None
    assert t3_dlmm.meteora_dlmm_plan["program_id"] == METEORA_DLMM_PROGRAM_ID
    assert t3_dlmm.meteora_dlmm_plan["single_sided_token_only"] is True
    assert t3_dlmm.meteora_dlmm_plan["additional_sol_required"] == pytest.approx(0.0)
    assert len(t3_dlmm.meteora_dlmm_plan["bins"]) == 12

    # Trigger 3b: Hard 6-Hour (`21,600s`) Time Stop on Ungraduated Curves
    t3_6h = run_stage4_automated_exit_and_dlmm_migration(
        token_mint="Trigger3SixHourUngradMint111111111111111111",
        hold_duration_sec=21_605.0,
        position_sol=2.0,
        unrealized_pnl_pct=10.0,
        curve_graduated=False,
        current_tvl_sol=68.0,
        peak_tvl_sol=72.0,
        idle_t_sec=25.0,
    )
    assert t3_6h.hour_6_ungraduated_stop_fired is True
    assert t3_6h.trigger_fired == "TRIGGER_3_HARD_6H_UNGRADUATED_TIME_STOP"
    assert t3_6h.exit_pct == pytest.approx(100.0)
    assert t3_6h.reclaim_ata_rent is True

    # Trigger 3c: Trailing stop profit lock
    t3_trail = run_stage4_automated_exit_and_dlmm_migration(
        token_mint="Trigger3TrailLockMint1111111111111111111111",
        hold_duration_sec=190.0,
        position_sol=2.0,
        unrealized_pnl_pct=35.0,
        trailing_stop_triggered=True,
    )
    assert t3_trail.trigger_fired == "TRIGGER_3_TRAILING_STOP_PROFIT_LOCK"
    assert t3_trail.exit_pct == pytest.approx(100.0)


def test_four_stage_zero_loss_pipeline_conductor_end_to_end() -> None:
    """Verifies `FourStageZeroLossPipeline.execute_full_4stage_pipeline`,
    `simulate_approved_vs_blocked_pipeline`, and `get_telemetry_summary`.
    """
    pipeline = FourStageZeroLossPipeline()

    sim = pipeline.simulate_approved_vs_blocked_pipeline()
    assert sim["comparison"]["approved_executed"] is True
    assert sim["comparison"]["blocked_prevented"] is True
    assert sim["comparison"]["blocked_capital_risked_sol"] == pytest.approx(0.0)
    assert sim["comparison"]["approved_delta_h10_pp"] <= 6.0
    assert sim["comparison"]["blocked_delta_h10_pp"] > 6.0
    assert sim["comparison"]["approved_pred_score"] < 0.30
    assert sim["comparison"]["blocked_pred_score"] >= 0.30
    assert sim["comparison"]["historical_loss_elimination_pct"] == pytest.approx(56.1)

    approved = sim["approved_goldilocks_dlmm_runner"]
    assert approved["pipeline_status"] == "EXECUTED_ALL_4_STAGES_ZERO_LOSS"
    assert approved["stage1_passed"] is True
    assert approved["stage2_passed"] is True
    assert approved["stage3_executed"] is True
    assert approved["stage4_executed"] is True
    assert approved["stage3_execution"]["extend_account_prepended"] is True
    assert approved["stage4_exit_and_dlmm"]["single_sided_meteora_dlmm_migrated"] is True

    blocked = sim["blocked_sybil_cabal_launch"]
    assert blocked["pipeline_status"] == "HARD_BLOCKED_AT_STAGE2_FIREWALL"
    assert blocked["stage1_passed"] is True
    assert blocked["stage2_passed"] is False
    assert blocked["stage3_executed"] is False
    assert blocked["stage4_executed"] is False
    assert blocked["stage3_execution"] is None
    assert blocked["stage4_exit_and_dlmm"] is None

    telemetry = pipeline.get_telemetry_summary()
    assert telemetry["counters"]["pipeline_runs"] == 5
    assert telemetry["counters"]["stage1_ingestions"] == 5
    assert telemetry["counters"]["stage2_evaluations"] == 5
    assert telemetry["counters"]["stage2_hard_blocks"] == 1
    assert telemetry["counters"]["stage2_approvals"] == 4
    assert telemetry["counters"]["stage3_atomic_executions"] == 4
    assert telemetry["counters"]["stage3_extend_accounts_prepended"] >= 2
    assert telemetry["counters"]["stage4_trigger1_dev_whale_exits"] == 1
    assert telemetry["counters"]["stage4_trigger2_microstructure_exits"] == 1
    assert telemetry["counters"]["stage4_trigger3_dlmm_migrations"] == 1
    assert telemetry["counters"]["stage4_trigger3_6h_time_stops"] == 1
    assert telemetry["last_simulation_available"] is True
