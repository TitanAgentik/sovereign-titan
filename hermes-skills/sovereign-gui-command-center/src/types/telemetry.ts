export type MacroRegime = "GREEN" | "AMBER" | "RED_MACRO_FLUSH";
export type VaultMode = "PAPER" | "CANARY" | "LIVE";

export interface SlotLeaderInfo {
  validator: string;
  city: "Frankfurt" | "New York" | "Amsterdam" | "Tokyo" | string;
  flag: string;
}

export interface MacroDirectiveState {
  regime: MacroRegime;
  sol_5m_return_pct: number;
  engine_a_active: boolean;
  engine_a_priority_multiplier: number;
  engine_b_active: boolean;
  shadow_executor_active: boolean;
  shadow_sizing_multiplier: number;
}

export interface GraduationState {
  mode: VaultMode;
  initial_virtual_balance_sol: number;
  virtual_balance_sol: number;
  peak_virtual_balance_sol: number;
  total_paper_trades: number;
  winning_trades: number;
  losing_trades: number;
  profit_factor: number;
  net_virtual_sol_pnl: number;
  max_drawdown_pct: number;
  unhandled_honeypot_count: number;
  zero_unhandled_honeypots: boolean;
  canary_eligible: boolean;
  live_25_shards_unlocked: boolean;
  active_live_shards: number;
}

export interface WithdrawalVaultState {
  withdraw_address: string;
  reserve_lockbox_pubkey: string;
  master_vault_pubkey: string;
  high_water_mark_sol: number;
  active_hot_wallet_sol: number;
  pending_unclaimed_sweeps_sol: number;
  total_historical_withdrawn_sol: number;
  daemons_paused: boolean;
  active_hot_shards_count?: number;
  standby_rent_saver_shards_count?: number;
  ata_rent_saved_sol?: number;
}

export type VaultTelemetry = WithdrawalVaultState;

export interface StealthShardState {
  shard_index: number;
  pubkey: string;
  status: "ACTIVE" | "COMPROMISED" | "COUNTER_BAIT_WALLET";
  profitable_trades_count: number;
  rotation_threshold_trades: number;
  sol_balance: number;
  detected_external_copy_bots: number;
}

export interface AuditTradeLot {
  timestamp_ns: number;
  tx_signature: string;
  shard_id: number;
  engine_id: string;
  token_mint: string;
  sol_in: number;
  sol_out: number;
  jito_tip_sol: number;
  ata_rent_reclaimed_sol: number;
  sol_usd_spot_price: number;
  net_pnl_sol: number;
  net_pnl_usd: number;
}

export interface GepaPolicyInfo {
  policy_id: string;
  git_tag: string;
  role: string;
  gatekeeper_system_prompt: string;
  instruction_token_count: number;
  min_rugcheck_score: number;
  max_top10_holder_pct: number;
  min_social_velocity_score: number;
  take_profit_1_mult: number;
  trailing_stop_drawdown_pct: number;
  triggers_evaluated: number;
  simulated_net_ev_sol: number;
  honeypot_hits: number;
  rolling_drawdown_pct: number;
}

export interface OpenPositionState {
  position_id: string;
  symbol: string;
  mint: string;
  venue: string;
  shard: string;
  size_sol: number;
  entry_price_usd: number;
  mark_price_usd: number;
  pnl_pct: number;
  pnl_sol: number;
  stage: string;
  locked_manual: boolean;
}

export interface TrackedAlphaWallet {
  wallet: string;
  tier: "MICRO_CAP_SHADOW_SHARK" | "MID_CAP_SHADOW_SHARK" | "CROWDED_WHALE_BAIT" | "BLACKLISTED";
  archetype: string;
  fastBots0To2Slots: number;
  slowFollowers3To18Slots: number;
  followerLpImpactPct: number;
  winRate30d: number;
  profitFactor30d: number;
  pnl30dUsd: number;
  sizingMultiplier: number;
  childBurners: string[];
  jsonProfile: Record<string, unknown>;
}

export interface BackrunFeedEntry {
  id: string;
  pair: string;
  mode: string;
  route: string;
  victim_swap_sol: number;
  borrow_sol: number;
  jito_tip_sol: number;
  net_profit_sol: number;
  v0_bytes: number;
  latency_ms: number;
}

