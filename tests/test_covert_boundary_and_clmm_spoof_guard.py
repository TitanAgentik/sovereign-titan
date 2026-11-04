"""Comprehensive pytest verification suite for
`/home/titanagentik/sovereign-titan/src/engines/covert_boundary_and_clmm_spoof_guard.py`
implementing Agent 22 (`covert-migration-jit-predator`):
1. 3-Vector Bonding Curve Graduation & Migration Boundary Exploitation
   (`evaluate_graduation_migration_boundary_vectors`)
2. Flash-Amplified Single-Tick 4,000x JIT Liquidity + Cross-Pool Delta Hedge
   (`execute_flash_amplified_single_tick_jit_with_hedge`)
3. October 2026 `$1.4B` Raydium CLMM Virtual Reserve Phantom Liquidity Loop Detector
   (`detect_clmm_virtual_reserve_phantom_spoof`)
4. `CovertBoundaryAndClmmSpoofGuard` Facade Class (`RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE`)
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engines.covert_boundary_and_clmm_spoof_guard import (
    AGENT_22_CORE_AFFINITY,
    AGENT_22_ID,
    AGENT_22_INDEX,
    ClmmPhantomLiquiditySpoofResult,
    CovertBoundaryAndClmmSpoofGuard,
    DECISION_ABORT_JIT_HEDGE_COST_EXCEEDS_FEE,
    DECISION_ABORT_JIT_INSUFFICIENT_SECONDARY_DEPTH,
    DECISION_ABORT_JIT_SPOT_OUTSIDE_ACTIVE_TICK,
    DECISION_EXECUTE_SINGLE_TICK_JIT_WITH_HEDGE,
    DECISION_EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB,
    DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB,
    DECISION_HARD_BLOCK_MAY16_AUTHORITY_ANOMALY,
    DECISION_HARD_BLOCK_PHANTOM_CLMM_SPOOF,
    DECISION_HOLD_NO_PROFITABLE_BOUNDARY_VECTOR,
    DECISION_PASS_AUTHENTIC_CLMM_LIQUIDITY,
    DEFAULT_VECTOR2_NEAR_COMPLETION_PCT,
    DEFAULT_VECTOR2_REMAINING_CURVE_PCT,
    DEFAULT_VECTOR2_REMAINING_SOL_AT_92PCT,
    FLASH_LOAN_PROVIDER_KAMINO,
    FLASH_LOAN_PROVIDER_MORPHO_BLUE,
    FLASH_LOAN_PROVIDER_UNISWAP_V4_TAKE,
    FlashAmplifiedSingleTickJitResult,
    GraduationMigrationBoundaryResult,
    IPC_ACTION_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE,
    IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE,
    KAMINO_FLASH_LOAN_FEE_PCT,
    MAX_PHANTOM_TVL_INFLATION_MULTIPLE,
    MAX_SINGLE_TICK_CAPITAL_EFFICIENCY_MULTIPLIER,
    MAY_16_2024_EXPLOIT_DATE,
    MAY_16_2024_STOLEN_SOL,
    MAY_16_2024_STOLEN_USD,
    MAY_16_2024_TOTAL_CURVE_LIQUIDITY_USD,
    MIN_REAL_CUSTODIAL_QUOTE_USD,
    OCT_2026_OPERATOR_LP_OWNERSHIP_PCT,
    OCT_2026_PHANTOM_WASH_VOLUME_30D_USD,
    OCT_2026_RAYDIUM_CLMM_FORENSIC_DATE,
    OCT_2026_RAYDIUM_CLMM_VOLUME_SHARE_PCT,
    OCT_2026_REAL_CUSTODIAL_USDC_USD,
    OCT_2026_REPORTED_AGGREGATOR_TVL_USD,
    OCT_2026_SPOOFED_CLMM_POOL_COUNT,
    OCT_2026_WASH_ROUNDTRIP_CADENCE_SEC,
    OCT_2026_WASH_ROUNDTRIP_SWAP_USDC,
    PUMPFUN_CURVE_CREATOR_FEE_PCT,
    PUMPFUN_CURVE_PLATFORM_FEE_PCT,
    PUMPFUN_CURVE_TOKEN_SUPPLY,
    PUMPFUN_CURVE_TOTAL_FEE_PCT,
    PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD,
    PUMPFUN_GRADUATION_MCAP_MAX_USD,
    PUMPFUN_GRADUATION_MCAP_MIN_USD,
    PUMPFUN_GRADUATION_MCAP_SOL,
    PUMPFUN_MIGRATION_AUTHORITY_PUBKEY,
    PUMPFUN_PERMISSIONLESS_MIGRATE_FEE_SOL,
    PUMPFUN_RESERVED_MIGRATION_SUPPLY,
    PUMPFUN_TOTAL_TOKEN_SUPPLY,
    PUMPSWAP_AMM_PROGRAM_ID,
    SUPPORTED_EXTERNAL_CLMM_VENUES,
    SUPPORTED_JIT_FEE_TIERS_BPS,
    SUPPORTED_SECONDARY_HEDGE_VENUES,
    audit_may16_withdraw_authority_anomaly,
    compute_clmm_tick_real_reserves,
    compute_intra_tx_curve_price_step_rounding_arb,
    compute_single_tick_capital_efficiency,
    detect_clmm_virtual_reserve_phantom_spoof,
    evaluate_graduation_migration_boundary_vectors,
    execute_flash_amplified_single_tick_jit_with_hedge,
    get_covert_boundary_and_clmm_spoof_guard,
    simulate_forced_graduation_kamino_flash_sweep,
)


def test_pumpfun_canonical_graduation_constants_and_vector2_forced_graduation_sweep() -> None:
    """Verifies Pump.fun canonical graduation constants and Vector 2 Forced Graduation
    Kamino Flash Sweep (`92% -> 100%`, `6.80 SOL` remaining, `0.015 SOL` permissionless
    `migrate`, LP burn on `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`, and CLMM arb).
    """
    assert AGENT_22_ID == "covert-migration-jit-predator"
    assert AGENT_22_INDEX == 22
    assert AGENT_22_CORE_AFFINITY == "Cores 16–31"
    assert PUMPFUN_TOTAL_TOKEN_SUPPLY == 1_000_000_000
    assert PUMPFUN_CURVE_TOKEN_SUPPLY == 800_000_000
    assert PUMPFUN_RESERVED_MIGRATION_SUPPLY == 200_000_000
    assert (
        PUMPFUN_CURVE_TOKEN_SUPPLY + PUMPFUN_RESERVED_MIGRATION_SUPPLY
        == PUMPFUN_TOTAL_TOKEN_SUPPLY
    )
    assert PUMPFUN_CURVE_TOTAL_FEE_PCT == pytest.approx(1.25)
    assert PUMPFUN_CURVE_PLATFORM_FEE_PCT == pytest.approx(0.95)
    assert PUMPFUN_CURVE_CREATOR_FEE_PCT == pytest.approx(0.30)
    assert (
        PUMPFUN_CURVE_PLATFORM_FEE_PCT + PUMPFUN_CURVE_CREATOR_FEE_PCT
        == pytest.approx(PUMPFUN_CURVE_TOTAL_FEE_PCT)
    )
    assert PUMPFUN_GRADUATION_COMPLETION_SOL_THRESHOLD == pytest.approx(85.0)
    assert PUMPFUN_GRADUATION_MCAP_MIN_USD == pytest.approx(30_000.0)
    assert PUMPFUN_GRADUATION_MCAP_MAX_USD == pytest.approx(69_000.0)
    assert PUMPFUN_GRADUATION_MCAP_SOL == pytest.approx(400.0)
    assert (
        PUMPFUN_MIGRATION_AUTHORITY_PUBKEY
        == "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
    )
    assert PUMPFUN_PERMISSIONLESS_MIGRATE_FEE_SOL == pytest.approx(0.015)
    assert PUMPSWAP_AMM_PROGRAM_ID == "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
    assert KAMINO_FLASH_LOAN_FEE_PCT == pytest.approx(0.001)
    assert DEFAULT_VECTOR2_NEAR_COMPLETION_PCT == pytest.approx(92.0)
    assert DEFAULT_VECTOR2_REMAINING_CURVE_PCT == pytest.approx(8.0)
    assert DEFAULT_VECTOR2_REMAINING_SOL_AT_92PCT == pytest.approx(6.80)

    res: GraduationMigrationBoundaryResult = (
        evaluate_graduation_migration_boundary_vectors(
            "GradCandidate92PctMint111111111111111111111",
            curve_completion_pct=92.0,
            external_clmm_venue="RAYDIUM_CLMM",
            external_clmm_pre_seeded=True,
            external_clmm_premium_pct=15.0,
            axiom_graduation_snipers_queued=4,
            jito_tip_sol=0.02,
        )
    )
    assert res.executable is True
    assert res.authority_guard_passed is True
    assert res.decision == DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB
    assert res.recommended_vector == "VECTOR_2_FORCED_GRADUATION_KAMINO_SWEEP"
    assert res.complete_flag_before is False
    assert res.complete_flag_after is True
    assert res.lp_burned_on_pumpswap is True
    assert res.migration_authority_pubkey == PUMPFUN_MIGRATION_AUTHORITY_PUBKEY
    assert res.permissionless_migrate_fee_sol == pytest.approx(0.015)
    assert res.pumpswap_amm_program_id == PUMPSWAP_AMM_PROGRAM_ID

    v2 = res.vector2_forced_graduation_sweep
    assert v2.remaining_curve_pct == pytest.approx(8.0)
    assert v2.remaining_sol_to_graduate == pytest.approx(6.80)
    assert v2.platform_fee_sol == pytest.approx(6.80 * 0.0095)
    assert v2.creator_fee_sol == pytest.approx(6.80 * 0.0030)
    assert v2.curve_fee_paid_sol == pytest.approx(6.80 * 0.0125)
    assert v2.migrate_instruction_fee_sol == pytest.approx(0.015)
    assert v2.kamino_flash_borrow_sol == pytest.approx(6.80 + 6.80 * 0.0125 + 0.015)
    assert v2.kamino_flash_fee_sol == pytest.approx(
        v2.kamino_flash_borrow_sol * 0.00001
    )
    assert v2.tokens_acquired_from_curve == pytest.approx(64_000_000.0)
    assert v2.net_profit_sol > 0.80
    assert len(v2.atomic_execution_steps) == 5
    # Verify dict-like compatibility
    assert res["decision"] == DECISION_EXECUTE_VECTOR2_FORCED_GRADUATION_CLMM_ARB
    assert "vector2_forced_graduation_sweep" in res


def test_vector1_intra_tx_curve_price_step_and_rounding_arbitrage() -> None:
    """Verifies Vector 1 Intra-Transaction Bonding Curve Price-Step & Rounding Arbitrage
    with zero cross-slot inventory risk.
    """
    v1 = compute_intra_tx_curve_price_step_rounding_arb(
        intra_tx_flash_sol=18.0,
        virtual_sol_reserves=30.0,
        virtual_token_reserves=1_073_000_000.0,
        sub_instruction_splits=10,
        price_step_dislocation_bps=24.0,
        priority_fee_sol=0.0005,
    )
    assert v1.enabled is True
    assert v1.atomic_same_tx is True
    assert v1.cross_slot_inventory_risk_sol == pytest.approx(0.0)
    assert v1.rounding_discrepancy_lamports > 0
    assert v1.price_step_edge_sol == pytest.approx(18.0 * 0.0024)
    assert v1.kamino_flash_fee_sol == pytest.approx(18.0 * 0.00001)
    assert v1.net_profit_sol > 0.04
    assert v1.profitable is True

    # Verify unified evaluation selects Vector 1 when curve is early (e.g. 40% complete)
    res = evaluate_graduation_migration_boundary_vectors(
        "EarlyCurveMint11111111111111111111111111111",
        curve_completion_pct=40.0,
        enable_vector1=True,
        enable_vector2=False,
        intra_tx_flash_sol=18.0,
        sub_instruction_splits=10,
        price_step_dislocation_bps=24.0,
    )
    assert res.executable is True
    assert res.decision == DECISION_EXECUTE_VECTOR1_INTRA_TX_CURVE_STEP_ARB
    assert res.recommended_vector == "VECTOR_1_INTRA_TX_PRICE_STEP_ROUNDING_ARB"
    assert res.net_expected_profit_sol == pytest.approx(v1.net_profit_sol)

    # Verify HOLD decision when neither Vector 1 nor Vector 2 is enabled/profitable
    hold_res = evaluate_graduation_migration_boundary_vectors(
        "UnprofitableBoundaryMint1111111111111111111",
        enable_vector1=False,
        enable_vector2=False,
    )
    assert hold_res.executable is False
    assert hold_res.decision == DECISION_HOLD_NO_PROFITABLE_BOUNDARY_VECTOR
    assert hold_res.net_expected_profit_sol == pytest.approx(0.0)

    # Verify Meteora and Orca pre-seeded CLMM graduation sweeps
    for venue in ("METEORA_DLMM", "ORCA_WHIRLPOOL"):
        v2_venue = simulate_forced_graduation_kamino_flash_sweep(
            curve_completion_pct=92.0,
            external_clmm_venue=venue,
            external_clmm_pre_seeded=True,
            external_clmm_premium_pct=12.0,
        )
        assert v2_venue.external_clmm_venue == venue
        assert v2_venue.profitable is True
        assert v2_venue.complete_flag_after is True
        assert v2_venue.lp_burned_on_pumpswap is True


def test_vector3_may16_2024_withdraw_authority_anomaly_guard() -> None:
    """Verifies Vector 3 historical May 16, 2024 (`12,300 SOL` / `$1.9M` from `$45M`
    curve liquidity) withdraw-authority integrity guard and multi-pool flash sweep blocker.
    """
    assert MAY_16_2024_EXPLOIT_DATE == "2024-05-16"
    assert MAY_16_2024_STOLEN_SOL == pytest.approx(12_300.0)
    assert MAY_16_2024_STOLEN_USD == pytest.approx(1_900_000.0)
    assert MAY_16_2024_TOTAL_CURVE_LIQUIDITY_USD == pytest.approx(45_000_000.0)

    clean_guard = audit_may16_withdraw_authority_anomaly()
    assert clean_guard.authority_guard_passed is True
    assert clean_guard.authority_matches_canonical is True
    assert len(clean_guard.anomaly_reasons) == 0

    compromised_res = evaluate_graduation_migration_boundary_vectors(
        "HijackedCurveMint11111111111111111111111111",
        withdraw_authority_pubkey="MaliciousWithdrawAuthority11111111111111111",
        unauthorized_authority_mutation=True,
        flash_loan_seeding_hijack_detected=True,
        simultaneous_flash_graduations_in_slot=6,
    )
    assert compromised_res.executable is False
    assert compromised_res.authority_guard_passed is False
    assert compromised_res.decision == DECISION_HARD_BLOCK_MAY16_AUTHORITY_ANOMALY
    assert compromised_res.net_expected_profit_sol == pytest.approx(0.0)
    assert len(compromised_res.vector3_may16_authority_guard.anomaly_reasons) == 4


def test_flash_amplified_single_tick_jit_4000x_efficiency_and_delta_hedge() -> None:
    """Verifies Flash-Amplified Single-Tick JIT Concentrated Liquidity (`up to 4,000x`
    capital efficiency at `100 bps` / `125 bps`) + Atomic LP Burn & Cross-Pool Delta Hedge
    across `AERODROME`, `PUMPSWAP`, and `METEORA`.
    """
    assert MAX_SINGLE_TICK_CAPITAL_EFFICIENCY_MULTIPLIER == pytest.approx(4_000.0)
    assert SUPPORTED_JIT_FEE_TIERS_BPS == (100, 125)
    assert set(SUPPORTED_SECONDARY_HEDGE_VENUES) == {"AERODROME", "PUMPSWAP", "METEORA"}
    assert set(SUPPORTED_EXTERNAL_CLMM_VENUES) == {
        "RAYDIUM_CLMM",
        "METEORA_DLMM",
        "ORCA_WHIRLPOOL",
    }

    # Ultra-tight single active tick [0.9995, 1.0005] reaches 4,000x cap
    eff = compute_single_tick_capital_efficiency(0.9995, 1.0005)
    assert eff == pytest.approx(4_000.0)

    # Profitable execution on PumpSwap at 1.25% (125 bps) fee tier
    jit_res: FlashAmplifiedSingleTickJitResult = (
        execute_flash_amplified_single_tick_jit_with_hedge(
            pool_address="RaydiumCLMMWhalePool11111111111111111111111",
            spot_price=1.0000,
            tick_lower_price=0.9995,
            tick_upper_price=1.0005,
            whale_swap_size_sol=400.0,
            fee_tier_bps=125,
            flash_borrowed_quote_sol=1_000.0,
            existing_tick_liquidity_l=20_000.0,
            flash_loan_provider=FLASH_LOAN_PROVIDER_MORPHO_BLUE,
            secondary_hedge_venue="PUMPSWAP",
            secondary_pool_depth_sol=300.0,
            cross_pool_hedge_cost_sol=1.80,
            jito_tip_sol=0.05,
        )
    )
    assert jit_res.executed is True
    assert jit_res.decision == DECISION_EXECUTE_SINGLE_TICK_JIT_WITH_HEDGE
    assert jit_res.capital_efficiency_multiplier == pytest.approx(4_000.0)
    assert jit_res.fee_tier_bps == 125
    assert jit_res.fee_tier_pct == pytest.approx(1.25)
    assert jit_res.bot_liquidity_share > 0.99
    assert jit_res.total_whale_fee_sol == pytest.approx(5.0)
    assert jit_res.captured_fee_revenue_sol > 4.95
    assert jit_res.hedge_cost_strictly_below_fee_revenue is True
    assert jit_res.secondary_pool_depth_sufficient is True
    assert jit_res.lp_burned_atomically is True
    assert jit_res.flash_loan_repaid_exact is True
    assert jit_res.residual_token_inventory_delta == pytest.approx(0.0)
    assert jit_res.net_profit_sol > 3.0
    assert len(jit_res.atomic_3step_trace) == 3

    # Also test 1.00% (100 bps) fee tier with Uniswap V4 transient take() and Aerodrome hedge
    jit_aerodrome = execute_flash_amplified_single_tick_jit_with_hedge(
        spot_price=2.0000,
        tick_lower_price=1.9990,
        tick_upper_price=2.0010,
        whale_swap_size_sol=300.0,
        fee_tier_bps=100,
        flash_borrowed_quote_sol=800.0,
        flash_loan_provider=FLASH_LOAN_PROVIDER_UNISWAP_V4_TAKE,
        secondary_hedge_venue="AERODROME",
        secondary_pool_depth_sol=250.0,
        cross_pool_hedge_cost_sol=1.10,
        jito_tip_sol=0.03,
    )
    assert jit_aerodrome.executed is True
    assert jit_aerodrome.secondary_hedge_venue == "AERODROME"
    assert jit_aerodrome.flash_loan_fee_sol == pytest.approx(0.0)
    assert jit_aerodrome.net_profit_sol > 1.80


def test_single_tick_jit_abort_guards_on_expensive_hedge_depth_and_out_of_range() -> None:
    """Verifies that Single-Tick JIT strictly aborts when:
    1. `cross_pool_hedge_cost_sol >= captured_fee_revenue_sol`
    2. `secondary_pool_depth_sol < required_hedge_notional_sol`
    3. `spot_price` is outside `[tick_lower_price, tick_upper_price]`
    """
    # 1. Hedge cost >= fee revenue
    abort_hedge = execute_flash_amplified_single_tick_jit_with_hedge(
        spot_price=1.0,
        tick_lower_price=0.9995,
        tick_upper_price=1.0005,
        whale_swap_size_sol=100.0,
        fee_tier_bps=100,  # 1.00 SOL max fee
        cross_pool_hedge_cost_sol=1.25,  # > 1.00 SOL
        secondary_hedge_venue="METEORA",
    )
    assert abort_hedge.executed is False
    assert abort_hedge.decision == DECISION_ABORT_JIT_HEDGE_COST_EXCEEDS_FEE
    assert abort_hedge.hedge_cost_strictly_below_fee_revenue is False
    assert abort_hedge.net_profit_sol == pytest.approx(0.0)

    # 2. Secondary pool depth insufficient
    abort_depth = execute_flash_amplified_single_tick_jit_with_hedge(
        spot_price=1.0,
        tick_lower_price=0.9995,
        tick_upper_price=1.0005,
        whale_swap_size_sol=500.0,
        fee_tier_bps=125,
        secondary_pool_depth_sol=10.0,  # < ~74.5 SOL required hedge notional
        cross_pool_hedge_cost_sol=1.50,
    )
    assert abort_depth.executed is False
    assert abort_depth.decision == DECISION_ABORT_JIT_INSUFFICIENT_SECONDARY_DEPTH
    assert abort_depth.secondary_pool_depth_sufficient is False

    # 3. Spot price outside [p_l, p_u]
    abort_tick = execute_flash_amplified_single_tick_jit_with_hedge(
        spot_price=1.05,
        tick_lower_price=0.9995,
        tick_upper_price=1.0005,
        whale_swap_size_sol=500.0,
    )
    assert abort_tick.executed is False
    assert abort_tick.decision == DECISION_ABORT_JIT_SPOT_OUTSIDE_ACTIVE_TICK
    assert abort_tick.spot_inside_active_tick is False


def test_clmm_tick_real_reserve_equations_and_oct2026_14b_phantom_spoof_detector() -> None:
    """Verifies the exact CLMM tick reserve equations `x(p)` and `y(p)` over `[p_l, p_u]`
    and the October 21, 2026 `$1.4B` Raydium CLMM Phantom Liquidity Loop Detector
    (`$579M+` reported TVL vs `$19.00` real USDC across `438` spoofed pools).
    """
    assert OCT_2026_RAYDIUM_CLMM_FORENSIC_DATE == "2026-10-21"
    assert OCT_2026_PHANTOM_WASH_VOLUME_30D_USD == pytest.approx(1_400_000_000.0)
    assert OCT_2026_RAYDIUM_CLMM_VOLUME_SHARE_PCT == pytest.approx(22.7)
    assert OCT_2026_SPOOFED_CLMM_POOL_COUNT == 438
    assert OCT_2026_REPORTED_AGGREGATOR_TVL_USD == pytest.approx(579_000_000.0)
    assert OCT_2026_REAL_CUSTODIAL_USDC_USD == pytest.approx(19.0)
    assert OCT_2026_WASH_ROUNDTRIP_SWAP_USDC == pytest.approx(11_000.0)
    assert OCT_2026_WASH_ROUNDTRIP_CADENCE_SEC == pytest.approx(22.0)
    assert OCT_2026_OPERATOR_LP_OWNERSHIP_PCT == pytest.approx(100.0)
    assert MIN_REAL_CUSTODIAL_QUOTE_USD == pytest.approx(5_000.0)
    assert MAX_PHANTOM_TVL_INFLATION_MULTIPLE == pytest.approx(50.0)

    # 1. Verify exact tick reserve math across all 3 regimes:
    # Regime A: p <= p_l (entirely in token X; quote Y = 0)
    x_below, y_below = compute_clmm_tick_real_reserves(
        spot_price=0.80,
        tick_lower_price=1.00,
        tick_upper_price=4.00,
        virtual_liquidity_l=1_000.0,
    )
    assert x_below == pytest.approx(1_000.0 * (1.0 / 1.0 - 1.0 / 2.0))  # 500.0
    assert y_below == pytest.approx(0.0)

    # Regime B: p_l < p < p_u (active tick holds both X and Y)
    x_in, y_in = compute_clmm_tick_real_reserves(
        spot_price=2.25,  # sqrt(p) = 1.5
        tick_lower_price=1.00,  # sqrt(p_l) = 1.0
        tick_upper_price=4.00,  # sqrt(p_u) = 2.0
        virtual_liquidity_l=1_200.0,
    )
    assert x_in == pytest.approx(1_200.0 * (1.0 / 1.5 - 1.0 / 2.0))  # 200.0
    assert y_in == pytest.approx(1_200.0 * (1.5 - 1.0))  # 600.0

    # Regime C: p >= p_u (entirely in quote Y; token X = 0)
    x_above, y_above = compute_clmm_tick_real_reserves(
        spot_price=5.00,
        tick_lower_price=1.00,
        tick_upper_price=4.00,
        virtual_liquidity_l=1_000.0,
    )
    assert x_above == pytest.approx(0.0)
    assert y_above == pytest.approx(1_000.0 * (2.0 - 1.0))  # 1,000.0

    # 2. Verify October 2026 $579M reported TVL vs $19.00 real custodial USDC spoof
    spoof_res: ClmmPhantomLiquiditySpoofResult = (
        detect_clmm_virtual_reserve_phantom_spoof(
            "Oct2026RaydiumPhantomPool438",
            spot_price=1.000019,
            tick_lower_price=1.000000,
            tick_upper_price=10_000.0,
            virtual_liquidity_l=2_000_000.0,
            total_parked_token_x=579_000_000.0,
            naive_reported_tvl_override_usd=579_000_000.0,
            operator_lp_ownership_pct=100.0,
            roundtrip_wash_swap_usd=11_000.0,
            roundtrip_wash_interval_sec=22.0,
        )
    )
    assert spoof_res.blocked is True
    assert spoof_res.decision == DECISION_HARD_BLOCK_PHANTOM_CLMM_SPOOF
    assert spoof_res.real_custodial_quote_usd == pytest.approx(19.0, rel=1e-4)
    assert spoof_res.naive_reported_tvl_usd == pytest.approx(579_000_000.0)
    assert spoof_res.phantom_tvl_inflation_multiple > 30_000_000.0
    assert spoof_res.custodial_quote_below_minimum is True
    assert spoof_res.phantom_inflation_exceeds_maximum is True
    assert spoof_res.lp_self_wash_loop_detected is True
    assert len(spoof_res.spoof_triggers) == 3

    # 3. Verify authentic deep CLMM pool passes cleanly
    clean_res = detect_clmm_virtual_reserve_phantom_spoof(
        "AuthenticSolUsdcCLMMPool",
        spot_price=1.44,  # sqrt(p) = 1.2
        tick_lower_price=1.00,  # sqrt(p_l) = 1.0
        tick_upper_price=1.96,  # sqrt(p_u) = 1.4
        virtual_liquidity_l=200_000.0,  # y(p) = 200,000 * 0.2 = $40,000 >= $5,000
        total_parked_token_x=50_000.0,
        operator_lp_ownership_pct=8.5,
        roundtrip_wash_swap_usd=0.0,
        roundtrip_wash_interval_sec=0.0,
    )
    assert clean_res.blocked is False
    assert clean_res.decision == DECISION_PASS_AUTHENTIC_CLMM_LIQUIDITY
    assert clean_res.real_custodial_quote_usd == pytest.approx(40_000.0)
    assert clean_res.phantom_tvl_inflation_multiple < 50.0
    assert clean_res.lp_self_wash_loop_detected is False
    assert len(clean_res.spoof_triggers) == 0


def test_covert_boundary_and_clmm_spoof_guard_facade_and_telemetry() -> None:
    """Verifies `CovertBoundaryAndClmmSpoofGuard` facade diagnostic and telemetry
    for `TitanIPCDaemon` (`RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE`).
    """
    guard = get_covert_boundary_and_clmm_spoof_guard()
    assert isinstance(guard, CovertBoundaryAndClmmSpoofGuard)

    fresh_guard = CovertBoundaryAndClmmSpoofGuard()
    report = fresh_guard.run_full_covert_boundary_diagnostic()
    assert report["status"] == "PASS"
    assert report["ok"] is True
    assert report["all_invariants_verified"] is True
    assert report["agent_id"] == AGENT_22_ID
    assert report["ipc_command"] == IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE
    assert (
        IPC_ACTION_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE
        == IPC_COMMAND_RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE
    )

    telemetry = fresh_guard.get_telemetry_summary()
    assert telemetry["agent_id"] == AGENT_22_ID
    assert telemetry["agent_index"] == 22
    assert telemetry["ipc_command"] == "RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE"
    assert telemetry["counters"]["diagnostics_run"] == 1
    assert telemetry["counters"]["graduation_evaluations_run"] == 3
    assert telemetry["counters"]["vector1_executions"] == 1
    assert telemetry["counters"]["vector2_executions"] == 1
    assert telemetry["counters"]["vector3_authority_blocks"] == 1
    assert telemetry["counters"]["single_tick_jit_runs"] == 2
    assert telemetry["counters"]["single_tick_jit_executions"] == 1
    assert telemetry["counters"]["single_tick_jit_aborts"] == 1
    assert telemetry["counters"]["clmm_spoof_audits_run"] == 2
    assert telemetry["counters"]["clmm_phantom_pools_blocked"] == 1
    assert telemetry["last_diagnostic_available"] is True
