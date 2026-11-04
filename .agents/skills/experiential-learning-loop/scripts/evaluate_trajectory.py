#!/usr/bin/env python3
"""
Black-box CLI utility for `@post-trade-reflector` and `@ace-curator` to record and audit
Solana memecoin trade trajectories across the 6-stage execution pipeline and evaluate
FinMem shadow heuristics against `memory/telemetry.db`.
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
        prog="evaluate_trajectory.py",
        description=(
            "Audit Solana memecoin trade trajectories across the 6-stage Pump.fun/Raydium "
            "latency budget (30-80ms gRPC, <15ms parse, <1ms wallet match, 20-40ms rug gate, "
            "10-20ms route build, 80-150ms Jito bundle), record Reflexion verbal self-critiques "
            "into memory/telemetry.db, and backtest shadow rules in FinMem train mode."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(WORKSPACE_ROOT / "memory" / "telemetry.db"),
        help="Path to SQLite telemetry database (default: memory/telemetry.db).",
    )
    parser.add_argument(
        "--tx-signature",
        type=str,
        default="5EvalCliTxSig111111111111111111111111111111",
        help="Transaction signature to record and evaluate.",
    )
    parser.add_argument(
        "--mint-address",
        type=str,
        default="PumpMint1111111111111111111111111111111111",
        help="Solana token mint address.",
    )
    parser.add_argument(
        "--mode",
        choices=["train", "test"],
        default="train",
        help="FinMem execution mode: train (shadow/replay) or test (live capital).",
    )
    parser.add_argument(
        "--curve-progress-pct",
        type=float,
        default=42.0,
        help="Pump.fun bonding curve completion percentage (0-100).",
    )
    parser.add_argument(
        "--latency-grpc-ms",
        type=float,
        default=48.0,
        help="Stage 1 Yellowstone gRPC ingestion latency in ms (target: 30-80ms).",
    )
    parser.add_argument(
        "--latency-parse-ms",
        type=float,
        default=4.5,
        help="Stage 2 Anchor IDL discriminator parse latency in ms (target: 0-15ms).",
    )
    parser.add_argument(
        "--latency-rug-gate-ms",
        type=float,
        default=28.0,
        help="Stage 4 Jupiter sellability & rug gate latency in ms (target: 20-40ms).",
    )
    parser.add_argument(
        "--latency-jito-ms",
        type=float,
        default=115.0,
        help="Stage 6 Jito bundle landing latency in ms (target: 80-150ms).",
    )
    parser.add_argument(
        "--total-latency-ms",
        type=float,
        default=0.0,
        help="Total end-to-end execution latency in ms (auto-summed if 0).",
    )
    parser.add_argument(
        "--jito-tip-sol",
        type=float,
        default=0.008,
        help="Jito tip in SOL.",
    )
    parser.add_argument(
        "--priority-fee-sol",
        type=float,
        default=0.012,
        help="Compute budget priority fee in SOL.",
    )
    parser.add_argument(
        "--expected-slippage-bps",
        type=float,
        default=85.0,
        help="Expected slippage at t=0ms quote in basis points.",
    )
    parser.add_argument(
        "--realized-slippage-bps",
        type=float,
        default=95.0,
        help="Realized fill slippage at landing in basis points.",
    )
    parser.add_argument(
        "--pnl-sol",
        type=float,
        default=0.35,
        help="Realized PnL in SOL.",
    )
    parser.add_argument(
        "--transfer-hook",
        type=str,
        default="",
        help="Optional Token-2022 transfer_hook program pubkey if present.",
    )
    parser.add_argument(
        "--validate-shadow-rule-id",
        type=str,
        default="",
        help="Optional rule_id in heuristic_ledger to backtest in train mode and promote if PnL > 0.",
    )
    parser.add_argument(
        "--knn-recall",
        type=int,
        default=3,
        help="Number of k-NN winning trajectories to retrieve via ExpeL cosine similarity.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pool = ExperiencePool(db_path=args.db_path)
    total_ms = (
        args.total_latency_ms
        if args.total_latency_ms > 0.0
        else (
            args.latency_grpc_ms
            + args.latency_parse_ms
            + args.latency_rug_gate_ms
            + args.latency_jito_ms
            + 12.0
        )
    )
    meta = {}
    if args.transfer_hook:
        meta["transfer_hook"] = args.transfer_hook

    traj, reflection = pool.record_trajectory(
        {
            "tx_signature": args.tx_signature,
            "mint_address": args.mint_address,
            "mode": args.mode,
            "curve_progress_pct": args.curve_progress_pct,
            "latency_grpc_ms": args.latency_grpc_ms,
            "latency_parse_ms": args.latency_parse_ms,
            "latency_rug_gate_ms": args.latency_rug_gate_ms,
            "latency_jito_ms": args.latency_jito_ms,
            "total_latency_ms": total_ms,
            "jito_tip_sol": args.jito_tip_sol,
            "priority_fee_sol": args.priority_fee_sol,
            "expected_slippage_bps": args.expected_slippage_bps,
            "realized_slippage_bps": args.realized_slippage_bps,
            "pnl_sol": args.pnl_sol,
            "metadata": meta,
        },
        auto_reflect=True,
    )

    knn_matches = pool.retrieve_knn_winning_trajectories(traj, k=args.knn_recall)
    output: dict[str, object] = {
        "trajectory": traj.to_dict(),
        "reflection": reflection.to_dict() if reflection else None,
        "knn_winning_trajectories": knn_matches,
    }

    if args.validate_shadow_rule_id:
        promo = pool.validate_and_promote_shadow_rule(rule_id=args.validate_shadow_rule_id)
        output["shadow_validation"] = promo.to_dict()

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
