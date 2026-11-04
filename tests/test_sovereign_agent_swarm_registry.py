"""Comprehensive pytest suite for `src/agents/sovereign_agent_swarm_registry.py`
verifying the 24-Agent / 72-Subagent Sovereign Titan OS Autonomous Hierarchy.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import List, Tuple

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agents.sovereign_agent_swarm_registry import (
    FOUNDATIONAL_ARXIV_PAPERS,
    IMMUTABLE_SAFETY_FILES,
    OSS_10_GITHUB_REPOS,
    PRIMARY_AGENT_IDS,
    SOVEREIGN_AGENT_MAP,
    SOVEREIGN_AGENT_ROSTER,
    SOVEREIGN_SUBAGENT_MAP,
    SUBAGENTS_PER_AGENT,
    SUBAGENT_IDS,
    TOTAL_PRIMARY_AGENTS,
    TOTAL_SUBAGENTS,
    PrimaryAgentSpec,
    SovereignAgentSwarmRegistry,
    SubagentSpec,
    get_sovereign_agent_swarm_registry,
)


EXPECTED_HIERARCHY: List[Tuple[str, str, Tuple[str, str, str]]] = [
    (
        "mev-hotpath-architect",
        "Cores 4–23",
        (
            "v0-packet-compactor-96acct",
            "bam-25ms-tick-aligner",
            "dynamic-contention-tip-scaler",
        ),
    ),
    (
        "flash-loan-arb-specialist",
        "Cores 4–15",
        (
            "victim-2hop-backrun-subagent",
            "triangular-3hop-4hop-graph-subagent",
            "bin-cliff-fstar-lst-5000sol-subagent",
        ),
    ),
    (
        "sandwich-jit-predator",
        "Cores 16–23 & 28–31",
        (
            "atomic-3tx-bundle-subagent",
            "wide-herd-quorum-n1-n8-subagent",
            "twap-clip-and-jit-dlmm-subagent",
        ),
    ),
    (
        "alpha-shadow-quant",
        "Cores 24–27",
        (
            "two-tranche-t1-t2-executor",
            "multi-shark-consensus-2x-subagent",
            "single-shark-probe-05x-subagent",
        ),
    ),
    (
        "burner-dag-cluster-tracker",
        "Cores 24–27",
        (
            "hop1-hop2-hop3-root-attributor",
            "fast-bot-vs-slow-herd-classifier",
            "gtg7784-sybil-transfer-tree-crawler",
        ),
    ),
    (
        "trail-win-shield-guardian",
        "Cores 0–3 & 24–27",
        (
            "h1-88-995-bonding-squeeze-subagent",
            "h2-reclaim-h3-45m-moonbag-subagent",
            "zero-loss-shield-dev-sell-exit-subagent",
        ),
    ),
    (
        "apex-predator-7module-hunter",
        "Cores 4–31",
        (
            "lp-removal-and-migration-sniper-subagent",
            "liquidation-cascade-and-vpin-subagent",
            "token2022-tax-and-ata-rent-subagent",
        ),
    ),
    (
        "arxiv-quant-defense-sentinel",
        "Cores 36–47",
        (
            "arxiv-2602-13480-melt-122feat-subagent",
            "arxiv-2608-20271-5m-rug-killswitch-subagent",
            "arxiv-2512-11850-2609-18975-coverage-subagent",
        ),
    ),
    (
        "pump-dbc-oss-integrator",
        "Cores 4–31",
        (
            "pumpswap-extend300-nirholas-curve-subagent",
            "chainstack-migrate-shredstream-sniper-subagent",
            "pumpfun-rs-bonk-meteora-dbc-subagent",
        ),
    ),
    (
        "gepa-llm-swarm-evolver",
        "Cores 36–95",
        (
            "lane1-hermes-gatekeeper-subagent",
            "lane2-qwen-vision-ocr-subagent",
            "lane3-deepseek-gepa-60trace-subagent",
        ),
    ),
    (
        "gui-cockpit-engineer",
        "Cores 32–35",
        (
            "superchart-v5-trail-overlay-subagent",
            "ramdisk-120hz-telemetry-subagent",
            "ipc-sub025ms-command-router-subagent",
        ),
    ),
    (
        "mainnet-infra-sre",
        "Cores 0–3",
        (
            "helius-laserstream-preconf-subagent",
            "strict-mainnet-clean-slate-subagent",
            "profit-guard-alt-deployer-subagent",
        ),
    ),
    (
        "deceptive-cto-counter-exploiter",
        "Cores 24–27",
        (
            "slot0-987pct-sybil-bundle-forensics-subagent",
            "fake-vs-genuine-cto-hair-trigger-subagent",
            "tarjan-scc-wash-and-kol-leadlag-subagent",
        ),
    ),
    (
        "slot0-845-migration-sniper-agent",
        "Cores 4–15",
        (
            "aperture-txstream-791us-lookahead-subagent",
            "pda-80pct-prewarm-845sol-hotpath-subagent",
            "curve-velocity-tip-6relay-fanout-subagent",
        ),
    ),
    (
        "eliza-rl-convergence-governor",
        "Cores 36–95",
        (
            "eliza-4primitive-multiwallet-trust-subagent",
            "melt-8model-tcn-transformer-auprc-subagent",
            "rl-weight-adapter-3tripwire-exit-subagent",
        ),
    ),
    (
        "dev-entity-tlsh-dlam-resolver",
        "Cores 36–47",
        (
            "cex-bridge-and-red-cohort-1012-subagent",
            "tlsh-ssdeep-dlam-keenhash-dna-subagent",
            "attention-gnn-pft-tier1-registry-subagent",
        ),
    ),
    (
        "agent-a-shred-pre-mint-listener",
        "Cores 0–3 & 4–15",
        (
            "pre-mint-peel-chain-8burner-subagent",
            "cabalspy-6ws-solbundler-sweep-subagent",
            "constant-product-65-78-squeeze-79-scaleout-subagent",
        ),
    ),
    (
        "agent-b-cabal-hunter-forensics",
        "Cores 24–27 & 36–47",
        (
            "six-gate-48h-wallet-arkham-rug-republic-subagent",
            "sol-native-skyeye-multiwallet-convergence-subagent",
            "token2022-roffett-permit-cabal-5hop-subagent",
        ),
    ),
    (
        "agent-c-jito-knapsack-judge",
        "Cores 4–23",
        (
            "stage1-conflict-set-tip-per-cu-subagent",
            "stage2-global-knapsack-70-30-edge-tip-subagent",
            "sub80ms-5region-jito-astralane-liljit-subagent",
        ),
    ),
    (
        "agent-d-artifact-bundle-validator",
        "Cores 32–35",
        (
            "sparse-bundle-slot-compactor-subagent",
            "jitodontfront-index0-signer-contiguity-subagent",
            "mission-control-privacy-mask-enforcer-subagent",
        ),
    ),
    (
        "zero-collateral-flash-architect",
        "Cores 4–15",
        (
            "kamino-v4-morpho-7primitive-router-subagent",
            "closed-form-delta-star-ito-lvr-subagent",
            "nostd-byte64-72-backpack-nonce-subagent",
        ),
    ),
    (
        "covert-migration-jit-predator",
        "Cores 16–31",
        (
            "forced-92to100-kamino-migration-sweep-subagent",
            "single-tick-4000x-jit-crosspool-hedge-subagent",
            "clmm-14b-phantom-virtual-reserve-spoof-subagent",
        ),
    ),
    (
        "mayhem-v4hook-multiply-synthesizer",
        "Cores 4–27 & 36–47",
        (
            "mayhem-ai-90quote-bayesian-hour24-burn-subagent",
            "parasitic-v4-afterswap-erc6909-base-subagent",
            "multiply-5x-squeeze-morpho-86lltv-liq-subagent",
        ),
    ),
    (
        "salmonella-fot-adversarial-shield",
        "Cores 0–3 & 32–47",
        (
            "fot-balance-delta-and-skim-desync-subagent",
            "salmonella-multi-origin-cu-profiler-subagent",
            "mica-doj-efficiency-compliance-tax-subagent",
        ),
    ),
    (
        "sanctum-lst-flash-arbitrageur",
        "Cores 4–15",
        (
            "sanctum-whale-lst-depeg-detector-subagent",
            "epoch-boundary-stake-nav-stepup-subagent",
            "kamino-sanctum-inf-atomic-unstake-subagent",
        ),
    ),
    (
        "jito-5tx-superbundle-combiner",
        "Cores 16–23",
        (
            "disjoint-writelock-5tx-packer-subagent",
            "jitodontfront-prefix-tip-aggregator-subagent",
            "knapsack-tip-per-cu-winrate-booster-subagent",
        ),
    ),
    (
        "meteora-dlmm-fee-surge-harvester",
        "Cores 24–31",
        (
            "dlmm-volatility-accumulator-fee-spike-subagent",
            "active-3bin-concentrated-lp-deployer-subagent",
            "continuous-pumpswap-delta-rebalancer-subagent",
        ),
    ),
    (
        "delta-neutral-funding-harvester",
        "Cores 32–35",
        (
            "drift-jupperps-hyperliquid-funding-scanner-subagent",
            "jitosol-spot-short-perp-cash-carry-subagent",
            "negative-funding-auto-unwind-guard-subagent",
        ),
    ),
    (
        "protocol-buyback-tax-crank-sniper",
        "Cores 4–15",
        (
            "creator-fee-buyback-vault-threshold-subagent",
            "token2022-withheld-tax-harvest-crank-subagent",
            "kamino-3step-crank-sandwich-executor-subagent",
        ),
    ),
    (
        "crosschain-whale-bridge-lookahead",
        "Cores 36–47",
        (
            "evm-source-ordercreated-whale-listener-subagent",
            "solana-3to12s-pre-solver-accumulator-subagent",
            "local-dln-mayan-auction-solver-subagent",
        ),
    ),
    (
        "multimodal-gpu-vision-ca-sniper",
        "Cores 48–71",
        (
            "qwen27b-port8002-screenshot-ca-ocr-subagent",
            "qwen3b-port8006-viral-narrative-classifier-subagent",
            "six-gate-phishing-honeypot-vision-guard-subagent",
        ),
    ),
    (
        "cex-polymarket-strike-latency-arb",
        "Cores 72–95",
        (
            "sub100ms-binance-coinbase-impulse-tracker-subagent",
            "black-scholes-digital-d2-probability-subagent",
            "polymarket-stale-clob-kelly-sweeper-subagent",
        ),
    ),
]


def test_roster_24_agents_and_72_subagents_exact_hierarchy() -> None:
    """Verifies the exact 32 Primary Agents and 96 Child Subagents in SOVEREIGN_AGENT_ROSTER."""
    assert TOTAL_PRIMARY_AGENTS == 32
    assert SUBAGENTS_PER_AGENT == 3
    assert TOTAL_SUBAGENTS == 96
    assert len(SOVEREIGN_AGENT_ROSTER) == 32
    assert len(PRIMARY_AGENT_IDS) == 32
    assert len(SUBAGENT_IDS) == 96
    assert len(set(PRIMARY_AGENT_IDS)) == 32
    assert len(set(SUBAGENT_IDS)) == 96

    for idx, (expected_agent_id, expected_cores, expected_subs) in enumerate(EXPECTED_HIERARCHY):
        agent_spec = SOVEREIGN_AGENT_ROSTER[idx]
        assert isinstance(agent_spec, PrimaryAgentSpec)
        assert agent_spec.agent_id == expected_agent_id
        assert agent_spec.index == idx + 1
        assert agent_spec.core_affinity == expected_cores
        assert agent_spec.subagent_ids == expected_subs
        assert len(agent_spec.subagents) == 3

        # Verify both sequence and mapping access on SOVEREIGN_AGENT_ROSTER
        assert expected_agent_id in SOVEREIGN_AGENT_ROSTER
        assert SOVEREIGN_AGENT_ROSTER[expected_agent_id] == agent_spec
        assert SOVEREIGN_AGENT_MAP[expected_agent_id] == agent_spec
        assert agent_spec["agent_id"] == expected_agent_id
        assert agent_spec["core_affinity"] == expected_cores

        for sub_idx, expected_sub_id in enumerate(expected_subs):
            sub_spec = agent_spec.subagents[sub_idx]
            assert isinstance(sub_spec, SubagentSpec)
            assert sub_spec.subagent_id == expected_sub_id
            assert sub_spec.parent_agent_id == expected_agent_id
            assert sub_spec["subagent_id"] == expected_sub_id
            assert expected_sub_id in agent_spec.subagents
            assert SOVEREIGN_SUBAGENT_MAP[expected_sub_id] == sub_spec


def test_dispatch_all_72_subagents_and_verify_domain_outputs(tmp_path: Path) -> None:
    """Dispatches tasks across all 32 primary agents and all 96 specialized child subagents."""
    state_file = tmp_path / "swarm_state.json"
    registry = SovereignAgentSwarmRegistry(state_path=state_file)

    for agent_id, _, subagent_ids in EXPECTED_HIERARCHY:
        # 1. Dispatch using only primary agent_id (auto-selects default subagent)
        primary_receipt = registry.dispatch_agent_task(agent_id, None, {"probe": True})
        assert primary_receipt["ok"] is True
        assert primary_receipt["status"] == "COMPLETED"
        assert primary_receipt["agent_id"] == agent_id
        assert primary_receipt["subagent_id"] == subagent_ids[0]
        assert primary_receipt["immutable_lock_verified"] is True

        # 2. Dispatch explicitly to each of the 3 child subagents
        for sub_id in subagent_ids:
            receipt = registry.dispatch_agent_task(
                agent_id=agent_id,
                subagent_id=sub_id,
                task_payload={"custom_test": True},
            )
            assert receipt["ok"] is True
            assert receipt["status"] == "COMPLETED"
            assert receipt["agent_id"] == agent_id
            assert receipt["subagent_id"] == sub_id
            assert receipt["within_sla"] is True
            assert isinstance(receipt["result"], dict)
            assert len(receipt["result"]) >= 3

    assert state_file.exists()
    summary = registry.get_telemetry_summary()
    assert summary["total_primary_agents"] == 32
    assert summary["total_subagents"] == 96
    # 32 primary-only dispatches + 96 explicit subagent dispatches = 128 total dispatches
    assert summary["total_dispatches"] == 128


def test_mev_flash_loan_and_sandwich_jit_calculations(tmp_path: Path) -> None:
    """Tests Agents 1–3: MEV Hot-Path, Engine A Flash-Loan Arb, and Engine B/C Sandwich/JIT."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "mev_state.json")

    # Agent 1: mev-hotpath-architect
    r_v0 = registry.dispatch_agent_task(
        "mev-hotpath-architect",
        "v0-packet-compactor-96acct",
        {"requested_accounts": 92, "hops": 4, "agave_45_enabled": True},
    )
    assert r_v0["result"]["max_versioned_tx_accounts"] == 96
    assert r_v0["result"]["compacted_accounts"] == 92
    assert r_v0["result"]["serialized_wire_bytes"] <= 1150
    assert r_v0["result"]["jitodontfront_injected"] is True

    r_bam = registry.dispatch_agent_task(
        "mev-hotpath-architect",
        "bam-25ms-tick-aligner",
        {"region_rtt_ms": 0.80, "slot_elapsed_ms": 27.0, "region": "ny"},
    )
    assert r_bam["result"]["alpenglow_slot_duration_ms"] == 200.0
    assert r_bam["result"]["bam_tick_cadence_ms"] == 25.0
    assert r_bam["result"]["current_tick_index"] == 1
    assert r_bam["result"]["next_tick_boundary_ms"] == 50.0

    r_tip = registry.dispatch_agent_task(
        "mev-hotpath-architect",
        "dynamic-contention-tip-scaler",
        {"expected_ev_sol": 0.80, "contention_score": 0.25, "dex_fees_sol": 0.002},
    )
    assert r_tip["result"]["passes_rule22_ev_gate"] is True

    # Agent 2: flash-loan-arb-specialist
    r_2hop = registry.dispatch_agent_task(
        "flash-loan-arb-specialist",
        "victim-2hop-backrun-subagent",
        {"pool_a_reserve_sol": 1200.0, "pool_b_reserve_sol": 1400.0, "dislocation_bps": 180.0},
    )
    assert r_2hop["result"]["net_profit_sol"] > 0.0
    assert r_2hop["result"]["profit_guard_enforced"] is True

    r_fstar = registry.dispatch_agent_task(
        "flash-loan-arb-specialist",
        "bin-cliff-fstar-lst-5000sol-subagent",
        {"max_borrow_sol": 5000.0, "lst_pair": "SOL/jitoSOL", "depeg_bps": 65.0},
    )
    assert r_fstar["result"]["f_star_optimal_borrow_sol"] <= 5000.0
    assert r_fstar["result"]["kamino_marginfi_zero_fee"] is True

    # Agent 3: sandwich-jit-predator
    r_jit = registry.dispatch_agent_task(
        "sandwich-jit-predator",
        "twap-clip-and-jit-dlmm-subagent",
        {"clip_interval_sec": 30.0, "realized_profit_sol": 45.0},
    )
    assert r_jit["result"]["engine_c_execution_mode"] == "PAPER_SIM"
    r_jit_live = registry.dispatch_agent_task(
        "sandwich-jit-predator",
        "twap-clip-and-jit-dlmm-subagent",
        {"clip_interval_sec": 30.0, "realized_profit_sol": 115.0},
    )
    assert r_jit_live["result"]["engine_c_execution_mode"] == "LIVE_MAINNET"


