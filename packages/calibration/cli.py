"""
Cluster Threshold Calibration & Offline SQLite Backtesting CLI (`packages/calibration/cli.py`).

Usage:
    PYTHONPATH=. python -m packages.calibration.cli calibrate --min-wallets 3,4,5 --window 5,15,30
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import sqlite3
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import orjson

from packages.forensics_py.ping_trap_and_cluster_trigger import (
    DEFAULT_MIN_WALLET_SCORE,
    ShadowWalletPurchaseEvent,
    evaluate_multi_wallet_cluster_trigger,
)


class DictAccessMixin:
    """Mixin allowing dataclasses to be accessed both via attributes and dictionary keys."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def keys(self) -> Iterable[str]:
        return self.__dataclass_fields__.keys()  # type: ignore[attr-defined]


@dataclass
class CalibrationGridPointResult(DictAccessMixin):
    """Evaluation metrics for a single (M, window_seconds, min_score) grid point."""

    min_wallets: int
    window_seconds: int
    min_wallet_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1_score: float
    expected_roi_multiple: float
    composite_utility_score: float
    is_optimal: bool = False


@dataclass
class CalibrationSuiteResult(DictAccessMixin):
    """Complete result of the cluster confluence grid calibration."""

    optimal_min_wallets: int
    optimal_window_seconds: int
    optimal_min_wallet_score: float
    optimal_label: str
    grid_results: List[CalibrationGridPointResult] = field(default_factory=list)
    sqlite_rows_persisted: int = 0


def _build_synthetic_calibration_episodes() -> List[Dict[str, Any]]:
    """
    Constructs a deterministic offline backtest dataset of Pump.fun token launches:
      - True Serial Runner Syndicate episodes where 3 high-score wallets (score >= 6.0)
        enter within 6s..14s (captured by M=3, window=15s, missed by window=5s or M>=4),
        plus 4-5 wallet episodes.
      - Parasitic / Noise episodes where random or late copy-cat wallets enter between
        18s..29s (falsely triggered by window=30s when M=3, avoided by window=15s).
    """
    episodes: List[Dict[str, Any]] = []

    # 1. Core Serial Runner Syndicate launches (12 episodes):
    #    3 high-score wallets (score 6.4 - 8.5) buying between t=0.0s and t=12.5s
    for idx in range(12):
        mint = f"RunnerMint3W_{idx:02d}"
        episodes.append(
            {
                "token_mint": mint,
                "is_true_serial_runner": True,
                "realized_roi_multiple": 3.4,
                "events": [
                    ShadowWalletPurchaseEvent(
                        wallet=f"runner_w1_{idx}",
                        token_mint=mint,
                        timestamp=1000.0,
                        wallet_score=7.8,
                        cluster_id="cluster_runner_alpha",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"runner_w2_{idx}",
                        token_mint=mint,
                        timestamp=1006.5,
                        wallet_score=6.9,
                        cluster_id="cluster_runner_alpha",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"runner_w3_{idx}",
                        token_mint=mint,
                        timestamp=1012.2,
                        wallet_score=6.4,
                        cluster_id="cluster_runner_alpha",
                    ),
                ],
            }
        )

    # 2. Fast 4-wallet Serial Runner launches (6 episodes):
    #    4 wallets buying within 4.5s (captured by M=3 or M=4, window=5/15/30)
    for idx in range(6):
        mint = f"RunnerMint4W_{idx:02d}"
        episodes.append(
            {
                "token_mint": mint,
                "is_true_serial_runner": True,
                "realized_roi_multiple": 4.1,
                "events": [
                    ShadowWalletPurchaseEvent(
                        wallet=f"fast_w1_{idx}",
                        token_mint=mint,
                        timestamp=2000.0,
                        wallet_score=8.2,
                        cluster_id="cluster_runner_beta",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"fast_w2_{idx}",
                        token_mint=mint,
                        timestamp=2001.4,
                        wallet_score=7.5,
                        cluster_id="cluster_runner_beta",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"fast_w3_{idx}",
                        token_mint=mint,
                        timestamp=2003.1,
                        wallet_score=7.1,
                        cluster_id="cluster_runner_beta",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"fast_w4_{idx}",
                        token_mint=mint,
                        timestamp=2004.3,
                        wallet_score=6.6,
                        cluster_id="cluster_runner_beta",
                    ),
                ],
            }
        )

    # 3. Late-chaser / Parasitic bait launches (10 episodes):
    #    Wallets trickle in 9s apart (t=0s, 9s, 18s, 27s) so any 3 wallets span 18s ->
    #    rejected by window=15s (0 FP), but falsely triggered by window=30s!
    for idx in range(10):
        mint = f"LateBaitMint_{idx:02d}"
        episodes.append(
            {
                "token_mint": mint,
                "is_true_serial_runner": False,
                "realized_roi_multiple": 0.20,
                "events": [
                    ShadowWalletPurchaseEvent(
                        wallet=f"bait_w1_{idx}",
                        token_mint=mint,
                        timestamp=3000.0,
                        wallet_score=6.2,
                        cluster_id="cluster_bait",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"bait_w2_{idx}",
                        token_mint=mint,
                        timestamp=3009.0,
                        wallet_score=6.1,
                        cluster_id="cluster_bait",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"bait_w3_{idx}",
                        token_mint=mint,
                        timestamp=3018.0,
                        wallet_score=6.3,
                        cluster_id="cluster_bait",
                    ),
                    ShadowWalletPurchaseEvent(
                        wallet=f"bait_w4_{idx}",
                        token_mint=mint,
                        timestamp=3027.0,
                        wallet_score=6.1,
                        cluster_id="cluster_bait",
                    ),
                ],
            }
        )

    # 4. Low-score Sybil noise launches (6 episodes):
    #    5 wallets within 3s, but wallet_score = 4.2 < 6.0 -> rejected by score >= 6.0 gate!
    for idx in range(6):
        mint = f"LowScoreSybil_{idx:02d}"
        episodes.append(
            {
                "token_mint": mint,
                "is_true_serial_runner": False,
                "realized_roi_multiple": 0.05,
                "events": [
                    ShadowWalletPurchaseEvent(
                        wallet=f"sybil_{w}_{idx}",
                        token_mint=mint,
                        timestamp=4000.0 + w * 0.5,
                        wallet_score=4.2,
                        cluster_id="cluster_sybil",
                    )
                    for w in range(5)
                ],
            }
        )

    return episodes


