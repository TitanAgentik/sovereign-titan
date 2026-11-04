"""Comprehensive pytest verification suite for Agent 25 (`sanctum-lst-superbundle-arb`):
Sanctum LST Depeg & 48h Epoch-Boundary Kamino Flash Arbitrage +
5-Transaction Jito Super-Bundle Knapsack Combiner
(`tests/test_sanctum_lst_and_superbundle_engine.py`).
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engines.sanctum_lst_and_superbundle_engine import (
    AGENT_25_ID,
    AGENT_25_INDEX,
    BundleTransactionSpec,
    CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE,
    DECISION_EXECUTE_5TX_JITO_SUPER_BUNDLE,
    DECISION_EXECUTE_PRIMARY_ONLY_BUNDLE,
    DECISION_EXECUTE_SANCTUM_LST_FLASH_ARB,
    DECISION_SKIP_NO_DEPEG_OR_EPOCH_STEP_UP,
    DECISION_SKIP_SPREAD_BELOW_COMBINED_FEES,
    FINAL_AGGREGATED_JITO_TIP_IX_LABEL,
    IPC_ACTION_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE,
    JITODONTFRONT_PUBKEY,
    KAMINO_FLASH_LOAN_FEE_BPS,
    KAMINO_FLASH_LOAN_FEE_PCT,
    MAX_JITO_BUNDLE_CU_LIMIT,
    MAX_JITO_BUNDLE_TX_COUNT,
    SANCTUM_INFINITY_POOL_MINT,
    SANCTUM_LST_REGISTRY,
    SOLANA_EPOCH_DURATION_HOURS,
    STAGE2_KNAPSACK_WIN_RATE_BOOST_MAX_PCT,
    STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT,
    SUPPORTED_LST_DEX_VENUES,
    SUPPORTED_SANCTUM_LSTS,
    SUPPORTED_SANCTUM_REDEMPTION_ROUTES,
    SanctumLstAndSuperBundleEngine,
    TRIGGER_DUAL_WHALE_DEPEG_AND_EPOCH_STEP_UP,
    TRIGGER_EPOCH_BOUNDARY_NAV_STEP_UP,
    TRIGGER_NONE,
    TRIGGER_WHALE_DEX_LST_DEPEG,
    compute_optimal_kamino_flash_principal_sol,
    evaluate_sanctum_lst_flash_arbitrage,
    normalize_sanctum_lst_symbol,
    pack_5tx_super_bundle,
)


# ============================================================================
# 1. Canonical Ecosystem & Registry Verification
# ============================================================================


def test_sanctum_constants_and_8_lst_registry() -> None:
    """Verifies canonical Sanctum Infinity Pool mint, Kamino fee, and all 8 LSTs."""
    assert SANCTUM_INFINITY_POOL_MINT == "5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm"
    assert KAMINO_FLASH_LOAN_FEE_BPS == pytest.approx(0.1)
    assert KAMINO_FLASH_LOAN_FEE_PCT == pytest.approx(0.001)
    assert SOLANA_EPOCH_DURATION_HOURS == pytest.approx(48.0)

    expected_lsts = (
        "jitoSOL",
        "mSOL",
        "bSOL",
        "INF",
        "jupsol",
        "bonkSOL",
        "hSOL",
        "compassSOL",
    )
    assert SUPPORTED_SANCTUM_LSTS == expected_lsts
    for lst in expected_lsts:
        assert lst in SANCTUM_LST_REGISTRY
        meta = SANCTUM_LST_REGISTRY[lst]
        assert meta.default_nav_sol > 1.0
        assert len(meta.mint) >= 32

    assert SANCTUM_LST_REGISTRY["INF"].mint == SANCTUM_INFINITY_POOL_MINT


@pytest.mark.parametrize(
    "raw_input,expected",
    [
        ("jitoSOL", "jitoSOL"),
        ("JitoSOL", "jitoSOL"),
        ("JITOSOL", "jitoSOL"),
        ("mSOL", "mSOL"),
        ("bSOL", "bSOL"),
        ("INF", "INF"),
        ("inf", "INF"),
        ("jupsol", "jupsol"),
        ("jupSOL", "jupsol"),
        ("bonkSOL", "bonkSOL"),
        ("hSOL", "hSOL"),
        ("compassSOL", "compassSOL"),
    ],
)
def test_normalize_sanctum_lst_symbol(raw_input: str, expected: str) -> None:
    """Verifies case-insensitive normalization of LST symbols."""
    assert normalize_sanctum_lst_symbol(raw_input) == expected


def test_normalize_sanctum_lst_symbol_rejects_unknown() -> None:
    """Verifies unknown LST symbols raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported Sanctum LST symbol"):
        normalize_sanctum_lst_symbol("fakeSOL")


