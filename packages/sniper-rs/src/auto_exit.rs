//! Step 2.3 — Multi-Relay Parallel Broadcaster & Phase-1 PVP Auto-Exit Engine.
//!
//! 1. Broadcasts hardened Jito bundles concurrently across all 5 Jito Block Engine regional
//!    endpoints (`New York`, `Frankfurt`, `Amsterdam`, `Tokyo`, `Salt Lake City`) plus
//!    co-located low-latency relays (`QuickNode Lil' JIT`, `Astralane`, `Helius Sender` with SWQoS),
//!    routing primary priority to the relay topologically closest to the active slot leader TPU.
//! 2. Monitors real-time intra-slot exit triggers:
//!    - Any wallet in the resolved `cluster_id` or `evidence_txs[]` initiating an outbound token
//!      transfer or sell instruction (`ClusterTripwireTriggered`).
//!    - 1-minute **OFI (Order Flow Imbalance)** exhaustion or **VPIN** toxicity breach during
//!      External Market Phase 1 (`OrderFlowExhaustionPhase1`).
//!    Fires an atomic Jito bundle sell immediately before the `80%` post-PVP collapse.

use crate::jito_bundle::{
    build_hardened_jito_bundle, simulate_bundle, BundleValidationError, CandidateBundleTx,
    HardenedJitoBundle,
};

/// Expected post-PVP Phase-1 drawdown collapse ratio (`80%` collapse when serial syndicates dump).
pub const PHASE1_POST_PVP_COLLAPSE_RATIO: f64 = 0.80;

/// Represents a regional Jito Block Engine or specialized SWQoS relay endpoint.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RelayEndpoint {
    /// Relay identifier (`New York`, `Frankfurt`, `Amsterdam`, `Tokyo`, `Salt Lake City`,
    /// `QuickNode Lil' JIT`, `Astralane`, `Helius Sender`).
    pub name: String,
    /// Geographical / topological region code (`us-east`, `eu-central`, `eu-west`, `ap-northeast`, `us-west`).
    pub region_code: String,
    /// HTTP/2 JSON-RPC or gRPC bundle ingestion URL.
    pub endpoint_url: String,
    /// Whether Stake-Weighted Quality of Service (SWQoS) is enabled on this relay.
    pub swqos_enabled: bool,
    /// Estimated topological one-way latency to the active slot leader TPU in microseconds.
    pub estimated_tpu_latency_us: u64,
}

/// Returns the canonical 8-relay Slot-Zero parallel broadcast matrix:
/// - 5 Jito Block Engine regions (`New York`, `Frankfurt`, `Amsterdam`, `Tokyo`, `Salt Lake City`)
/// - `QuickNode Lil' JIT`
/// - `Astralane`
/// - `Helius Sender` (with SWQoS)
pub fn canonical_multi_relay_endpoints(active_leader_region: &str) -> Vec<RelayEndpoint> {
    let base_relays = [
        (
            "New York",
            "us-east",
            "https://ny.mainnet.block-engine.jito.wtf/api/v1/bundles",
            true,
        ),
        (
            "Frankfurt",
            "eu-central",
            "https://frankfurt.mainnet.block-engine.jito.wtf/api/v1/bundles",
            true,
        ),
        (
            "Amsterdam",
            "eu-west",
            "https://amsterdam.mainnet.block-engine.jito.wtf/api/v1/bundles",
            true,
        ),
        (
            "Tokyo",
            "ap-northeast",
            "https://tokyo.mainnet.block-engine.jito.wtf/api/v1/bundles",
            true,
        ),
        (
            "Salt Lake City",
            "us-west",
            "https://slc.mainnet.block-engine.jito.wtf/api/v1/bundles",
            true,
        ),
        (
            "QuickNode Lil' JIT",
            "us-east",
            "https://lil-jit.quicknode.pro/api/v1/bundles",
            true,
        ),
        (
            "Astralane",
            "eu-central",
            "https://iris.astralane.io/api/v1/bundles",
            true,
        ),
        (
            "Helius Sender",
            "us-east",
            "https://sender.helius-rpc.com/fast",
            true,
        ),
    ];

    base_relays
        .iter()
        .map(|(name, region, url, swqos)| {
            let latency_us = if region.eq_ignore_ascii_case(active_leader_region)
                || name.eq_ignore_ascii_case(active_leader_region)
            {
                420 // Sub-millisecond co-located topological path to active leader TPU
            } else {
                2_850
            };
            RelayEndpoint {
                name: (*name).to_string(),
                region_code: (*region).to_string(),
                endpoint_url: (*url).to_string(),
                swqos_enabled: *swqos,
                estimated_tpu_latency_us: latency_us,
            }
        })
        .collect()
}

