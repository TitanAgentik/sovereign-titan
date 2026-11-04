"""Comprehensive pytest verification suite for
`src/execution/zero_collateral_flash_primitives.py` (Agent 21: `zero-collateral-flash-architect`).

Verifies:
1. 7 Cross-Chain Zero-Collateral Flash Primitives & Unit Economics Router
   (`route_optimal_flash_primitive` & `simulate_atomic_5stage_flash_lifecycle`)
2. Exact Closed-Form Optimal Flash Loan Sizing (`Delta_alpha^*`, `Delta_beta^*`),
   Post-Trade Invariant Preservation, Second-Order Taylor Depth Spread, and
   Continuous-Time Ito Lemma Loss-Versus-Rebalancing (`dLVR_t`)
   (`solve_closed_form_optimal_flash_loan_and_lvr`)
3. `#![no_std]` Ultra-Low-CU Byte-Offset `[64..72]` Balance Verifier, Validator
   Scheduler Backpack Priority Ratio, Kafka Shred-Stream Whale Backrunner, and
   Durable Nonce Account Dual-Routing (`evaluate_nostd_byte64_72_and_durable_nonce_dual_route`
   & `read_spl_token_balance_at_offset_64_72`)
4. `ZeroCollateralFlashPrimitivesEngine` Facade Diagnostics & Telemetry Summary
   (`RUN_ZERO_COLLATERAL_FLASH_PRIMITIVES`)
"""

from __future__ import annotations

import math
from pathlib import Path
import struct
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.execution.zero_collateral_flash_primitives import (
    AAVE_V3_FEE_BPS,
    AAVE_V3_FLASH_LOAN,
    AGENT_21_CORE_AFFINITY,
    AGENT_21_ID,
    ALL_7_FLASH_PRIMITIVES,
    ANCHOR_BLOATED_CU_CONSUMPTION,
    ATOMIC_5STAGE_NAMES,
    BALANCER_VAULT_EVM,
    BALANCER_VAULT_FEE_BPS,
    BASELINE_BUNDLE_LANDING_RATE_PCT,
    BASELINE_RPC_WS_P99_LATENCY_MS,
    DEFAULT_TAIL_OF_BLOCK_REMAINING_CU,
    EVM_FLASH_PRIMITIVES,
    FLASH_PRIMITIVE_SPECS,
    IPC_COMMAND_RUN_ZERO_COLLATERAL_FLASH_PRIMITIVES,
    KAFKA_SHRED_BUNDLE_LANDING_RATE_PCT,
    KAFKA_SHRED_CAPTURE_RATE_MULTIPLIER,
    KAFKA_SHRED_FAILED_TX_REDUCTION_PCT,
    KAFKA_SHRED_P99_LATENCY_MS,
    KAMINO_KLEND_BORROW_IX_INDEX,
    KAMINO_KLEND_DEFAULT_FEE_BPS,
    KAMINO_KLEND_FLASH_LOAN_FEE_SF,
    KAMINO_KLEND_SOLANA,
    MARGINFI_DEFAULT_FEE_BPS,
    MARGINFI_MAX_FEE_BPS,
    MARGINFI_MIN_FEE_BPS,
    MARGINFI_SAVE_SOLANA,
    MORPHO_BLUE_FEE_BPS,
    MORPHO_BLUE_SINGLETON_EVM,
    MORPHO_BLUE_SUPPORTED_CHAINS_COUNT,
    MORPHO_BLUE_TVL_USD,
    NOSTD_NATIVE_CU_CONSUMPTION,
    PUMPSWAP_DEFAULT_SWAP_FEE,
    SOLANA_FLASH_PRIMITIVES,
    SPL_TOKEN_ACCOUNT_SIZE_BYTES,
    SPL_TOKEN_BALANCE_OFFSET_END,
    SPL_TOKEN_BALANCE_OFFSET_START,
    UNISWAP_V2_DEFAULT_SWAP_FEE,
    UNISWAP_V2_V3_DEFAULT_FEE_BPS,
    UNISWAP_V2_V3_FLASH_SWAP,
    UNISWAP_V2_V3_MAX_FEE_BPS,
    UNISWAP_V2_V3_MIN_FEE_BPS,
    UNISWAP_V4_FEE_BPS,
    UNISWAP_V4_REVERT_CURRENCY_NOT_SETTLED,
    UNISWAP_V4_SINGLETON_EVM,
    ZeroCollateralFlashPrimitivesEngine,
    build_spl_token_account_bytes,
    evaluate_nostd_byte64_72_and_durable_nonce_dual_route,
    get_zero_collateral_flash_primitives_engine,
    read_spl_token_balance_at_offset_64_72,
    route_optimal_flash_primitive,
    simulate_atomic_5stage_flash_lifecycle,
    solve_closed_form_optimal_flash_loan_and_lvr,
)