def test_shadow_burner_trail_and_apex_predator_calculations(tmp_path: Path) -> None:
    """Tests Agents 4–7: Alpha Shadow, Burner DAG, Trail-Win Shields, and Apex Predator."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "alpha_state.json")

    # Agent 4: Multi-shark consensus 2.0x boost
    r_quorum = registry.dispatch_agent_task(
        "alpha-shadow-quant",
        "multi-shark-consensus-2x-subagent",
        {
            "shark_wallets": ["Shark1", "Shark2", "Shark3"],
            "slot_span": 8,
            "shared_3hop_funder": False,
        },
    )
    assert r_quorum["result"]["consensus_2x_triggered"] is True
    assert r_quorum["result"]["sizing_multiplier"] == pytest.approx(2.0)

    # Agent 5: Burner DAG 3-hop attribution & GTG-7784 Sybil blocker
    r_hop = registry.dispatch_agent_task(
        "burner-dag-cluster-tracker",
        "hop1-hop2-hop3-root-attributor",
        {"hop_distance": 1},
    )
    assert r_hop["result"]["attribution_confidence"] == pytest.approx(0.90)

    r_sybil = registry.dispatch_agent_task(
        "burner-dag-cluster-tracker",
        "gtg7784-sybil-transfer-tree-crawler",
        {"cabal_bundled_supply_pct": 19.2},
    )
    assert r_sybil["result"]["blocked"] is True
    assert r_sybil["result"]["verdict"] == "CABAL_BUNDLED_SUPPLY_TRAP"

    # Agent 6: Horizon 1 99.5% squeeze exit & Stage 3 blow-off ratchet
    r_h1 = registry.dispatch_agent_task(
        "trail-win-shield-guardian",
        "h1-88-995-bonding-squeeze-subagent",
        {"bonding_curve_progress_pct": 99.6},
    )
    assert r_h1["result"]["recommended_action"] == "MANDATORY_PRE_FREEZE_EXIT_99_5PCT"

    r_trail = registry.dispatch_agent_task(
        "trail-win-shield-guardian",
        "h2-reclaim-h3-45m-moonbag-subagent",
        {"unrealized_multiple": 18.5},
    )
    assert r_trail["result"]["active_trail_stage"] == 3
    assert r_trail["result"]["chandelier_trail_below_hwm_pct"] == pytest.approx(6.5)

    # Agent 7: Apex Predator Token-2022 hook & ATA rent reclaim
    r_t22 = registry.dispatch_agent_task(
        "apex-predator-7module-hunter",
        "token2022-tax-and-ata-rent-subagent",
        {"transfer_fee_bps": 0, "unauthorized_transfer_hook": True},
    )
    assert r_t22["result"]["blocked_by_token2022_guard"] is True
    assert r_t22["result"]["close_account_ata_reclaim_lamports"] == 2_039_280


def test_arxiv_oss_gepa_gui_and_sre_calculations(tmp_path: Path) -> None:
    """Tests Agents 8–12: arXiv Sentinel, 10 OSS Repos, GEPA Swarm, GUI Cockpit, and Mainnet SRE."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "phase9_state.json")

    # Agent 8: arXiv:2602.13480 MELT 122-feature & arXiv:2608.20271 5m rug kill-switch
    r_melt = registry.dispatch_agent_task(
        "arxiv-quant-defense-sentinel",
        "arxiv-2602-13480-melt-122feat-subagent",
        {"min_price_ratio": 0.85, "pred_score": 0.14, "top10_share_delta_pp": 5.2},
    )
    assert r_melt["result"]["feature_vector_dim"] == 122
    assert r_melt["result"]["strategy5_smart_money_allowed"] is True
    assert r_melt["result"]["benchmark_loss_reduction_pct"] == pytest.approx(56.1)

    r_rug = registry.dispatch_agent_task(
        "arxiv-quant-defense-sentinel",
        "arxiv-2608-20271-5m-rug-killswitch-subagent",
        {"mdd_t": -0.35, "idle_t_sec": 40.0, "window_sec": 300.0},
    )
    assert r_rug["result"]["rug_t_indicator"] == 1
    assert r_rug["result"]["kill_switch_triggered"] is True

    # Agent 9: PumpSwap 300-byte account extension & 10 OSS repos
    r_pump = registry.dispatch_agent_task(
        "pump-dbc-oss-integrator",
        "pumpswap-extend300-nirholas-curve-subagent",
        {"virtual_sol_reserves": 80.0, "virtual_token_reserves": 350_000_000.0},
    )
    assert r_pump["result"]["extend_account_bytes"] == 300
    assert r_pump["result"]["bonding_progress_pct"] > 85.0

    r_dbc = registry.dispatch_agent_task(
        "pump-dbc-oss-integrator",
        "pumpfun-rs-bonk-meteora-dbc-subagent",
        {"launchpad": "METEORA_DBC"},
    )
    assert r_dbc["result"]["oss_repos_integrated_count"] == 10

    # Agent 10: GEPA 60-trace evolution & Vision pHash vampire clone detection
    r_vision = registry.dispatch_agent_task(
        "gepa-llm-swarm-evolver",
        "lane2-qwen-vision-ocr-subagent",
        {"nearest_phash_distance": 2},
    )
    assert r_vision["result"]["verdict"] == "VAMPIRE_CLONE_SKIP"

    r_gepa = registry.dispatch_agent_task(
        "gepa-llm-swarm-evolver",
        "lane3-deepseek-gepa-60trace-subagent",
        {"challenger_tokens": 240, "ev_improvement_pct": 15.2, "challenger_honeypot_hits": 0},
    )
    assert r_gepa["result"]["total_stratified_traces"] == 60
    assert r_gepa["result"]["ready_for_promotion"] is True
    assert r_gepa["result"]["immutable_lock_verified"] is True

    # Agent 11 & 12: GUI IPC router & Mainnet Profit-Guard Reserve Lockbox sweep
    r_ipc = registry.dispatch_agent_task(
        "gui-cockpit-engineer",
        "ipc-sub025ms-command-router-subagent",
        {"routed_command": "RUN_SWARM_AGENT_AUDIT"},
    )
    assert r_ipc["result"]["within_sub025ms_sla"] is True

    r_sre = registry.dispatch_agent_task(
        "mainnet-infra-sre",
        "profit-guard-alt-deployer-subagent",
        {"hot_wallet_balance_sol": 72.0},
    )
    assert r_sre["result"]["reserve_lockbox_sweep_triggered"] is True
    assert r_sre["result"]["reserve_lockbox_sweep_amount_sol"] == pytest.approx(50.0)