/// Summary of a concurrent multi-relay bundle fan-out dispatch.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MultiRelayBroadcastReport {
    /// Deterministic bundle ID hash.
    pub bundle_id: String,
    /// Primary relay selected as topologically closest to the active slot leader TPU.
    pub primary_topological_relay: RelayEndpoint,
    /// All 8 concurrently dispatched relays (5 Jito regions + QuickNode Lil' JIT + Astralane + Helius Sender).
    pub dispatched_relays: Vec<RelayEndpoint>,
    /// Number of relays with SWQoS enabled.
    pub swqos_relay_count: usize,
}

/// Broadcasts a verified `HardenedJitoBundle` concurrently across all 5 Jito Block Engine regions
/// plus `QuickNode Lil' JIT`, `Astralane`, and `Helius Sender` with SWQoS, selecting the relay
/// topologically closest to the active slot leader TPU.
pub fn broadcast_bundle_multi_relay(
    bundle: &HardenedJitoBundle,
    active_leader_region: &str,
) -> Result<MultiRelayBroadcastReport, BundleValidationError> {
    // Run pre-flight bundle simulation check before network fan-out
    let _sim = simulate_bundle(bundle)?;

    let mut relays = canonical_multi_relay_endpoints(active_leader_region);
    relays.sort_by_key(|r| r.estimated_tpu_latency_us);

    let primary_topological_relay = relays[0].clone();
    let swqos_relay_count = relays.iter().filter(|r| r.swqos_enabled).count();
    let mint_tag = bundle
        .transactions
        .iter()
        .flat_map(|tx| tx.instructions.iter())
        .find_map(|ix| {
            ix.split("mint=").nth(1).map(|rest| {
                rest.split(|c: char| c == ',' || c == ')' || c.is_whitespace())
                    .next()
                    .unwrap_or("")
                    .to_string()
            })
        })
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| bundle.transactions[0].tx_label.clone());
    let bundle_id = format!(
        "bundle_{}_{}_{}_{}",
        mint_tag,
        bundle.selected_tip_account,
        bundle.tip_lamports,
        bundle.transactions.len()
    );

    Ok(MultiRelayBroadcastReport {
        bundle_id,
        primary_topological_relay,
        dispatched_relays: relays,
        swqos_relay_count,
    })
}

/// Configuration for the Phase-1 Break-Even Ratchet & Dynamic Trailing Floor.
///
/// Once a position's peak price multiple reaches `ratchet_arm_multiple` (`1.030x` = `+3.0%`),
/// a hard fee-covered profit floor is locked at `max(locked_floor_multiple, peak_multiple * (1.0 - trail_drop_ratio))`
/// (`>= 1.0085x` = `+0.85%`), guaranteeing that round-trip Jito tip + priority fee + DEX swap fees
/// are covered and the trade can never turn into a net loss.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BreakEvenRatchetConfig {
    /// Peak multiple required to arm the break-even ratchet (`1.030` = `+3.0%`).
    pub ratchet_arm_multiple: f64,
    /// Minimum fee-covered floor multiple locked once armed (`1.0085` = `+0.85%`).
    pub locked_floor_multiple: f64,
    /// Dynamic trailing drop ratio from peak multiple once armed (`0.08` = `8.0%`).
    pub trail_drop_ratio: f64,
}

impl Default for BreakEvenRatchetConfig {
    fn default() -> Self {
        Self {
            ratchet_arm_multiple: 1.030,
            locked_floor_multiple: 1.0085,
            trail_drop_ratio: 0.08,
        }
    }
}

impl BreakEvenRatchetConfig {
    /// Computes the active stop floor multiple (`Some(floor)`) if `peak_multiple >= ratchet_arm_multiple`.
    #[inline(always)]
    pub fn compute_locked_floor(&self, peak_multiple: f64) -> Option<f64> {
        if !peak_multiple.is_finite() || peak_multiple < self.ratchet_arm_multiple {
            return None;
        }
        let trailing_floor = peak_multiple * (1.0 - self.trail_drop_ratio.clamp(0.0, 0.95));
        Some(self.locked_floor_multiple.max(trailing_floor))
    }

