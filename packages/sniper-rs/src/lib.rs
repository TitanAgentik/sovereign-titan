//! Sovereign Titan — Slot-Zero Rust Execution Engine (`sniper-rs`).
//!
//! Exports:
//! - [`grpc_ingest`]: Step 2.1 — Yellowstone gRPC (`Dragon's Mouth` `.so` Geyser Plugin) Intra-Slot
//!   Streamer & Zero-RPC Deterministic Fire-Time PDA Calculator.
//! - [`jito_bundle`] & [`jito_executor`]: Step 2.2 — Dynamic Jito Bundle Builder, `70/30` Fee Split,
//!   and Anti-MEV Hardening against `vpe`-Class Sandwich Bots.
//! - [`auto_exit`]: Step 2.3 — 5-Region + Lil' JIT + Astralane + Helius Sender (SWQoS) Parallel
//!   Broadcaster & Phase-1 PVP Auto-Exit Engine.

pub mod auto_exit;
pub mod grpc_ingest;
pub mod jito_bundle;
pub mod jito_executor;
pub mod mega_flash;

pub use auto_exit::{
    broadcast_bundle_multi_relay, canonical_multi_relay_endpoints, evaluate_phase1_auto_exit,
    AutoExitExecutionDecision, AutoExitTriggerReason, BreakEvenRatchetConfig,
    MultiRelayBroadcastReport, Phase1MarketTelemetry, RelayEndpoint,
    PHASE1_POST_PVP_COLLAPSE_RATIO,
};
pub use grpc_ingest::{
    compute_curve_fill_velocity, decode_base58_32, decode_base58_32_const,
    derive_pumpfun_bonding_curve_pda, derive_pumpswap_or_raydium_pool_pda, encode_base58,
    evaluate_bonding_curve_state, find_program_address, process_intra_slot_geyser_batch,
    process_intra_slot_geyser_update, sha256_digest, BondingCurveEvaluation, GeyserAccountUpdate,
    PdaDerivation, YellowstoneDragonMouthSubscription, BASE58_DECODE_LUT,
    KAMINO_KLEND_PROGRAM_ID, LIFINITY_V2_PROGRAM_ID, MARGINFI_V2_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID, ORCA_WHIRLPOOL_PROGRAM_ID, PHOENIX_CLOB_PROGRAM_ID,
    PUMPFUN_BONDING_CURVE_PROGRAM_ID, PUMPFUN_GRADUATION_MCAP_USD,
    PUMPFUN_GRADUATION_SOL_THRESHOLD, PUMPFUN_PROGRAM_ID_BYTES, PUMPFUN_TOTAL_SUPPLY,
    PUMPSWAP_AMM_PROGRAM_ID, PUMPSWAP_PROGRAM_ID_BYTES, RAYDIUM_AMM_V4_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID, RAYDIUM_V4_PROGRAM_ID_BYTES, SANCTUM_S_CONTROLLER_PROGRAM_ID,
    SAVE_SOLEND_PROGRAM_ID, WSOL_MINT_ADDRESS, WSOL_MINT_BYTES,
};
pub use jito_bundle::{
    attach_profit_guard_min_out_instruction, build_hardened_jito_bundle,
    compute_constant_product_min_out, compute_dynamic_jito_bundle_tip,
    compute_single_tx_70_30_fee_split, is_official_jito_tip_account, select_jito_tip_account,
    simulate_bundle, BundleSimulationReport, BundleValidationError, CandidateBundleTx,
    DynamicJitoTipCalculation, HardenedJitoBundle, JitoTipFloorPercentiles,
    ProfitGuardMinOutInvariant, SingleTx7030FeeSplit, DEFAULT_JITO_DONT_FRONT_PUBKEY,
    JITO_DONT_FRONT_PREFIX, JITO_MIN_TIP_LAMPORTS, JITO_SOLANA_ACTIVE_STAKE_RATIO,
    JITO_TIP_ACCOUNTS, SPECIALIZED_RELAY_MIN_TIP_LAMPORTS,
};
pub use jito_executor::{prepare_and_simulate_slot_zero_bundle, PreparedSlotZeroBundle};
pub use mega_flash::{
    allocate_stacked_flash_tranches, canonical_institutional_venue_pools, isqrt_u128,
    solve_lagrange_water_filling_u128, FlashProtocol, InstitutionalVenue, ProtocolTranche,
    VenueLiquidityPool, VenueSplitLeg, KAMINO_KLEND_MAX_SOL_LAMPORTS, LAMPORTS_PER_SOL,
    MARGINFI_V2_MAX_SOL_LAMPORTS, MAX_MEGA_FLASH_BORROW_LAMPORTS,
    SANCTUM_JUPITER_MAX_SOL_LAMPORTS, SAVE_SOLEND_MAX_SOL_LAMPORTS, TIER_1_100K_LAMPORTS,
    TIER_2_1M_LAMPORTS, TIER_3_10M_LAMPORTS, TIER_4_50M_LAMPORTS,
};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_step_2_1_zero_rpc_deterministic_pda_derivation_and_dragon_mouth_stream() {
        let mint = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU";

        assert_eq!(
            decode_base58_32(PUMPFUN_BONDING_CURVE_PROGRAM_ID),
            PUMPFUN_PROGRAM_ID_BYTES
        );
        assert_eq!(
            decode_base58_32(PUMPSWAP_AMM_PROGRAM_ID),
            PUMPSWAP_PROGRAM_ID_BYTES
        );
        assert_eq!(
            decode_base58_32(RAYDIUM_AMM_V4_PROGRAM_ID),
            RAYDIUM_V4_PROGRAM_ID_BYTES
        );
        assert_eq!(decode_base58_32(WSOL_MINT_ADDRESS), WSOL_MINT_BYTES);

        let curve_pda_1 = derive_pumpfun_bonding_curve_pda(mint);
        let curve_pda_2 = derive_pumpfun_bonding_curve_pda(mint);

        assert_eq!(curve_pda_1.pda_address, curve_pda_2.pda_address);
        assert_eq!(curve_pda_1.bump_seed, curve_pda_2.bump_seed);
        assert_eq!(curve_pda_1.blocking_rpc_calls_at_fire_time, 0);
        assert_eq!(curve_pda_1.program_id, PUMPFUN_BONDING_CURVE_PROGRAM_ID);
        assert!(!curve_pda_1.pda_address.is_empty());

        let pumpswap_pda =
            derive_pumpswap_or_raydium_pool_pda(mint, WSOL_MINT_ADDRESS, "pumpswap");
        assert_eq!(pumpswap_pda.blocking_rpc_calls_at_fire_time, 0);
        assert_eq!(pumpswap_pda.program_id, PUMPSWAP_AMM_PROGRAM_ID);

        let raydium_pda = derive_pumpswap_or_raydium_pool_pda(mint, WSOL_MINT_ADDRESS, "raydium");
        assert_eq!(raydium_pda.blocking_rpc_calls_at_fire_time, 0);
        assert_eq!(raydium_pda.program_id, RAYDIUM_AMM_V4_PROGRAM_ID);
        assert_ne!(pumpswap_pda.pda_address, raydium_pda.pda_address);

        // Verify Yellowstone gRPC Dragon's Mouth intra-slot stream evaluation
        let sub = YellowstoneDragonMouthSubscription::new_default(
            "https://grpc.triton.one:443",
            vec!["SyndicateLeadWallet111111111111111111111111".to_string()],
        );
        let update = GeyserAccountUpdate {
            slot: 312_450_001,
            write_version: 992_811,
            program_id: PUMPFUN_BONDING_CURVE_PROGRAM_ID.to_string(),
            signer_wallet: "SyndicateLeadWallet111111111111111111111111".to_string(),
            mint: mint.to_string(),
            real_sol_reserves: 85.4,
            delta_sol: 14.2,
            delta_seconds: 2.0,
        };

        let eval = process_intra_slot_geyser_update(&sub, &update)
            .expect("Dragon's Mouth update should match subscription");
        assert_eq!(eval.total_supply, 1_000_000_000);
        assert!((eval.graduation_threshold_sol - 85.0).abs() < 1e-9);
        assert!((eval.fill_velocity_sol_per_sec - 7.1).abs() < 1e-6);
        assert!(eval.is_graduation_ready);
        assert_eq!(eval.bonding_curve_pda.blocking_rpc_calls_at_fire_time, 0);
        assert_eq!(eval.migration_pool_pda.blocking_rpc_calls_at_fire_time, 0);

        // Verify batch processing with local mint PDA memoization
        let batch_updates = vec![
            update.clone(),
            GeyserAccountUpdate {
                slot: 312_450_001,
                write_version: 992_812,
                program_id: PUMPFUN_BONDING_CURVE_PROGRAM_ID.to_string(),
                signer_wallet: "SyndicateLeadWallet111111111111111111111111".to_string(),
                mint: mint.to_string(),
                real_sol_reserves: 82.0,
                delta_sol: 6.0,
                delta_seconds: 2.0,
            },
        ];
        let batch_evals = process_intra_slot_geyser_batch(&sub, &batch_updates);
        assert_eq!(batch_evals.len(), 2);
        assert_eq!(
            batch_evals[0].bonding_curve_pda.pda_address,
            batch_evals[1].bonding_curve_pda.pda_address
        );
        assert!(batch_evals[0].is_graduation_ready);
        assert!(batch_evals[1].is_graduation_ready);
    }

    #[test]
    fn test_step_2_2_single_tx_70_30_fee_split_exact_conservation() {
        let budget = 10_000_000u64; // 0.01 SOL
        let split = compute_single_tx_70_30_fee_split(budget, 200_000);

        assert_eq!(split.prio_lamports, 7_000_000);
        assert_eq!(split.jito_tip_lamports, 3_000_000);
        assert_eq!(
            split.prio_lamports + split.jito_tip_lamports,
            split.total_fee_budget_lamports
        );
        assert_eq!(split.micro_lamports_per_cu, 35_000_000);

        // Odd prime lamport budget must also strictly conserve total budget
        let odd_budget = 1_234_567u64;
        let odd_split = compute_single_tx_70_30_fee_split(odd_budget, 150_000);
        assert_eq!(
            odd_split.prio_lamports + odd_split.jito_tip_lamports,
            odd_budget
        );
    }

    #[test]
    fn test_step_2_2_dynamic_velocity_scaled_jito_tip_10x_to_50x_and_floors() {
        let floor = JitoTipFloorPercentiles {
            p25_lamports: 10_000,
            p50_lamports: 25_000,
            p75_lamports: 70_000,
            p95_lamports: 200_000,
            p99_lamports: 650_000,
        };

        // 1. Calm curve (V_curve = 0): enforces min_floor or P95
        let calm = compute_dynamic_jito_bundle_tip(&floor, 0.0, 2.5, false, true);
        assert_eq!(calm.min_tip_floor_lamports, 1_000);
        assert_eq!(calm.dynamic_tip_lamports, 200_000);
        assert!(calm.slot_leader_is_jito_solana);
        assert!(calm.active_jito_stake_ratio > 0.95);

        // 2. Specialized relay floor (0.001 SOL = 1,000,000 lamports) when P95 is smaller
        let specialized = compute_dynamic_jito_bundle_tip(&floor, 0.0, 1.0, true, true);
        assert_eq!(specialized.min_tip_floor_lamports, 1_000_000);
        assert_eq!(specialized.dynamic_tip_lamports, 1_000_000);

        // 3. Viral migration spike (15x scaling: 1 + 2.0 * 7.0 = 15.0x)
        let spike_15x = compute_dynamic_jito_bundle_tip(&floor, 7.0, 2.0, false, true);
        assert!((spike_15x.velocity_multiplier - 15.0).abs() < 1e-9);
        assert_eq!(spike_15x.dynamic_tip_lamports, 200_000 * 15);

        // 4. Extreme syndicate migration spike (capped at 50x scaling)
        let spike_50x = compute_dynamic_jito_bundle_tip(&floor, 30.0, 3.0, false, true);
        assert!((spike_50x.velocity_multiplier - 50.0).abs() < 1e-9);
        assert_eq!(spike_50x.dynamic_tip_lamports, 200_000 * 50);
    }

    #[test]
    fn test_step_2_2_anti_mev_hardening_dont_front_tail_tip_and_rejection_rules() {
        let mut tx0 = CandidateBundleTx {
            tx_label: "slot0_entry_swap".to_string(),
            instructions: vec!["pumpswap_amm::buy_exact_sol_in".to_string()],
            readonly_accounts: vec![],
            alt_lookup_accounts: vec!["SysvarRent111111111111111111111111111111111".to_string()],
            is_standalone_tip_tx: false,
        };
        let invariant = compute_constant_product_min_out(
            2_000_000_000,         // 2.0 SOL in
            30_000_000_000,        // 30.0 SOL reserve_in
            1_073_000_000_000_000, // 1.073B token reserve_out
            100,                   // 1.0% fee
            150,                   // 1.5% max slippage
        );
        assert!(invariant.expected_amount_out > 0);
        assert!(invariant.minimum_amount_out > 0);
        assert!(invariant.minimum_amount_out < invariant.expected_amount_out);
        assert_eq!(
            invariant.invariant_k,
            30_000_000_000u128 * 1_073_000_000_000_000u128
        );
        attach_profit_guard_min_out_instruction(&mut tx0, &invariant);

        let tx1 = CandidateBundleTx {
            tx_label: "slot0_ata_cleanup_and_guard".to_string(),
            instructions: vec!["spl_token::sync_native".to_string()],
            readonly_accounts: vec![],
            alt_lookup_accounts: vec![],
            is_standalone_tip_tx: false,
        };

        let hardened = build_hardened_jito_bundle(vec![tx0, tx1], 1_500_000, 42, None)
            .expect("Valid 2-tx bundle should harden cleanly");

        // Verify jitodontfront is injected in Transaction 1 (index 0)
        assert!(hardened.transactions[0]
            .readonly_accounts
            .iter()
            .any(|k| k.starts_with(JITO_DONT_FRONT_PREFIX)));

        // Verify selected tip account is one of the 8 official Jito tip accounts
        assert!(is_official_jito_tip_account(&hardened.selected_tip_account));

        // Verify tip transfer instruction is at the tail of the final transaction (Tx[k-1])
        let last_tx = &hardened.transactions[1];
        let tail_ix = last_tx.instructions.last().expect("Must have tail instruction");
        assert!(tail_ix.contains("system_instruction::transfer"));
        assert!(tail_ix.contains(&hardened.selected_tip_account));

        // Verify pre-flight simulate_bundle passes
        let sim = simulate_bundle(&hardened).expect("Pre-flight simulation must pass");
        assert!(sim.simulation_passed);
        assert!(sim.dont_front_locked_at_index_0);
        assert!(sim.tail_tip_verified_at_last_tx);
        assert!(sim.zero_tip_accounts_in_alt);
        assert!(sim.profit_guard_verified);

        // Rule Check A: Reject forbidden `[tip, tx_with_dont_front]` standalone-tip-first pattern
        let forbidden_tip_first = vec![
            CandidateBundleTx {
                tx_label: "standalone_tip_tx".to_string(),
                instructions: vec!["system_instruction::transfer".to_string()],
                readonly_accounts: vec![],
                alt_lookup_accounts: vec![],
                is_standalone_tip_tx: true,
            },
            CandidateBundleTx {
                tx_label: "swap_tx_with_dont_front".to_string(),
                instructions: vec!["pumpswap_amm::buy".to_string()],
                readonly_accounts: vec![DEFAULT_JITO_DONT_FRONT_PUBKEY.to_string()],
                alt_lookup_accounts: vec![],
                is_standalone_tip_tx: false,
            },
        ];
        let err_tip_first = build_hardened_jito_bundle(forbidden_tip_first, 500_000, 1, None);
        assert_eq!(
            err_tip_first,
            Err(BundleValidationError::ForbiddenStandaloneTipBeforeDontFront)
        );

        // Rule Check A2: Also reject non-final tx transferring to JITO_TIP_ACCOUNTS even when is_standalone_tip_tx == false
        let disguised_tip_first = vec![
            CandidateBundleTx {
                tx_label: "disguised_tip_tx".to_string(),
                instructions: vec![format!(
                    "system_instruction::transfer(to={}, lamports=500000)",
                    JITO_TIP_ACCOUNTS[0]
                )],
                readonly_accounts: vec![],
                alt_lookup_accounts: vec![],
                is_standalone_tip_tx: false,
            },
            CandidateBundleTx {
                tx_label: "swap_tx_2".to_string(),
                instructions: vec!["pumpswap_amm::buy".to_string()],
                readonly_accounts: vec![],
                alt_lookup_accounts: vec![],
                is_standalone_tip_tx: false,
            },
        ];
        assert_eq!(
            build_hardened_jito_bundle(disguised_tip_first, 500_000, 1, None),
            Err(BundleValidationError::ForbiddenStandaloneTipBeforeDontFront)
        );

        // Rule Check B: Reject Jito tip account inside an Address Lookup Table (ALT)
        let forbidden_alt_tx = vec![CandidateBundleTx {
            tx_label: "swap_with_tip_in_alt".to_string(),
            instructions: vec!["pumpswap_amm::buy".to_string()],
            readonly_accounts: vec![],
            alt_lookup_accounts: vec![JITO_TIP_ACCOUNTS[0].to_string()],
            is_standalone_tip_tx: false,
        }];
        let err_alt = build_hardened_jito_bundle(forbidden_alt_tx, 500_000, 1, None);
        assert_eq!(
            err_alt,
            Err(BundleValidationError::TipAccountInsideAltForbidden(
                JITO_TIP_ACCOUNTS[0].to_string()
            ))
        );
    }

    #[test]
    fn test_step_2_3_multi_relay_broadcast_and_phase1_auto_exit_triggers() {
        let tx = CandidateBundleTx {
            tx_label: "slot0_entry".to_string(),
            instructions: vec!["pumpswap_amm::buy".to_string()],
            readonly_accounts: vec![],
            alt_lookup_accounts: vec![],
            is_standalone_tip_tx: false,
        };
        let bundle = build_hardened_jito_bundle(vec![tx], 1_200_000, 99, None).unwrap();

        // Broadcast across all 5 Jito regions + QuickNode Lil' JIT + Astralane + Helius Sender (SWQoS)
        let broadcast = broadcast_bundle_multi_relay(&bundle, "Frankfurt")
            .expect("Multi-relay broadcast should succeed");
        assert_eq!(broadcast.dispatched_relays.len(), 8);
        assert_eq!(broadcast.swqos_relay_count, 8);
        assert_eq!(broadcast.primary_topological_relay.region_code, "eu-central");
        assert_eq!(broadcast.primary_topological_relay.estimated_tpu_latency_us, 420);

        // Verify Trigger 1: Cluster wallet or `evidence_txs[]` initiating outbound transfer/sell
        let telemetry_cluster_tripwire = Phase1MarketTelemetry {
            mint: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU".to_string(),
            watched_cluster_id: "cluster_syndicate_alpha_01".to_string(),
            cluster_wallets: vec![
                "SyndicateWalletA111111111111111111111111111".to_string(),
                "SyndicateWalletB222222222222222222222222222".to_string(),
            ],
            tracked_evidence_txs: vec!["5KqEvidenceTxSig99112233445566778899".to_string()],
            observed_actor_wallet: Some(
                "SyndicateWalletB222222222222222222222222222".to_string(),
            ),
            observed_reference_tx: Some("5KqEvidenceTxSig99112233445566778899".to_string()),
            is_outbound_transfer_or_sell: true,
            ofi_1m: 0.15,
            vpin_toxicity: 0.35,
            ofi_exhaustion_threshold: -0.35,
            vpin_toxicity_threshold: 0.72,
            ..Default::default()
        };

        let decision_1 =
            evaluate_phase1_auto_exit(&telemetry_cluster_tripwire, 2_000_000, 77, "New York")
                .expect("Cluster tripwire evaluation should succeed");
        assert!(decision_1.should_exit_immediately);
        assert!(matches!(
            decision_1.trigger_reason,
            Some(AutoExitTriggerReason::ClusterTripwireTriggered { .. })
        ));
        assert!(decision_1.emergency_exit_bundle.is_some());
        assert_eq!(
            decision_1.broadcast_report.unwrap().dispatched_relays.len(),
            8
        );

        // Verify Trigger 2: 1m OFI exhaustion / VPIN toxicity breach during External Market Phase 1
        let telemetry_ofi_vpin = Phase1MarketTelemetry {
            mint: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU".to_string(),
            watched_cluster_id: "cluster_syndicate_alpha_01".to_string(),
            cluster_wallets: vec!["SyndicateWalletA111111111111111111111111111".to_string()],
            tracked_evidence_txs: vec![],
            observed_actor_wallet: None,
            observed_reference_tx: None,
            is_outbound_transfer_or_sell: false,
            ofi_1m: -0.52,
            vpin_toxicity: 0.84,
            ofi_exhaustion_threshold: -0.35,
            vpin_toxicity_threshold: 0.72,
            ..Default::default()
        };

        let decision_2 = evaluate_phase1_auto_exit(&telemetry_ofi_vpin, 2_500_000, 88, "Tokyo")
            .expect("OFI/VPIN evaluation should succeed");
        assert!(decision_2.should_exit_immediately);
        match decision_2.trigger_reason {
            Some(AutoExitTriggerReason::OrderFlowExhaustionPhase1 {
                ofi_1m,
                vpin_toxicity,
                avoided_collapse_pct,
            }) => {
                assert!((ofi_1m - (-0.52)).abs() < 1e-9);
                assert!((vpin_toxicity - 0.84).abs() < 1e-9);
                assert!((avoided_collapse_pct - 80.0).abs() < 1e-6);
            }
            other => panic!("Expected OrderFlowExhaustionPhase1, got {:?}", other),
        }

        // Verify Trigger 3: Break-Even Ratchet (reached +3.5% >= +3.0%, locked +0.85% floor, breached at +0.60%)
        let ratchet_cfg = BreakEvenRatchetConfig::default();
        assert!((ratchet_cfg.ratchet_arm_multiple - 1.030).abs() < 1e-9);
        assert!((ratchet_cfg.locked_floor_multiple - 1.0085).abs() < 1e-9);
        assert!((ratchet_cfg.trail_drop_ratio - 0.08).abs() < 1e-9);

        let telemetry_ratchet = Phase1MarketTelemetry {
            mint: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU".to_string(),
            watched_cluster_id: "cluster_syndicate_alpha_01".to_string(),
            ofi_1m: 0.12,
            vpin_toxicity: 0.25,
            peak_price_multiple: 1.035,
            current_price_multiple: 1.006,
            ratchet_config: ratchet_cfg,
            ..Default::default()
        };
        let decision_3 = evaluate_phase1_auto_exit(&telemetry_ratchet, 1_800_000, 91, "Amsterdam")
            .expect("Break-even ratchet evaluation should succeed");
        assert!(decision_3.should_exit_immediately);
        match decision_3.trigger_reason {
            Some(AutoExitTriggerReason::BreakEvenRatchetTriggered {
                peak_price_multiple,
                current_price_multiple,
                locked_floor_multiple,
            }) => {
                assert!((peak_price_multiple - 1.035).abs() < 1e-9);
                assert!((current_price_multiple - 1.006).abs() < 1e-9);
                assert!((locked_floor_multiple - 1.0085).abs() < 1e-9);
            }
            other => panic!("Expected BreakEvenRatchetTriggered, got {:?}", other),
        }
    }
}