# ============================================================================
# 1. Tests for 7 Cross-Chain Zero-Collateral Flash Primitives & Router
# ============================================================================


def test_all_7_cross_chain_flash_primitives_specs_and_unit_economics() -> None:
    """Verifies the exact 7 flash liquidity primitives and their fee/mechanism invariants."""
    assert len(ALL_7_FLASH_PRIMITIVES) == 7
    assert len(SOLANA_FLASH_PRIMITIVES) == 2
    assert len(EVM_FLASH_PRIMITIVES) == 5

    # 1. Kamino klend (Solana)
    kamino = FLASH_PRIMITIVE_SPECS[KAMINO_KLEND_SOLANA]
    assert kamino.chain_family == "SOLANA"
    assert kamino.default_fee_bps == pytest.approx(0.1)
    assert kamino.fee_fraction == pytest.approx(0.00001)
    assert kamino.requires_borrow_ix_index_zero is True
    assert kamino.klend_flash_loan_fee_sf == KAMINO_KLEND_FLASH_LOAN_FEE_SF
    assert kamino.klend_flash_loan_fee_sf > 0

    # 2. MarginFi / Save (Solana)
    marginfi = FLASH_PRIMITIVE_SPECS[MARGINFI_SAVE_SOLANA]
    assert marginfi.chain_family == "SOLANA"
    assert marginfi.default_fee_bps == pytest.approx(0.0)
    assert marginfi.min_fee_bps == pytest.approx(0.0)
    assert marginfi.max_fee_bps == pytest.approx(5.0)

    # 3. Uniswap V4 Singleton (EVM)
    univ4 = FLASH_PRIMITIVE_SPECS[UNISWAP_V4_SINGLETON_EVM]
    assert univ4.chain_family == "EVM"
    assert univ4.default_fee_bps == pytest.approx(0.0)
    assert univ4.uses_eip1153_transient_storage is True
    assert univ4.uses_erc6909_claims is True
    assert univ4.supports_complementary_token_repay is True

    # 4. Morpho Blue Singleton (EVM)
    morpho = FLASH_PRIMITIVE_SPECS[MORPHO_BLUE_SINGLETON_EVM]
    assert morpho.chain_family == "EVM"
    assert morpho.default_fee_bps == pytest.approx(0.0)
    assert morpho.tvl_usd >= 11_190_000_000.0
    assert morpho.supported_chains_count >= 36

    # 5. Balancer Vault (EVM)
    balancer = FLASH_PRIMITIVE_SPECS[BALANCER_VAULT_EVM]
    assert balancer.chain_family == "EVM"
    assert balancer.default_fee_bps == pytest.approx(0.0)

    # 6. Uniswap V2/V3 Flash Swap (EVM)
    univ2_v3 = FLASH_PRIMITIVE_SPECS[UNISWAP_V2_V3_FLASH_SWAP]
    assert univ2_v3.chain_family == "EVM"
    assert univ2_v3.min_fee_bps == pytest.approx(1.0)
    assert univ2_v3.max_fee_bps == pytest.approx(100.0)
    assert univ2_v3.supports_complementary_token_repay is True

    # 7. Aave V3 Flash Loan (EVM)
    aave = FLASH_PRIMITIVE_SPECS[AAVE_V3_FLASH_LOAN]
    assert aave.chain_family == "EVM"
    assert aave.default_fee_bps == pytest.approx(5.0)