export interface SandwichFeedEntry {
  id: string;
  pair: string;
  mode: string;
  front_run_sol: number;
  victim_sol: number;
  victim_slippage_bps: number;
  back_run_sol_out: number;
  jito_tip_sol: number;
  net_profit_sol: number;
  rent_reclaimed_sol: number;
  status: string;
}

export interface MevTriadState {
  engine_a_mode: "ON" | "OFF" | "PAPER_SIM";
  flash_provider:
    | "KAMINO"
    | "MARGINFI"
    | "SAVE_SOLEND"
    | "DRIFT_SPOT"
    | "JUPITER_LEND"
    | "METEORA_DLMM"
    | "MEGA_SYNDICATE_ALL"
    | string;
  max_borrow_sol: number;
  flash_tier_usd?: number;
  syndicate_active_protocols?: string[];
  whole_ecosystem_mode?: string;
  jito_bid_pct: number;
  backrun_submode?: "2HOP_VICTIM_BUNDLE" | "3HOP_TRIANGULAR" | string;
  backrun_bundles_landed?: number;
  backrun_total_profit_sol?: number;
  last_flash_sim: string;
  backrun_feed?: BackrunFeedEntry[];
  engine_b_mode: "ON" | "OFF" | "PAPER_SIM";
  sandwich_submode?: "ATOMIC_3TX_BUNDLE" | "WIDE_HERD_N1_N8" | "TWAP_PREDATOR" | string;
  victim_sol_in?: number;
  victim_slippage_bps?: number;
  active_sandwich_slot: number;
  sandwiches_landed?: number;
  sandwich_total_profit_sol?: number;
  engine_b_status: string;
  sandwich_feed?: SandwichFeedEntry[];
  engine_c_mode: "ON" | "OFF" | "PAPER_SIM";
  realized_cumulative_sol: number;
  engine_c_manual_override: boolean;
}

export interface HorizonConfigItem {
  id?: "H1" | "H2" | "H3" | "H4" | "H1_BLIND_0BLOCK" | string;
  horizon_type?: string;
  label?: string;
  subtitle?: string;
  mode: "ON" | "PAPER" | "OFF" | "AUTO_AI" | "MANUAL_ONLY";
  max_sol: number;
  min_bonding_curve_pct?: number;
  max_bonding_curve_pct?: number;
  max_raw_principal_hold_sec?: number;
}

export interface TrailWinStepPoint {
  timestamp: number;
  price: number;
  stop_price: number;
  stage: number;
}

export interface TrailWinPositionTelemetry {
  mint: string;
  symbol: string;
  horizon: string;
  entry_price_sol: number;
  current_price_sol: number;
  high_water_mark_price_sol: number;
  unrealized_multiple: number;
  hwm_multiple: number;
  initial_sol_invested: number;
  realized_sol_recovered: number;
  remaining_bag_fraction: number;
  current_stage: number;
  active_trail_stop_price: number;
  locked_profit_pct: number;
  dynamic_trail_pct: number;
  manual_trail_override_pct: number | null;
  is_risk_free_moonbag: boolean;
  time_in_trade_sec: number;
  is_closed: boolean;
  close_reason: string | null;
  step_history: TrailWinStepPoint[];
}

export interface DriftHedgeTelemetry {
  enabled: boolean;
  mode: "OFF" | "HALF_50PCT" | "FULL_100PCT";
  hedge_ratio_pct: number;
  drift_program_id: string;
  perp_market_symbol: string;
  perp_market_index: number;
  idle_treasury_sol: number;
  short_perp_notional_sol: number;
  entry_sol_usd_price: number;
  locked_usd_value: number;
  estimated_funding_apy_pct: number;
  accrued_funding_yield_usd: number;
  last_rebalance_v0_tx_bytes: number;
}

export interface ZeroLossShieldsTelemetry {
  locked_daily_profit_floor_sol: number;
  daily_realized_net_sol: number;
  daily_high_water_mark_pnl_sol: number;
  house_money_phase: string;
  directional_sizing_multiplier: number;
  directional_engines_allowed: boolean;
  engine_a_max_borrow_sol: number;
  roundtrip_honeypot_blocks_today: number;
  sybil_wash_traps_blocked_today: number;
  scratch_saves_3s_today: number;
  ev_tip_blocks_today: number;
  drift_hedge: DriftHedgeTelemetry;
  bayesian_win_rate_gate_enabled?: boolean;
  bayesian_min_win_prob_pct?: number;
  bayesian_current_win_prob_pct?: number;
  instant_breakeven_ratchet_enabled?: boolean;
  fee_adjusted_breakeven_floor_pct?: number;
  shred_throughput_msg_per_sec?: number;
  pda_bundle_hotpath_latency_us?: number;
}