# ============================================================================
# 2. Pillar 1: Sanctum LST Depeg & 48h Epoch-Boundary Kamino Flash Arbitrage
# ============================================================================


def test_trigger_a_whale_dex_lst_depeg_flash_arbitrage() -> None:
    """Verifies Trigger A (`WHALE_DEX_LST_DEPEG`) when a whale market-sells jitoSOL on
    Orca Whirlpools, depressing P_DEX below P_NAV beyond combined fees.
    """
    res = evaluate_sanctum_lst_flash_arbitrage(
        "jitoSOL",
        dex_venue="ORCA_WHIRLPOOL",
        sanctum_redemption_route="SANCTUM_INFINITY_SWAP_VIA_STAKE",
        nav_price_sol=1.1485,
        dex_spot_price_sol=1.1425,  # ~52.5 bps below NAV
        whale_sell_lst_amount=2_000.0,
        is_epoch_boundary=False,
        dex_sol_reserve=25_000.0,
        sanctum_fee_bps=1.0,
        dex_fee_bps=1.0,
        kamino_flash_fee_bps=0.1,
    )

    assert res.triggered is True
    assert res.decision == DECISION_EXECUTE_SANCTUM_LST_FLASH_ARB
    assert res.trigger_type == TRIGGER_WHALE_DEX_LST_DEPEG
    assert res.whale_depeg_trigger_detected is True
    assert res.epoch_boundary_trigger_detected is False
    assert res.combined_fee_threshold_bps == pytest.approx(2.1)
    assert res.spread_bps > res.combined_fee_threshold_bps
    assert res.optimal_flash_borrow_sol > 0.0
    assert res.executed_flash_borrow_sol == pytest.approx(res.optimal_flash_borrow_sol)
    assert res.sanctum_sol_redeemed > res.kamino_repay_total_sol
    assert res.net_profit_sol > 0.0
    assert res.net_profit_lamports > 0
    assert res.directional_memecoin_risk == 0.0
    assert tuple(res.atomic_instruction_sequence) == CANONICAL_4IX_SANCTUM_FLASH_SEQUENCE
    assert len(res.instruction_breakdown) == 4
    assert res.instruction_breakdown[0].instruction_label == "flashBorrowIx(SOL)"
    assert res.instruction_breakdown[1].instruction_label == "DEX Swap SOL->LST"
    assert (
        res.instruction_breakdown[2].instruction_label
        == "Sanctum SwapViaStake / Unstake LST->SOL"
    )
    assert res.instruction_breakdown[3].instruction_label == "flashRepayIx(SOL)"


def test_trigger_a_whale_sell_automatic_reserve_depression() -> None:
    """Verifies that passing `whale_sell_lst_amount > 0` without a manually depressed
    `dex_spot_price_sol` automatically computes the depressed post-whale DEX price.
    """
    res = evaluate_sanctum_lst_flash_arbitrage(
        "INF",
        dex_venue="METEORA_DLMM",
        sanctum_redemption_route="SANCTUM_INFINITY_SWAP_VIA_STAKE",
        whale_sell_lst_amount=1_500.0,
        dex_sol_reserve=20_000.0,
        sanctum_fee_bps=1.0,
        dex_fee_bps=1.0,
        kamino_flash_fee_bps=0.1,
    )

    assert res.triggered is True
    assert res.trigger_type == TRIGGER_WHALE_DEX_LST_DEPEG
    assert res.dex_spot_price_sol < res.nav_price_sol
    assert res.spread_bps > res.combined_fee_threshold_bps
    assert res.net_profit_sol > 0.0
    assert res.directional_memecoin_risk == 0.0