def test_route_optimal_flash_primitive_across_solana_and_evm() -> None:
    """Verifies unit-economic routing across Solana and EVM primitives."""
    # Solana with Kamino introspection preference
    kamino_res = route_optimal_flash_primitive(
        chain_family="SOLANA",
        principal_amount=1_000_000.0,
        prefer_kamino_klend_introspection=True,
        total_instructions_in_tx=6,
    )
    assert kamino_res.selected_primitive_id == KAMINO_KLEND_SOLANA
    assert kamino_res.selected_fee_bps == pytest.approx(0.1)
    assert kamino_res.flash_fee_amount == pytest.approx(10.0)
    assert kamino_res.total_repayment_amount == pytest.approx(1_000_010.0)
    assert kamino_res.borrow_ix_index == KAMINO_KLEND_BORROW_IX_INDEX == 0
    assert kamino_res.repay_ix_index == 5
    assert kamino_res.all_7_primitives_evaluated_count == 7
    assert kamino_res["selected_primitive_id"] == KAMINO_KLEND_SOLANA

    # Solana default lowest-fee route selects 0 bps MarginFi CPI
    marginfi_res = route_optimal_flash_primitive(
        chain_family="SOLANA",
        principal_amount=250_000.0,
        prefer_kamino_klend_introspection=False,
    )
    assert marginfi_res.selected_primitive_id == MARGINFI_SAVE_SOLANA
    assert marginfi_res.selected_fee_bps == pytest.approx(0.0)
    assert marginfi_res.flash_fee_amount == pytest.approx(0.0)

    # EVM with EIP-1153 transient storage preference selects Uniswap V4
    univ4_res = route_optimal_flash_primitive(
        chain_family="EVM",
        principal_amount=3_000_000.0,
        prefer_eip1153_transient_accounting=True,
    )
    assert univ4_res.selected_primitive_id == UNISWAP_V4_SINGLETON_EVM
    assert univ4_res.selected_fee_bps == pytest.approx(0.0)
    assert univ4_res.uses_eip1153_transient_storage is True
    assert univ4_res.uses_erc6909_claims is True

    # EVM default highest-TVL 0-fee singleton selects Morpho Blue ($11.19B+ TVL)
    morpho_res = route_optimal_flash_primitive(
        chain_family="EVM",
        principal_amount=5_000_000.0,
    )
    assert morpho_res.selected_primitive_id == MORPHO_BLUE_SINGLETON_EVM
    assert morpho_res.selected_fee_bps == pytest.approx(0.0)
    assert morpho_res.flash_fee_amount == pytest.approx(0.0)

    # EVM requiring complementary pair token repayment when V4 liquidity is constrained selects Uniswap V2/V3
    comp_res = route_optimal_flash_primitive(
        chain_family="EVM",
        principal_amount=2_000_000.0,
        require_complementary_token_repay=True,
        available_liquidity_by_primitive={UNISWAP_V4_SINGLETON_EVM: 100_000.0},
        custom_fee_bps_overrides={UNISWAP_V2_V3_FLASH_SWAP: 1.0},
    )
    assert comp_res.selected_primitive_id == UNISWAP_V2_V3_FLASH_SWAP
    assert comp_res.supports_complementary_token_repay is True
    assert comp_res.selected_fee_bps == pytest.approx(1.0)


