"""Sovereign Titan OS — "House-Money Ratchet" Daily Bankroll Governor (`src/risk/house_money_governor.py`).

Enforces `/AGENTS.md` Rule 21:
Guarantees that once the system is green on the day, it cannot finish the day red:
  1. Tracks `daily_realized_net_sol` and `daily_high_water_mark_pnl_sol` (resetting at 00:00 UTC)
     across all engines.
  2. Tiered Daily Sizing & Floor Lock:
     - Phase 0 (Start of Day — `daily_realized_net_sol < +0.5 SOL`):
       * Runs `Engine A (Zero-Risk Flash-Loan Back-Runner)` at **100% Max Power (up to 5,000 SOL
         flash borrow)** since it has `0` principal risk via `anchor_profit_guard`.
       * Restricts directional trades (`Shadow`, `Horizons 1–4`) to **Conservative Scout Sizing
         (`0.35x` base size)** and requires `PreApprovedTokenState.confidence >= 88/100`.
     - Phase 1 (House-Money Unlocked — `daily_realized_net_sol >= +1.0 SOL`):
       * Unlocks `1.0x` full directional sizing, and locks a hard **Daily Profit Floor** at `55%`
         of `daily_high_water_mark_pnl_sol`.
     - Hard Daily Profit Lock:
       * If `daily_realized_net_sol` ever pulls back to `<= 0.55 * daily_high_water_mark_pnl_sol`
         (e.g., peaking at `+10.0 SOL` today and pulling back to `+5.5 SOL`), automatically pauses
         directional engines for the remainder of the UTC day while keeping **Engine A (0-Risk
         Flash-Loan Arbs)** running 24/7.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, Literal, Optional

import orjson

from src.config.settings import Settings, get_settings


PHASE0_UPPER_SOL = 0.50  # < +0.50 SOL -> Phase 0 Scout Mode (0.35x, conf >= 88)
PHASE1_UNLOCK_SOL = 1.00  # >= +1.00 SOL -> Phase 1 Full House-Money Mode (1.0x, 55% HWM Floor)
SCOUT_SIZING_MULTIPLIER = 0.35
TRANSITIONAL_SIZING_MULTIPLIER = 0.65
FULL_HOUSE_MONEY_MULTIPLIER = 1.00
SCOUT_MIN_CONFIDENCE = 88.0
NORMAL_MIN_CONFIDENCE = 75.0
DAILY_PROFIT_FLOOR_HWM_RATIO = 0.55  # 55% of daily_high_water_mark_pnl_sol
ENGINE_A_MAX_FLASH_BORROW_SOL = 5_000.0  # 100% max flash borrow capacity 24/7


HouseMoneyPhase = Literal[
    "PHASE_0_CONSERVATIVE_SCOUT",
    "PHASE_0_5_BUILDING_CUSHION",
    "PHASE_1_HOUSE_MONEY_UNLOCKED",
    "DAILY_PROFIT_FLOOR_LOCKED_ARB_ONLY",
]


@dataclass
class HouseMoneyStatusSnapshot:
    """Live state of the Daily House-Money Bankroll Governor."""

    utc_date: str
    phase: HouseMoneyPhase
    daily_realized_net_sol: float
    daily_high_water_mark_pnl_sol: float
    locked_daily_profit_floor_sol: float
    available_directional_risk_budget_sol: float
    directional_sizing_multiplier: float
    min_required_confidence: float
    directional_engines_allowed: bool
    directional_paused_for_day: bool
    engine_a_flash_arb_allowed: bool
    engine_a_max_borrow_sol: float
    updated_at_ns: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HouseMoneyGovernor:
    """Enforces the 0.35x Scout Start and 55% Daily High-Water-Mark Profit Floor Lock."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        state_path: Optional[Path] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.state_path = state_path or (
            self.settings.RAMDISK_EXECUTION_STATE / "house_money_state.json"
        )
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        self.utc_date: str = self._current_utc_date()
        self.daily_realized_net_sol: float = 0.0
        self.daily_high_water_mark_pnl_sol: float = 0.0
        self.directional_paused_for_day: bool = False
        self._load_state()

    @staticmethod
    def _current_utc_date() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _check_utc_rollover(self, override_utc_date: Optional[str] = None) -> None:
        target_date = override_utc_date or self._current_utc_date()
        if target_date != self.utc_date:
            self.utc_date = target_date
            self.daily_realized_net_sol = 0.0
            self.daily_high_water_mark_pnl_sol = 0.0
            self.directional_paused_for_day = False
            self._persist_state()

    @property
    def locked_daily_profit_floor_sol(self) -> float:
        """Once daily HWM >= +1.0 SOL, locks 55% of daily_high_water_mark_pnl_sol."""
        if self.daily_high_water_mark_pnl_sol >= PHASE1_UNLOCK_SOL:
            return round(
                self.daily_high_water_mark_pnl_sol * DAILY_PROFIT_FLOOR_HWM_RATIO, 6
            )
        return 0.0

    def record_realized_pnl_delta(
        self,
        pnl_delta_sol: float,
        override_utc_date: Optional[str] = None,
    ) -> HouseMoneyStatusSnapshot:
        """Records a realized PnL delta (from Engine A, Shadow, or Horizons 1–4) and updates the ratchet."""
        self._check_utc_rollover(override_utc_date)
        self.daily_realized_net_sol = round(
            self.daily_realized_net_sol + float(pnl_delta_sol), 6
        )
        if self.daily_realized_net_sol > self.daily_high_water_mark_pnl_sol:
            self.daily_high_water_mark_pnl_sol = self.daily_realized_net_sol

        # Check if daily realized PnL pulled back to or below the 55% HWM floor after unlocking Phase 1
        floor_sol = self.locked_daily_profit_floor_sol
        if (
            self.daily_high_water_mark_pnl_sol >= PHASE1_UNLOCK_SOL
            and self.daily_realized_net_sol <= floor_sol + 1e-9
        ):
            self.directional_paused_for_day = True

        self._persist_state()
        return self.get_status_snapshot()

    def set_daily_pnl_state(
        self,
        daily_realized_net_sol: float,
        daily_high_water_mark_pnl_sol: Optional[float] = None,
    ) -> HouseMoneyStatusSnapshot:
        """Explicitly sets daily realized PnL and HWM (used for simulation/verification/reset)."""
        self.daily_realized_net_sol = round(float(daily_realized_net_sol), 6)
        hwm = (
            float(daily_high_water_mark_pnl_sol)
            if daily_high_water_mark_pnl_sol is not None
            else max(self.daily_high_water_mark_pnl_sol, self.daily_realized_net_sol)
        )
        self.daily_high_water_mark_pnl_sol = round(hwm, 6)
        floor_sol = self.locked_daily_profit_floor_sol
        if (
            self.daily_high_water_mark_pnl_sol >= PHASE1_UNLOCK_SOL
            and self.daily_realized_net_sol <= floor_sol + 1e-9
        ):
            self.directional_paused_for_day = True
        else:
            self.directional_paused_for_day = False
        self._persist_state()
        return self.get_status_snapshot()

    def evaluate_directional_entry(
        self,
        requested_size_sol: float,
        token_confidence_score: float = 90.0,
    ) -> Dict[str, Any]:
        """Evaluates whether a directional trade (`Shadow` / `Horizons 1–4`) is permitted and scales size."""
        snap = self.get_status_snapshot()
        if not snap.directional_engines_allowed:
            return {
                "allowed": False,
                "reason": (
                    f"DAILY_PROFIT_FLOOR_LOCKED: Realized={snap.daily_realized_net_sol:+.2f} SOL "
                    f"touched 55% HWM Floor (+{snap.locked_daily_profit_floor_sol:.2f} SOL). "
                    f"Directional engines paused; Engine A (0-Risk Flash Arbs) active 24/7."
                ),
                "approved_size_sol": 0.0,
                "sizing_multiplier": 0.0,
                "phase": snap.phase,
            }

        if token_confidence_score < snap.min_required_confidence:
            return {
                "allowed": False,
                "reason": (
                    f"CONFIDENCE_BELOW_PHASE_THRESHOLD: {token_confidence_score:.1f} < "
                    f"{snap.min_required_confidence:.1f} ({snap.phase})"
                ),
                "approved_size_sol": 0.0,
                "sizing_multiplier": snap.directional_sizing_multiplier,
                "phase": snap.phase,
            }

        scaled_sol = round(float(requested_size_sol) * snap.directional_sizing_multiplier, 4)
        return {
            "allowed": True,
            "reason": f"APPROVED_{snap.phase}",
            "approved_size_sol": scaled_sol,
            "sizing_multiplier": snap.directional_sizing_multiplier,
            "phase": snap.phase,
        }

    def get_status_snapshot(self) -> HouseMoneyStatusSnapshot:
        floor_sol = self.locked_daily_profit_floor_sol
        risk_budget = max(0.0, round(self.daily_realized_net_sol - floor_sol, 6))

        if self.directional_paused_for_day:
            phase: HouseMoneyPhase = "DAILY_PROFIT_FLOOR_LOCKED_ARB_ONLY"
            mult = 0.0
            min_conf = 100.0
            dir_allowed = False
        elif self.daily_realized_net_sol < PHASE0_UPPER_SOL and self.daily_high_water_mark_pnl_sol < PHASE1_UNLOCK_SOL:
            phase = "PHASE_0_CONSERVATIVE_SCOUT"
            mult = SCOUT_SIZING_MULTIPLIER  # 0.35x
            min_conf = SCOUT_MIN_CONFIDENCE  # 88.0
            dir_allowed = True
        elif self.daily_realized_net_sol < PHASE1_UNLOCK_SOL and self.daily_high_water_mark_pnl_sol < PHASE1_UNLOCK_SOL:
            phase = "PHASE_0_5_BUILDING_CUSHION"
            mult = TRANSITIONAL_SIZING_MULTIPLIER  # 0.65x
            min_conf = 82.0
            dir_allowed = True
        else:
            phase = "PHASE_1_HOUSE_MONEY_UNLOCKED"
            mult = FULL_HOUSE_MONEY_MULTIPLIER  # 1.00x
            min_conf = NORMAL_MIN_CONFIDENCE  # 75.0
            dir_allowed = True

        return HouseMoneyStatusSnapshot(
            utc_date=self.utc_date,
            phase=phase,
            daily_realized_net_sol=self.daily_realized_net_sol,
            daily_high_water_mark_pnl_sol=self.daily_high_water_mark_pnl_sol,
            locked_daily_profit_floor_sol=floor_sol,
            available_directional_risk_budget_sol=risk_budget,
            directional_sizing_multiplier=mult,
            min_required_confidence=min_conf,
            directional_engines_allowed=dir_allowed,
            directional_paused_for_day=self.directional_paused_for_day,
            engine_a_flash_arb_allowed=True,  # Always 100% active 24/7 (0 principal risk)
            engine_a_max_borrow_sol=ENGINE_A_MAX_FLASH_BORROW_SOL,
            updated_at_ns=time.time_ns(),
        )

    def _persist_state(self) -> None:
        snap = self.get_status_snapshot()
        self.state_path.write_bytes(orjson.dumps(snap.to_dict(), option=orjson.OPT_INDENT_2))

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self._persist_state()
            return
        try:
            data = orjson.loads(self.state_path.read_bytes())
            saved_date = str(data.get("utc_date", self.utc_date))
            if saved_date == self.utc_date:
                self.daily_realized_net_sol = float(
                    data.get("daily_realized_net_sol", 0.0)
                )
                self.daily_high_water_mark_pnl_sol = float(
                    data.get("daily_high_water_mark_pnl_sol", 0.0)
                )
                self.directional_paused_for_day = bool(
                    data.get("directional_paused_for_day", False)
                )
            else:
                self._persist_state()
        except Exception:
            self._persist_state()