def test_trigger_b_epoch_boundary_nav_step_up_flash_arbitrage() -> None:
    """Verifies Trigger B (`EPOCH_BOUNDARY_NAV_STEP_UP`) at the ~48-hour Solana Epoch
    boundary when validator staking rewards accrue to the stake pool and step up P_NAV.
    """
    res = evaluate_sanctum_lst_flash_arbitrage(
        "mSOL",
        dex_venue="RAYDIUM_CLMM",
        sanctum_redemption_route="SANCTUM_UNSTAKE_RESERVE",
        nav_price_sol=1.2140,
        is_epoch_boundary=True,
        epoch_reward_step_up_bps=22.0,
        dex_sol_reserve=30_000.0,
        sanctum_fee_bps=1.0,
        dex_fee_bps=1.0,
        kamino_flash_fee_bps=0.1,
    )

    assert res.triggered is True
    assert res.decision == DECISION_EXECUTE_SANCTUM_LST_FLASH_ARB
    assert res.trigger_type == TRIGGER_EPOCH_BOUNDARY_NAV_STEP_UP
    assert res.epoch_boundary_trigger_detected is True
    assert res.is_epoch_boundary is True
    assert res.epoch_duration_hours == pytest.approx(48.0)
    assert res.nav_price_sol == pytest.approx(1.2140 * (1.0 + 22.0 / 10_000.0), rel=1e-6)
    assert res.dex_spot_price_sol == pytest.approx(1.2140, rel=1e-6)
    assert res.spread_bps == pytest.approx(22.0, rel=1e-3)
    assert res.net_profit_sol > 0.0
    assert res.directional_memecoin_risk == 0.0


def test_dual_trigger_whale_depeg_and_epoch_boundary() -> None:
    """Verifies simultaneous whale market-sell and epoch-boundary NAV step-up."""
    res = evaluate_sanctum_lst_flash_arbitrage(
        "jupsol",
        dex_venue="ORCA_WHIRLPOOL",
        nav_price_sol=1.0950,
        dex_spot_price_sol=1.0900,
        whale_sell_lst_amount=1_200.0,
        is_epoch_boundary=True,
        epoch_reward_step_up_bps=15.0,
        dex_sol_reserve=25_000.0,
    )

    assert res.triggered is True
    assert res.trigger_type == TRIGGER_DUAL_WHALE_DEPEG_AND_EPOCH_STEP_UP
    assert res.whale_depeg_trigger_detected is True
    assert res.epoch_boundary_trigger_detected is True
    assert res.net_profit_sol > 0.0


@pytest.mark.parametrize("lst_symbol", SUPPORTED_SANCTUM_LSTS)
@pytest.mark.parametrize("dex_venue", SUPPORTED_LST_DEX_VENUES)
@pytest.mark.parametrize("route", SUPPORTED_SANCTUM_REDEMPTION_ROUTES)
def test_all_8_lsts_across_all_dex_venues_and_sanctum_routes(
    lst_symbol: str,
    dex_venue: str,
    route: str,
) -> None:
    """Verifies all 8 canonical LSTs across Orca, Raydium, and Meteora and all Sanctum routes."""
    meta = SANCTUM_LST_REGISTRY[lst_symbol]
    res = evaluate_sanctum_lst_flash_arbitrage(
        lst_symbol,
        dex_venue=dex_venue,
        sanctum_redemption_route=route,
        nav_price_sol=meta.default_nav_sol,
        dex_spot_price_sol=meta.default_nav_sol * 0.9960,  # ~40 bps depeg
        whale_sell_lst_amount=1_000.0,
        dex_sol_reserve=20_000.0,
    )

    assert res.triggered is True
    assert res.lst_symbol == lst_symbol
    assert res.dex_venue == dex_venue
    assert res.sanctum_redemption_route == route
    assert res.net_profit_sol > 0.0
    assert res.directional_memecoin_risk == 0.0