def test_simulate_atomic_5stage_flash_lifecycle_commit_and_reverts() -> None:
    """Verifies the 5-stage atomic lifecycle for profitable commits and deterministic reverts."""
    # 1. Profitable Kamino klend 5-stage commit
    commit_res = simulate_atomic_5stage_flash_lifecycle(
        primitive_id=KAMINO_KLEND_SOLANA,
        principal_borrowed=1_000.0,
        buy_price_pool_a=0.0100,
        sell_price_pool_b=0.0105,
        pool_a_swap_fee_rate=0.0030,
        pool_b_swap_fee_rate=0.0030,
        execution_priority_or_gas_fee=0.01,
        min_profit_threshold=1.0,
        borrow_ix_index=0,
    )
    assert commit_res.committed is True
    assert commit_res.reverted is False
    assert commit_res.revert_reason is None
    assert commit_res.collateral_posted == pytest.approx(0.0)
    assert commit_res.flash_fee_amount == pytest.approx(0.01)
    assert commit_res.net_profit_after_all_fees > 40.0
    assert commit_res.stages_completed_count == 5
    assert [s.stage_name for s in commit_res.stages] == list(ATOMIC_5STAGE_NAMES)

    # 2. Kamino klend revert when borrow_ix_index != 0
    bad_ix_res = simulate_atomic_5stage_flash_lifecycle(
        primitive_id=KAMINO_KLEND_SOLANA,
        principal_borrowed=1_000.0,
        buy_price_pool_a=0.0100,
        sell_price_pool_b=0.0105,
        borrow_ix_index=2,
    )
    assert bad_ix_res.committed is False
    assert bad_ix_res.reverted is True
    assert bad_ix_res.kamino_introspection_valid is False
    assert bad_ix_res.revert_reason == "KaminoFlashBorrowIxIndexMustBeZero"
    assert bad_ix_res.principal_loss_on_revert == pytest.approx(0.0)

    # 3. Uniswap V4 EIP-1153 CurrencyNotSettled revert when nonzero_delta_count != 0
    univ4_revert = simulate_atomic_5stage_flash_lifecycle(
        primitive_id=UNISWAP_V4_SINGLETON_EVM,
        principal_borrowed=50_000.0,
        buy_price_pool_a=1.00,
        sell_price_pool_b=1.02,
        simulate_unsettled_eip1153_delta=True,
    )
    assert univ4_revert.committed is False
    assert univ4_revert.reverted is True
    assert univ4_revert.eip1153_is_unlocked_during_callback is True
    assert univ4_revert.eip1153_nonzero_delta_count_after_take == 1
    assert univ4_revert.eip1153_nonzero_delta_count_after_settle == 1
    assert univ4_revert.revert_reason == UNISWAP_V4_REVERT_CURRENCY_NOT_SETTLED
    assert univ4_revert.principal_loss_on_revert == pytest.approx(0.0)

    # 4. Revert when gross proceeds are below minimum profit threshold
    unprofitable_revert = simulate_atomic_5stage_flash_lifecycle(
        primitive_id=AAVE_V3_FLASH_LOAN,
        principal_borrowed=10_000.0,
        buy_price_pool_a=1.000,
        sell_price_pool_b=1.002,
        pool_a_swap_fee_rate=0.003,
        pool_b_swap_fee_rate=0.003,
        min_profit_threshold=5.0,
    )
    assert unprofitable_revert.committed is False
    assert unprofitable_revert.reverted is True
    assert unprofitable_revert.principal_loss_on_revert == pytest.approx(0.0)


# ============================================================================
# 2. Tests for Closed-Form Optimal Flash Loan Sizing & Continuous-Time LVR
# ============================================================================