def test_phase10_deceptive_sniper_eliza_and_entity_resolver_calculations(tmp_path: Path) -> None:
    """Tests Agents 13–16: Deceptive CTO Counter-Exploiter, Slot-0 & 84.5 SOL Sniper, Eliza RL Governor, and Dev Entity Resolver."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "phase10_state.json")

    # Agent 13: Deceptive CTO Counter-Exploiter
    r_sybil = registry.dispatch_agent_task(
        "deceptive-cto-counter-exploiter",
        "slot0-987pct-sybil-bundle-forensics-subagent",
        {"bundled_supply_pct": 38.0, "sybil_wallet_count": 22},
    )
    assert r_sybil["result"]["empirical_adversarial_bundle_rate_pct"] == pytest.approx(98.7)
    assert r_sybil["result"]["hard_veto_triggered"] is True

    r_cto = registry.dispatch_agent_task(
        "deceptive-cto-counter-exploiter",
        "fake-vs-genuine-cto-hair-trigger-subagent",
        {"supply_concentration_pct": 8.5, "stealth_reaccumulation_pct": 0.2, "sell_pct_of_pool_per_slot": 2.6},
    )
    assert r_cto["result"]["cto_classification"] == "GENUINE_ORGANIC_CTO"
    assert r_cto["result"]["hair_trigger_exit_fired"] is True

    # Agent 14: Slot-0 & 84.5 SOL Migration Sniper
    r_sniper = registry.dispatch_agent_task(
        "slot0-845-migration-sniper-agent",
        "pda-80pct-prewarm-845sol-hotpath-subagent",
        {"real_sol_reserves": 84.65, "pda_prewarmed": True},
    )
    assert r_sniper["result"]["stage_b_hotpath_fired"] is True

    # Agent 15: Eliza RL Convergence Governor
    r_eliza = registry.dispatch_agent_task(
        "eliza-rl-convergence-governor",
        "eliza-4primitive-multiwallet-trust-subagent",
        {"converging_wallets": 5, "base_trust_score": 0.50},
    )
    assert r_eliza["result"]["convergence_multiplier"] == pytest.approx(1.85)

    # Agent 16: Persistent Developer Entity Resolver
    r_entity = registry.dispatch_agent_task(
        "dev-entity-tlsh-dlam-resolver",
        "attention-gnn-pft-tier1-registry-subagent",
        {"prior_graduations": 3, "tier1_confidence": 0.94},
    )
    assert r_entity["result"]["selected_execution_route"] == "PATH_A_SLOT0_GENESIS_SNIPE"


def test_phase11_alpha_exploit_4agents_calculations(tmp_path: Path) -> None:
    """Tests Agents 17–20: Agent A Pre-Mint Peel-Chain, Agent B 6-Gate Cabal Hunter, Agent C Jito Knapsack Judge, and Agent D Bundle Validator."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "phase11_state.json")

    # Agent 17: Agent A — Shred Pre-Mint Peel-Chain & Curve Squeeze
    r_peel = registry.dispatch_agent_task(
        "agent-a-shred-pre-mint-listener",
        "pre-mint-peel-chain-8burner-subagent",
        {"fresh_burner_count": 10, "window_slots": 14},
    )
    assert r_peel["result"]["signal_type"] == "PRE_LAUNCH_DEV_SIGNAL"
    assert r_peel["result"]["pre_arm_execution_action"] == "PRE_ARM_BLOCK1_BASE_CURVE_SNIPE"

    r_squeeze = registry.dispatch_agent_task(
        "agent-a-shred-pre-mint-listener",
        "constant-product-65-78-squeeze-79-scaleout-subagent",
        {"curve_completion_pct": 72.0, "real_sol_reserves": 61.2},
    )
    assert r_squeeze["result"]["recommended_action"] == "ENTER_PRE_GRADUATION_CURVE_SQUEEZE"

    # Agent 18: Agent B — 6-Gate Cabal Hunter & SkyEye SOL-Native Convergence
    r_6gate = registry.dispatch_agent_task(
        "agent-b-cabal-hunter-forensics",
        "six-gate-48h-wallet-arkham-rug-republic-subagent",
        {"win_rate_pct": 65.0, "realized_pnl_30d_usd": 92000.0, "rug_republic_flagged": False},
    )
    assert r_6gate["result"]["admitted_to_gem_finder_registry"] is True

    r_skyeye = registry.dispatch_agent_task(
        "agent-b-cabal-hunter-forensics",
        "sol-native-skyeye-multiwallet-convergence-subagent",
        {"distinct_audited_wallets": 3, "market_cap_usd": 29500.0},
    )
    assert r_skyeye["result"]["action"] == "EXECUTE_SOL_NATIVE_MULTIWALLET_CONVERGENCE"
    assert r_skyeye["result"]["zero_usdc_bridge_hops"] is True

    # Agent 19: Agent C — Jito Two-Stage Knapsack Judge & <80ms 5-Region Submitter
    r_knapsack = registry.dispatch_agent_task(
        "agent-c-jito-knapsack-judge",
        "stage2-global-knapsack-70-30-edge-tip-subagent",
        {"expected_edge_lamports": 10_000_000, "regime": "STANDARD_70_30"},
    )
    assert r_knapsack["result"]["tip_share_ratio"] == pytest.approx(0.30)
    assert r_knapsack["result"]["optimal_jito_tip_lamports"] == 3_000_000

    # Agent 20: Agent D — Sparse Bundle Compactor, jitodontfront Index-0 & Privacy Mask
    r_dontfront = registry.dispatch_agent_task(
        "agent-d-artifact-bundle-validator",
        "jitodontfront-index0-signer-contiguity-subagent",
        {},
    )
    assert r_dontfront["result"]["jitodontfront_at_index_0_readonly_nonsigner"] is True
    assert r_dontfront["result"]["structural_validation_passed"] is True


