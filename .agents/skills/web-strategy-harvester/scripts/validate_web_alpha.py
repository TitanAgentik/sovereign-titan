#!/usr/bin/env python3
"""
Black-box CLI utility for `@web-alpha-researcher` to register a web-harvested trading
or anti-rug heuristic in `heuristic_ledger` with `status='shadow'`, sandbox-test it
against historical `train` trajectories in `memory/telemetry.db`, and promote it to
`status='active'` if counterfactual PnL improves.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.memory.experience_pool import ExperiencePool  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_web_alpha.py",
        description=(
            "Register a web-discovered Solana trading or Token-2022 anti-rug heuristic in "
            "memory/telemetry.db (status='shadow'), backtest it in FinMem train mode against "
            "historical trajectories, and promote to status='active' only after positive "
            "shadow validation."
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
        "--rule-id",
        type=str,
        default="RULE-WEB-T22-HOOK-01",
        help="Unique rule identifier for the web-harvested heuristic.",
    )
    parser.add_argument(
        "--rule-text",
        type=str,
        default=(
            "Web-Harvested Token-2022 CPI Guard: Reject any Token-2022 mint whose "
            "transfer_hook program is non-empty or whose transfer_fee configuration is mutable."
        ),
        help="Natural-language heuristic extracted from external web research.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="ONCHAIN_RUG_TOKEN2022",
        help="Heuristic category (EXECUTION_LATENCY or ONCHAIN_RUG_TOKEN2022).",
    )
    parser.add_argument(
        "--target-failure-category",
        type=str,
        default="Token-2022/SPL Rug Vector",
        help="Canonical failure category targeted by this heuristic.",
    )
    parser.add_argument(
        "--min-trajectories",
        type=int,
        default=5,
        help="Minimum number of train trajectories required before promotion (default: 5).",
    )
    parser.add_argument(
        "--register-only",
        action="store_true",
        help="Only register the rule with status='shadow' without running promotion yet.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pool = ExperiencePool(
        db_path=args.db_path,
        heuristics_rule_path=args.rules_path,
    )
    existing_entry = pool.get_heuristic_rule(args.rule_id)
    if existing_entry is None:
        shadow_entry = pool.apply_expel_operation(
            operation="ADD",
            rule_id=args.rule_id,
            rule_text=args.rule_text,
            category=args.category,
            initial_status="shadow",
            sync_markdown=False,
        )
    else:
        shadow_entry = existing_entry

    if args.register_only:
        print(
            json.dumps(
                {
                    "registered_shadow_rule": shadow_entry.to_dict(),
                    "promoted_to_active": shadow_entry.status == "active",
                },
                indent=2,
            )
        )
        return 0

    validation = pool.validate_and_promote_shadow_rule(
        rule_id=args.rule_id,
        rule_text=args.rule_text,
        category=args.category,
        target_failure_category=args.target_failure_category,
        min_trajectories=args.min_trajectories,
    )
    print(
        json.dumps(
            {
                "initial_shadow_status": shadow_entry.status,
                "validation": validation.to_dict(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