def test_closed_form_optimal_flash_loan_sizing_and_invariant_preservation() -> None:
    """Verifies exact closed-form Delta_alpha^*, Delta_beta^*, and post-trade k invariant."""
    r_alpha = 1_000_000.0
    r_beta = 1_000.0
    fee = PUMPSWAP_DEFAULT_SWAP_FEE  # 0.0125 -> gamma = 0.9875
    gamma = 1.0 - fee
    mp = 0.00125  # m_u = 0.00100, gamma * mp = 0.001234375 > 0.00100

    res = solve_closed_form_optimal_flash_loan_and_lvr(
        reserve_alpha=r_alpha,
        reserve_beta=r_beta,
        swap_fee_rate=fee,
        marginal_sell_price_mp=mp,
        flash_loan_fee_bps=0.1,
        second_pool_reserve_alpha=2_500_000.0,
        g3m_weight_w=0.5,
        volatility_sigma=1.20,
        time_step_dt=1.0,
    )

    k = r_alpha * r_beta
    expected_delta_alpha = r_alpha - math.sqrt(k / (gamma * mp))
    expected_delta_beta = (math.sqrt(k * gamma * mp) - r_beta) / gamma

    assert res.positivity_condition_met is True
    assert res.optimal_delta_alpha_star == pytest.approx(expected_delta_alpha, rel=1e-12)
    assert res.optimal_delta_beta_star == pytest.approx(expected_delta_beta, rel=1e-12)
    assert res.post_trade_invariant_k == pytest.approx(k, rel=1e-12)
    assert res.invariant_k_preserved is True
    assert res.strictly_concave_objective is True
    assert res.second_derivative_concavity < 0.0
    assert res.gross_arbitrage_profit_beta > 0.0
    assert res.net_arbitrage_profit_beta > 0.0

    # Verify numerical optimality: perturbing Delta_beta^* slightly up or down yields strictly lower profit
    for eps in (-5.0, -1.0, 1.0, 5.0):
        candidate_db = res.optimal_delta_beta_star + eps
        candidate_da = r_alpha - (k / (r_beta + gamma * candidate_db))
        candidate_profit = mp * candidate_da - candidate_db
        assert res.gross_arbitrage_profit_beta > candidate_profit


def test_closed_form_non_positive_spread_returns_zero_sizing() -> None:
    """Verifies that when gamma * m_p <= R_beta / R_alpha = m_u, optimal sizing is 0.0."""
    res = solve_closed_form_optimal_flash_loan_and_lvr(
        reserve_alpha=1_000_000.0,
        reserve_beta=1_000.0,
        swap_fee_rate=UNISWAP_V2_DEFAULT_SWAP_FEE,
        marginal_sell_price_mp=0.001001,  # gamma * m_p = 0.997 * 0.001001 < 0.001000
    )
    assert res.positivity_condition_met is False
    assert res.optimal_delta_alpha_star == pytest.approx(0.0)
    assert res.optimal_delta_beta_star == pytest.approx(0.0)
    assert res.invariant_k_preserved is True


def test_second_order_taylor_depth_spread_and_continuous_time_ito_lvr() -> None:
    """Verifies the 2nd-order Taylor depth spread formula and continuous-time Ito dLVR_t."""
    r_alpha = 500_000.0
    r_beta = 500.0
    r_alpha_prime = 2_000_000.0
    fee = 0.0030
    gamma = 1.0 - fee
    m_u = r_beta / r_alpha
    trade_alpha = 10_000.0

    # 1. Test with w = 0.5 (50/50 CPMM)
    res_50 = solve_closed_form_optimal_flash_loan_and_lvr(
        reserve_alpha=r_alpha,
        reserve_beta=r_beta,
        swap_fee_rate=fee,
        marginal_sell_price_mp=0.00130,
        second_pool_reserve_alpha=r_alpha_prime,
        taylor_trade_size_alpha=trade_alpha,
        g3m_weight_w=0.5,
        g3m_invariant_ell=15_000.0,
        spot_price_pt=0.00130,
        volatility_sigma=1.50,
        time_step_dt=0.5,
    )

    expected_taylor_spread = (
        m_u * (1.0 / gamma) * (trade_alpha ** 2) * ((1.0 / r_alpha) - (1.0 / r_alpha_prime))
    )
    assert res_50.taylor_second_order_depth_spread == pytest.approx(
        expected_taylor_spread, rel=1e-12
    )
    assert res_50.deeper_pool_requires_less_input is True

    # Verify exact Ito LVR formula for w = 0.5:
    # dLVR_t = (w^{1-w} * (1-w)^w / 2) * ell * P_t^{w-2} * sigma^2 * P_t^2 * dt
    w = 0.5
    ell = 15_000.0
    pt = 0.00130
    sigma = 1.50
    dt = 0.5
    expected_prefactor = ((w ** (1.0 - w)) * ((1.0 - w) ** w)) / 2.0
    expected_dlvr = (
        expected_prefactor * ell * (pt ** (w - 2.0)) * (sigma ** 2) * (pt ** 2) * dt
    )
    assert res_50.g3m_weight_prefactor == pytest.approx(0.25, rel=1e-12)
    assert res_50.d_lvr_t == pytest.approx(expected_dlvr, rel=1e-12)

    # 2. Test with w = 0.8 (80/20 weighted pool) and verify normalized LVR reduction
    res_80 = solve_closed_form_optimal_flash_loan_and_lvr(
        reserve_alpha=r_alpha,
        reserve_beta=r_beta,
        swap_fee_rate=fee,
        marginal_sell_price_mp=0.00130,
        g3m_weight_w=0.8,
        g3m_invariant_ell=ell,
        spot_price_pt=pt,
        volatility_sigma=sigma,
        time_step_dt=dt,
    )
    expected_prefactor_80 = ((0.8 ** 0.2) * (0.2 ** 0.8)) / 2.0
    expected_dlvr_80 = (
        expected_prefactor_80 * ell * (pt ** (0.8 - 2.0)) * (sigma ** 2) * (pt ** 2) * dt
    )
    assert res_80.d_lvr_t == pytest.approx(expected_dlvr_80, rel=1e-12)
    assert res_80.weighted_80_20_reduces_lvr_vs_50_50 is True
    assert res_80.normalized_lvr_rate_80_20 < res_80.normalized_lvr_rate_50_50