export type ZeroLossShieldTelemetry = ZeroLossShieldsTelemetry;

export interface ApexPredatorTelemetry {
  rug_dumps_frontrun_today: number;
  saved_capital_sol_today: number;
  liquidations_landed_today: number;
  liquidation_yield_sol_today: number;
  super_signals_triggered_today: number;
  migrations_captured_today: number;
  migration_profit_sol_today: number;
  total_slippage_saved_sol_today: number;
  lead_lag_snipes_today: number;
  lead_lag_profit_sol_today: number;
  total_tip_rebates_saved_sol_today: number;
}

export interface MeltGuardTelemetry {
  paper_ref: string;
  feature_count: number;
  max_risk_threshold: number;
  probes_allowed_threshold: number;
  evaluations_today: number;
  vetoes_today: number;
  probes_only_today: number;
  clean_launches_today: number;
  cabal_clusters_detected_today: number;
  last_evaluated_mint: string;
  last_risk_score: number;
  last_decision: string;
}

export interface ShortHorizonRugGuardTelemetry {
  paper_ref: string;
  benchmark_mcc: number;
  evaluations_today: number;
  rug_t_triggers_today: number;
  emergency_exits_today: number;
  saved_sol_estimate_today: number;
  last_evaluated_mint: string;
  last_rug_probability: number;
  last_recommended_action: string;
}

export interface LaunchpadStoreTelemetry {
  paper_refs: string[];
  db_path: string;
  coverage_pct: number;
  tables: {
    bonding_curve_states: number;
    token_trades_microstructure: number;
    creator_social_profiles: number;
  };
  graduated_curves_count: number;
  rug_abandoned_curves_count: number;
}

export interface OssRepoSuiteTelemetry {
  integrated_repos_count: number;
  repos: string[];
  extend_account_threshold_bytes: number;
  graduation_target_sol: number;
  diagnostics_run_today: number;
  extend_account_Injections_today: number;
  graduation_sweeps_triggered_today: number;
  dev_sell_emergency_exits_today: number;
  migration_snipes_triggered_today: number;
}

export interface SovereignSubagentSpec {
  id: string;
  name: string;
  role: string;
  focus: string;
  status: string;
}

export interface SovereignPrimaryAgentSpec {
  id: string;
  name: string;
  tier: string;
  cores: string;
  model: string;
  description: string;
  status: string;
  subagents: SovereignSubagentSpec[];
}

export interface AgentSwarmTelemetry {
  primary_agent_count: number;
  subagent_count: number;
  total_primary_agents?: number;
  total_subagents?: number;
  online_primary_agents?: number;
  online_subagents?: number;
  status?: string;
  dispatches_today: number;
  last_dispatched_agent: string;
  last_dispatched_subagent: string;
  agents: SovereignPrimaryAgentSpec[];
}

export interface DeceptiveCounterExploiterTelemetry {
  slot0_evaluations?: number;
  slot0_hard_vetoes?: number;
  cto_evaluations?: number;
  genuine_cto_count?: number;
  staged_fake_cto_count?: number;
  hair_trigger_exits_fired?: number;
  tarjan_evaluations?: number;
  organic_breakout_entries?: number;
  wash_trade_abstains?: number;
}

export interface Slot0And845SniperTelemetry {
  colocated_slot0_landing_rate_pct?: number;
  public_rpc_landing_rate_pct?: number;
  aperture_txstream_overhead_us?: number;
  stage_a_prewarm_threshold_pct?: number;
  stage_b_fire_threshold_sol?: number;
  counters?: {
    slot0_snipes_triggered?: number;
    stage_a_prewarms?: number;
    stage_b_hotpath_fires?: number;
    fanout_dispatches_run?: number;
  };
}

export interface ElizaRlEngineTelemetry {
  tracked_wallets_count?: number;
  closed_trades_logged?: number;
  adaptation_runs?: number;
  evaluations_run?: number;
  diagnostics_run?: number;
  active_weights?: Record<string, number>;
}