def test_phase12_zero_collateral_flash_and_mev_4agents_calculations(tmp_path: Path) -> None:
    """Tests Agents 21–24: Zero-Collateral Flash Architect, Covert Migration & JIT Predator, Mayhem V4-Hook & Multiply Synthesizer, and Salmonella/FoT Adversarial Shield."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "phase12_state.json")

    # Agent 21: Zero-Collateral Flash Architect
    r_flash = registry.dispatch_agent_task(
        "zero-collateral-flash-architect",
        "kamino-v4-morpho-7primitive-router-subagent",
        {"chain": "SOLANA", "principal": 3000.0},
    )
    assert r_flash["result"]["selected_flash_source"] == "KAMINO_KLEND"
    assert r_flash["result"]["fee_bps"] == 0

    r_lvr = registry.dispatch_agent_task(
        "zero-collateral-flash-architect",
        "closed-form-delta-star-ito-lvr-subagent",
        {"delta_alpha_star": 112.5, "sigma_annual": 0.80},
    )
    assert r_lvr["result"]["closed_form_newton_iterations"] == 0
    assert r_lvr["result"]["ito_lvr_instantaneous_rate"] == pytest.approx(0.08)

    # Agent 22: Covert Migration & JIT Predator
    r_sweep = registry.dispatch_agent_task(
        "covert-migration-jit-predator",
        "forced-92to100-kamino-migration-sweep-subagent",
        {"curve_completion_pct": 95.8, "migration_authority": "may16 SpoofAuthority111111111"},
    )
    assert r_sweep["result"]["may16_authority_hard_blocked"] is True
    assert r_sweep["result"]["forced_kamino_flash_graduation_sweep"] is False

    r_spoof = registry.dispatch_agent_task(
        "covert-migration-jit-predator",
        "clmm-14b-phantom-virtual-reserve-spoof-subagent",
        {"implied_virtual_reserve_usd": 14_200_000_000.0, "real_vault_balance_usd": 18.50},
    )
    assert r_spoof["result"]["phantom_reserve_spoof_blocked"] is True

    # Agent 23: Mayhem V4-Hook & Multiply Synthesizer
    r_mayhem = registry.dispatch_agent_task(
        "mayhem-v4hook-multiply-synthesizer",
        "mayhem-ai-90quote-bayesian-hour24-burn-subagent",
        {"quote_predictability_confidence": 0.94, "minutes_to_hour24_burn": 8.0},
    )
    assert r_mayhem["result"]["triangular_backrun_armed"] is True
    assert r_mayhem["result"]["hour24_burn_frontrun_armed"] is True

    # Agent 24: Salmonella, FoT & Adversarial Shield
    r_salm = registry.dispatch_agent_task(
        "salmonella-fot-adversarial-shield",
        "salmonella-multi-origin-cu-profiler-subagent",
        {"simulated_cu": 310_000, "dual_origin_divergence_pct": 42.5},
    )
    assert r_salm["result"]["dynamic_cu_limit_1_12x"] == 347_200
    assert r_salm["result"]["static_200k_cu_trap_avoided"] is True
    assert r_salm["result"]["salmonella_trap_blocked"] is True


def test_phase13_profit_expansion_8agents_calculations(tmp_path: Path) -> None:
    """Tests Agents 25–32: Sanctum 8-LST Flash Arb, Jito 5-TX SuperBundle, Meteora DLMM Surge,
    Delta-Neutral Funding, Buyback/Token-2022 Crank, Cross-Chain Bridge Lookahead,
    Multimodal GPU Vision CA Sniper, and CEX-to-Polymarket Strike Latency Arb.
    """
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "phase13_state.json")

    # Agent 25: Sanctum 8-LST Flash Arbitrageur
    r_lst = registry.dispatch_agent_task(
        "sanctum-lst-flash-arbitrageur",
        "sanctum-whale-lst-depeg-detector-subagent",
        {"lst_symbol": "mSOL", "true_nav_sol_per_lst": 1.2500, "amm_spot_sol_per_lst": 1.2440},
    )
    assert r_lst["result"]["whale_depeg_actionable"] is True
    assert r_lst["result"]["depeg_discount_bps"] > 40.0

    # Agent 26: Jito 5-TX SuperBundle Combiner
    r_sb = registry.dispatch_agent_task(
        "jito-5tx-superbundle-combiner",
        "disjoint-writelock-5tx-packer-subagent",
        {"candidate_tx_count": 7, "packed_disjoint_tx_count": 5, "total_bundle_cu": 1_650_000},
    )
    assert r_sb["result"]["packed_disjoint_tx_count"] == 5
    assert r_sb["result"]["within_5tx_jito_limit"] is True

    # Agent 27: Meteora DLMM Dynamic Fee-Surge Harvester
    r_dlmm = registry.dispatch_agent_task(
        "meteora-dlmm-fee-surge-harvester",
        "dlmm-volatility-accumulator-fee-spike-subagent",
        {"base_fee_bps": 20.0, "variable_fee_bps": 435.0},
    )
    assert r_dlmm["result"]["total_dynamic_fee_bps"] == pytest.approx(455.0)
    assert r_dlmm["result"]["surge_harvest_active"] is True

    # Agent 28: Delta-Neutral Perp Funding Harvester
    r_fund = registry.dispatch_agent_task(
        "delta-neutral-funding-harvester",
        "jitosol-spot-short-perp-cash-carry-subagent",
        {"notional_usd": 150_000.0, "funding_apr_pct": 74.46, "lst_staking_apr_pct": 8.10},
    )
    assert r_fund["result"]["net_directional_delta_pct"] == pytest.approx(0.0)
    assert r_fund["result"]["combined_total_apr_pct"] == pytest.approx(82.56)

    # Agent 29: Protocol Buyback & Token-2022 Tax Crank Sniper
    r_crank = registry.dispatch_agent_task(
        "protocol-buyback-tax-crank-sniper",
        "creator-fee-buyback-vault-threshold-subagent",
        {"accumulated_vault_sol": 185.0, "crank_threshold_sol": 100.0},
    )
    assert r_crank["result"]["crank_ready"] is True

    # Agent 30: Cross-Chain Whale Bridge Lookahead
    r_bridge = registry.dispatch_agent_task(
        "crosschain-whale-bridge-lookahead",
        "evm-source-ordercreated-whale-listener-subagent",
        {"source_chain": "BASE", "source_amount_usd": 185_000.0, "estimated_settlement_seconds": 4.5},
    )
    assert r_bridge["result"]["whale_intent_actionable"] is True

    # Agent 31: Multimodal GPU Vision Social CA Sniper
    r_vis = registry.dispatch_agent_task(
        "multimodal-gpu-vision-ca-sniper",
        "qwen27b-port8002-screenshot-ca-ocr-subagent",
        {"ocr_confidence": 0.97, "ocr_latency_ms": 118.4},
    )
    assert r_vis["result"]["valid_ca_extracted"] is True

    # Agent 32: CEX-to-Polymarket Binary Strike Latency Arbitrageur
    r_poly = registry.dispatch_agent_task(
        "cex-polymarket-strike-latency-arb",
        "polymarket-stale-clob-kelly-sweeper-subagent",
        {"fair_probability": 0.784, "stale_clob_ask": 0.540},
    )
    assert r_poly["result"]["fok_sweep_profitable"] is True
    assert r_poly["result"]["quarter_kelly_fraction"] > 0.10


def test_full_swarm_health_check_and_immutable_safety_lock(tmp_path: Path) -> None:
    """Verifies run_full_swarm_health_check() and Rule 3 immutable SHA-256 protection."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "health_state.json")
    health = registry.run_full_swarm_health_check()

    assert health["ok"] is True
    assert health["healthy"] is True
    assert health["status"] == "ALL_32_AGENTS_96_SUBAGENTS_HEALTHY"
    assert health["total_primary_agents"] == 32
    assert health["online_primary_agents"] == 32
    assert health["total_subagents"] == 96
    assert health["online_subagents"] == 96
    assert health["immutable_lock_verified"] is True
    assert health["core_partition_verified"] is True
    assert health["total_threadripper_cores_covered"] == 96
    assert len(health["arxiv_papers_verified"]) == len(FOUNDATIONAL_ARXIV_PAPERS)
    assert len(health["oss_repos_verified"]) == len(OSS_10_GITHUB_REPOS)

    for rel_path in IMMUTABLE_SAFETY_FILES:
        assert rel_path in health["immutable_file_digests"]
        assert len(health["immutable_file_digests"][rel_path]) == 64

    # Attempting to modify protected files must raise PermissionError
    with pytest.raises(PermissionError, match="IMMUTABLE_SAFETY_LOCK_VIOLATION"):
        registry.dispatch_agent_task(
            "gepa-llm-swarm-evolver",
            "lane3-deepseek-gepa-60trace-subagent",
            {"target_files_to_modify": ["src/risk/risk_watchdog.py"]},
        )

    with pytest.raises(PermissionError, match="IMMUTABLE_SAFETY_LOCK_VIOLATION"):
        registry.verify_immutable_safety_lock(
            ["anchor_profit_guard/programs/profit_guard/src/lib.rs"]
        )