# ============================================================================
# 3. Tests for `#![no_std]` Byte-Offset `[64..72]`, Backpack Priority & Nonce
# ============================================================================


def test_read_spl_token_balance_at_offset_64_72_exact_bytes() -> None:
    """Verifies raw little-endian u64 decoding at byte offsets [64..72]."""
    expected_balance = 98_765_432_109_876
    acct_bytes = build_spl_token_account_bytes(expected_balance)

    assert len(acct_bytes) == SPL_TOKEN_ACCOUNT_SIZE_BYTES == 165
    assert acct_bytes[SPL_TOKEN_BALANCE_OFFSET_START:SPL_TOKEN_BALANCE_OFFSET_END] == struct.pack(
        "<Q", expected_balance
    )
    assert read_spl_token_balance_at_offset_64_72(acct_bytes) == expected_balance

    # Short buffer (< 72 bytes) must raise ValueError
    with pytest.raises(ValueError, match="72 bytes"):
        read_spl_token_balance_at_offset_64_72(b"\x00" * 71)


def test_nostd_backpack_priority_kafka_shred_and_durable_nonce_dual_route() -> None:
    """Verifies `#![no_std]` profit gate, validator backpack priority, Kafka Shred metrics,
    and Durable Nonce dual-routing zero duplicate execution risk.
    """
    res = evaluate_nostd_byte64_72_and_durable_nonce_dual_route(
        balance_before_units=2_000_000_000,
        balance_after_units=2_080_000_000,
        min_profit_units=15_000_000,
        fee_lamports=500_000,
        nostd_requested_cu=NOSTD_NATIVE_CU_CONSUMPTION,
        anchor_bloated_cu=ANCHOR_BLOATED_CU_CONSUMPTION,
        remaining_tail_block_cu=DEFAULT_TAIL_OF_BLOCK_REMAINING_CU,
    )

    # 1. `#![no_std]` byte-offset `[64..72]` profit gate
    assert res.no_std_enabled is True
    assert res.zero_anchor_overhead is True
    assert res.no_heap_allocator is True
    assert res.no_msg_string_formatting is True
    assert res.klend_zero_copy_cpi is True
    assert res.byte_offset_start == 64
    assert res.byte_offset_end == 72
    assert res.realized_profit_units == 80_000_000
    assert res.strict_profit_invariant_passed is True
    assert res.entrypoint_exit_code == 0

    # 2. Validator scheduler backpack priority ratio
    assert res.nostd_priority_ratio_lamports_per_cu == pytest.approx(500_000 / 18_500)
    assert res.anchor_priority_ratio_lamports_per_cu == pytest.approx(500_000 / 180_000)
    assert res.scheduler_priority_multiplier == pytest.approx(180_000 / 18_500)
    assert res.nostd_fits_remaining_block_space is True
    assert res.anchor_fits_remaining_block_space is False
    assert res.slotted_as_backpack_bonus is True

    # 3. Durable Nonce Dual-Routing (Variant A Jito + Variant B TPU)
    assert res.shared_durable_nonce_identical is True
    assert (
        res.variant_a_jito.shared_durable_nonce_hash
        == res.variant_b_tpu.shared_durable_nonce_hash
    )
    assert res.variant_a_jito.jito_tip_lamports > 0
    assert res.variant_b_tpu.jito_tip_lamports == 0
    assert res.second_variant_invalidated is True
    assert res.max_executable_variants == 1
    assert res.duplicate_execution_risk_pct == pytest.approx(0.0)

    # 4. Kafka Shred-stream whale backrunning latency compression
    assert res.baseline_rpc_ws_p99_ms == pytest.approx(BASELINE_RPC_WS_P99_LATENCY_MS)
    assert res.kafka_shred_p99_ms == pytest.approx(KAFKA_SHRED_P99_LATENCY_MS)
    assert res.p99_latency_reduction_ms == pytest.approx(73.0)
    assert res.capture_rate_multiplier == pytest.approx(KAFKA_SHRED_CAPTURE_RATE_MULTIPLIER)
    assert res.baseline_bundle_landing_rate_pct == pytest.approx(
        BASELINE_BUNDLE_LANDING_RATE_PCT
    )
    assert res.kafka_shred_bundle_landing_rate_pct == pytest.approx(
        KAFKA_SHRED_BUNDLE_LANDING_RATE_PCT
    )
    assert res.failed_tx_reduction_pct == pytest.approx(KAFKA_SHRED_FAILED_TX_REDUCTION_PCT)

    # Verify profit gate failure when balance_after <= balance_before + min_profit
    fail_res = evaluate_nostd_byte64_72_and_durable_nonce_dual_route(
        balance_before_units=2_000_000_000,
        balance_after_units=2_005_000_000,
        min_profit_units=15_000_000,
    )
    assert fail_res.strict_profit_invariant_passed is False
    assert fail_res.entrypoint_exit_code != 0


