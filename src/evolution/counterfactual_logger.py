"""Sovereign Titan OS — Counterfactual "Missed Runner" Logger (`src/evolution/counterfactual_logger.py`).

Whenever any filter or Gatekeeper outputs `SKIP`, logs the mint, P_skip, and rejection
reason into `/mnt/ramdisk/counterfactual_log.duckdb`. Tracks pool price at `+60s`, `+300s`,
and `+900s`, flagging skipped tokens that hit `>= 3.0x` (`LP > $25k`) as
`FALSE_NEGATIVE_OMISSION`. Also stores stratified execution traces (`TOP_WINNER`,
`WORST_LOSS`, `TRUE_RUG_BLOCK`) for the 60-trace GEPA Optimizer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Literal, Optional

import duckdb

from src.config.settings import Settings, get_settings


TraceCategory = Literal[
    "TOP_WINNER",
    "WORST_LOSS",
    "FALSE_NEGATIVE_OMISSION",
    "TRUE_RUG_BLOCK",
    "BENIGN_SKIP",
]

FALSE_NEGATIVE_MIN_MULTIPLE = 3.0  # >= 3.0x post-skip rally
FALSE_NEGATIVE_MIN_LP_USD = 25_000.0  # LP > $25k


@dataclass
class CounterfactualSkipRecord:
    """Record of a skipped token and its subsequent +60s, +300s, +900s price trajectory."""

    trace_id: str
    token_mint: str
    p_skip: float
    rejection_reason: str
    filter_stage: str
    initial_price_sol: float
    initial_lp_usd: float
    price_60s_sol: float
    price_300s_sol: float
    price_900s_sol: float
    peak_lp_usd: float
    max_multiple: float
    classification: TraceCategory
    feature_summary: str
    timestamp_ns: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StratifiedExecutionTrace:
    """Unified trace used in the 60-trace GEPA reflective optimization sample."""

    trace_id: str
    category: TraceCategory
    token_mint: str
    action_taken: str
    realized_or_missed_sol: float
    max_multiple: float
    lp_usd: float
    rejection_or_exit_reason: str
    feature_summary: str
    timestamp_ns: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CounterfactualLogger:
    """DuckDB-backed Counterfactual Logger in `/mnt/ramdisk/counterfactual_log.duckdb`."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.db_path = db_path or (self.settings.ramdisk_root / "counterfactual_log.duckdb")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = duckdb.connect(str(self.db_path))
        except Exception:
            self.conn = duckdb.connect(":memory:")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS counterfactual_skips (
                trace_id VARCHAR PRIMARY KEY,
                token_mint VARCHAR NOT NULL,
                p_skip DOUBLE NOT NULL,
                rejection_reason VARCHAR NOT NULL,
                filter_stage VARCHAR NOT NULL,
                initial_price_sol DOUBLE NOT NULL,
                initial_lp_usd DOUBLE NOT NULL,
                price_60s_sol DOUBLE DEFAULT 0.0,
                price_300s_sol DOUBLE DEFAULT 0.0,
                price_900s_sol DOUBLE DEFAULT 0.0,
                peak_lp_usd DOUBLE DEFAULT 0.0,
                max_multiple DOUBLE DEFAULT 1.0,
                classification VARCHAR DEFAULT 'BENIGN_SKIP',
                feature_summary VARCHAR DEFAULT '',
                timestamp_ns BIGINT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS executed_trade_traces (
                trace_id VARCHAR PRIMARY KEY,
                category VARCHAR NOT NULL,
                token_mint VARCHAR NOT NULL,
                action_taken VARCHAR NOT NULL,
                realized_pnl_sol DOUBLE NOT NULL,
                max_multiple DOUBLE NOT NULL,
                lp_usd DOUBLE NOT NULL,
                exit_reason VARCHAR NOT NULL,
                feature_summary VARCHAR NOT NULL,
                timestamp_ns BIGINT NOT NULL
            );
            """
        )

    def log_skip_decision(
        self,
        token_mint: str,
        p_skip: float,
        rejection_reason: str,
        initial_price_sol: float,
        initial_lp_usd: float,
        filter_stage: str = "PORT_8000_GATEKEEPER",
        feature_summary: str = "",
        trace_id: Optional[str] = None,
    ) -> str:
        """Logs an initial `SKIP` decision prior to +60s/+300s/+900s horizon checks."""
        now_ns = time.time_ns()
        tid = trace_id or f"skip_{token_mint[:10]}_{now_ns}"
        self.conn.execute(
            """
            INSERT OR REPLACE INTO counterfactual_skips (
                trace_id, token_mint, p_skip, rejection_reason, filter_stage,
                initial_price_sol, initial_lp_usd, price_60s_sol, price_300s_sol,
                price_900s_sol, peak_lp_usd, max_multiple, classification,
                feature_summary, timestamp_ns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                tid,
                token_mint,
                float(p_skip),
                rejection_reason,
                filter_stage,
                float(initial_price_sol),
                float(initial_lp_usd),
                float(initial_price_sol),
                float(initial_price_sol),
                float(initial_price_sol),
                float(initial_lp_usd),
                1.0,
                "BENIGN_SKIP",
                feature_summary,
                now_ns,
            ],
        )
        return tid

    def update_horizon_prices(
        self,
        trace_id: str,
        price_60s_sol: float,
        price_300s_sol: float,
        price_900s_sol: float,
        peak_lp_usd: float,
    ) -> CounterfactualSkipRecord:
        """Updates `+60s`, `+300s`, and `+900s` prices for a skipped token and flags:
        - `FALSE_NEGATIVE_OMISSION` if `max_multiple >= 3.0x` and `peak_lp_usd > $25,000`.
        - `TRUE_RUG_BLOCK` if price collapsed by `>= 75%` (`price_900s <= 0.25 * initial_price`) or LP rugged.
        """
        row = self.conn.execute(
            """
            SELECT trace_id, token_mint, p_skip, rejection_reason, filter_stage,
                   initial_price_sol, initial_lp_usd, feature_summary, timestamp_ns
            FROM counterfactual_skips
            WHERE trace_id = ?
            """,
            [trace_id],
        ).fetchone()
        if row is None:
            raise KeyError(f"Counterfactual trace_id not found: {trace_id}")

        (
            tid,
            token_mint,
            p_skip,
            rejection_reason,
            filter_stage,
            initial_price,
            initial_lp,
            feature_summary,
            ts_ns,
        ) = row

        base_price = max(float(initial_price), 1e-12)
        peak_price = max(float(price_60s_sol), float(price_300s_sol), float(price_900s_sol))
        max_mult = round(peak_price / base_price, 4)
        max_lp = max(float(initial_lp), float(peak_lp_usd))

        if max_mult >= FALSE_NEGATIVE_MIN_MULTIPLE and max_lp > FALSE_NEGATIVE_MIN_LP_USD:
            classification: TraceCategory = "FALSE_NEGATIVE_OMISSION"
        elif float(price_900s_sol) <= base_price * 0.25 or float(peak_lp_usd) < 2_500.0:
            classification = "TRUE_RUG_BLOCK"
        else:
            classification = "BENIGN_SKIP"

        self.conn.execute(
            """
            UPDATE counterfactual_skips
            SET price_60s_sol = ?,
                price_300s_sol = ?,
                price_900s_sol = ?,
                peak_lp_usd = ?,
                max_multiple = ?,
                classification = ?
            WHERE trace_id = ?
            """,
            [
                float(price_60s_sol),
                float(price_300s_sol),
                float(price_900s_sol),
                max_lp,
                max_mult,
                classification,
                tid,
            ],
        )

        return CounterfactualSkipRecord(
            trace_id=tid,
            token_mint=token_mint,
            p_skip=float(p_skip),
            rejection_reason=rejection_reason,
            filter_stage=filter_stage,
            initial_price_sol=float(initial_price),
            initial_lp_usd=float(initial_lp),
            price_60s_sol=float(price_60s_sol),
            price_300s_sol=float(price_300s_sol),
            price_900s_sol=float(price_900s_sol),
            peak_lp_usd=max_lp,
            max_multiple=max_mult,
            classification=classification,
            feature_summary=feature_summary,
            timestamp_ns=int(ts_ns),
        )

    def record_executed_trade_trace(
        self,
        token_mint: str,
        realized_pnl_sol: float,
        max_multiple: float,
        lp_usd: float,
        exit_reason: str,
        feature_summary: str,
        trace_id: Optional[str] = None,
    ) -> StratifiedExecutionTrace:
        """Logs an executed trade outcome as `TOP_WINNER` (`realized_pnl_sol > 0`) or
        `WORST_LOSS` (`realized_pnl_sol <= 0`) for the 60-trace GEPA optimizer.
        """
        now_ns = time.time_ns()
        tid = trace_id or f"exec_{token_mint[:10]}_{now_ns}"
        category: TraceCategory = "TOP_WINNER" if realized_pnl_sol > 0.0 else "WORST_LOSS"
        self.conn.execute(
            """
            INSERT OR REPLACE INTO executed_trade_traces (
                trace_id, category, token_mint, action_taken, realized_pnl_sol,
                max_multiple, lp_usd, exit_reason, feature_summary, timestamp_ns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                tid,
                category,
                token_mint,
                "ENTER_CONVICTION",
                float(realized_pnl_sol),
                float(max_multiple),
                float(lp_usd),
                exit_reason,
                feature_summary,
                now_ns,
            ],
        )
        return StratifiedExecutionTrace(
            trace_id=tid,
            category=category,
            token_mint=token_mint,
            action_taken="ENTER_CONVICTION",
            realized_or_missed_sol=float(realized_pnl_sol),
            max_multiple=float(max_multiple),
            lp_usd=float(lp_usd),
            rejection_or_exit_reason=exit_reason,
            feature_summary=feature_summary,
            timestamp_ns=now_ns,
        )

    def fetch_stratified_60_traces(self) -> List[StratifiedExecutionTrace]:
        """Returns the strict 60-trace stratified sample:
        - 15 top winners (`TOP_WINNER`)
        - 15 worst losses (`WORST_LOSS`)
        - 15 missed runners (`FALSE_NEGATIVE_OMISSION`)
        - 15 true rug blocks (`TRUE_RUG_BLOCK`)
        """
        traces: List[StratifiedExecutionTrace] = []

        # 1. 15 Top Winners
        winners = self.conn.execute(
            """
            SELECT trace_id, token_mint, realized_pnl_sol, max_multiple, lp_usd,
                   exit_reason, feature_summary, timestamp_ns
            FROM executed_trade_traces
            WHERE category = 'TOP_WINNER'
            ORDER BY realized_pnl_sol DESC
            LIMIT 15
            """
        ).fetchall()
        for r in winners:
            traces.append(
                StratifiedExecutionTrace(
                    trace_id=r[0],
                    category="TOP_WINNER",
                    token_mint=r[1],
                    action_taken="ENTER_CONVICTION",
                    realized_or_missed_sol=float(r[2]),
                    max_multiple=float(r[3]),
                    lp_usd=float(r[4]),
                    rejection_or_exit_reason=r[5],
                    feature_summary=r[6],
                    timestamp_ns=int(r[7]),
                )
            )

        # 2. 15 Worst Losses
        losses = self.conn.execute(
            """
            SELECT trace_id, token_mint, realized_pnl_sol, max_multiple, lp_usd,
                   exit_reason, feature_summary, timestamp_ns
            FROM executed_trade_traces
            WHERE category = 'WORST_LOSS'
            ORDER BY realized_pnl_sol ASC
            LIMIT 15
            """
        ).fetchall()
        for r in losses:
            traces.append(
                StratifiedExecutionTrace(
                    trace_id=r[0],
                    category="WORST_LOSS",
                    token_mint=r[1],
                    action_taken="ENTER_CONVICTION",
                    realized_or_missed_sol=float(r[2]),
                    max_multiple=float(r[3]),
                    lp_usd=float(r[4]),
                    rejection_or_exit_reason=r[5],
                    feature_summary=r[6],
                    timestamp_ns=int(r[7]),
                )
            )

        # 3. 15 Missed Runners (FALSE_NEGATIVE_OMISSION)
        missed = self.conn.execute(
            """
            SELECT trace_id, token_mint, max_multiple, peak_lp_usd,
                   rejection_reason, feature_summary, timestamp_ns
            FROM counterfactual_skips
            WHERE classification = 'FALSE_NEGATIVE_OMISSION'
            ORDER BY max_multiple DESC
            LIMIT 15
            """
        ).fetchall()
        for r in missed:
            traces.append(
                StratifiedExecutionTrace(
                    trace_id=r[0],
                    category="FALSE_NEGATIVE_OMISSION",
                    token_mint=r[1],
                    action_taken="SKIP",
                    realized_or_missed_sol=round((float(r[2]) - 1.0) * 1.5, 4),
                    max_multiple=float(r[2]),
                    lp_usd=float(r[3]),
                    rejection_or_exit_reason=r[4],
                    feature_summary=r[5],
                    timestamp_ns=int(r[6]),
                )
            )

        # 4. 15 True Rug Blocks (TRUE_RUG_BLOCK)
        rugs = self.conn.execute(
            """
            SELECT trace_id, token_mint, max_multiple, peak_lp_usd,
                   rejection_reason, feature_summary, timestamp_ns
            FROM counterfactual_skips
            WHERE classification = 'TRUE_RUG_BLOCK'
            ORDER BY timestamp_ns DESC
            LIMIT 15
            """
        ).fetchall()
        for r in rugs:
            traces.append(
                StratifiedExecutionTrace(
                    trace_id=r[0],
                    category="TRUE_RUG_BLOCK",
                    token_mint=r[1],
                    action_taken="SKIP",
                    realized_or_missed_sol=0.0,
                    max_multiple=float(r[2]),
                    lp_usd=float(r[3]),
                    rejection_or_exit_reason=r[4],
                    feature_summary=r[5],
                    timestamp_ns=int(r[6]),
                )
            )

        return traces

    def close(self) -> None:
        self.conn.close()