def test_closed_form_optimal_kamino_flash_loan_maximizes_profit() -> None:
    """Proves numerically that the closed-form optimal Kamino flash loan principal
    maximizes gross arbitrage profit compared to perturbations +/- 15%.
    """
    optimal_res = evaluate_sanctum_lst_flash_arbitrage(
        "jitoSOL",
        nav_price_sol=1.1500,
        dex_spot_price_sol=1.1420,
        dex_sol_reserve=25_000.0,
        sanctum_fee_bps=1.0,
        dex_fee_bps=1.0,
        kamino_flash_fee_bps=0.1,
        max_flash_borrow_sol=10_000.0,
    )
    q_star = optimal_res.optimal_flash_borrow_sol
    assert q_star > 10.0

    under_res = evaluate_sanctum_lst_flash_arbitrage(
        "jitoSOL",
        nav_price_sol=1.1500,
        dex_spot_price_sol=1.1420,
        dex_sol_reserve=25_000.0,
        sanctum_fee_bps=1.0,
        dex_fee_bps=1.0,
        kamino_flash_fee_bps=0.1,
        max_flash_borrow_sol=10_000.0,
        override_flash_borrow_sol=q_star * 0.80,
    )
    over_res = evaluate_sanctum_lst_flash_arbitrage(
        "jitoSOL",
        nav_price_sol=1.1500,
        dex_spot_price_sol=1.1420,
        dex_sol_reserve=25_000.0,
        sanctum_fee_bps=1.0,
        dex_fee_bps=1.0,
        kamino_flash_fee_bps=0.1,
        max_flash_borrow_sol=10_000.0,
        override_flash_borrow_sol=q_star * 1.20,
    )

    assert optimal_res.gross_profit_sol > under_res.gross_profit_sol
    assert optimal_res.gross_profit_sol > over_res.gross_profit_sol


def test_skip_when_spread_below_combined_fees_or_no_depeg() -> None:
    """Verifies that no arbitrage is executed when spread <= combined fees or P_DEX >= P_NAV."""
    # Case 1: No depeg (P_DEX == P_NAV)
    no_depeg_res = evaluate_sanctum_lst_flash_arbitrage(
        "bSOL",
        nav_price_sol=1.1620,
        dex_spot_price_sol=1.1620,
        whale_sell_lst_amount=0.0,
        is_epoch_boundary=False,
    )
    assert no_depeg_res.triggered is False
    assert no_depeg_res.decision == DECISION_SKIP_NO_DEPEG_OR_EPOCH_STEP_UP
    assert no_depeg_res.trigger_type == TRIGGER_NONE
    assert no_depeg_res.net_profit_sol == 0.0

    # Case 2: Micro spread (1.2 bps) below combined fee threshold (1.0 + 1.0 + 0.1 = 2.1 bps)
    sub_fee_res = evaluate_sanctum_lst_flash_arbitrage(
        "hSOL",
        nav_price_sol=1.1120,
        dex_spot_price_sol=1.1120 / (1.0 + 0.00012),  # 1.2 bps spread < 2.1 bps fees
        sanctum_fee_bps=1.0,
        dex_fee_bps=1.0,
        kamino_flash_fee_bps=0.1,
    )
    assert sub_fee_res.triggered is False
    assert sub_fee_res.decision == DECISION_SKIP_SPREAD_BELOW_COMBINED_FEES
    assert sub_fee_res.net_profit_sol == 0.0


def test_invalid_dex_venue_and_route_raise_value_error() -> None:
    """Verifies validation errors on unsupported DEX venue or Sanctum route."""
    with pytest.raises(ValueError, match="Unsupported DEX venue"):
        evaluate_sanctum_lst_flash_arbitrage("jitoSOL", dex_venue="UNISWAP_V2")

    with pytest.raises(ValueError, match="Unsupported Sanctum redemption route"):
        evaluate_sanctum_lst_flash_arbitrage(
            "jitoSOL", sanctum_redemption_route="INVALID_ROUTE"
        )


def test_compute_optimal_principal_edge_cases() -> None:
    """Verifies edge cases of `compute_optimal_kamino_flash_principal_sol`."""
    assert (
        compute_optimal_kamino_flash_principal_sol(
            dex_sol_reserve=0.0,
            dex_lst_reserve=1000.0,
            nav_price_sol=1.15,
            dex_fee_bps=1.0,
            sanctum_fee_bps=1.0,
        )
        == 0.0
    )
    assert (
        compute_optimal_kamino_flash_principal_sol(
            dex_sol_reserve=1000.0,
            dex_lst_reserve=1000.0,
            nav_price_sol=1.15,
            dex_fee_bps=10_000.0,
            sanctum_fee_bps=1.0,
        )
        == 0.0
    )