export interface DevEntityResolverTelemetry {
  diagnostic_runs?: number;
  red_cohort_empirical_rings?: number;
  tlsh_digest_hex_len?: number;
  keenhash_speedup_multiplier?: number;
  attention_gnn_cluster_accuracy_pct?: number;
  tier1_registered_entities?: number;
  routing_decisions_logged?: number;
}

export interface PreMintPeelChainListenerTelemetry {
  subsystem?: string;
  agent_id?: string;
  pre_armed_burner_wallets_count?: number;
  solbundler_sweeps_registered?: number;
  pre_mint_signals_evaluated?: number;
  curve_evaluations_logged?: number;
  diagnostic_runs?: number;
}

export interface AlphaExploitForensicsTelemetry {
  wallet_audits_run?: number;
  wallets_admitted?: number;
  wallets_rejected?: number;
  active_audited_gem_finders?: number;
  skyeye_convergence_triggers?: number;
  firewall_inspections?: number;
  firewall_blocks?: number;
  cabal_inspections?: number;
  tier1_snipes?: number;
  tier2_emergency_exits?: number;
  tier3_hard_rejects?: number;
  diagnostics_run?: number;
}

export interface JitoKnapsackJudgeTelemetry {
  agent_c_id?: string;
  agent_d_id?: string;
  stage2_block_compute_capacity_cu?: number;
  jito_regions?: string[];
  counters?: {
    diagnostics_run?: number;
    auctions_solved?: number;
    tips_calibrated?: number;
    bundles_validated?: number;
    bundles_rejected?: number;
    multi_region_dispatches?: number;
  };
}

export interface FlashPrimitivesEngineTelemetry {
  subsystem?: string;
  supported_primitives_count?: number;
  counters?: {
    diagnostics_run?: number;
    routes_evaluated?: number;
    lifecycles_simulated?: number;
    lifecycles_committed?: number;
    lifecycles_reverted?: number;
    closed_form_solves?: number;
    nostd_dual_route_checks?: number;
  };
}

export interface CovertBoundaryGuardTelemetry {
  subsystem?: string;
  counters?: {
    diagnostics_run?: number;
    graduation_evaluations_run?: number;
    vector1_executions?: number;
    vector2_executions?: number;
    vector3_authority_blocks?: number;
    single_tick_jit_runs?: number;
    single_tick_jit_executions?: number;
    clmm_spoof_audits_run?: number;
    clmm_phantom_pools_blocked?: number;
  };
}

export interface NextGenMayhemEngineTelemetry {
  subsystem?: string;
  mayhem_evaluations?: number;
  mayhem_ai_backruns_triggered?: number;
  mayhem_hour24_burn_frontruns_triggered?: number;
  v4_hook_simulations?: number;
  v4_hook_arbs_triggered?: number;
  multiply_squeezes_triggered?: number;
  isolated_liquidations_triggered?: number;
  cumulative_liquidation_profit_usd?: number;
}

export interface SalmonellaAdversarialShieldTelemetry {
  subsystem?: string;
  fot_evaluations?: number;
  fot_nominal_rejections?: number;
  skim_opportunities_detected?: number;
  cu_profiles_computed?: number;
  static_cu_exhaustions_prevented?: number;
  salmonella_scans?: number;
  salmonella_traps_blocked?: number;
  five_vector_approvals?: number;
  five_vector_blocks?: number;
  compliance_approvals?: number;
  compliance_blocks?: number;
  tax_disposal_ledger_count?: number;
}

export interface ColocatedTunnel {
  id: string;
  region: string;
  datacenter: string;
  interface: string;
  protocol: string;
  endpoint: string;
  validator_stake_share_pct: number;
  rtt_ms: number;
  jitter_us: number;
  packet_loss_pct: number;
  mtu_bytes: number;
  status: string;
  enabled: boolean;
  relays: string[];
}

export interface ColocatedNicInfo {
  operstate: string;
  mtu: number;
  ipv4: string;
}

export interface ColocatedVpnMeshTelemetry {
  routing_mode: string;
  active_mode?: string;
  primary_nic: string;
  tailscale_iface: string;
  tailscale_ip: string;
  mtu_safe_verified: boolean;
  wireguard_mtu_bytes: number;
  solana_tx_payload_cap_bytes: number;
  solana_udp_mtu_limit_bytes: number;
  slot0_colocated_landing_rate_pct: number;
  non_colocated_baseline_rate_pct: number;
  active_primary_tunnel_id: string;
  last_probe_ms: number;
  last_live_probe_ts?: number;
  nic_interfaces?: Record<string, ColocatedNicInfo>;
  tunnels: ColocatedTunnel[];
}