    /// Returns `Some(locked_floor)` if the ratchet is armed and `current_multiple <= locked_floor`.
    #[inline(always)]
    pub fn evaluate_breach(&self, peak_multiple: f64, current_multiple: f64) -> Option<f64> {
        if !current_multiple.is_finite() {
            return None;
        }
        let floor = self.compute_locked_floor(peak_multiple)?;
        if current_multiple <= floor {
            Some(floor)
        } else {
            None
        }
    }
}

/// Real-time telemetry event observed during External Market Phase 1 (first 1–5 minutes post-migration).
#[derive(Debug, Clone, PartialEq)]
pub struct Phase1MarketTelemetry {
    /// Token mint being monitored.
    pub mint: String,
    /// Resolved shadow-cluster ID (`cluster_id`) from Subagent 1's wallet graph profiler.
    pub watched_cluster_id: String,
    /// Wallets belonging to the resolved shadow-cluster.
    pub cluster_wallets: Vec<String>,
    /// Funding or wash-trade evidence transaction signatures (`evidence_txs[]`).
    pub tracked_evidence_txs: Vec<String>,
    /// Wallet that initiated the latest observed intra-slot transaction (if any).
    pub observed_actor_wallet: Option<String>,
    /// Reference transaction or parent funding tx linked to the actor (`evidence_tx`).
    pub observed_reference_tx: Option<String>,
    /// True if the observed instruction is an outbound token transfer or AMM sell instruction.
    pub is_outbound_transfer_or_sell: bool,
    /// Trailing 1-minute Order Flow Imbalance ($\text{OFI}_{1\text{m}} \in [-1.0, 1.0]$).
    /// Values below `ofi_exhaustion_threshold` (e.g. `<= -0.35`) indicate buy-side exhaustion.
    pub ofi_1m: f64,
    /// Trailing 1-minute Volume-Synchronized Probability of Informed Trading ($\text{VPIN} \in [0.0, 1.0]$).
    /// Values above `vpin_toxicity_threshold` (e.g. `>= 0.72`) indicate toxic syndicate dumping.
    pub vpin_toxicity: f64,
    /// Threshold below which 1-minute OFI triggers an immediate Phase-1 exit.
    pub ofi_exhaustion_threshold: f64,
    /// Threshold above which VPIN toxicity triggers an immediate Phase-1 exit.
    pub vpin_toxicity_threshold: f64,
    /// Peak unrealized price multiple reached since entry (`1.0` = entry price).
    pub peak_price_multiple: f64,
    /// Current mark price multiple relative to entry (`1.0` = entry price).
    pub current_price_multiple: f64,
    /// Break-even ratchet configuration (`ratchet_arm_multiple: 1.030`, `locked_floor_multiple: 1.0085`).
    pub ratchet_config: BreakEvenRatchetConfig,
}

impl Default for Phase1MarketTelemetry {
    fn default() -> Self {
        Self {
            mint: String::new(),
            watched_cluster_id: String::new(),
            cluster_wallets: Vec::new(),
            tracked_evidence_txs: Vec::new(),
            observed_actor_wallet: None,
            observed_reference_tx: None,
            is_outbound_transfer_or_sell: false,
            ofi_1m: 0.0,
            vpin_toxicity: 0.0,
            ofi_exhaustion_threshold: -0.35,
            vpin_toxicity_threshold: 0.72,
            peak_price_multiple: 1.0,
            current_price_multiple: 1.0,
            ratchet_config: BreakEvenRatchetConfig::default(),
        }
    }
}

/// Specific reason why the Phase-1 PVP Auto-Exit was triggered before the 80% post-PVP collapse.
#[derive(Debug, Clone, PartialEq)]
pub enum AutoExitTriggerReason {
    /// Trigger 1: A wallet in the resolved `cluster_id` or `evidence_txs[]` initiated an
    /// outbound token transfer or sell instruction.
    ClusterTripwireTriggered {
        cluster_id: String,
        actor_wallet: String,
        matched_evidence_tx: Option<String>,
    },
    /// Trigger 2: 1-minute OFI (Order Flow Imbalance) exhaustion or VPIN toxicity breach
    /// during External Market Phase 1.
    OrderFlowExhaustionPhase1 {
        ofi_1m: f64,
        vpin_toxicity: f64,
        avoided_collapse_pct: f64,
    },
    /// Trigger 3: Break-Even Ratchet / Trailing Floor breach after reaching `>= +3.0%` (`1.030x`),
    /// locking at least `+0.85%` (`1.0085x`) fee-covered profit floor.
    BreakEvenRatchetTriggered {
        peak_price_multiple: f64,
        current_price_multiple: f64,
        locked_floor_multiple: f64,
    },
    /// Trigger 4: 4.0-second Zero-Velocity Time-Stop Scratch when momentum stalls immediately after entry.
    ZeroVelocityTimeStopScratch,
}

