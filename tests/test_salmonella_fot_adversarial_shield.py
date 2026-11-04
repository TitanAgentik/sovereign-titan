"""Comprehensive pytest verification suite for
`/home/titanagentik/sovereign-titan/src/security/salmonella_fot_adversarial_shield.py`
implementing Agent 24 (`salmonella-fot-adversarial-shield`):
1. October 2026 Empirical Memecoin Forensics Benchmark Suite (`OCTOBER_2026_EMPIRICAL_FORENSICS_BENCHMARKS`)
2. 5-Vector Adversarial Engineering & Failure-Mode Mitigation Engine (`evaluate_5vector_adversarial_shield`):
   - Vector 1: Fee-on-Transfer (FoT) Exact Balance-Delta Verifier & Vulnerable AMM `skim()` Detector
   - Vector 2: Dynamic Post-Graduation Compute Unit (CU) Exhaustion Profiler
   - Vector 3: Counter-MEV "Salmonella" & State-Dependent Honeypot Detector
   - Vector 4: Unbundling & Uncle/Reorg Isolation Gate
   - Vector 5: Callback Authentication Spoofing & Zero-Idle-Balance Guard
3. 2026 MiCA & DOJ Regulatory Market-Efficiency Compliance Filter & Taxable Disposal Ledger
4. `SalmonellaFotAdversarialShield` Facade Class (`RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD`)
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.security.salmonella_fot_adversarial_shield import (
    ANALYZED_LAUNCHES_COUNT,
    ATOMIC_MODE_ALL_OR_NOTHING_JITO_FLASHBOTS_BUNDLE,
    ATOMIC_MODE_NON_ATOMIC_PUBLIC_MEMPOOL,
    ATOMIC_MODE_SINGLE_TX_FLASH_CALLBACK,
    AUTOMATED_WASH_LOOP_SHARE_PCT,
    BLOCK0_SNIPER_EXTRACTED_USD,
    BUYER_NET_LOSS_RATE_PCT,
    COLLECTIVE_BUYER_LOSS_USD,
    COMPLIANCE_STATUS_BLOCKED_MANIPULATION,
    COMPLIANCE_STATUS_COMPLIANT_EXTRACTION,
    CU_LIMIT_MULTI_TICK_CLMM_OR_DLMM,
    CU_LIMIT_PUMPSWAP_CPMM_AMM,
    CU_LIMIT_PUMP_BONDING_CURVE,
    DAY_ONE_EXTINCTION_RATE_PCT,
    DEV_BUNDLE_EXTRACTED_USD,
    DOCUMENTED_DEV_BUNDLE_CLUSTER_SIZE,
    FOT_ACTION_ABORT_UNPROFITABLE_AFTER_TAX,
    FOT_ACTION_EXECUTE_RESERVE_DESYNC_SKIM_ARB,
    FOT_ACTION_EXECUTE_VERIFIED_DELTA_ARB,
    GENUINE_TRADING_PROFIT_SHARE_PCT,
    GRADUATION_RATE_MAX_PCT,
    GRADUATION_RATE_MIN_PCT,
    GRADUATION_RATIO_1_IN_N,
    HARD_BLOCKED_MANIPULATIVE_STRATEGIES,
    INSIDER_TOKEN_HANDOFF_SHARE_PCT,
    IPC_ACTION_RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD,
    MEDIAN_BUYER_LOSS_USD,
    MEV_SANDWICH_ATTACK_COUNT,
    MEV_SANDWICH_EXTRACTED_USD,
    OCTOBER_2026_EMPIRICAL_FORENSICS_BENCHMARKS,
    OCTOBER_2026_EMPIRICAL_FORENSICS_DATACLASS,
    PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB,
    PANCAKE_FOT_SKIM_NET_PROFIT_WBNB,
    PUMPFUN_CUMULATIVE_VOLUME_USD,
    PUMPFUN_PLATFORM_FEE_REVENUE_USD,
    PUMPFUN_TOTAL_UNIQUE_TOKENS,
    SALMONELLA_DECISION_ABORT_HONEYPOT_TRAP,
    SALMONELLA_DECISION_SAFE_EXECUTION,
    SHIELD_DECISION_APPROVED_ATOMIC_EXECUTION,
    SHIELD_DECISION_BLOCKED_ADVERSARIAL_RISK,
    STRATEGY_CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING,
    STRATEGY_CROSS_DEX_SPATIAL_ARB,
    STRATEGY_FLASH_AMPLIFIED_JIT_LIQUIDITY,
    STRATEGY_FORCED_GRADUATION_PRICE_EQUALIZATION,
    STRATEGY_ISOLATED_MARKET_BAD_DEBT_LIQUIDATION,
    STRATEGY_MAYHEM_AI_NOISE_BACKRUN,
    STRATEGY_PARASITIC_V4_AFTERSWAP_EQUALIZATION,
    STRATEGY_PREDATORY_RETAIL_WIRE_FRAUD_BAITING,
    STRATEGY_SALMONELLA_HONEYPOT_DEPLOYMENT,
    STRATEGY_TRIANGULAR_ROUTING_ARB,
    SalmonellaFotAdversarialShield,
    TOP_100K_WALLET_WINS_COUNT,
    TOP_1PCT_GAIN_SHARE_PCT,
    TRACKED_11M_SAMPLE_TOKENS,
    TRACKED_BUYERS_COUNT,
    VENUE_MULTI_TICK_CLMM_OR_DLMM,
    VENUE_PUMPSWAP_CPMM_AMM,
    VENUE_PUMP_BONDING_CURVE,
    WHITELISTED_MARKET_EFFICIENCY_STRATEGIES,
    detect_salmonella_state_dependent_trap,
    evaluate_5vector_adversarial_shield,
    evaluate_regulatory_compliance_and_tax_ledger,
    evaluate_unbundling_and_reorg_isolation_gate,
    get_october_2026_empirical_forensics_benchmarks,
    profile_dynamic_cu_budget,
    verify_callback_auth_and_zero_idle_balance,
    verify_fot_balance_delta_and_skim_opportunity,
)


def test_october_2026_empirical_forensics_benchmarks_exact_values() -> None:
    """Verifies that all October 2026 empirical memecoin forensic constants and dictionary
    entries match the specification (`15.2M` tokens, `$90B` volume, `$780M` fees, `1-in-58`
    graduation, `79%` day-1 extinction, `74%` buyer loss rate, `$269M` buyer losses, etc.).
    """
    b = OCTOBER_2026_EMPIRICAL_FORENSICS_BENCHMARKS

    # Dictionary access and attribute access both work
    assert b["pumpfun_total_unique_tokens"] == 15_200_000
    assert b.pumpfun_total_unique_tokens == PUMPFUN_TOTAL_UNIQUE_TOKENS == 15_200_000
    assert b["pumpfun_cumulative_volume_usd"] == pytest.approx(90_000_000_000.0)
    assert PUMPFUN_CUMULATIVE_VOLUME_USD == pytest.approx(90_000_000_000.0)
    assert b["pumpfun_platform_fee_revenue_usd"] == pytest.approx(780_000_000.0)
    assert PUMPFUN_PLATFORM_FEE_REVENUE_USD == pytest.approx(780_000_000.0)

    assert b["tracked_11m_sample_tokens"] == TRACKED_11M_SAMPLE_TOKENS == 11_500_000
    assert b["graduation_ratio_1_in_n"] == GRADUATION_RATIO_1_IN_N == 58
    assert b["graduation_rate_min_pct"] == GRADUATION_RATE_MIN_PCT == pytest.approx(1.02)
    assert b["graduation_rate_max_pct"] == GRADUATION_RATE_MAX_PCT == pytest.approx(1.72)
    assert b["day_one_extinction_rate_pct"] == DAY_ONE_EXTINCTION_RATE_PCT == pytest.approx(79.0)

    assert b["tracked_buyers_count"] == TRACKED_BUYERS_COUNT == 2_900_000
    assert b["buyer_net_loss_rate_pct"] == BUYER_NET_LOSS_RATE_PCT == pytest.approx(74.0)
    assert b["collective_buyer_loss_usd"] == COLLECTIVE_BUYER_LOSS_USD == pytest.approx(269_000_000.0)
    assert b["median_buyer_loss_usd"] == MEDIAN_BUYER_LOSS_USD == pytest.approx(13.0)
    assert b["top_1pct_gain_share_pct"] == TOP_1PCT_GAIN_SHARE_PCT == pytest.approx(50.0)

    assert b["top_100k_wallet_wins_count"] == TOP_100K_WALLET_WINS_COUNT == 3_170
    assert b["genuine_trading_profit_share_pct"] == GENUINE_TRADING_PROFIT_SHARE_PCT == pytest.approx(26.0)
    assert b["insider_token_handoff_share_pct"] == INSIDER_TOKEN_HANDOFF_SHARE_PCT == pytest.approx(50.0)
    assert b["automated_wash_loop_share_pct"] == AUTOMATED_WASH_LOOP_SHARE_PCT == pytest.approx(13.0)

    assert b["analyzed_launches_count"] == ANALYZED_LAUNCHES_COUNT == 8_200_000
    assert b["documented_dev_bundle_cluster_size"] == DOCUMENTED_DEV_BUNDLE_CLUSTER_SIZE == 542
    assert b["dev_bundle_extracted_usd"] == DEV_BUNDLE_EXTRACTED_USD == pytest.approx(579_000_000.0)
    assert b["block0_sniper_extracted_usd"] == BLOCK0_SNIPER_EXTRACTED_USD == pytest.approx(31_500_000.0)
    assert b["mev_sandwich_extracted_usd"] == MEV_SANDWICH_EXTRACTED_USD == pytest.approx(29_700_000.0)
    assert b["mev_sandwich_attack_count"] == MEV_SANDWICH_ATTACK_COUNT == 6_900_000

    # Verify helper getter and dataclass serialization
    helper_copy = get_october_2026_empirical_forensics_benchmarks()
    assert helper_copy.to_dict() == OCTOBER_2026_EMPIRICAL_FORENSICS_DATACLASS.to_dict()


def test_vector1_fot_exact_balance_delta_and_pancake_skim_arbitrage() -> None:
    """Verifies Vector 1:
    1. Rejects nominal `amountOut` assumptions when a 5.0% Fee-on-Transfer (FoT) tax causes
       `balance_after - balance_before` to fall short of flash-loan repayment.
    2. Approves FoT arbitrage when the cross-pool spread is wide enough to clear loan
       repayment + profit after accounting for the exact `balance_after - balance_before` delta.
    3. Detects vulnerable AMM FoT reserve-desync `skim()` arbitrage (`49.15 WBNB` flash loan ->
       `37.55 WBNB` net profit).
    """
    # Case A: 5% FoT tax causes nominal 2% arb spread to fail loan repayment
    res_abort = verify_fot_balance_delta_and_skim_opportunity(
        "Deflationary5PctToken",
        nominal_amount_in=100.0,
        nominal_amount_out=1_000.0,
        balance_before=250.0,
        balance_after=1_200.0,  # actual_received = 950.0 (5.0% FoT tax)
        second_leg_exchange_rate=0.102,  # Nominal would yield 102.0 (> 100.09), actual yields 950 * 0.95 * 0.102 = 92.055
        flash_loan_principal=100.0,
        flash_loan_fee=0.09,
        min_required_profit=0.10,
    )
    assert res_abort.actual_received == pytest.approx(950.0)
    assert res_abort.nominal_vs_actual_shortfall == pytest.approx(50.0)
    assert res_abort.observed_fot_tax_pct == pytest.approx(5.0)
    assert res_abort.has_fee_on_transfer_tax is True
    assert res_abort.net_profit_nominal_assumption > 1.0
    assert res_abort.net_profit_actual_balance_delta < 0.0
    assert res_abort.nominal_assumption_would_revert_on_repay is True
    assert res_abort.fot_nominal_assumption_rejected is True
    assert res_abort.clears_loan_repayment_after_tax is False
    assert res_abort.vector1_passed is False
    assert res_abort.recommended_action == FOT_ACTION_ABORT_UNPROFITABLE_AFTER_TAX

    # Case B: Wide 18% spread still clears loan repayment + profit even after 5% FoT tax on both legs
    res_viable = verify_fot_balance_delta_and_skim_opportunity(
        "WideSpreadFoTToken",
        nominal_amount_in=100.0,
        nominal_amount_out=1_000.0,
        balance_before=0.0,
        balance_after=950.0,
        second_leg_exchange_rate=0.118,  # 950 * 0.95 * 0.118 = 106.495 > 100.09 + 0.50
        flash_loan_principal=100.0,
        flash_loan_fee=0.09,
        min_required_profit=0.50,
    )
    assert res_viable.actual_received == pytest.approx(950.0)
    assert res_viable.clears_loan_repayment_after_tax is True
    assert res_viable.fot_nominal_assumption_rejected is False
    assert res_viable.vector1_passed is True
    assert res_viable.recommended_action == FOT_ACTION_EXECUTE_VERIFIED_DELTA_ARB

    # Case C: Vulnerable AMM FoT Reserve-Desync skim() Arbitrage (49.15 WBNB -> 37.55 WBNB)
    assert PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB == pytest.approx(49.15)
    assert PANCAKE_FOT_SKIM_NET_PROFIT_WBNB == pytest.approx(37.55)

    res_skim = verify_fot_balance_delta_and_skim_opportunity(
        "VulnerablePancakeForkPair",
        nominal_amount_in=49.15,
        nominal_amount_out=10_000.0,
        balance_before=0.0,
        fot_tax_pct=5.0,
        second_leg_exchange_rate=0.0049,
        flash_loan_principal=49.15,
        flash_loan_fee=0.12,
        min_required_profit=0.50,
        amm_uses_nominal_reserve_accounting=True,
        amm_has_public_skim_function=True,
        stored_reserve_token=500_000.0,
        actual_pair_balance_token=475_000.0,
        skim_flash_loan_wbnb=PANCAKE_FOT_SKIM_FLASH_LOAN_WBNB,
    )
    assert res_skim.skim_arbitrage_detected is True
    assert res_skim.reserve_desync_amount == pytest.approx(25_000.0)
    assert res_skim.skim_flash_loan_wbnb == pytest.approx(49.15)
    assert res_skim.skim_estimated_net_profit_wbnb == pytest.approx(37.55)
    assert res_skim.vector1_passed is True
    assert res_skim.recommended_action == FOT_ACTION_EXECUTE_RESERVE_DESYNC_SKIM_ARB


def test_vector2_dynamic_post_graduation_cu_profiler() -> None:
    """Verifies Vector 2: Dynamic Post-Graduation Compute Unit (CU) Exhaustion Profiler
    across `PUMP_BONDING_CURVE` (`65,000` CU), `PUMPSWAP_CPMM_AMM` (`145,000` CU), and
    `MULTI_TICK_CLMM_OR_DLMM` (`320,000` CU).
    """
    assert CU_LIMIT_PUMP_BONDING_CURVE == 65_000
    assert CU_LIMIT_PUMPSWAP_CPMM_AMM == 145_000
    assert CU_LIMIT_MULTI_TICK_CLMM_OR_DLMM == 320_000

    # 1. Pre-graduation Pump.fun bonding curve swap
    p_curve = profile_dynamic_cu_budget(
        "CurveMint111111111111111111111111111111111",
        lifecycle_venue=VENUE_PUMP_BONDING_CURVE,
        previous_venue=None,
        configured_static_cu_limit=65_000,
    )
    assert p_curve.recommended_compute_unit_limit == 65_000
    assert p_curve.graduated_from_bonding_curve is False
    assert p_curve.static_cu_would_exhaust is False
    assert (
        p_curve.compute_budget_instruction
        == "ComputeBudgetInstruction::set_compute_unit_limit(65000)"
    )

    # 2. Post-graduation PumpSwap CPMM swap where static 65k CU would revert mid-flight
    p_pumpswap = profile_dynamic_cu_budget(
        "PumpSwapGradMint11111111111111111111111111",
        lifecycle_venue=VENUE_PUMPSWAP_CPMM_AMM,
        previous_venue=VENUE_PUMP_BONDING_CURVE,
        configured_static_cu_limit=65_000,
    )
    assert p_pumpswap.recommended_compute_unit_limit == 145_000
    assert p_pumpswap.graduated_from_bonding_curve is True
    assert p_pumpswap.static_cu_would_exhaust is True
    assert (
        p_pumpswap.compute_budget_instruction
        == "ComputeBudgetInstruction::set_compute_unit_limit(145000)"
    )

    # 3. Multi-tick CLMM / DLMM routing
    p_clmm = profile_dynamic_cu_budget(
        "MultiTickClmmMint1111111111111111111111111",
        lifecycle_venue=VENUE_MULTI_TICK_CLMM_OR_DLMM,
        previous_venue=VENUE_PUMP_BONDING_CURVE,
        configured_static_cu_limit=145_000,
    )
    assert p_clmm.recommended_compute_unit_limit == 320_000
    assert p_clmm.graduated_from_bonding_curve is True
    assert p_clmm.static_cu_would_exhaust is True
    assert (
        p_clmm.compute_budget_instruction
        == "ComputeBudgetInstruction::set_compute_unit_limit(320000)"
    )


def test_vector3_salmonella_state_dependent_honeypot_detector() -> None:
    """Verifies Vector 3: Counter-MEV "Salmonella" & State-Dependent Honeypot Detector
    catching `tx.origin` XOR storage branches, `gasleft()` modulo traps, transient/block
    state traps, and `Transfer` event vs balance-slot desynchronization, plus the outer
    `require(FINAL_BALANCE >= INITIAL_BALANCE + MIN_PROFIT)` invariant.
    """
    # Clean ERC-20 / SPL token passing multi-origin, perturbed-gas, and randomized-block probes
    clean_res = detect_salmonella_state_dependent_trap(
        "0xCleanToken000000000000000000000000000001",
        emitted_transfer_event_tokens=50_000.0,
        operator_origin_credited_tokens=50_000.0,
        searcher_origin_credited_tokens=50_000.0,
        perturbed_gas_credited_tokens=50_000.0,
        randomized_block_credited_tokens=50_000.0,
        initial_balance=20.0,
        final_balance=20.45,
        min_profit=0.10,
    )
    assert clean_res.salmonella_honeypot_detected is False
    assert clean_res.outer_balance_invariant_passed is True
    assert clean_res.vector3_passed is True
    assert clean_res.decision == SALMONELLA_DECISION_SAFE_EXECUTION

    # Salmonella trap: emits Transfer(50,000) and credits operator 50,000, but credits searcher 50 tokens
    trap_origin = detect_salmonella_state_dependent_trap(
        "0xSalmonellaOriginTrap00000000000000000002",
        emitted_transfer_event_tokens=50_000.0,
        operator_origin_credited_tokens=50_000.0,
        searcher_origin_credited_tokens=50.0,
        perturbed_gas_credited_tokens=50_000.0,
        randomized_block_credited_tokens=50_000.0,
        initial_balance=20.0,
        final_balance=0.02,
        min_profit=0.10,
    )
    assert trap_origin.trap_tx_origin_xor_branch is True
    assert trap_origin.trap_transfer_event_balance_desync is True
    assert trap_origin.salmonella_honeypot_detected is True
    assert trap_origin.outer_balance_invariant_passed is False
    assert trap_origin.vector3_passed is False
    assert trap_origin.decision == SALMONELLA_DECISION_ABORT_HONEYPOT_TRAP

    # Perturbed gasleft() modulo trap
    trap_gas = detect_salmonella_state_dependent_trap(
        "0xSalmonellaGasModuloTrap00000000000000003",
        emitted_transfer_event_tokens=50_000.0,
        operator_origin_credited_tokens=50_000.0,
        searcher_origin_credited_tokens=50_000.0,
        perturbed_gas_credited_tokens=10.0,  # Triggers when gas is perturbed by +-3,000
        randomized_block_credited_tokens=50_000.0,
        initial_balance=20.0,
        final_balance=19.5,
        min_profit=0.10,
    )
    assert trap_gas.trap_gasleft_modulo_branch is True
    assert trap_gas.salmonella_honeypot_detected is True
    assert trap_gas.vector3_passed is False

    # Outer balance invariant failure even on non-Salmonella token (slippage/loss guard)
    invariant_fail = detect_salmonella_state_dependent_trap(
        "0xUnprofitableSlippageToken000000000000004",
        emitted_transfer_event_tokens=50_000.0,
        operator_origin_credited_tokens=50_000.0,
        searcher_origin_credited_tokens=50_000.0,
        initial_balance=20.0,
        final_balance=20.02,  # Less than 20.0 + 0.10 min_profit
        min_profit=0.10,
    )
    assert invariant_fail.salmonella_honeypot_detected is False
    assert invariant_fail.outer_balance_invariant_passed is False
    assert invariant_fail.vector3_passed is False


def test_vector4_and_vector5_unbundling_and_callback_auth_guards() -> None:
    """Verifies Vector 4 (Unbundling & Reorg Isolation Gate) and Vector 5 (Callback
    Authentication Spoofing & Zero-Idle-Balance Guard).
    """
    # Vector 4: Single-tx flash callback vs non-atomic public mempool broadcast
    v4_clean = evaluate_unbundling_and_reorg_isolation_gate(
        is_single_tx_flash_callback=True,
        is_all_or_nothing_atomic_bundle=True,
        allow_non_atomic_mempool_broadcast=False,
    )
    assert v4_clean.vector4_passed is True
    assert v4_clean.execution_mode == ATOMIC_MODE_SINGLE_TX_FLASH_CALLBACK

    v4_bundle = evaluate_unbundling_and_reorg_isolation_gate(
        is_single_tx_flash_callback=False,
        is_all_or_nothing_atomic_bundle=True,
        allow_non_atomic_mempool_broadcast=False,
    )
    assert v4_bundle.vector4_passed is True
    assert v4_bundle.execution_mode == ATOMIC_MODE_ALL_OR_NOTHING_JITO_FLASHBOTS_BUNDLE

    v4_blocked = evaluate_unbundling_and_reorg_isolation_gate(
        is_single_tx_flash_callback=True,
        is_all_or_nothing_atomic_bundle=True,
        allow_non_atomic_mempool_broadcast=True,
    )
    assert v4_blocked.vector4_passed is False
    assert v4_blocked.reorg_split_leg_vulnerable is True
    assert v4_blocked.execution_mode == ATOMIC_MODE_NON_ATOMIC_PUBLIC_MEMPOOL

    # Vector 5: Verified PoolManager & 0 idle balance vs Spoofed msg.sender or non-zero idle funds
    v5_clean = verify_callback_auth_and_zero_idle_balance(
        callback_function="unlockCallback(bytes)",
        msg_sender="0x000000000004444c5dc75cB358380D2e3dE08A90",
        verified_pool_or_manager_address="0x000000000004444c5dc75cB358380D2e3dE08A90",
        initiator_authenticated=True,
        idle_contract_balance_lamports=0,
        idle_erc20_balance_raw=0,
    )
    assert v5_clean.vector5_passed is True
    assert v5_clean.callback_sender_authenticated is True
    assert v5_clean.zero_idle_balance_enforced is True

    v5_spoofed = verify_callback_auth_and_zero_idle_balance(
        callback_function="uniswapV3SwapCallback(int256,int256,bytes)",
        msg_sender="0xMaliciousCallerContract00000000000000001",
        verified_pool_or_manager_address="0xVerifiedUniswapV3Pool0000000000000000001",
        initiator_authenticated=True,
        idle_contract_balance_lamports=0,
    )
    assert v5_spoofed.vector5_passed is False
    assert v5_spoofed.callback_sender_authenticated is False

    v5_idle_funds = verify_callback_auth_and_zero_idle_balance(
        callback_function="onMorphoFlashLoan(uint256,bytes)",
        msg_sender="0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        verified_pool_or_manager_address="0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        initiator_authenticated=True,
        idle_contract_balance_lamports=250_000,
    )
    assert v5_idle_funds.vector5_passed is False
    assert v5_idle_funds.zero_idle_balance_enforced is False


def test_composite_5vector_adversarial_shield_evaluation() -> None:
    """Verifies `evaluate_5vector_adversarial_shield` approves clean atomic bundles and
    blocks bundles failing any of Vectors 1–5.
    """
    approved = evaluate_5vector_adversarial_shield(
        "CleanGraduatedToken11111111111111111111111",
        nominal_amount_in=50.0,
        nominal_amount_out=5_000.0,
        balance_before=0.0,
        balance_after=5_000.0,
        second_leg_exchange_rate=0.0105,
        flash_loan_principal=50.0,
        flash_loan_fee=0.05,
        min_required_profit=0.10,
        lifecycle_venue=VENUE_PUMPSWAP_CPMM_AMM,
        previous_venue=VENUE_PUMP_BONDING_CURVE,
        emitted_transfer_event_tokens=5_000.0,
        operator_origin_credited_tokens=5_000.0,
        searcher_origin_credited_tokens=5_000.0,
        initial_balance=50.0,
        final_balance=52.45,
        is_single_tx_flash_callback=True,
        allow_non_atomic_mempool_broadcast=False,
        callback_function="unlockCallback(bytes)",
        msg_sender="0x000000000004444c5dc75cB358380D2e3dE08A90",
        verified_pool_or_manager_address="0x000000000004444c5dc75cB358380D2e3dE08A90",
        idle_contract_balance_lamports=0,
    )
    assert approved.all_five_vectors_passed is True
    assert approved.passed_vector_count == 5
    assert approved.should_execute_atomic_bundle is True
    assert approved.decision == SHIELD_DECISION_APPROVED_ATOMIC_EXECUTION
    assert approved.blocking_vectors == []

    blocked = evaluate_5vector_adversarial_shield(
        "MaliciousMultiTrapToken9999999999999999999",
        nominal_amount_in=50.0,
        nominal_amount_out=5_000.0,
        balance_before=0.0,
        balance_after=4_750.0,  # 5% FoT tax
        second_leg_exchange_rate=0.0101,
        flash_loan_principal=50.0,
        flash_loan_fee=0.05,
        min_required_profit=0.10,
        emitted_transfer_event_tokens=5_000.0,
        operator_origin_credited_tokens=5_000.0,
        searcher_origin_credited_tokens=5.0,  # Salmonella trap
        initial_balance=50.0,
        final_balance=0.05,
        allow_non_atomic_mempool_broadcast=True,  # Unbundling risk
        msg_sender="0xSpoofedSender",
        verified_pool_or_manager_address="0x000000000004444c5dc75cB358380D2e3dE08A90",
        idle_contract_balance_lamports=10_000,
    )
    assert blocked.all_five_vectors_passed is False
    assert blocked.should_execute_atomic_bundle is False
    assert blocked.decision == SHIELD_DECISION_BLOCKED_ADVERSARIAL_RISK
    assert "VECTOR_1_FOT_BALANCE_DELTA_AND_SKIM" in blocked.blocking_vectors
    assert "VECTOR_3_SALMONELLA_STATE_DEPENDENT_HONEYPOT" in blocked.blocking_vectors
    assert "VECTOR_4_UNBUNDLING_AND_REORG_ISOLATION" in blocked.blocking_vectors
    assert "VECTOR_5_CALLBACK_AUTH_AND_ZERO_IDLE_BALANCE" in blocked.blocking_vectors


def test_regulatory_compliance_filter_and_taxable_disposal_ledger() -> None:
    """Verifies the 2026 MiCA & DOJ Regulatory Market-Efficiency Compliance Gate across all
    7 whitelisted strategies and all 3 hard-blocked manipulation vectors, plus auditable
    `TaxableDisposalLedgerEntry` generation.
    """
    assert len(WHITELISTED_MARKET_EFFICIENCY_STRATEGIES) == 7
    assert len(HARD_BLOCKED_MANIPULATIVE_STRATEGIES) == 3

    ledger = []
    expected_whitelisted = [
        STRATEGY_CROSS_DEX_SPATIAL_ARB,
        STRATEGY_TRIANGULAR_ROUTING_ARB,
        STRATEGY_FLASH_AMPLIFIED_JIT_LIQUIDITY,
        STRATEGY_FORCED_GRADUATION_PRICE_EQUALIZATION,
        STRATEGY_MAYHEM_AI_NOISE_BACKRUN,
        STRATEGY_PARASITIC_V4_AFTERSWAP_EQUALIZATION,
        STRATEGY_ISOLATED_MARKET_BAD_DEBT_LIQUIDATION,
    ]
    for idx, strat in enumerate(expected_whitelisted, start=1):
        res = evaluate_regulatory_compliance_and_tax_ledger(
            strat,
            flash_primitive="AAVE_V3_OR_JITO_FLASH_LOAN",
            gross_proceeds_usd=10_000.0 + idx * 500.0,
            cost_basis_plus_fees_usd=9_500.0 + idx * 400.0,
            tx_or_bundle_hash=f"0xcompliant_tx_{idx}",
            timestamp_utc="2026-10-28T20:00:00Z",
            ledger_sink=ledger,
        )
        assert res.is_whitelisted_market_efficiency is True
        assert res.is_hard_blocked_manipulation is False
        assert res.compliance_status == COMPLIANCE_STATUS_COMPLIANT_EXTRACTION
        assert res.execution_permitted is True
        assert res.taxable_disposal_entry is not None
        assert res.taxable_disposal_entry.disposal_id.startswith("DISP-")
        assert res.taxable_disposal_entry.timestamp_utc == "2026-10-28T20:00:00Z"
        assert res.taxable_disposal_entry.strategy_type == strat
        assert res.taxable_disposal_entry.realized_net_gain_usd == pytest.approx(
            500.0 + idx * 100.0
        )

    assert len(ledger) == 7

    # Hard-blocked manipulative vectors must be rejected and produce no ledger disposal entry
    for blocked_strat in [
        STRATEGY_CLMM_PHANTOM_LIQUIDITY_WASH_SPOOFING,
        STRATEGY_SALMONELLA_HONEYPOT_DEPLOYMENT,
        STRATEGY_PREDATORY_RETAIL_WIRE_FRAUD_BAITING,
    ]:
        res_blocked = evaluate_regulatory_compliance_and_tax_ledger(
            blocked_strat,
            flash_primitive="MANIPULATIVE_BUNDLE",
            gross_proceeds_usd=25_000.0,
            cost_basis_plus_fees_usd=20_000.0,
            ledger_sink=ledger,
        )
        assert res_blocked.is_whitelisted_market_efficiency is False
        assert res_blocked.is_hard_blocked_manipulation is True
        assert res_blocked.compliance_status == COMPLIANCE_STATUS_BLOCKED_MANIPULATION
        assert res_blocked.execution_permitted is False
        assert res_blocked.taxable_disposal_entry is None

    # Ledger still contains only the 7 compliant disposals
    assert len(ledger) == 7


def test_salmonella_fot_adversarial_shield_facade_diagnostic_and_telemetry() -> None:
    """Verifies `SalmonellaFotAdversarialShield` facade class (`run_full_adversarial_shield_diagnostic`
    and `get_telemetry_summary`) for `TitanIPCDaemon` (`RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD`).
    """
    shield = SalmonellaFotAdversarialShield()
    diag = shield.run_full_adversarial_shield_diagnostic()

    assert diag["status"] == "OK"
    assert diag["ipc_action"] == IPC_ACTION_RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD
    assert (
        diag["october_2026_empirical_forensics_benchmarks"][
            "pumpfun_total_unique_tokens"
        ]
        == 15_200_000
    )
    assert diag["fot_abort_scenario"]["fot_nominal_assumption_rejected"] is True
    assert diag["fot_skim_arbitrage_scenario"]["skim_arbitrage_detected"] is True
    assert diag["fot_skim_arbitrage_scenario"][
        "skim_estimated_net_profit_wbnb"
    ] == pytest.approx(37.55)
    assert (
        diag["cu_profiles"]["bonding_curve"]["recommended_compute_unit_limit"] == 65_000
    )
    assert (
        diag["cu_profiles"]["pumpswap_cpmm"]["recommended_compute_unit_limit"]
        == 145_000
    )
    assert (
        diag["cu_profiles"]["multi_tick_clmm"]["recommended_compute_unit_limit"]
        == 320_000
    )
    assert diag["salmonella_blocked_scenario"]["salmonella_honeypot_detected"] is True
    assert diag["clean_5vector_shield"]["all_five_vectors_passed"] is True
    assert diag["blocked_5vector_shield"]["all_five_vectors_passed"] is False
    assert (
        diag["compliant_regulatory_extraction"]["compliance_status"]
        == COMPLIANCE_STATUS_COMPLIANT_EXTRACTION
    )
    assert (
        diag["blocked_regulatory_manipulation"]["compliance_status"]
        == COMPLIANCE_STATUS_BLOCKED_MANIPULATION
    )
    assert len(diag["tax_disposal_ledger"]) == 1

    telemetry = shield.get_telemetry_summary()
    assert telemetry["agent_id"] == 24
    assert telemetry["agent_name"] == "salmonella-fot-adversarial-shield"
    assert telemetry["ipc_action"] == IPC_ACTION_RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD
    assert telemetry["fot_evaluations"] >= 4
    assert telemetry["fot_nominal_rejections"] >= 2
    assert telemetry["skim_opportunities_detected"] >= 1
    assert telemetry["cu_profiles_computed"] >= 5
    assert telemetry["static_cu_exhaustions_prevented"] >= 2
    assert telemetry["salmonella_scans"] >= 3
    assert telemetry["salmonella_traps_blocked"] >= 2
    assert telemetry["five_vector_evaluations"] == 2
    assert telemetry["five_vector_approvals"] == 1
    assert telemetry["five_vector_blocks"] == 1
    assert telemetry["compliance_checks"] == 2
    assert telemetry["compliance_approvals"] == 1
    assert telemetry["compliance_blocks"] == 1
    assert telemetry["tax_disposal_ledger_count"] == 1