def test_flexible_resolution_error_handling_and_singleton(tmp_path: Path) -> None:
    """Verifies flexible subagent resolution, clean ValueError handling, and singleton."""
    registry = SovereignAgentSwarmRegistry(state_path=tmp_path / "err_state.json")

    # Passing a subagent_id as the first argument auto-resolves its parent primary agent
    direct_sub_receipt = registry.dispatch_agent_task(
        "arxiv-2608-20271-5m-rug-killswitch-subagent",
        None,
        {"mdd_t": -0.05, "idle_t_sec": 12.0},
    )
    assert direct_sub_receipt["agent_id"] == "arxiv-quant-defense-sentinel"
    assert direct_sub_receipt["subagent_id"] == "arxiv-2608-20271-5m-rug-killswitch-subagent"

    with pytest.raises(ValueError, match="Unknown primary agent_id"):
        registry.dispatch_agent_task("non-existent-agent", None, {})

    with pytest.raises(ValueError, match="Unknown subagent_id"):
        registry.dispatch_agent_task("mev-hotpath-architect", "non-existent-subagent", {})

    with pytest.raises(ValueError, match="belongs to"):
        registry.dispatch_agent_task(
            "mev-hotpath-architect",
            "lane1-hermes-gatekeeper-subagent",
            {},
        )

    singleton = get_sovereign_agent_swarm_registry()
    assert isinstance(singleton, SovereignAgentSwarmRegistry)
    assert len(singleton.roster) == 32