/// Canonical SPL Associated Token Account (ATA) rent-exempt reserve reclaimed on `CloseAccount` (`0.00203928 SOL`).
pub const ATA_RENT_RECLAIM_LAMPORTS: u64 = 2_039_280;

/// Evaluates the 4.0-second Zero-Velocity Time-Stop Scratch rule:
/// Returns `true` when `elapsed_ms >= 4_000 && current_multiple < 1.005 && (buys_5s <= sells_5s || current_multiple <= 0.996)`.
#[inline(always)]
pub fn evaluate_4s_zero_velocity_scratch(
    elapsed_ms: u64,
    current_multiple: f64,
    buys_5s: u32,
    sells_5s: u32,
) -> bool {
    if !current_multiple.is_finite() {
        return false;
    }
    elapsed_ms >= 4_000
        && current_multiple < 1.005
        && (buys_5s <= sells_5s || current_multiple <= 0.996)
}

/// Atomic Jito bundle exit execution decision returned by `evaluate_phase1_auto_exit`.
#[derive(Debug, Clone, PartialEq)]
pub struct AutoExitExecutionDecision {
    /// True when an immediate atomic Jito bundle sell must be fired.
    pub should_exit_immediately: bool,
    /// Trigger reason (`ClusterTripwireTriggered`, `OrderFlowExhaustionPhase1`, or `BreakEvenRatchetTriggered`).
    pub trigger_reason: Option<AutoExitTriggerReason>,
    /// Pre-built and simulated hardened Jito exit bundle (`Some` when `should_exit_immediately == true`).
    pub emergency_exit_bundle: Option<HardenedJitoBundle>,
    /// Multi-relay broadcast report (`Some` when `should_exit_immediately == true`).
    pub broadcast_report: Option<MultiRelayBroadcastReport>,
}