export interface MemoryPersistenceTelemetry {
  nvme_snapshot_dir?: string;
  snapshot_dir?: string;
  has_nvme_snapshot?: boolean;
  ramdisk_root?: string;
  last_checkpoint_ts?: number;
  last_checkpoint_reason?: string;
  files_synced?: number;
  total_bytes_synced?: number;
  elapsed_ms?: number;
  [key: string]: unknown;
}

export interface ExperientialPlaybookRule {
  rule_id: string;
  category: string;
  utility_score: number;
  status: "ACTIVE" | "SHADOW_VALIDATION" | "PRUNED" | string;
  rule_text: string;
  upvotes?: number;
  downvotes?: number;
  source?: string;
}

export interface EpisodicTradeReflection {
  tx_signature: string;
  failure_category: string;
  verbal_critique: string;
  counterfactual_fix: string;
  timestamp_ts?: number;
}

export interface ExperientialLearningTelemetry {
  cycles_executed: number;
  on_device_token_share_pct: number;
  active_rules_count: number;
  shadow_rules_count: number;
  episodic_reflections_count: number;
  heuristics_file_bytes: number;
  heuristics_file_cap_bytes: number;
  cron_schedule: string;
  last_cycle_summary: string;
  top_rules: ExperientialPlaybookRule[];
  recent_reflections: EpisodicTradeReflection[];
  [key: string]: unknown;
}

export interface SmartMoneyCopyEngineTelemetry {
  subsystem?: string;
  active_copied_wallets_count?: number;
  gmgn_onchart_markers_enabled?: boolean;
  cielo_bots_online?: number;
  suite_runs?: number;
  zero_dev_louvain_runs?: number;
  slot_zero_dynamic_tip_runs?: number;
  recon_ping_traps_triggered?: number;
  last_action_summary?: string;
  [key: string]: unknown;
}

export interface MainnetReadinessCheckItem {
  id: number | string;
  key: string;
  label: string;
  detail: string;
  ready: boolean;
  status:
    | "READY"
    | "ARMED"
    | "DRY_RUN_SAFE"
    | "ACTION_REQUIRED"
    | "PASS"
    | "WARN"
    | string;
}

export interface MainnetApiInventoryItem {
  id: string;
  name: string;
  category:
    | "PAID_CORE_4"
    | "FREE_7_STREAM"
    | "WEBHOOK_MTPROTO"
    | "MCP_SERVER";
  endpoint: string;
  configured: boolean;
  status: string;
  latency_ms?: number;
}

export interface MainnetReadinessTelemetry {
  overall_ready?: boolean;
  passed_checks?: number;
  ready_count?: number;
  total_checks?: number;
  ramdisk_mounted?: boolean;
  mlock_keyring_active?: boolean;
  local_llm_4lane_ready?: boolean;
  helius_configured?: boolean;
  jupiter_configured?: boolean;
  birdeye_configured?: boolean;
  socialdata_configured?: boolean;
  keystore_persisted?: boolean;
  keystore_path?: string;
  keystore_wallets_count?: number;
  withdraw_address_bound?: boolean;
  bound_withdraw_address?: string;
  profit_guard_compiled?: boolean;
  profit_guard_program_id?: boolean | string;
  profit_guard_so_path?: string;
  alt_prewarmed?: boolean;
  alt_address?: string;
  alt_account_count?: number;
  jito_tips_excluded_from_alt?: boolean;
  atas_prewarmed?: boolean;
  prewarmed_atas_count?: number;
  target_atas_count?: number;
  prewarmed_mints?: string[];
  jito_5region_swqos_ready?: boolean;
  live_broadcast_enabled?: boolean;
  broadcast_mode?: "ARMED" | "DRY_RUN_SAFE" | string;
  onchain_master_sol?: number;
  onchain_shards_total_sol?: number;
  onchain_total_sol?: number;
  last_preflight_ts?: number;
  last_balance_sync_ts?: number;
  last_prewarm_ts?: number;
  last_action_summary?: string;
  checks?: MainnetReadinessCheckItem[];
  paid_core_4_apis?: MainnetApiInventoryItem[];
  free_7_apis_streams?: MainnetApiInventoryItem[];
  webhooks_and_mtproto?: MainnetApiInventoryItem[];
  mcp_servers?: MainnetApiInventoryItem[];
  [key: string]: unknown;
}