@pytest.mark.asyncio
async def test_titan_ipc_daemon_phase10_to_12_actions_and_24_agent_telemetry() -> None:
    """Verifies TitanIPCDaemon dispatches all Phase 10, 11, 12 & 13 actions and 32-Agent / 96-Subagent telemetry."""
    from src.ipc.titan_ipc_daemon import TitanIPCDaemon

    daemon = TitanIPCDaemon()
    frame = daemon.build_telemetry_frame()
    assert "deceptive_counter_exploiter" in frame
    assert "slot0_845_sniper" in frame
    assert "eliza_rl_engine" in frame
    assert "dev_entity_resolver" in frame
    assert "pre_mint_listener" in frame
    assert "alpha_exploit_forensics" in frame
    assert "jito_knapsack_judge" in frame
    assert "flash_primitives_engine" in frame
    assert "covert_boundary_guard" in frame
    assert "nextgen_mayhem_engine" in frame
    assert "salmonella_adversarial_shield" in frame
    assert "sanctum_superbundle_engine" in frame
    assert "meteora_funding_harvester" in frame
    assert "crank_bridge_engine" in frame
    assert "vision_polymarket_sniper" in frame
    assert frame["agent_swarm"]["total_primary_agents"] == 32
    assert frame["agent_swarm"]["total_subagents"] == 96
    assert len(frame["agent_swarm"]["agents"]) == 32

    for action in (
        "RUN_DECEPTIVE_COUNTER_EXPLOIT_SUITE",
        "RUN_SLOT0_845_PRE_MIGRATION_SNIPER",
        "RUN_ELIZA_RL_CONVERGENCE_SUITE",
        "RUN_DEV_ENTITY_RESOLUTION_SUITE",
        "RUN_PRE_MINT_PEEL_CHAIN_LISTENER",
        "RUN_6GATE_CABAL_HUNTER_FORENSICS",
        "RUN_JITO_KNAPSACK_DONTFRONT_JUDGE",
        "RUN_ZERO_COLLATERAL_FLASH_PRIMITIVES",
        "RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE",
        "RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE",
        "RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD",
        "RUN_SANCTUM_LST_FLASH_ARB",
        "RUN_SANCTUM_LST_SUPERBUNDLE_SUITE",
        "RUN_JITO_5TX_SUPERBUNDLE_COMBINER",
        "RUN_METEORA_DLMM_FEE_SURGE_HARVESTER",
        "RUN_METEORA_DLMM_FUNDING_HARVESTER",
        "RUN_DELTA_NEUTRAL_FUNDING_HARVESTER",
        "RUN_PROTOCOL_BUYBACK_TAX_CRANK_SNIPER",
        "RUN_CRANK_BUYBACK_BRIDGE_LOOKAHEAD",
        "RUN_CROSSCHAIN_WHALE_BRIDGE_LOOKAHEAD",
        "RUN_MULTIMODAL_GPU_VISION_CA_SNIPER",
        "RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER",
        "RUN_CEX_POLYMARKET_STRIKE_LATENCY_ARB",
        "RUN_ALL_8_PROFIT_ENGINES",
    ):
        resp = await daemon.handle_ipc_payload({"action": action})
        assert resp["ok"] is True
        assert resp["action"] == action
        assert "unhandled_action" not in resp["data"]
        assert "message" in resp["data"]

    swarm_resp = await daemon.handle_ipc_payload(
        {"action": "DISPATCH_SOVEREIGN_SUBAGENT", "agent_id": "ALL"}
    )
    assert swarm_resp["ok"] is True
    assert swarm_resp["data"]["total_primary_agents"] == 32
    assert swarm_resp["data"]["total_subagents"] == 96
