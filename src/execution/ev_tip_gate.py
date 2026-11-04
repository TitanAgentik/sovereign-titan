"""Sovereign Titan OS — Jito Tip-to-EV Ratio Gate (`src/execution/ev_tip_gate.py`).

Enforces `/AGENTS.md` Rule 22:
Prevents high Jito tip spikes from turning small winning trades into net SOL losses:
  1. Reads the live Jito 75th/95th percentile tip stream from `/mnt/ramdisk/execution_state/jito_tip_telemetry.json`.
  2. Before dispatching any directional or MEV trade, asserts:
       `expected_gross_profit_lamports >= 3.5 * (entry_jito_tip_lamports + estimated_exit_jito_tip_lamports + total_dex_fees_lamports)`
  3. If live Jito tips exceed `28%` (`0.28`) of expected trade EV (or total friction exceeds `1 / 3.5 = 28.57%`),
     automatically blocks small-size scalps (`JITO_TIP_EXCEEDS_28PCT_EV_GATE`) until tip congestion
     cools or computes `min_viable_position_sol` where expected profit is `>= 3.5x` total execution friction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any, Dict, Optional

import orjson

from src.config.settings import Settings, get_settings
from src.execution.flash_loan_builder import LAMPORTS_PER_SOL


MIN_EV_FRICTION_MULTIPLIER = 3.5  # expected_gross_profit >= 3.5 * total_friction
MAX_TIP_TO_EV_RATIO = 0.28  # Jito tips <= 28% of expected gross profit
TIP_GATE_BLOCK_REASON = "JITO_TIP_EXCEEDS_28PCT_EV_GATE"


@dataclass
class JitoTipStreamState:
    """Live Jito BAM/Block-Engine tip telemetry in `/mnt/ramdisk/execution_state/jito_tip_telemetry.json`."""

    p50_tip_lamports: int = 200_000  # 0.0002 SOL
    p75_tip_lamports: int = 500_000  # 0.0005 SOL
    p95_tip_lamports: int = 1_500_000  # 0.0015 SOL
    updated_at_ns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EVTipGateDecision:
    """Result of evaluating a trade's expected gross profit against live Jito tips + DEX fees."""

    passed: bool
    status_code: str  # "EV_TIP_GATE_PASSED" | "JITO_TIP_EXCEEDS_28PCT_EV_GATE"
    position_size_sol: float
    expected_gain_pct: float
    expected_gross_profit_lamports: int
    entry_jito_tip_lamports: int
    estimated_exit_jito_tip_lamports: int
    total_dex_fees_lamports: int
    total_friction_lamports: int
    required_gross_profit_lamports: int
    ev_to_friction_multiple: float
    tip_to_ev_ratio_pct: float
    min_viable_position_sol: float
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExpectedValueTipGate:
    """Sub-millisecond Jito Tip-Floor EV Gate (`>= 3.5x` friction coverage, `<= 28%` tip-to-EV)."""

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.settings = config or get_settings()
        self.telemetry_path: Path = (
            self.settings.RAMDISK_EXECUTION_STATE / "jito_tip_telemetry.json"
        )
        self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        self.tip_state = JitoTipStreamState(updated_at_ns=time.time_ns())
        self.tip_blocks_today: int = 0
        self._load_or_init_tip_stream()

    def _load_or_init_tip_stream(self) -> None:
        if not self.telemetry_path.exists():
            self._persist_tip_stream()
            return
        try:
            data = orjson.loads(self.telemetry_path.read_bytes())
            self.tip_state = JitoTipStreamState(
                p50_tip_lamports=int(data.get("p50_tip_lamports", 200_000)),
                p75_tip_lamports=int(data.get("p75_tip_lamports", 500_000)),
                p95_tip_lamports=int(data.get("p95_tip_lamports", 1_500_000)),
                updated_at_ns=int(data.get("updated_at_ns", time.time_ns())),
            )
            self.tip_blocks_today = int(data.get("tip_blocks_today", 0))
        except Exception:
            self._persist_tip_stream()

    def _persist_tip_stream(self) -> None:
        payload = {
            **self.tip_state.to_dict(),
            "tip_blocks_today": self.tip_blocks_today,
        }
        self.telemetry_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))

    def update_live_tip_stream(
        self,
        p50_tip_sol: float = 0.0002,
        p75_tip_sol: float = 0.0005,
        p95_tip_sol: float = 0.0015,
    ) -> JitoTipStreamState:
        """Updates the live Jito 50th/75th/95th percentile tip floor in `/mnt/ramdisk`."""
        self.tip_state = JitoTipStreamState(
            p50_tip_lamports=int(round(p50_tip_sol * LAMPORTS_PER_SOL)),
            p75_tip_lamports=int(round(p75_tip_sol * LAMPORTS_PER_SOL)),
            p95_tip_lamports=int(round(p95_tip_sol * LAMPORTS_PER_SOL)),
            updated_at_ns=time.time_ns(),
        )
        self._persist_tip_stream()
        return self.tip_state

    def evaluate_trade_ev(
        self,
        position_size_sol: float,
        expected_gain_pct: float,
        entry_jito_tip_lamports: Optional[int] = None,
        estimated_exit_jito_tip_lamports: Optional[int] = None,
        pool_fee_bps: float = 25.0,
        use_95th_percentile: bool = False,
    ) -> EVTipGateDecision:
        """Asserts `expected_gross_profit_lamports >= 3.5 * (entry_tip + exit_tip + dex_fees)`
        and `jito_tips <= 28%` of `expected_gross_profit_lamports`.
        """
        t0 = time.perf_counter_ns()
        pos_sol = max(float(position_size_sol), 1e-6)
        gain_ratio = max(float(expected_gain_pct) / 100.0, 1e-6)
        expected_gross_lamports = int(round(pos_sol * gain_ratio * LAMPORTS_PER_SOL))

        default_tip = (
            self.tip_state.p95_tip_lamports
            if use_95th_percentile
            else self.tip_state.p75_tip_lamports
        )
        in_tip = (
            int(entry_jito_tip_lamports)
            if entry_jito_tip_lamports is not None
            else default_tip
        )
        out_tip = (
            int(estimated_exit_jito_tip_lamports)
            if estimated_exit_jito_tip_lamports is not None
            else default_tip
        )

        # Roundtrip DEX swap fees (entry + exit on principal + gain)
        fee_rate = max(0.0, float(pool_fee_bps)) * 0.0001
        dex_fees_lamports = int(
            round(pos_sol * (2.0 + gain_ratio) * fee_rate * LAMPORTS_PER_SOL)
        )

        total_tips = in_tip + out_tip
        total_friction = total_tips + dex_fees_lamports
        required_gross = int(round(MIN_EV_FRICTION_MULTIPLIER * total_friction))

        ev_multiple = expected_gross_lamports / max(total_friction, 1)
        tip_to_ev_ratio = total_tips / max(expected_gross_lamports, 1)

        # Compute minimum position size (in SOL) needed so expected_gross >= 3.5 * (tips + dex_fees(size))
        # size * gain_ratio >= 3.5 * (tips_sol + size * (2 + gain_ratio) * fee_rate)
        net_edge_per_sol = gain_ratio - (
            MIN_EV_FRICTION_MULTIPLIER * (2.0 + gain_ratio) * fee_rate
        )
        tips_sol = total_tips / LAMPORTS_PER_SOL
        if net_edge_per_sol > 1e-6:
            min_sol_for_35x = (MIN_EV_FRICTION_MULTIPLIER * tips_sol) / net_edge_per_sol
            min_sol_for_28pct_tip = tips_sol / (MAX_TIP_TO_EV_RATIO * gain_ratio)
            min_viable_sol = max(min_sol_for_35x, min_sol_for_28pct_tip)
        else:
            min_viable_sol = 999_999.0

        passed = (
            expected_gross_lamports >= required_gross
            and tip_to_ev_ratio <= MAX_TIP_TO_EV_RATIO + 1e-9
        )
        status_code = "EV_TIP_GATE_PASSED" if passed else TIP_GATE_BLOCK_REASON
        if not passed:
            self.tip_blocks_today += 1
            self._persist_tip_stream()

        lat_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return EVTipGateDecision(
            passed=passed,
            status_code=status_code,
            position_size_sol=round(pos_sol, 4),
            expected_gain_pct=round(float(expected_gain_pct), 3),
            expected_gross_profit_lamports=expected_gross_lamports,
            entry_jito_tip_lamports=in_tip,
            estimated_exit_jito_tip_lamports=out_tip,
            total_dex_fees_lamports=dex_fees_lamports,
            total_friction_lamports=total_friction,
            required_gross_profit_lamports=required_gross,
            ev_to_friction_multiple=round(ev_multiple, 3),
            tip_to_ev_ratio_pct=round(tip_to_ev_ratio * 100.0, 2),
            min_viable_position_sol=round(min_viable_sol, 4),
            latency_ms=round(lat_ms, 4),
        )