export interface Daily5kTierItem {
  tier_id: number;
  name: string;
  engines?: string[];
  capital_source?: string;
  daily_frequency?: string;
  target_sol_per_day: number;
  target_usd_per_day: number;
  principal_at_risk_sol?: number;
  downside_shield?: string;
}

export interface Daily5kMultiplierItem {
  multiplier_id: number;
  key: string;
  label: string;
  detail: string;
  enabled: boolean;
  status: string;
}

export interface CapitalEvolutionEchelonItem {
  echelon_id: number;
  code?: string;
  name: string;
  min_equity_sol?: number;
  max_equity_sol?: number;
  daily_velocity_floor_sol?: number;
  daily_velocity_floor_usd?: number;
  daily_velocity_range_sol?: string;
  daily_velocity_range_usd?: string;
  daily_target_range_usd?: string;
  kamino_flash_cap_sol: number;
  meteora_dlmm_surge_pool_sol: number;
  per_shard_curve_cap_sol?: number;
  per_shard_entry_cap_sol?: number;
  concurrent_curve_waves?: number;
  simultaneous_token_waves?: number;
  deep_amm_max_swing_sol?: number;
  deep_amm_swing_size_sol?: number;
  polymarket_usdc_float?: number;
  crosschain_solver_inventory_sol?: number;
  evolved_strategy_unlock?: string;
  strategy_evolution_unlocks?: string;
}

export interface Daily5kVelocityPresetTelemetry {
  enabled?: boolean;
  status?: "ARMED" | "STANDBY" | string;
  uncapped_compounding_enabled?: boolean;
  daily_profit_ceiling_mode?: string;
  daily_profit_ceiling_usd?: string;
  is_5k_only_a_floor?: boolean;
  auto_reinvest_profit_ratio?: number;
  auto_reinvest_profit_ratio_pct?: number;
  auto_evolve_strategies_with_capital?: boolean;
  min_daily_target_usd?: number;
  min_daily_target_sol?: number;
  optimal_daily_target_sol?: number;
  optimal_daily_target_usd?: number;
  scaled_compounded_daily_target_sol?: number;
  scaled_compounded_daily_target_usd?: number;
  weekly_target_usd?: number;
  monthly_target_usd?: number;
  total_compounded_equity_sol?: number;
  total_auto_reinvested_profit_sol?: number;
  total_compounded_profit_sol?: number;
  reinvested_dlmm_and_funding_sol?: number;
  reinvested_reserve_lockbox_sol?: number;
  reinvested_protected_vault_sol?: number;
  reinvested_hot_shard_waves_sol?: number;
  compounding_reinvest_cycles?: number;
  strategy_evolution_upgrades_count?: number;
  active_capital_echelon_id?: number;
  active_capital_echelon_code?: string;
  active_capital_echelon_name?: string;
  current_echelon_daily_range_sol?: string;
  current_echelon_daily_range_usd?: string;
  active_capital_echelon_daily_range_usd?: string;
  last_evolved_strategy_unlock?: string;
  active_strategy_evolution_note?: string;
  strategy_evolutions_count?: number;
  concurrent_curve_waves_limit?: number;
  active_simultaneous_token_waves?: number;
  deep_amm_max_position_sol?: number;
  active_deep_amm_swing_size_sol?: number;
  crosschain_solver_inventory_sol?: number;
  kamino_flash_cap_sol?: number;
  active_parallel_shards?: number;
  per_shard_entry_cap_sol?: number;
  meteora_dlmm_surge_pool_sol?: number;
  polymarket_usdc_float?: number;
  prewarmed_shard_atas_count?: number;
  mainnet_alt_accounts_count?: number;
  local_jupiter_binary_url?: string;
  quote_latency_ms?: number;
  vpn_routing_mode?: string;
  bayesian_win_prob_gate_pct?: number;
  instant_breakeven_floor_pct?: number;
  profit_guard_cpi_enforced?: boolean;
  multipliers_armed_count?: number;
  total_multipliers_count?: number;
  activations_count?: number;
  tiers?: Daily5kTierItem[];
  multipliers?: Daily5kMultiplierItem[];
  capital_evolution_echelons?: CapitalEvolutionEchelonItem[];
  [key: string]: unknown;
}