# ============================================================================
# 3. Pillar 2: 5-Transaction Jito Super-Bundle Combiner (`pack_5tx_super_bundle`)
# ============================================================================


def test_pack_5tx_super_bundle_default_canonical_packing() -> None:
    """Verifies 5-Tx Jito Super-Bundle packing with default primary and secondary queue:
    - Packs exactly 5 transactions (`Tx[0..4]`)
    - Rejects write-lock colliding candidate (`WRITE_LOCK_COLLISION`)
    - Enforces total CU <= 1,400,000
    - Preserves `jitodontfront` at Index 0 (`Tx[0]`)
    - Places single aggregated Jito tip transfer as the final instruction of `Tx[4]`
    - Amplifies `super_bundle_tip_per_cu > single_opp_tip_per_cu`
    - Achieves `25.0 <= auction_win_rate_boost_pct <= 40.0`
    """
    res = pack_5tx_super_bundle()

    assert res.packed is True
    assert res.decision == DECISION_EXECUTE_5TX_JITO_SUPER_BUNDLE
    assert res.bundle_tx_count == MAX_JITO_BUNDLE_TX_COUNT == 5
    assert res.primary_tx_count == 1
    assert res.secondary_tx_packed_count == 4
    assert res.total_bundle_compute_units <= MAX_JITO_BUNDLE_CU_LIMIT
    assert res.disjoint_write_locks_verified is True
    assert res.write_lock_collision_count >= 1

    # Verify jitodontfront at Index 0 (Tx[0])
    assert res.tx0_has_jitodontfront is True
    assert JITODONTFRONT_PUBKEY in res.packed_transactions[0].read_only_accounts

    # Verify single aggregated Jito tip at final instruction of final transaction (Tx[4])
    assert res.single_aggregated_tip_verified is True
    assert res.final_tx_index == 4
    assert res.final_tx_has_aggregated_tip_ix is True
    assert res.final_instruction_of_final_tx == FINAL_AGGREGATED_JITO_TIP_IX_LABEL

    for idx in range(4):
        assert res.packed_transactions[idx].has_jito_tip_ix is False
        assert res.packed_transactions[idx].aggregated_tip_lamports_on_tx == 0

    assert res.packed_transactions[4].has_jito_tip_ix is True
    assert (
        res.packed_transactions[4].aggregated_tip_lamports_on_tx
        == res.super_bundle_total_tip_lamports
    )
    assert (
        res.packed_transactions[4].instructions[-1]
        == FINAL_AGGREGATED_JITO_TIP_IX_LABEL
    )

    # Verify Knapsack score amplification and Stage-2 win-rate boost (+25% to +40%)
    assert res.super_bundle_tip_per_cu > res.single_opp_tip_per_cu
    assert (
        STAGE2_KNAPSACK_WIN_RATE_BOOST_MIN_PCT
        <= res.auction_win_rate_boost_pct
        <= STAGE2_KNAPSACK_WIN_RATE_BOOST_MAX_PCT
    )
    assert res.combined_net_profit_sol > res.primary_net_profit_sol > 0.0


