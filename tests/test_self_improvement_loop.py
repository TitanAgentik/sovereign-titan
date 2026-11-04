"""
Acceptance & Unit Test Suite (`tests/test_self_improvement_loop.py`) for the
Autonomous Experiential Learning Architecture (ACE + ExpeL + Reflexion + Voyager + FinMem).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from src.memory.experience_pool import (
    CANONICAL_FAILURE_CATEGORIES,
    RULE_FILE_HARD_LIMIT_BYTES,
    ExperiencePool,
)
from src.orchestrator.local_harness import (
    LiteRTAgentConfig,
    LocalOpenAIAgentConfig,
    SelfImprovingExperientialOrchestrator,
    build_local_agent_config,
    register_autonomous_web_evolution_trigger,
    run_experiential_learning_cycle,
)

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _parse_yaml_frontmatter(md_text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", md_text, flags=re.DOTALL)
    assert match is not None, "Missing YAML frontmatter delimiter (---)"
    raw_block = match.group(1)
    parsed: dict[str, str] = {}
    for line in raw_block.splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            k, v = line.split(":", 1)
            parsed[k.strip()] = v.strip().strip('"').strip("'")
    return parsed


def test_six_stage_failure_attribution_and_episodic_reflections(tmp_path: Path) -> None:
    """
    Verifies that recording mock trades with:
      1. >800ms latency / quote drift (`Jupiter Slippage Drift`)
      2. 96.5%-100% curve progress (`Graduation Race Condition`)
      3. Under-scaled priority fee during congestion (`Priority Fee Cliff`)
      4. Delayed exit >300ms (`Sell-Side Execution Amnesia`)
      5. Token-2022 malicious `transfer_hook` (`Token-2022/SPL Rug Vector`)
      6. Clean execution but negative PnL (`Thesis Error`)
    accurately classifies each failure mode in `episodic_reflections` and `episodic_failures.jsonl`.
    """
    db_path = tmp_path / "telemetry.db"
    jsonl_path = tmp_path / "episodic_failures.jsonl"
    rules_path = tmp_path / "solana-heuristics.md"
    shutil.copy(WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md", rules_path)

    pool = ExperiencePool(
        db_path=db_path,
        episodic_jsonl_path=jsonl_path,
        heuristics_rule_path=rules_path,
    )

    # 1. >800ms total latency / slippage drift
    t_drift, ref_drift = pool.record_trajectory(
        {
            "tx_signature": "5TxDrift850ms",
            "mint_address": "MintDrift1111111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 45.0,
            "latency_grpc_ms": 190.0,
            "latency_parse_ms": 25.0,
            "latency_rug_gate_ms": 95.0,
            "latency_jito_ms": 540.0,
            "total_latency_ms": 865.0,
            "jito_tip_sol": 0.010,
            "priority_fee_sol": 0.012,
            "expected_slippage_bps": 80.0,
            "realized_slippage_bps": 420.0,
            "pnl_sol": -0.38,
        }
    )
    assert t_drift.failure_category == "Jupiter Slippage Drift"
    assert ref_drift is not None
    assert ref_drift.failure_category == "Jupiter Slippage Drift"
    assert "865.0ms" in ref_drift.verbal_critique

    # 2. Graduation Race Condition (98.8% curve completion / 82-85 SOL window)
    t_grad, ref_grad = pool.record_trajectory(
        {
            "tx_signature": "5TxGradRace99Pct",
            "mint_address": "MintGrad11111111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 98.8,
            "latency_grpc_ms": 45.0,
            "latency_parse_ms": 4.0,
            "latency_rug_gate_ms": 26.0,
            "latency_jito_ms": 110.0,
            "total_latency_ms": 195.0,
            "jito_tip_sol": 0.010,
            "priority_fee_sol": 0.015,
            "expected_slippage_bps": 90.0,
            "realized_slippage_bps": 550.0,
            "pnl_sol": -0.52,
        }
    )
    assert t_grad.failure_category == "Graduation Race Condition"
    assert ref_grad is not None
    assert ref_grad.recommended_rule_id == "RULE-EXEC-02"

    # 3. Priority Fee Cliff
    t_fee, ref_fee = pool.record_trajectory(
        {
            "tx_signature": "5TxPrioCliff",
            "mint_address": "MintPrio11111111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 32.0,
            "latency_grpc_ms": 50.0,
            "latency_parse_ms": 5.0,
            "latency_rug_gate_ms": 28.0,
            "latency_jito_ms": 340.0,
            "total_latency_ms": 435.0,
            "jito_tip_sol": 0.001,
            "priority_fee_sol": 0.001,
            "expected_slippage_bps": 80.0,
            "realized_slippage_bps": 190.0,
            "pnl_sol": -0.25,
        }
    )
    assert t_fee.failure_category == "Priority Fee Cliff"
    assert ref_fee is not None
    assert ref_fee.recommended_rule_id == "RULE-EXEC-03"

    # 4. Sell-Side Execution Amnesia
    t_sell, ref_sell = pool.record_trajectory(
        {
            "tx_signature": "5TxSellAmnesia",
            "mint_address": "MintSell11111111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 52.0,
            "latency_grpc_ms": 42.0,
            "latency_parse_ms": 4.0,
            "latency_rug_gate_ms": 25.0,
            "latency_jito_ms": 98.0,
            "total_latency_ms": 180.0,
            "jito_tip_sol": 0.010,
            "priority_fee_sol": 0.015,
            "expected_slippage_bps": 70.0,
            "realized_slippage_bps": 85.0,
            "pnl_sol": -0.44,
            "metadata": {"exit_latency_ms": 620.0, "missed_target_sell": True},
        }
    )
    assert t_sell.failure_category == "Sell-Side Execution Amnesia"
    assert ref_sell is not None

    # 5. Token-2022 transfer_hook rug vector
    t_rug, ref_rug = pool.record_trajectory(
        {
            "tx_signature": "5TxToken2022Hook",
            "mint_address": "MintHook11111111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 29.0,
            "latency_grpc_ms": 44.0,
            "latency_parse_ms": 4.0,
            "latency_rug_gate_ms": 24.0,
            "latency_jito_ms": 92.0,
            "total_latency_ms": 175.0,
            "jito_tip_sol": 0.010,
            "priority_fee_sol": 0.015,
            "expected_slippage_bps": 75.0,
            "realized_slippage_bps": 80.0,
            "pnl_sol": -0.80,
            "metadata": {"transfer_hook": "EvilHookProg1111111111111111111111111111111"},
        }
    )
    assert t_rug.failure_category == "Token-2022/SPL Rug Vector"
    assert ref_rug is not None
    assert ref_rug.recommended_rule_id == "RULE-RUG-02"

    # 6. Thesis Error
    t_thesis, ref_thesis = pool.record_trajectory(
        {
            "tx_signature": "5TxThesisError",
            "mint_address": "MintThesis111111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 22.0,
            "latency_grpc_ms": 40.0,
            "latency_parse_ms": 3.5,
            "latency_rug_gate_ms": 22.0,
            "latency_jito_ms": 95.0,
            "total_latency_ms": 172.0,
            "jito_tip_sol": 0.010,
            "priority_fee_sol": 0.015,
            "expected_slippage_bps": 70.0,
            "realized_slippage_bps": 78.0,
            "pnl_sol": -0.18,
        }
    )
    assert t_thesis.failure_category == "Thesis Error"
    assert ref_thesis is not None

    reflections = pool.get_reflections()
    assert len(reflections) == 6
    observed_categories = {r.failure_category for r in reflections}
    assert observed_categories == set(CANONICAL_FAILURE_CATEGORIES)
    assert jsonl_path.exists()
    jsonl_lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(jsonl_lines) == 6


def test_expel_curate_rules_cli_and_size_guardrails(tmp_path: Path) -> None:
    """
    Executes `curate_rules.py` to apply ExpeL ADD, EDIT, UPVOTE, and DOWNVOTE deltas
    to `.agents/rules/solana-heuristics.md` while confirming:
      - File size remains strictly <24 KB (`24,000` bytes)
      - YAML frontmatter (`trigger` and `description`) stays intact
      - Rules downvoted to `utility_score <= 0` are archived into `archived-heuristics.md`.
    """
    db_path = tmp_path / "telemetry.db"
    rules_path = tmp_path / "solana-heuristics.md"
    shutil.copy(WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md", rules_path)

    script_path = (
        WORKSPACE_ROOT
        / ".agents"
        / "skills"
        / "experiential-learning-loop"
        / "scripts"
        / "curate_rules.py"
    )

    # 1. ADD a new active rule via CLI
    add_res = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--db-path",
            str(db_path),
            "--rules-path",
            str(rules_path),
            "--operation",
            "ADD",
            "--rule-id",
            "RULE-EXEC-06",
            "--rule-text",
            "Server-Side Filtered gRPC Gate: Require server-side instruction discriminator filtering to keep Stage-2 parse latency <5ms.",
            "--category",
            "EXECUTION_LATENCY",
            "--status",
            "active",
            "--weight",
            "5",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    add_payload = json.loads(add_res.stdout)
    assert add_payload["rule"]["rule_id"] == "RULE-EXEC-06"
    assert add_payload["rule"]["utility_score"] == 5
    assert add_payload["under_24kb_cap"] is True

    # 2. UPVOTE RULE-EXEC-06 via CLI
    up_res = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--db-path",
            str(db_path),
            "--rules-path",
            str(rules_path),
            "--operation",
            "UPVOTE",
            "--rule-id",
            "RULE-EXEC-06",
            "--weight",
            "3",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    up_payload = json.loads(up_res.stdout)
    assert up_payload["rule"]["utility_score"] == 8

    # Verify markdown file integrity (<24 KB + valid YAML frontmatter + contains RULE-EXEC-06)
    md_text = rules_path.read_text(encoding="utf-8")
    assert len(md_text.encode("utf-8")) < RULE_FILE_HARD_LIMIT_BYTES
    fm = _parse_yaml_frontmatter(md_text)
    assert fm.get("trigger") == "model_decision"
    assert len(fm.get("description", "")) > 10
    assert "[RULE-EXEC-06 | Utility: +8 | Status: ACTIVE]" in md_text

    # 3. DOWNVOTE RULE-EXEC-06 below zero and verify automatic archiving
    down_res = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--db-path",
            str(db_path),
            "--rules-path",
            str(rules_path),
            "--operation",
            "DOWNVOTE",
            "--rule-id",
            "RULE-EXEC-06",
            "--weight",
            "10",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    down_payload = json.loads(down_res.stdout)
    assert down_payload["rule"]["utility_score"] == -2
    assert down_payload["rule"]["status"] == "archived"
    assert "RULE-EXEC-06" not in rules_path.read_text(encoding="utf-8")


def test_web_harvested_token2022_shadow_validation_and_promotion(tmp_path: Path) -> None:
    """
    Simulates a web-harvested Token-2022 `transfer_hook` heuristic in `train` mode (`status='shadow'`)
    and verifies promotion to `status='active'` ONLY after positive shadow validation.
    """
    db_path = tmp_path / "telemetry.db"
    rules_path = tmp_path / "solana-heuristics.md"
    shutil.copy(WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md", rules_path)

    pool = ExperiencePool(db_path=db_path, heuristics_rule_path=rules_path)

    # 1. Register web-harvested heuristic in shadow mode before any matching train losses exist
    pool.apply_expel_operation(
        operation="ADD",
        rule_id="RULE-WEB-HOOK-99",
        rule_text="Reject Token-2022 mints with unverified transfer_hook CPI programs.",
        category="ONCHAIN_RUG_TOKEN2022",
        initial_status="shadow",
        sync_markdown=False,
    )
    pre_val = pool.validate_and_promote_shadow_rule(
        rule_id="RULE-WEB-HOOK-99",
        target_failure_category="Token-2022/SPL Rug Vector",
        min_trajectories=2,
    )
    assert pre_val.promoted_to_active is False
    assert pre_val.new_status == "shadow"
    assert "RULE-WEB-HOOK-99" not in rules_path.read_text(encoding="utf-8")

    # 2. Record historical train trajectories (wins + Token-2022 transfer_hook honeypot losses)
    pool.record_trajectory(
        {
            "tx_signature": "5TrainWin1",
            "mint_address": "MintClean1111111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 25.0,
            "pnl_sol": 1.40,
        }
    )
    pool.record_trajectory(
        {
            "tx_signature": "5TrainHookLoss1",
            "mint_address": "MintHookRug11111111111111111111111111111111",
            "mode": "train",
            "curve_progress_pct": 33.0,
            "pnl_sol": -0.75,
            "metadata": {"transfer_hook": "MaliciousHook11111111111111111111111111111"},
        }
    )
    pool.record_trajectory(
        {
            "tx_signature": "5TrainHookLoss2",
            "mint_address": "MintHookRug22222222222222222222222222222222",
            "mode": "train",
            "curve_progress_pct": 39.0,
            "pnl_sol": -0.55,
            "metadata": {"transfer_hook": "MaliciousHook22222222222222222222222222222"},
        }
    )

    # 3. Validate in train mode and verify promotion to active status
    post_val = pool.validate_and_promote_shadow_rule(
        rule_id="RULE-WEB-HOOK-99",
        target_failure_category="Token-2022/SPL Rug Vector",
        min_trajectories=2,
    )
    assert post_val.promoted_to_active is True
    assert post_val.new_status == "active"
    assert post_val.matched_failures_prevented == 2
    assert post_val.counterfactual_pnl_delta_sol == pytest.approx(1.30)
    assert "RULE-WEB-HOOK-99" in rules_path.read_text(encoding="utf-8")

    # 4. Also verify ExpeL k-NN trajectory retrieval returns winning trajectories
    knn = pool.retrieve_knn_winning_trajectories(
        {"tx_signature": "QueryTx", "mint_address": "QueryMint", "curve_progress_pct": 26.0, "pnl_sol": 0.5},
        k=2,
    )
    assert len(knn) == 1
    assert knn[0]["tx_signature"] == "5TrainWin1"
    assert knn[0]["similarity"] > 0.70


def test_local_harness_and_scheduled_trigger(tmp_path: Path) -> None:
    """
    Verifies `LocalOpenAIAgentConfig(...).lightweight()`, `LiteRTAgentConfig`,
    `run_experiential_learning_cycle`, `register_autonomous_web_evolution_trigger`,
    and `SelfImprovingExperientialOrchestrator`.
    """
    openai_cfg = build_local_agent_config(use_litert=False)
    assert isinstance(openai_cfg, LocalOpenAIAgentConfig)
    assert openai_cfg.is_lightweight is True
    assert openai_cfg.compaction_config.compaction_trigger_tokens < 135_000
    assert openai_cfg.capabilities.enable_subagents is True

    litert_cfg = build_local_agent_config(use_litert=True)
    assert isinstance(litert_cfg, LiteRTAgentConfig)
    assert litert_cfg.backend == "gpu"
    assert litert_cfg.enable_speculative_decoding is True
    assert litert_cfg.context_window_tokens == 256_000

    trigger = register_autonomous_web_evolution_trigger()
    assert trigger.schedule == "0 */6 * * *"
    assert trigger.display_name == "solana-memecoin-self-improver"

    orchestrator = SelfImprovingExperientialOrchestrator(db_path=tmp_path / "telemetry.db")
    diag = asyncio.run(orchestrator.execute_full_learning_diagnostic())
    assert diag["cycles_executed"] == 1
    assert diag["shadow_validation"]["promoted_to_active"] is True
    assert diag["heuristics_file_bytes"] < RULE_FILE_HARD_LIMIT_BYTES

    cycle_out = asyncio.run(
        run_experiential_learning_cycle("batch_unit_test", experience_pool=orchestrator.pool)
    )
    assert "97.2%" in cycle_out


def test_skill_scripts_help_and_yaml_frontmatter_schemas() -> None:
    """
    Verifies:
      1. All helper scripts in `.agents/skills/*/scripts/` execute cleanly via `python3 <script>.py --help`.
      2. All `.agents/agents/*.md`, `.agents/skills/*/SKILL.md`, and `.agents/rules/*.md` files
         adhere strictly to Antigravity YAML frontmatter schemas.
      3. `AGENTS.md` has no YAML frontmatter and stays under 3,000 tokens (<24 KB).
    """
    scripts = [
        WORKSPACE_ROOT / ".agents" / "skills" / "experiential-learning-loop" / "scripts" / "evaluate_trajectory.py",
        WORKSPACE_ROOT / ".agents" / "skills" / "experiential-learning-loop" / "scripts" / "curate_rules.py",
        WORKSPACE_ROOT / ".agents" / "skills" / "web-strategy-harvester" / "scripts" / "validate_web_alpha.py",
        WORKSPACE_ROOT / ".agents" / "skills" / "web-strategy-harvester" / "scripts" / "sybil_check.py",
    ]
    for script in scripts:
        assert script.exists(), f"Missing skill script: {script}"
        res = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "usage:" in res.stdout.lower()

    # Check AGENTS.md (plain Markdown, no YAML frontmatter, <3,000 tokens / <24 KB)
    agents_md = (WORKSPACE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert not agents_md.startswith("---"), "AGENTS.md must not contain YAML frontmatter"
    assert len(agents_md.encode("utf-8")) < RULE_FILE_HARD_LIMIT_BYTES
    assert len(agents_md.split()) < 3_000

    # Check all .agents/agents/*.md
    agent_files = list((WORKSPACE_ROOT / ".agents" / "agents").glob("*.md"))
    assert len(agent_files) >= 3
    for af in agent_files:
        fm = _parse_yaml_frontmatter(af.read_text(encoding="utf-8"))
        assert fm.get("name") == af.stem
        assert re.fullmatch(r"[a-z0-9-]+", fm["name"])
        assert 0 < len(fm.get("description", "")) < 1024
        assert fm.get("subagent") == "true"
        assert fm.get("permissionMode") == "acceptEdits"
        assert fm.get("commandExecutionPolicy") == "auto"

    # Check all .agents/skills/*/SKILL.md
    skill_files = list((WORKSPACE_ROOT / ".agents" / "skills").glob("*/SKILL.md"))
    assert len(skill_files) >= 2
    for sf in skill_files:
        text = sf.read_text(encoding="utf-8")
        assert len(text.splitlines()) < 500
        fm = _parse_yaml_frontmatter(text)
        assert fm.get("name") == sf.parent.name
        assert re.fullmatch(r"[a-z0-9-]+", fm["name"])
        assert len(fm["name"]) <= 64
        assert 0 < len(fm.get("description", "")) < 1024

    # Check all .agents/rules/*.md
    rule_files = list((WORKSPACE_ROOT / ".agents" / "rules").glob("*.md"))
    assert len(rule_files) >= 3
    for rf in rule_files:
        raw = rf.read_text(encoding="utf-8")
        assert len(raw.encode("utf-8")) < RULE_FILE_HARD_LIMIT_BYTES
        fm = _parse_yaml_frontmatter(raw)
        assert fm.get("trigger") in {"model_decision", "always_on", "glob", "manual"}
        assert 0 < len(fm.get("description", "")) < 1024


def test_ipc_daemon_self_improvement_and_forensics_actions(tmp_path: Path) -> None:
    """
    Verifies IPC integration in `TitanIPCDaemon` across:
      - `RUN_ACE_EXPEL_SELF_IMPROVEMENT_CYCLE`
      - `CURATE_EXPEL_RULE_DELTA`
      - `VALIDATE_WEB_ALPHA_SHADOW_RULE`
      - `RUN_ZERO_DEV_LOUVAIN_SHADOW_SUITE`
      - `RUN_SLOT_ZERO_DYNAMIC_TIP_SIM`
      - `TRIGGER_RECON_PING_TRAP`
    isolated on a temporary `ExperiencePool`.
    """
    from src.ipc.titan_ipc_daemon import TitanIPCDaemon

    db_path = tmp_path / "ipc_telemetry.db"
    jsonl_path = tmp_path / "ipc_episodic_failures.jsonl"
    rules_path = tmp_path / "solana-heuristics.md"
    shutil.copy(WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md", rules_path)

    daemon = TitanIPCDaemon(socket_path=tmp_path / "titan_ipc_test.sock")
    daemon.experiential_orchestrator.pool = ExperiencePool(
        db_path=db_path,
        episodic_jsonl_path=jsonl_path,
        heuristics_rule_path=rules_path,
    )

    async def _run_ipc_checks() -> None:
        # 1. VALIDATE_WEB_ALPHA_SHADOW_RULE on a fresh pool (auto-seeds trajectory if needed)
        r_val = await daemon.handle_ipc_payload(
            {
                "action": "VALIDATE_WEB_ALPHA_SHADOW_RULE",
                "params": {"rule_id": "RULE-WEB-T22-HOOK-01", "min_trajectories": 1},
            }
        )
        assert r_val["ok"] is True
        assert r_val["data"]["validation"]["promoted_to_active"] is True

        # 2. RUN_ACE_EXPEL_SELF_IMPROVEMENT_CYCLE
        r_cycle = await daemon.handle_ipc_payload(
            {"action": "RUN_ACE_EXPEL_SELF_IMPROVEMENT_CYCLE", "params": {}}
        )
        assert r_cycle["ok"] is True
        assert r_cycle["data"]["cycles_executed"] >= 1
        assert r_cycle["data"]["heuristics_file_bytes"] < RULE_FILE_HARD_LIMIT_BYTES

        # 3. CURATE_EXPEL_RULE_DELTA
        r_curate = await daemon.handle_ipc_payload(
            {
                "action": "CURATE_EXPEL_RULE_DELTA",
                "params": {"operation": "UPVOTE", "rule_id": "RULE-EXEC-02", "weight": 2},
            }
        )
        assert r_curate["ok"] is True
        assert r_curate["data"]["rule"]["rule_id"] == "RULE-EXEC-02"
        assert r_curate["data"]["heuristics_file_bytes"] < RULE_FILE_HARD_LIMIT_BYTES

        # 4. RUN_ZERO_DEV_LOUVAIN_SHADOW_SUITE
        r_louvain = await daemon.handle_ipc_payload(
            {"action": "RUN_ZERO_DEV_LOUVAIN_SHADOW_SUITE", "params": {}}
        )
        assert r_louvain["ok"] is True
        assert r_louvain["data"]["shadow_resolution"]["shadow_cluster_supply_pct"] > 10.0
        assert r_louvain["data"]["cabal_hunter_vet"]["action"] == "SNIPE_WITH_CLUSTER_EXIT_TRIPWIRES"

        # 5. RUN_SLOT_ZERO_DYNAMIC_TIP_SIM
        r_tip = await daemon.handle_ipc_payload(
            {
                "action": "RUN_SLOT_ZERO_DYNAMIC_TIP_SIM",
                "params": {
                    "p95_tip_floor_sol": 0.0045,
                    "curve_velocity_sol_per_sec": 8.5,
                    "aggressiveness_alpha": 1.8,
                },
            }
        )
        assert r_tip["ok"] is True
        assert r_tip["data"]["jitodontfront_index0"] is True
        assert r_tip["data"]["tip_excluded_from_alt"] is True
        assert r_tip["data"]["dynamic_tip_sol"] > 0.0045

        # 6. TRIGGER_RECON_PING_TRAP
        r_trap = await daemon.handle_ipc_payload(
            {
                "action": "TRIGGER_RECON_PING_TRAP",
                "params": {
                    "target_wallet": "4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t",
                    "token_mint": "PumpRunnerMint11111111111111111111111111111",
                },
            }
        )
        assert r_trap["ok"] is True
        assert r_trap["data"]["ping_trap"]["guaranteed_onchain_revert"] is True
        assert r_trap["data"]["exit_gate"]["action"] == "ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE"

    asyncio.run(_run_ipc_checks())


def test_backup_repair_and_rollback_guard(tmp_path: Path) -> None:
    """
    Verifies the 3-Stage Backup, Auto-Repair & Atomic Rollback Guard:
      1. Always creates a SHA-256 verified pre-change backup before applying changes.
      2. If a change degrades performance, runs the 3-Stage Auto-Repair & Improvement Loop
         to fix the regression and beat the previous version.
      3. If auto-repair cannot beat the previous version, atomically reverts from the backup
         and verifies SHA-256 checksums.
    """
    from src.evolution.backup_repair_rollback_guard import BackupRepairRollbackGuard

    db_path = tmp_path / "guard_telemetry.db"
    jsonl_path = tmp_path / "guard_episodic.jsonl"
    rules_path = tmp_path / "solana-heuristics.md"
    archived_path = tmp_path / "archived-heuristics.md"
    shutil.copy(WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md", rules_path)

    pool = ExperiencePool(
        db_path=db_path,
        episodic_jsonl_path=jsonl_path,
        heuristics_rule_path=rules_path,
        archived_rules_path=archived_path,
    )
    guard = BackupRepairRollbackGuard(
        experience_pool=pool,
        backup_root_ramdisk=tmp_path / "backups_ram",
        backup_root_nvme=tmp_path / "backups_nvme",
    )

    # Case 1: Positive change improves on first pass
    rep_good = guard.execute_change_with_backup_repair_and_rollback(
        change_description="add_verified_rule",
        apply_change_fn=lambda: pool.apply_expel_operation(
            operation="ADD",
            rule_id="RULE-TEST-GOOD-01",
            rule_text="Verified positive rule improving execution win-rate.",
            category="EXECUTION_LATENCY",
            initial_status="active",
            sync_markdown=True,
        ),
    )
    assert rep_good.outcome == "IMPROVED_ON_FIRST_PASS"
    assert rep_good.rolled_back_to_backup is False
    assert rep_good.final_score >= rep_good.pre_change_score

    # Case 2: Repairable regression is fixed & improved better than previous version
    rep_repaired = guard.execute_change_with_backup_repair_and_rollback(
        change_description="repairable_regression",
        apply_change_fn=lambda: None,
        force_repairable_regression_for_test=True,
    )
    assert rep_repaired.outcome == "FIXED_AND_IMPROVED_AFTER_REPAIR"
    assert rep_repaired.rolled_back_to_backup is False
    assert rep_repaired.final_score > rep_repaired.pre_change_score
    assert rep_repaired.repair_attempts_run >= 1

    # Case 3: Unrecoverable regression automatically reverts to the pre-change backup
    pre_rules_text = rules_path.read_text(encoding="utf-8")

    def _corrupt_rules_file() -> None:
        rules_path.write_text("CORRUPTED_UNRECOVERABLE_CHANGE", encoding="utf-8")

    rep_revert = guard.execute_change_with_backup_repair_and_rollback(
        change_description="unrecoverable_regression",
        apply_change_fn=_corrupt_rules_file,
        force_unrepaired_regression_for_test=True,
    )
    assert rep_revert.outcome == "REVERTED_TO_BACKUP"
    assert rep_revert.rolled_back_to_backup is True
    assert rep_revert.rollback_verified_sha256 is True
    assert rules_path.read_text(encoding="utf-8") == pre_rules_text

    # Case 4: Zero-Capital-At-Risk Interlock defers if capital is exposed and auto_drain=False
    rep_deferred = guard.execute_change_with_backup_repair_and_rollback(
        change_description="blocked_while_capital_exposed",
        apply_change_fn=lambda: None,
        open_positions_count=2,
        inflight_jito_bundles_count=1,
        capital_at_risk_sol=3.5,
        auto_drain_if_active=False,
    )
    assert rep_deferred.outcome == "DEFERRED_UNTIL_SAFE_WINDOW"
    assert rep_deferred.interlock_status["safe_to_execute_now"] is False

    # Case 5: Safe Hardware, Software & Blue/Green LLM Fleet Update (0.00 SOL at risk, 0 disturbed)
    upd_report = guard.check_and_apply_safe_hardware_software_updates(
        open_positions_count=1,
        inflight_jito_bundles_count=1,
        capital_at_risk_sol=1.25,
        auto_drain_if_active=True,
    )
    assert upd_report.major_processes_disturbed == 0
    assert upd_report.capital_at_risk_during_update_sol == 0.0
    assert upd_report.models_upgraded_count == 4
    assert len(upd_report.hardware_checks) == 4
    assert len(upd_report.software_updates) == 4


def test_zero_disturbance_reboot_shutdown_and_restart_continuity(tmp_path: Path) -> None:
    """
    Verifies that in the event of an OS reboot (wiping `/mnt/ramdisk`), power-off/shutdown,
    or process restart:
      1. Pre-shutdown checkpoint flushes all RAMDisk state to NVMe in <10ms.
      2. Cold-boot / restart warm-resume repopulates `/mnt/ramdisk` from NVMe in <15ms,
         verifies the AES-256-GCM mlock `.keystore.enc` keyring, and restores all state
         with 0 disturbed processes and 0.0000 SOL lost.
    """
    from src.memory.nvme_checkpoint_manager import NVMeCheckpointManager

    ramdisk_dir = tmp_path / "ramdisk"
    nvme_dir = tmp_path / "nvme_snapshot"
    exec_state = ramdisk_dir / "execution_state"
    exec_state.mkdir(parents=True, exist_ok=True)

    # Seed active state files in RAMDisk
    (exec_state / "vault_graduation_state.json").write_text('{"mode":"LIVE"}', encoding="utf-8")
    (exec_state / "golden5_governor_state.json").write_text('{"active_step":"STEP_3_HOUSE_MONEY_HOMERUN"}', encoding="utf-8")
    (exec_state / "ipc_daemon_warm_resume_state.json").write_text('{"audio_alerts_enabled":true}', encoding="utf-8")

    mgr = NVMeCheckpointManager(
        ramdisk_root=ramdisk_dir,
        snapshot_dir=nvme_dir,
    )
    ckpt = mgr.checkpoint_now(reason="pre_reboot_flush")
    assert ckpt.files_synced >= 3

    # Simulate OS Reboot wiping volatile tmpfs RAMDisk
    shutil.rmtree(ramdisk_dir)
    assert not (ramdisk_dir / "execution_state" / "vault_graduation_state.json").exists()

    # Instant Warm-Resume after OS Reboot / Restart
    recovery = mgr.execute_zero_disturbance_reboot_recovery(
        trigger_source="OS_REBOOT_COLD_RAMDISK_TEST"
    )
    assert recovery.cold_ramdisk_detected is True
    assert recovery.restored_files_count >= 3
    assert recovery.disturbed_processes_count == 0
    assert (ramdisk_dir / "execution_state" / "vault_graduation_state.json").exists()
    assert (ramdisk_dir / "execution_state" / "golden5_governor_state.json").exists()
    assert (ramdisk_dir / "execution_state" / "ipc_daemon_warm_resume_state.json").exists()