export interface LiveMarketTokenItem {
  mint: string;
  symbol: string;
  name: string;
  launchpad?: string;
  column?: "NEW_CREATIONS" | "FINAL_STRETCH" | "GRADUATED";
  priceUsd: number;
  priceSol?: number;
  marketCapUsd: number;
  liquidityUsd: number;
  volume5mUsd: number;
  volume1hUsd?: number;
  txns5mBuys: number;
  txns5mSells: number;
  priceChange5mPct: number;
  priceChange1hPct?: number;
  bondingCurvePct?: number;
  ageLabel?: string;
  pairAddress?: string;
  dexId?: string;
}

export interface HardwareGpuTelemetry {
  index: number;
  name: string;
  utilization_pct: number;
  vram_used_gb: number;
  vram_total_gb: number;
  temp_c: number;
  power_w: number;
}

export interface HardwareMetricsTelemetry {
  cpu_load_1m: number;
  cpu_load_5m: number;
  cpu_load_15m: number;
  cpu_cores_count: number;
  cpu_utilization_pct: number;
  core_zone_loads: number[];
  ram_total_gb: number;
  ram_used_gb: number;
  ram_available_gb: number;
  ramdisk_used_gb: number;
  gpus: HardwareGpuTelemetry[];
}

export interface AtomicArbOpportunityItem {
  id?: string;
  mint: string;
  symbol: string;
  route?: string;
  route_summary?: string;
  buy_dex?: string;
  sell_dex?: string;
  input_sol: number;
  return_sol?: number;
  expected_out_sol?: number;
  gross_profit_sol?: number;
  gross_spread_bps?: number;
  net_spread_bps?: number;
  jito_tip_sol: number;
  net_profit_sol: number;
  principal_risk_sol?: number;
  executable?: boolean;
  status?: string;
  timestamp_ms?: number;
}

export interface AtomicArbScannerTelemetry {
  enabled?: boolean;
  status?: string;
  scans_completed?: number;
  tokens_scanned?: number;
  profitable_routes_count?: number;
  best_net_spread_bps?: number;
  bundles_executed?: number;
  total_profit_sol?: number;
  jito_tip_cap_pct?: number;
  max_small_clip_tip_sol?: number;
  local_mmap_sub50us_scan_us?: number;
  local_mmap_candidates_count?: number;
  last_scan_ts?: number;
  last_action_summary?: string;
  opportunities?: AtomicArbOpportunityItem[];
}

export interface WalletDiscoveryTelemetry {
  enabled?: boolean;
  status?: string;
  scans_completed?: number;
  discovered_count?: number;
  verified_wallets_count?: number;
  min_win_rate_pct?: number;
  min_avg_hold_secs?: number;
  min_hold_sec?: number;
  last_discovery_ts?: number;
  last_action_summary?: string;
  discovered_wallets?: TrackedAlphaWallet[];
}

export interface AutonomousClosedLoopTelemetry {
  enabled: boolean;
  execution_stage: string;
  onchain_sol_detected: number;
  min_boot_sol_required: number;
  profit_guard_deployed_onchain: boolean;
  native_jupiter_slippage_guard_fallback: boolean;
  direct_v0_without_undeployed_alt: boolean;
  deployment_rent_saved_sol: number;
  local_mmap_sub50us_prefilter_active: boolean;
  offline_llm_zero_ms_bypass_active: boolean;
  auto_arbs_executed_count: number;
  auto_copy_snipes_executed_count: number;
  auto_crank_sandwiches_executed_count: number;
  auto_exits_executed_count: number;
  last_autonomous_action: string;
  last_autonomous_action_ts: number;
}

export interface MegaFlashSyndicateTelemetry {
  active_tier_usd: number;
  active_tier_label: string;
  max_borrow_sol: number;
  syndicate_mode: string;
  blended_flash_fee_bps?: number;
  protocols_armed: string[];
  whole_ecosystem_strategies_armed: string[];
  syndicate_executions_count: number;
  cumulative_syndicate_profit_sol: number;
  cumulative_syndicate_profit_usd: number;
  last_syndicate_action: string;
  last_syndicate_ts: number;
}