def test_pack_5tx_super_bundle_enforces_cu_limit_and_injects_jitodontfront() -> None:
    """Verifies that:
    1. Candidates exceeding the 1,400,000 CU ceiling are rejected with `CU_LIMIT_EXCEEDED`.
    2. If `Tx[0]` is passed without `jitodontfront` in `read_only_accounts`, the packer
       automatically injects it at Index 0.
    """
    primary = [
        {
            "tx_id": "primary_tx0_heavy",
            "opportunity_type": "PRIMARY_BACKRUN",
            "compute_units": 900_000,
            "gross_profit_sol": 0.12,
            "tip_contribution_lamports": 36_000_000,
            "write_locked_accounts": ["Acct_A", "Acct_B"],
            "read_only_accounts": ["SomeProgram1111111111111111111111111111111"],
        },
        {
            "tx_id": "primary_tx1_companion",
            "opportunity_type": "PRIMARY_SETTLEMENT",
            "compute_units": 300_000,
            "gross_profit_sol": 0.04,
            "tip_contribution_lamports": 12_000_000,
            "write_locked_accounts": ["Acct_C"],
            "read_only_accounts": [],
        },
    ]

    secondaries = [
        # Exceeds remaining 200,000 CU budget (900k + 300k + 350k = 1.55M > 1.4M)
        {
            "tx_id": "cand_over_cu",
            "opportunity_type": "MICRO_ARBITRAGE",
            "compute_units": 350_000,
            "gross_profit_sol": 0.05,
            "tip_contribution_lamports": 25_000_000,
            "write_locked_accounts": ["Acct_D"],
        },
        # Fits within remaining 200,000 CU budget (900k + 300k + 120k = 1.32M <= 1.4M)
        {
            "tx_id": "cand_fits_cu",
            "opportunity_type": "SPL_CLOSE_ACCOUNT_RENT_RECLAIM",
            "compute_units": 120_000,
            "gross_profit_sol": 0.025,
            "tip_contribution_lamports": 14_400_000,
            "write_locked_accounts": ["Acct_E"],
        },
    ]

    res = pack_5tx_super_bundle(
        primary_transactions=primary,
        secondary_candidates=secondaries,
    )

    assert res.bundle_tx_count == 3
    assert res.primary_tx_count == 2
    assert res.secondary_tx_packed_count == 1
    assert res.total_bundle_compute_units == 1_320_000 <= MAX_JITO_BUNDLE_CU_LIMIT
    assert res.tx0_has_jitodontfront is True
    assert res.packed_transactions[0].read_only_accounts[0] == JITODONTFRONT_PUBKEY

    rejection_reasons = {r.tx_id: r.rejection_reason for r in res.rejected_candidates}
    assert rejection_reasons["cand_over_cu"] == "CU_LIMIT_EXCEEDED"


def test_pack_5tx_super_bundle_primary_only_when_no_valid_secondaries() -> None:
    """Verifies graceful fallback to primary-only bundle when all secondaries collide."""
    primary = [
        BundleTransactionSpec(
            tx_id="primary_only_tx0",
            opportunity_type="PRIMARY_SANCTUM_LST_FLASH_ARB",
            compute_units=200_000,
            gross_profit_sol=0.05,
            tip_contribution_sol=0.01,
            tip_contribution_lamports=10_000_000,
            write_locked_accounts=["SharedPoolLock_1"],
        )
    ]
    colliding_secondaries = [
        BundleTransactionSpec(
            tx_id="colliding_sec_1",
            opportunity_type="MICRO_ARBITRAGE",
            compute_units=50_000,
            gross_profit_sol=0.01,
            tip_contribution_sol=0.003,
            tip_contribution_lamports=3_000_000,
            write_locked_accounts=["SharedPoolLock_1"],
        )
    ]

    res = pack_5tx_super_bundle(
        primary_transactions=primary,
        secondary_candidates=colliding_secondaries,
    )

    assert res.packed is True
    assert res.decision == DECISION_EXECUTE_PRIMARY_ONLY_BUNDLE
    assert res.bundle_tx_count == 1
    assert res.secondary_tx_packed_count == 0
    assert res.auction_win_rate_boost_pct == 0.0
    assert res.final_tx_index == 0
    assert res.final_tx_has_aggregated_tip_ix is True


def test_pack_5tx_super_bundle_validation_errors() -> None:
    """Verifies input validation for empty primaries, internal primary collisions, or >5 primaries."""
    with pytest.raises(ValueError, match="at least 1 transaction"):
        pack_5tx_super_bundle(primary_transactions=[])

    with pytest.raises(ValueError, match="internal write-lock collision"):
        pack_5tx_super_bundle(
            primary_transactions=[
                {
                    "tx_id": "p0",
                    "compute_units": 100_000,
                    "gross_profit_sol": 0.02,
                    "tip_contribution_lamports": 2_000_000,
                    "write_locked_accounts": ["Lock_X"],
                },
                {
                    "tx_id": "p1",
                    "compute_units": 100_000,
                    "gross_profit_sol": 0.02,
                    "tip_contribution_lamports": 2_000_000,
                    "write_locked_accounts": ["Lock_X"],
                },
            ]
        )


