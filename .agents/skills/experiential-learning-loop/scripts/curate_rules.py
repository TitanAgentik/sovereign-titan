#!/usr/bin/env python3
"""
Black-box CLI utility for `@ace-curator` to execute discrete ExpeL rule operations
(`ADD`, `EDIT`, `UPVOTE`, `DOWNVOTE`) on `heuristic_ledger` (`memory/telemetry.db`)
and apply incremental delta updates to `.agents/rules/solana-heuristics.md` while
enforcing the <24 KB file size limit and preserving YAML frontmatter.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.memory.experience_pool import ExperiencePool, RULE_FILE_HARD_LIMIT_BYTES  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="curate_rules.py",
        description=(
            "Execute discrete ExpeL rule operations (ADD, EDIT, UPVOTE, DOWNVOTE) on "
            "memory/telemetry.db and incrementally update .agents/rules/solana-heuristics.md "
            "while enforcing the <24 KB rule limit and FinMem train-to-test promotion gate."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(WORKSPACE_ROOT / "memory" / "telemetry.db"),
        help="Path to SQLite telemetry database.",
    )
    parser.add_argument(
        "--rules-path",
        type=str,
        default=str(WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md"),
        help="Path to .agents/rules/solana-heuristics.md.",
    )
    parser.add_argument(
        "--archived-rules-path",
        type=str,
        default=None,
        help="Optional path to archived-heuristics.md (auto-isolated when --db-path is custom).",
    )
    parser.add_argument(
        "--operation",
        choices=["ADD", "EDIT", "UPVOTE", "DOWNVOTE"],
        required=False,
        default="UPVOTE",
        help="ExpeL atomic rule operation to apply.",
    )
    parser.add_argument(
        "--rule-id",
        type=str,
        default="RULE-EXEC-01",
        help="Unique rule identifier (e.g. RULE-EXEC-01, RULE-RUG-06).",
    )
    parser.add_argument(
        "--rule-text",
        type=str,
        default="",
        help="Rule text required for ADD or EDIT operations.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="ONCHAIN_RUG_TOKEN2022",
        help="Rule category (EXECUTION_LATENCY or ONCHAIN_RUG_TOKEN2022).",
    )
    parser.add_argument(
        "--status",
        choices=["shadow", "active", "archived"],
        default="shadow",
        help="Initial status for ADD operation (default: shadow per FinMem protocol).",
    )
    parser.add_argument(
        "--weight",
        type=int,
        default=1,
        help="Vote delta weight for UPVOTE / DOWNVOTE operations.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pool = ExperiencePool(
        db_path=args.db_path,
        heuristics_rule_path=args.rules_path,
        archived_rules_path=args.archived_rules_path,
    )
    entry = pool.apply_expel_operation(
        operation=args.operation,  # type: ignore[arg-type]
        rule_id=args.rule_id,
        rule_text=args.rule_text if args.rule_text else None,
        category=args.category,
        initial_status=args.status,  # type: ignore[arg-type]
        weight=args.weight,
        sync_markdown=True,
    )
    file_bytes = len(pool.heuristics_rule_path.read_text(encoding="utf-8").encode("utf-8"))
    assert file_bytes < RULE_FILE_HARD_LIMIT_BYTES, (
        f"Rule file exceeded 24 KB limit: {file_bytes} bytes"
    )

    print(
        json.dumps(
            {
                "operation": args.operation,
                "rule": entry.to_dict(),
                "heuristics_file_path": str(pool.heuristics_rule_path),
                "heuristics_file_bytes": file_bytes,
                "under_24kb_cap": file_bytes < RULE_FILE_HARD_LIMIT_BYTES,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