export interface TitanTelemetryFrame {
  timestamp_ns: number;
  alpenglow_slot: number;
  bam_tick_index: number;
  bam_tick_ms: number;
  slot_duration_ms: number;
  ptp_offset_ns: number;
  ptp_locked: boolean;
  leader: SlotLeaderInfo;
  sol_usd: number;
  btc_usd: number;
  unrealized_pnl_sol: number;
  net_24h_pnl_sol: number;
  net_24h_pnl_usd: number;
  ata_rent_reclaimed_total_sol?: number;
  paused_all: boolean;
  macro_directive: MacroDirectiveState;
  graduation: GraduationState;
  vault: WithdrawalVaultState;
  gepa: {
    champion: GepaPolicyInfo;
    challenger: GepaPolicyInfo | null;
  };
  shards: StealthShardState[];
  audit_lots: AuditTradeLot[];
  open_positions?: OpenPositionState[];
  horizons_config?: Record<string, HorizonConfigItem>;
  trail_win_positions?: Record<string, TrailWinPositionTelemetry>;
  zero_loss_shields?: ZeroLossShieldsTelemetry;
  apex_predator?: ApexPredatorTelemetry;
  melt_guard?: MeltGuardTelemetry;
  short_horizon_rug_guard?: ShortHorizonRugGuardTelemetry;
  launchpad_store?: LaunchpadStoreTelemetry;
  oss_repo_suite?: OssRepoSuiteTelemetry;
  four_stage_pipeline?: Record<string, unknown>;
  deceptive_counter_exploiter?: DeceptiveCounterExploiterTelemetry;
  slot0_845_sniper?: Slot0And845SniperTelemetry;
  eliza_rl_engine?: ElizaRlEngineTelemetry;
  dev_entity_resolver?: DevEntityResolverTelemetry;
  pre_mint_listener?: PreMintPeelChainListenerTelemetry;
  alpha_exploit_forensics?: AlphaExploitForensicsTelemetry;
  jito_knapsack_judge?: JitoKnapsackJudgeTelemetry;
  flash_primitives_engine?: FlashPrimitivesEngineTelemetry;
  covert_boundary_guard?: CovertBoundaryGuardTelemetry;
  nextgen_mayhem_engine?: NextGenMayhemEngineTelemetry;
  salmonella_adversarial_shield?: SalmonellaAdversarialShieldTelemetry;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  sanctum_superbundle_engine?: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  meteora_funding_harvester?: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  crank_bridge_engine?: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  vision_polymarket_sniper?: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  golden5_governor?: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  smart_money_copy_engine?: SmartMoneyCopyEngineTelemetry & Record<string, any>;
  experiential_learning?: ExperientialLearningTelemetry;
  mainnet_readiness?: MainnetReadinessTelemetry;
  daily_5k_preset?: Daily5kVelocityPresetTelemetry;
  atomic_arb_scanner?: AtomicArbScannerTelemetry;
  wallet_discovery?: WalletDiscoveryTelemetry;
  autonomous_closed_loop?: AutonomousClosedLoopTelemetry;
  mega_flash_syndicate?: MegaFlashSyndicateTelemetry;
  module_toggle_states?: Record<string, boolean>;
  agent_swarm?: AgentSwarmTelemetry;
  colocated_vpn_mesh?: ColocatedVpnMeshTelemetry;
  memory_persistence?: MemoryPersistenceTelemetry;
  mmap_slot0_r_sol?: number;
  execution_events?: string[];
  shadow_wallets?: TrackedAlphaWallet[];
  mev_state?: MevTriadState;
  audio_alerts_enabled?: boolean;
  enable_bam_dbi?: boolean;
  gui_pinned_cores: number[];
  live_market_tokens?: LiveMarketTokenItem[];
  hardware_metrics?: HardwareMetricsTelemetry;
  env_api_keys?: Record<string, string>;
  max_daily_drawdown_pct?: number;
  max_concurrent_positions?: number;
  jito_tip_cap_pct?: number;
  slippage_bps?: number;
  master_cap_multiplier?: number;
  asymmetric_tp_multiplier?: number;
  jitodontfront_enabled?: boolean;
  insider_max_pct?: number;
  total_equity_sol?: number;
  total_equity_usd?: number;
}

