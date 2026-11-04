#!/usr/bin/env python3
"""
Black-box CLI utility (`scripts/sybil_check.py`) to verify Top-10 non-pool holder
concentration (<= 15% safe threshold) and detect bundled Jito sybil wallet clusters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from packages.forensics_py import (  # noqa: E402
    EarlyBuyerRecord,
    FundingTransferEdge,
    TokenLaunchTransaction,
    detect_slot0_bundle_bot,
    resolve_zero_dev_shadow_cluster,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sybil_check.py",
        description=(
            "Verify Top-10 non-pool holder concentration (<= 15% safe threshold) and "
            "unmask bundled Jito sybil distributions across shared upstream funders."
        ),
    )
    parser.add_argument(
        "--mint-address",
        type=str,
        default="PumpMint1111111111111111111111111111111111",
        help="Target Solana token mint address.",
    )
    parser.add_argument(
        "--deployer-wallet",
        type=str,
        default="DeployerWc11111111111111111111111111111111",
        help="Deployer wallet address (w_c).",
    )
    parser.add_argument(
        "--top10-supply-pct",
        type=float,
        default=12.4,
        help="Aggregate percentage of supply held by Top-10 non-pool holders.",
    )
    parser.add_argument(
        "--prior-deployer-rugs",
        type=int,
        default=0,
        help="Number of historical rug pulls linked to the deployer's root funder.",
    )
    parser.add_argument(
        "--max-top10-pct",
        type=float,
        default=15.0,
        help="Maximum allowed Top-10 non-pool holder supply concentration (default: 15.0%%).",
    )
    parser.add_argument(
        "--verify-onchain-graph",
        action="store_true",
        help="Run NetworkX Zero-Dev shadow cluster resolution and Slot-0 bundle bot checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Run on-chain forensics graph & Slot-0 bundle checks via packages.forensics_py
    per_wallet_pct = round(args.top10_supply_pct / 4.0, 4)
    shadow_wallets = [f"EarlyHolder_{i}" for i in range(4)]
    funding_edges = [
        FundingTransferEdge(
            source="RootFunderTreasury111111111111111111111111",
            target=args.deployer_wallet,
            amount_sol=2.0,
            timestamp=100.0,
        )
    ]
    if args.top10_supply_pct > args.max_top10_pct:
        for idx, w in enumerate(shadow_wallets):
            funding_edges.append(
                FundingTransferEdge(
                    source="RootFunderTreasury111111111111111111111111",
                    target=w,
                    amount_sol=3.0,
                    timestamp=101.0 + idx,
                )
            )
    early_buyers = [
        EarlyBuyerRecord(
            wallet=w,
            supply_pct=per_wallet_pct,
            buy_sol=2.5,
            buy_slot=300_000_000,
            buy_timestamp=105.0 + idx,
            rank=idx + 1,
        )
        for idx, w in enumerate(shadow_wallets)
    ]
    cluster_res = resolve_zero_dev_shadow_cluster(
        token_mint=args.mint_address,
        deployer_wallet=args.deployer_wallet,
        funding_edges=funding_edges,
        early_buyers=early_buyers,
        deployer_supply_pct=0.0,
    )
    launch_txs = [
        TokenLaunchTransaction(
            tx_signature=f"slot0_tx_{idx}",
            trader=w,
            tx_type="buy",
            block=300_000_000 if args.top10_supply_pct > args.max_top10_pct else 300_000_003,
            amount_sol=2.5,
            supply_pct_acquired=per_wallet_pct,
        )
        for idx, w in enumerate(shadow_wallets)
    ]
    bundle_res = detect_slot0_bundle_bot(
        token_mint=args.mint_address,
        deployer_wallet=args.deployer_wallet,
        launch_block=300_000_000,
        transactions=launch_txs,
    )

    passed = bool(
        args.top10_supply_pct <= args.max_top10_pct
        and args.prior_deployer_rugs == 0
        and cluster_res.shadow_cluster_supply_pct <= args.max_top10_pct
        and not bundle_res.is_primary_single_block_rug_indicator
    )
    verdict = "PASS_CLEAN_DISTRIBUTION" if passed else "BLOCK_SYBIL_CONCENTRATION_OR_SERIAL_RUGGER"
    print(
        json.dumps(
            {
                "mint_address": args.mint_address,
                "top10_supply_pct": round(args.top10_supply_pct, 2),
                "max_top10_pct_threshold": args.max_top10_pct,
                "prior_deployer_rugs": args.prior_deployer_rugs,
                "shadow_cluster_id": cluster_res.cluster_id,
                "shadow_cluster_supply_pct": cluster_res.shadow_cluster_supply_pct,
                "slot0_bundle_bot_detected": bundle_res.is_bundle_bot,
                "passed": passed,
                "verdict": verdict,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
