//! Step 2.2 (Part B) — Slot-Zero Jito Bundle Executor & Leader Schedule Coordinator.
//!
//! Coordinates pre-signed `VersionedTransaction` (`TransactionV0`) execution across:
//! - Mode A: Single-Tx `sendTransaction` with strict `70%` Priority Fee / `30%` Jito Tip split
//! - Mode B: Atomic Multi-Tx `sendBundle` (`1..=5` txs) with dynamic velocity-scaled tipping,
//!   `jitodontfront` front-running immunity, ALT tip-exclusion checks, and pre-flight `simulate_bundle`.

pub use crate::jito_bundle::{
    attach_profit_guard_min_out_instruction, build_hardened_jito_bundle,
    compute_constant_product_min_out, compute_dynamic_jito_bundle_tip,
    compute_single_tx_70_30_fee_split, is_official_jito_tip_account, select_jito_tip_account,
    simulate_bundle, BundleSimulationReport, BundleValidationError, CandidateBundleTx,
    DynamicJitoTipCalculation, HardenedJitoBundle, JitoTipFloorPercentiles,
    ProfitGuardMinOutInvariant, SingleTx7030FeeSplit, DEFAULT_JITO_DONT_FRONT_PUBKEY,
    JITO_DONT_FRONT_PREFIX, JITO_MIN_TIP_LAMPORTS, JITO_SOLANA_ACTIVE_STAKE_RATIO,
    JITO_TIP_ACCOUNTS, SPECIALIZED_RELAY_MIN_TIP_LAMPORTS,
};

/// Result of preparing and simulating an atomic Slot-Zero Jito execution package.
#[derive(Debug, Clone, PartialEq)]
pub struct PreparedSlotZeroBundle {
    /// Hardened Jito bundle (`1..=5` transactions).
    pub bundle: HardenedJitoBundle,
    /// Dynamic tip calculation metadata.
    pub tip_calculation: DynamicJitoTipCalculation,
    /// Exact constant-product (`x * y = k`) minimum-output invariant enforced by `profit_guard`.
    pub profit_guard_invariant: ProfitGuardMinOutInvariant,
    /// Pre-flight `simulate_bundle` verification report.
    pub simulation_report: BundleSimulationReport,
    /// Single-Tx `70/30` fallback split if executed via single-tx `sendTransaction` mode.
    pub fallback_single_tx_split: SingleTx7030FeeSplit,
}

/// Prepares, hardens, and runs pre-flight `simulate_bundle` verification on a Slot-Zero
/// atomic bundle before multi-relay dispatch.
pub fn prepare_and_simulate_slot_zero_bundle(
    mut candidate_txs: Vec<CandidateBundleTx>,
    tip_floor_t50: &JitoTipFloorPercentiles,
    curve_velocity_sol_per_sec: f64,
    alpha_syndicate_scalar: f64,
    use_specialized_relay_floor: bool,
    slot_leader_is_jito_solana: bool,
    slot_or_entropy: u64,
) -> Result<PreparedSlotZeroBundle, BundleValidationError> {
    if !slot_leader_is_jito_solana {
        return Err(BundleValidationError::SlotLeaderNotJitoSolana);
    }
    if candidate_txs.is_empty() || candidate_txs.len() > 5 {
        return Err(BundleValidationError::InvalidBundleSize(
            candidate_txs.len(),
        ));
    }

    let profit_guard_invariant = compute_constant_product_min_out(
        1_000_000_000,
        30_000_000_000,
        1_073_000_000_000_000,
        100,
        150,
    );
    let already_has_guard = candidate_txs.iter().any(|tx| {
        tx.instructions
            .iter()
            .any(|ix| ix.contains("profit_guard::assert_min_out"))
    });
    if !already_has_guard {
        attach_profit_guard_min_out_instruction(&mut candidate_txs[0], &profit_guard_invariant);
    }

    let tip_calculation = compute_dynamic_jito_bundle_tip(
        tip_floor_t50,
        curve_velocity_sol_per_sec,
        alpha_syndicate_scalar,
        use_specialized_relay_floor,
        slot_leader_is_jito_solana,
    );

    let bundle = build_hardened_jito_bundle(
        candidate_txs,
        tip_calculation.dynamic_tip_lamports,
        slot_or_entropy,
        None,
    )?;

    let simulation_report = simulate_bundle(&bundle)?;
    if !simulation_report.profit_guard_verified {
        return Err(BundleValidationError::MissingProfitGuardMinOut);
    }
    let fallback_single_tx_split =
        compute_single_tx_70_30_fee_split(tip_calculation.dynamic_tip_lamports, 200_000);

    Ok(PreparedSlotZeroBundle {
        bundle,
        tip_calculation,
        profit_guard_invariant,
        simulation_report,
        fallback_single_tx_split,
    })
}