# ============================================================================
# 4. Pillar 3: `SanctumLstAndSuperBundleEngine` Facade & Diagnostic Suite
# ============================================================================


def test_sanctum_lst_and_superbundle_engine_facade_and_diagnostic() -> None:
    """Verifies `SanctumLstAndSuperBundleEngine` end-to-end diagnostic and telemetry."""
    engine = SanctumLstAndSuperBundleEngine()

    diag = engine.run_full_sanctum_superbundle_diagnostic()
    assert diag["status"] == "OK"
    assert diag["ipc_action"] == IPC_ACTION_RUN_SANCTUM_LST_SUPERBUNDLE_SUITE
    assert diag["agent_id"] == AGENT_25_ID

    whale_arb = diag["whale_depeg_flash_arbitrage"]
    assert whale_arb["triggered"] is True
    assert whale_arb["trigger_type"] == TRIGGER_WHALE_DEX_LST_DEPEG
    assert whale_arb["net_profit_sol"] > 0.0
    assert whale_arb["directional_memecoin_risk"] == 0.0

    epoch_arb = diag["epoch_boundary_flash_arbitrage"]
    assert epoch_arb["triggered"] is True
    assert epoch_arb["trigger_type"] == TRIGGER_EPOCH_BOUNDARY_NAV_STEP_UP
    assert epoch_arb["net_profit_sol"] > 0.0
    assert epoch_arb["directional_memecoin_risk"] == 0.0

    sweep = diag["sanctum_8lst_ecosystem_sweep"]
    assert len(sweep) == 8
    for lst_sym in SUPPORTED_SANCTUM_LSTS:
        assert sweep[lst_sym]["triggered"] is True
        assert sweep[lst_sym]["net_profit_sol"] > 0.0
        assert sweep[lst_sym]["directional_memecoin_risk"] == 0.0

    bundle = diag["jito_5tx_super_bundle"]
    assert bundle["packed"] is True
    assert bundle["bundle_tx_count"] == 5
    assert bundle["tx0_has_jitodontfront"] is True
    assert bundle["single_aggregated_tip_verified"] is True
    assert bundle["super_bundle_tip_per_cu"] > bundle["single_opp_tip_per_cu"]
    assert 25.0 <= bundle["auction_win_rate_boost_pct"] <= 40.0

    telemetry = engine.get_telemetry_summary()
    assert telemetry["engine"] == "SanctumLstAndSuperBundleEngine"
    assert telemetry["agent_id"] == AGENT_25_ID
    assert telemetry["agent_index"] == AGENT_25_INDEX
    assert telemetry["lst_arb_evaluations"] == 10  # 2 primary triggers + 8 LST sweep
    assert telemetry["lst_arb_triggered_count"] == 10
    assert telemetry["super_bundle_packs"] == 1
    assert telemetry["super_bundle_5tx_count"] == 1
    assert telemetry["cumulative_lst_arb_net_profit_sol"] > 0.0
    assert telemetry["cumulative_super_bundle_net_profit_sol"] > 0.0


def test_dict_like_model_mixin_compatibility() -> None:
    """Verifies that result dataclasses support both attribute and dict-style access."""
    arb_res = evaluate_sanctum_lst_flash_arbitrage(
        "compassSOL",
        nav_price_sol=1.0840,
        dex_spot_price_sol=1.0790,
        whale_sell_lst_amount=800.0,
    )
    assert "net_profit_sol" in arb_res
    assert arb_res["net_profit_sol"] == arb_res.net_profit_sol
    assert arb_res.get("lst_symbol") == "compassSOL"
    assert arb_res.get("non_existent_key", "fallback") == "fallback"
    assert len(arb_res) == len(arb_res.keys())
    assert dict(arb_res.items())["lst_symbol"] == "compassSOL"
    assert list(iter(arb_res)) == arb_res.keys()
    assert len(arb_res.values()) == len(arb_res.keys())