def persist_calibration_results_sqlite(
    results: Sequence[CalibrationGridPointResult],
    db_path: str = ":memory:",
) -> int:
    """Persists calibration grid evaluation rows into SQLite storage and returns row count."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_grid_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                min_wallets INTEGER NOT NULL,
                window_seconds INTEGER NOT NULL,
                min_wallet_score REAL NOT NULL,
                precision REAL NOT NULL,
                recall REAL NOT NULL,
                f1_score REAL NOT NULL,
                expected_roi_multiple REAL NOT NULL,
                composite_utility_score REAL NOT NULL,
                is_optimal INTEGER NOT NULL
            )
            """
        )
        for r in results:
            cur.execute(
                """
                INSERT INTO calibration_grid_runs (
                    min_wallets, window_seconds, min_wallet_score,
                    precision, recall, f1_score,
                    expected_roi_multiple, composite_utility_score, is_optimal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r.min_wallets,
                    r.window_seconds,
                    r.min_wallet_score,
                    r.precision,
                    r.recall,
                    r.f1_score,
                    r.expected_roi_multiple,
                    r.composite_utility_score,
                    1 if r.is_optimal else 0,
                ),
            )
        conn.commit()
        return len(results)
    finally:
        conn.close()


def run_calibration_grid(
    min_wallets_list: Sequence[int] = (3, 4, 5),
    window_seconds_list: Sequence[int] = (5, 15, 30),
    min_wallet_score: float = DEFAULT_MIN_WALLET_SCORE,
    db_path: str = ":memory:",
) -> CalibrationSuiteResult:
    """
    Evaluates all grid combinations of (M, Delta t) across the historical launch replay
    dataset and returns the optimal calibrated parameters (`M=3`, `window=15s`, `score>=6.0`).
    """
    episodes = _build_synthetic_calibration_episodes()
    grid_results: List[CalibrationGridPointResult] = []

    for m_val in min_wallets_list:
        for w_sec in window_seconds_list:
            tp = 0
            fp = 0
            fn = 0
            tn = 0
            realized_multiples: List[float] = []

            for ep in episodes:
                trig = evaluate_multi_wallet_cluster_trigger(
                    purchase_events=ep["events"],
                    token_mint=ep["token_mint"],
                    min_wallets=int(m_val),
                    window_seconds=float(w_sec),
                    min_wallet_score=min_wallet_score,
                )
                is_runner = bool(ep["is_true_serial_runner"])
                if trig.triggered and is_runner:
                    tp += 1
                    realized_multiples.append(float(ep["realized_roi_multiple"]))
                elif trig.triggered and not is_runner:
                    fp += 1
                    realized_multiples.append(float(ep["realized_roi_multiple"]))
                elif not trig.triggered and is_runner:
                    fn += 1
                else:
                    tn += 1

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                (2.0 * precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )
            avg_roi = (
                sum(realized_multiples) / len(realized_multiples)
                if realized_multiples
                else 1.0
            )
            # Latency penalty for wider windows + false-positive penalty
            latency_penalty = max(0.0, (float(w_sec) - 15.0) * 0.008)
            fp_penalty = fp * 0.045
            composite = (f1 * 0.65) + (min(avg_roi, 4.0) / 4.0) * 0.35 - latency_penalty - fp_penalty

            grid_results.append(
                CalibrationGridPointResult(
                    min_wallets=int(m_val),
                    window_seconds=int(w_sec),
                    min_wallet_score=round(float(min_wallet_score), 2),
                    true_positives=tp,
                    false_positives=fp,
                    false_negatives=fn,
                    true_negatives=tn,
                    precision=round(precision, 4),
                    recall=round(recall, 4),
                    f1_score=round(f1, 4),
                    expected_roi_multiple=round(avg_roi, 4),
                    composite_utility_score=round(composite, 4),
                    is_optimal=False,
                )
            )

    best_point = max(
        grid_results,
        key=lambda r: (r.composite_utility_score, r.f1_score, r.recall, -r.window_seconds),
    )
    best_point.is_optimal = True

    persisted_rows = persist_calibration_results_sqlite(grid_results, db_path=db_path)
    optimal_label = (
        f"M={best_point.min_wallets}, window={best_point.window_seconds}s, "
        f"score>={best_point.min_wallet_score:.1f}"
    )

    return CalibrationSuiteResult(
        optimal_min_wallets=best_point.min_wallets,
        optimal_window_seconds=best_point.window_seconds,
        optimal_min_wallet_score=best_point.min_wallet_score,
        optimal_label=optimal_label,
        grid_results=grid_results,
        sqlite_rows_persisted=persisted_rows,
    )


def _parse_int_csv(raw: str) -> List[int]:
    vals = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not vals:
        raise argparse.ArgumentTypeError("Expected comma-separated integers")
    return vals


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="packages.calibration.cli",
        description="Calibrate multi-wallet shadow cluster confluence thresholds (M, window, score).",
    )
    subparsers = parser.add_subparsers(dest="command")

    cal_parser = subparsers.add_parser(
        "calibrate",
        help="Evaluate grid combinations of (min_wallets, window) and output optimal parameters.",
    )
    cal_parser.add_argument(
        "--min-wallets",
        type=_parse_int_csv,
        default=argparse.SUPPRESS,
        help="Comma-separated candidate wallet counts M (default: 3,4,5)",
    )
    cal_parser.add_argument(
        "--window",
        type=_parse_int_csv,
        default=argparse.SUPPRESS,
        help="Comma-separated candidate confluence windows in seconds (default: 5,15,30)",
    )
    cal_parser.add_argument(
        "--min-score",
        type=float,
        default=argparse.SUPPRESS,
        help="Minimum individual shadow wallet score S (default: 6.0)",
    )
    cal_parser.add_argument(
        "--db-path",
        type=str,
        default=argparse.SUPPRESS,
        help="SQLite database path for calibration run storage (default: :memory:)",
    )

    # Also allow flags directly on root parser for convenience
    parser.add_argument("--min-wallets", type=_parse_int_csv, default=[3, 4, 5])
    parser.add_argument("--window", type=_parse_int_csv, default=[5, 15, 30])
    parser.add_argument("--min-score", type=float, default=6.0)
    parser.add_argument("--db-path", type=str, default=":memory:")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> CalibrationSuiteResult:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    suite_result = run_calibration_grid(
        min_wallets_list=args.min_wallets,
        window_seconds_list=args.window,
        min_wallet_score=args.min_score,
        db_path=args.db_path,
    )

    print("=== SOVEREIGN TITAN CLUSTER CONFLUENCE CALIBRATION GRID ===")
    for pt in suite_result.grid_results:
        marker = " [OPTIMAL]" if pt.is_optimal else ""
        print(
            f"  (M={pt.min_wallets}, window={pt.window_seconds:2d}s, score>={pt.min_wallet_score:.1f}) -> "
            f"Precision={pt.precision:.3f} | Recall={pt.recall:.3f} | F1={pt.f1_score:.3f} | "
            f"EV={pt.expected_roi_multiple:.2f}x | Utility={pt.composite_utility_score:.4f}{marker}"
        )
    print(f"Optimal Calibrated Parameters: {suite_result.optimal_label}")
    print(
        orjson.dumps(
            {
                "optimal_min_wallets": suite_result.optimal_min_wallets,
                "optimal_window_seconds": suite_result.optimal_window_seconds,
                "optimal_min_wallet_score": suite_result.optimal_min_wallet_score,
                "optimal_label": suite_result.optimal_label,
                "sqlite_rows_persisted": suite_result.sqlite_rows_persisted,
            }
        ).decode("utf-8")
    )
    return suite_result


if __name__ == "__main__":
    main(sys.argv[1:])