# ============================================================================
# 4. Tests for `ZeroCollateralFlashPrimitivesEngine` Facade & Diagnostics
# ============================================================================


def test_zero_collateral_flash_primitives_engine_facade_and_telemetry() -> None:
    """Verifies the singleton facade, full diagnostic report, and IPC telemetry."""
    engine = get_zero_collateral_flash_primitives_engine()
    assert isinstance(engine, ZeroCollateralFlashPrimitivesEngine)

    report = engine.run_full_flash_primitives_diagnostic()
    assert report["status"] == "PASS"
    assert report["ok"] is True
    assert report["agent_id"] == AGENT_21_ID
    assert report["core_affinity"] == AGENT_21_CORE_AFFINITY
    assert report["ipc_command"] == IPC_COMMAND_RUN_ZERO_COLLATERAL_FLASH_PRIMITIVES
    assert report["all_invariants_verified"] is True

    telemetry = engine.get_telemetry_summary()
    assert telemetry["agent_id"] == AGENT_21_ID
    assert telemetry["ipc_command"] == IPC_COMMAND_RUN_ZERO_COLLATERAL_FLASH_PRIMITIVES
    assert len(telemetry["all_7_flash_primitives"]) == 7
    assert telemetry["spl_balance_byte_offsets"] == [64, 72]
    assert telemetry["counters"]["diagnostics_run"] >= 1
    assert telemetry["last_diagnostic_available"] is True