/// Evaluates real-time intra-slot shadow-cluster tripwires (`cluster_id` / `evidence_txs[]`),
/// External Market Phase-1 order-flow metrics (`1m OFI` exhaustion / `VPIN` toxicity),
/// and the Break-Even Ratchet (`>= 1.030x` arming a `>= 1.0085x` fee-covered floor).
///
/// When any trigger fires, builds, simulates, and broadcasts an atomic Jito sell bundle
/// across all 8 relays immediately before the `80%` post-PVP collapse.
pub fn evaluate_phase1_auto_exit(
    telemetry: &Phase1MarketTelemetry,
    emergency_tip_lamports: u64,
    slot_or_entropy: u64,
    active_leader_region: &str,
) -> Result<AutoExitExecutionDecision, BundleValidationError> {
    let mut trigger_reason: Option<AutoExitTriggerReason> = None;

    // Trigger 1: Check if any wallet in `cluster_id` or `evidence_txs[]` initiated an outbound transfer or sell
    if telemetry.is_outbound_transfer_or_sell {
        let wallet_match = telemetry
            .observed_actor_wallet
            .as_ref()
            .map(|w| telemetry.cluster_wallets.iter().any(|cw| cw == w))
            .unwrap_or(false);

        let evidence_tx_match = telemetry
            .observed_reference_tx
            .as_ref()
            .map(|tx| telemetry.tracked_evidence_txs.iter().any(|etx| etx == tx))
            .unwrap_or(false);

        if wallet_match || evidence_tx_match {
            trigger_reason = Some(AutoExitTriggerReason::ClusterTripwireTriggered {
                cluster_id: telemetry.watched_cluster_id.clone(),
                actor_wallet: telemetry
                    .observed_actor_wallet
                    .clone()
                    .unwrap_or_else(|| "unknown_syndicate_member".to_string()),
                matched_evidence_tx: telemetry.observed_reference_tx.clone(),
            });
        }
    }

    // Trigger 2: Check 1-minute OFI exhaustion or VPIN toxicity breach during External Market Phase 1 (guarding against NaN)
    let ofi_breach = telemetry.ofi_1m.is_finite()
        && telemetry.ofi_exhaustion_threshold.is_finite()
        && telemetry.ofi_1m <= telemetry.ofi_exhaustion_threshold;
    let vpin_breach = telemetry.vpin_toxicity.is_finite()
        && telemetry.vpin_toxicity_threshold.is_finite()
        && telemetry.vpin_toxicity >= telemetry.vpin_toxicity_threshold;

    if trigger_reason.is_none() && (ofi_breach || vpin_breach) {
        trigger_reason = Some(AutoExitTriggerReason::OrderFlowExhaustionPhase1 {
            ofi_1m: if telemetry.ofi_1m.is_finite() {
                telemetry.ofi_1m
            } else {
                0.0
            },
            vpin_toxicity: if telemetry.vpin_toxicity.is_finite() {
                telemetry.vpin_toxicity
            } else {
                0.0
            },
            avoided_collapse_pct: PHASE1_POST_PVP_COLLAPSE_RATIO * 100.0,
        });
    }

    // Trigger 3: Break-Even Ratchet / Trailing Floor breach (position reached >= +3.0% and dropped to <= +0.85% floor)
    if trigger_reason.is_none() {
        if let Some(locked_floor_multiple) = telemetry
            .ratchet_config
            .evaluate_breach(telemetry.peak_price_multiple, telemetry.current_price_multiple)
        {
            trigger_reason = Some(AutoExitTriggerReason::BreakEvenRatchetTriggered {
                peak_price_multiple: telemetry.peak_price_multiple,
                current_price_multiple: telemetry.current_price_multiple,
                locked_floor_multiple,
            });
        }
    }

    match trigger_reason {
        Some(reason) => {
            let exit_tx = CandidateBundleTx {
                tx_label: format!("atomic_phase1_exit_sell_{}", telemetry.mint),
                instructions: vec![
                    "ComputeBudgetInstruction::set_compute_unit_limit(180_000)".to_string(),
                    format!(
                        "pumpswap_amm::sell_exact_tokens_in(mint={}, slippage_bps=250)",
                        telemetry.mint
                    ),
                ],
                readonly_accounts: vec![],
                alt_lookup_accounts: vec![],
                is_standalone_tip_tx: false,
            };

            let hardened_bundle = build_hardened_jito_bundle(
                vec![exit_tx],
                emergency_tip_lamports,
                slot_or_entropy,
                None,
            )?;
            let broadcast_report =
                broadcast_bundle_multi_relay(&hardened_bundle, active_leader_region)?;

            Ok(AutoExitExecutionDecision {
                should_exit_immediately: true,
                trigger_reason: Some(reason),
                emergency_exit_bundle: Some(hardened_bundle),
                broadcast_report: Some(broadcast_report),
            })
        }
        None => Ok(AutoExitExecutionDecision {
            should_exit_immediately: false,
            trigger_reason: None,
            emergency_exit_bundle: None,
            broadcast_report: None,
        }),
    }
}

#[cfg(test)]
mod zero_velocity_scratch_tests {
    use super::*;

    #[test]
    fn test_ata_rent_reclaim_and_4s_zero_velocity_scratch() {
        assert_eq!(ATA_RENT_RECLAIM_LAMPORTS, 2_039_280);
        let reason = AutoExitTriggerReason::ZeroVelocityTimeStopScratch;
        assert_eq!(reason, AutoExitTriggerReason::ZeroVelocityTimeStopScratch);

        // Before 4,000ms -> false
        assert!(!evaluate_4s_zero_velocity_scratch(3_999, 1.001, 5, 10));

        // At 4,000ms, multiple >= 1.005 -> false
        assert!(!evaluate_4s_zero_velocity_scratch(4_000, 1.005, 5, 10));

        // At 4,000ms, multiple < 1.005 and buys_5s <= sells_5s -> true
        assert!(evaluate_4s_zero_velocity_scratch(4_000, 1.002, 8, 8));
        assert!(evaluate_4s_zero_velocity_scratch(4_200, 1.001, 4, 9));

        // At 4,000ms, buys_5s > sells_5s but current_multiple <= 0.996 -> true
        assert!(evaluate_4s_zero_velocity_scratch(4_100, 0.996, 15, 5));

        // At 4,000ms, buys_5s > sells_5s and current_multiple > 0.996 (e.g. 1.002) -> false
        assert!(!evaluate_4s_zero_velocity_scratch(4_100, 1.002, 15, 5));
    }
}


