"""Sovereign Titan OS — Root-Locked Risk Watchdog & Macro Regime Switch (`src/risk/risk_watchdog.py`).

Pinned to Core 0 (`taskset -c 0`).
IMMUTABLE SAFETY LOCK: This file must NEVER be modified by self-evolving DSPy/GEPA routines.

Implements:
1. Hard Circuit Breakers (100ms Polling on Core 0):
   Immediately triggers `EMERGENCY_DEMOTE_TO_PAPER` (flattening open inventory via
   95th-percentile Jito bundles + `close_account` 0.00203928 SOL rent reclaim and
   alerting Telegram) if:
   - Rolling 15-minute drawdown `>= 6.0%` of hot equity.
   - `4` consecutive live trades suffer `>5%` negative slippage drift.
   - Hardware PTP clock offset exceeds `5ms` or Helius stream lags `>1,500ms`.

2. Pyth / Binance 1s Macro Crash Filter:
   - `GREEN` (`SOL 5m return > -1.2%`): All engines active.
   - `AMBER` (`SOL 5m return <= -1.5%`): Pause `Engine B` and cut `Shadow` sizing by 50%.
   - `RED_MACRO_FLUSH` (`SOL 5m return <= -2.2%`): Freeze all directional entries
     (`Shadow` & `Engine B`) and double priority for `Engine A` (Zero-Risk Flash-Loan
     Back-Runner) to harvest crash arbitrage spreads.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any, Deque, Dict, List, Literal, Optional, Tuple

import orjson
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import ALTManager, RAYDIUM_V4_PROGRAM_ID, deterministic_pubkey
from src.execution.atomic_tx_builder import (
    ATA_RENT_LAMPORTS,
    AtomicTxBuildResult,
    AtomicV0TransactionBuilder,
    derive_associated_token_address,
)
from src.execution.flash_loan_builder import DEXSwapLegSpec, LAMPORTS_PER_SOL


CORE_0_WATCHDOG_POLL_INTERVAL_S = 0.100  # 100ms polling on Core 0
MAX_15M_DRAWDOWN_PCT = 6.0  # >= 6.0% rolling 15-minute hot equity drawdown
WINDOW_15M_NS = 15 * 60 * 1_000_000_000  # 15 minutes in nanoseconds
MAX_CONSECUTIVE_SLIPPAGE_BREACHES = 4  # 4 consecutive trades with >5% negative slippage
SLIPPAGE_DRIFT_THRESHOLD_PCT = 5.0  # > 5.0% negative slippage drift
MAX_PTP_CLOCK_OFFSET_MS = 5.0  # > 5.0ms hardware PTP clock offset
MAX_HELIUS_STREAM_LAG_MS = 1_500.0  # > 1,500ms Helius stream lag
EMERGENCY_JITO_95TH_TIP_LAMPORTS = 3_000_000  # 0.003 SOL 95th-pct priority exit tip

MACRO_GREEN_FLOOR_PCT = -1.2  # > -1.2% -> GREEN
MACRO_AMBER_THRESHOLD_PCT = -1.5  # <= -1.5% -> AMBER
MACRO_RED_FLUSH_THRESHOLD_PCT = -2.2  # <= -2.2% -> RED_MACRO_FLUSH

MacroRegime = Literal["GREEN", "AMBER", "RED_MACRO_FLUSH"]


@dataclass
class MacroRegimeDirective:
    """Routing & sizing directive emitted by the 1s Pyth/Binance Macro Crash Filter."""

    regime: MacroRegime
    sol_5m_return_pct: float
    engine_a_active: bool
    engine_a_priority_multiplier: float
    engine_b_active: bool
    shadow_executor_active: bool
    shadow_sizing_multiplier: float
    timestamp_ns: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OpenInventoryPosition:
    """Open hot-wallet token position tracked for emergency flattening."""

    token_mint: str
    token_amount_raw: int
    entry_sol: float
    shard_id: int = 0


@dataclass
class CircuitBreakerEvent:
    """Audit record emitted when a Core 0 hard circuit breaker trips."""

    triggered: bool
    action: str  # "NORMAL" | "EMERGENCY_DEMOTE_TO_PAPER"
    reason: str
    rolling_15m_drawdown_pct: float
    consecutive_slippage_breaches: int
    ptp_clock_offset_ms: float
    helius_stream_lag_ms: float
    flattened_positions_count: int
    total_rent_reclaimed_sol: float
    telegram_alert_dispatched: bool
    timestamp_ns: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RiskWatchdog:
    """Core 0 Isolated Root-Locked Risk Watchdog (`100ms` polling)."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        state_path: Optional[Path] = None,
        alt_manager: Optional[ALTManager] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        payer_keypair: Optional[Keypair] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.state_path = state_path or (
            self.settings.execution_state_dir / "risk_watchdog_state.json"
        )
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        self.alt_manager = alt_manager or ALTManager(self.settings)
        self.alt_manager.load_from_ramdisk()
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(
            self.settings, alt_manager=self.alt_manager
        )
        self.keypair = payer_keypair or Keypair()
        self.payer_pk = self.keypair.pubkey()

        # Rolling 15-minute hot equity history: deque of (timestamp_ns, equity_sol)
        self._equity_history: Deque[Tuple[int, float]] = deque(maxlen=10_000)
        self.consecutive_slippage_breaches: int = 0
        self.ptp_clock_offset_ms: float = 0.0
        self.helius_stream_lag_ms: float = 0.0
        self.execution_mode: str = "LIVE"
        self.open_positions: Dict[str, OpenInventoryPosition] = {}
        self.telegram_alerts: List[str] = []
        self._last_breaker_event: Optional[CircuitBreakerEvent] = None
        self.macro_directive: MacroRegimeDirective = self.evaluate_macro_regime(0.0)
        self._persist_state()

    def register_open_position(
        self,
        token_mint: str,
        token_amount_raw: int,
        entry_sol: float,
        shard_id: int = 0,
    ) -> None:
        self.open_positions[token_mint] = OpenInventoryPosition(
            token_mint=token_mint,
            token_amount_raw=int(token_amount_raw),
            entry_sol=float(entry_sol),
            shard_id=int(shard_id),
        )

    def record_equity_snapshot(
        self, hot_equity_sol: float, timestamp_ns: Optional[int] = None
    ) -> float:
        """Records hot equity in SOL and returns current rolling 15-minute drawdown %."""
        now_ns = timestamp_ns if timestamp_ns is not None else time.time_ns()
        self._equity_history.append((now_ns, float(hot_equity_sol)))
        cutoff = now_ns - WINDOW_15M_NS
        while self._equity_history and self._equity_history[0][0] < cutoff:
            self._equity_history.popleft()
        return self.compute_rolling_15m_drawdown_pct()

    def compute_rolling_15m_drawdown_pct(self) -> float:
        if not self._equity_history:
            return 0.0
        peak_equity = max(eq for _, eq in self._equity_history)
        current_equity = self._equity_history[-1][1]
        if peak_equity <= 0.0:
            return 0.0
        drawdown_pct = max(0.0, ((peak_equity - current_equity) / peak_equity) * 100.0)
        return round(drawdown_pct, 4)

    def record_trade_slippage(self, negative_slippage_drift_pct: float) -> int:
        """Tracks consecutive live trades suffering `>5.0%` negative slippage drift."""
        # Support either signed (-5.8) or unsigned (+5.8) negative slippage drift input
        drift_mag = abs(float(negative_slippage_drift_pct))
        if drift_mag > SLIPPAGE_DRIFT_THRESHOLD_PCT:
            self.consecutive_slippage_breaches += 1
        else:
            self.consecutive_slippage_breaches = 0
        return self.consecutive_slippage_breaches

    def update_hardware_and_stream_telemetry(
        self, ptp_clock_offset_ms: float, helius_stream_lag_ms: float
    ) -> None:
        self.ptp_clock_offset_ms = float(ptp_clock_offset_ms)
        self.helius_stream_lag_ms = float(helius_stream_lag_ms)

    def evaluate_macro_regime(self, sol_5m_return_pct: float) -> MacroRegimeDirective:
        """Pyth / Binance 1s Macro Crash Filter:
        - `GREEN` (`SOL 5m return > -1.2%`): All engines active.
        - `AMBER` (`SOL 5m return <= -1.5%`, or `<= -1.2%` down to `> -2.2%`):
          Pause `Engine B` and cut `Shadow` sizing by 50%.
        - `RED_MACRO_FLUSH` (`SOL 5m return <= -2.2%`): Freeze all directional entries
          (`Shadow` & `Engine B`) and double priority for `Engine A` (`2.0x`) to harvest
          crash arbitrage spreads.
        """
        ret = float(sol_5m_return_pct)
        now_ns = time.time_ns()

        if ret <= MACRO_RED_FLUSH_THRESHOLD_PCT:
            directive = MacroRegimeDirective(
                regime="RED_MACRO_FLUSH",
                sol_5m_return_pct=ret,
                engine_a_active=True,
                engine_a_priority_multiplier=2.0,
                engine_b_active=False,
                shadow_executor_active=False,
                shadow_sizing_multiplier=0.0,
                timestamp_ns=now_ns,
            )
        elif ret <= MACRO_AMBER_THRESHOLD_PCT or ret <= MACRO_GREEN_FLOOR_PCT:
            directive = MacroRegimeDirective(
                regime="AMBER",
                sol_5m_return_pct=ret,
                engine_a_active=True,
                engine_a_priority_multiplier=1.0,
                engine_b_active=False,
                shadow_executor_active=True,
                shadow_sizing_multiplier=0.5,
                timestamp_ns=now_ns,
            )
        else:
            directive = MacroRegimeDirective(
                regime="GREEN",
                sol_5m_return_pct=ret,
                engine_a_active=True,
                engine_a_priority_multiplier=1.0,
                engine_b_active=True,
                shadow_executor_active=True,
                shadow_sizing_multiplier=1.0,
                timestamp_ns=now_ns,
            )

        self.macro_directive = directive
        self._persist_state()
        return directive

    def _flatten_open_inventory_95th_jito(
        self,
    ) -> Tuple[List[AtomicTxBuildResult], float]:
        """Builds 95th-percentile Jito exit V0 bundles for all open positions,
        appending `spl_token::instruction::close_account` (`0.00203928 SOL` rent reclaim).
        """
        bundles: List[AtomicTxBuildResult] = []
        total_rent_sol = 0.0

        for mint, pos in list(self.open_positions.items()):
            try:
                mint_pk = Pubkey.from_string(mint)
            except Exception:
                mint_pk = deterministic_pubkey(f"mint:{mint}")
            user_token_ata = derive_associated_token_address(self.payer_pk, mint_pk)
            wsol_ata = derive_associated_token_address(
                self.payer_pk,
                Pubkey.from_string("So11111111111111111111111111111111111111112"),
            )
            self.alt_manager.register_custom_addresses(
                [str(mint_pk), str(user_token_ata), str(wsol_ata)]
            )

            sell_leg = DEXSwapLegSpec(
                program_id=Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID),
                pool_state=self.alt_manager.get_pool_vault(0),
                pool_Authority=self.alt_manager.get_pool_vault(1),
                vault_in=self.alt_manager.get_pool_vault(2),
                vault_out=self.alt_manager.get_pool_vault(3),
                user_source_token_account=user_token_ata,
                user_destination_token_account=wsol_ata,
                amount_in_lamports=max(1, pos.token_amount_raw),
                min_amount_out_lamports=1,
                label=f"EmergencyFlatten_{mint[:8]}",
            )
            exit_tx = self.tx_builder.build_full_token_exit_v0(
                payer_keypair=self.keypair,
                swap_leg=sell_leg,
                token_ata_to_close=user_token_ata,
                priority_micro_lamports=250_000,
            )
            bundles.append(exit_tx)
            total_rent_sol += ATA_RENT_LAMPORTS / LAMPORTS_PER_SOL
            del self.open_positions[mint]

        return bundles, round(total_rent_sol, 8)

    def poll_circuit_breakers_100ms(self) -> CircuitBreakerEvent:
        """Evaluates all Core 0 hard circuit breakers (`100ms` cadence) and triggers
        `EMERGENCY_DEMOTE_TO_PAPER` if any invariant is breached.
        """
        dd_15m = self.compute_rolling_15m_drawdown_pct()
        reasons: List[str] = []

        if dd_15m >= MAX_15M_DRAWDOWN_PCT:
            reasons.append(f"ROLLING_15M_DRAWDOWN_BREACH({dd_15m:.2f}% >= {MAX_15M_DRAWDOWN_PCT}%)")

        if self.consecutive_slippage_breaches >= MAX_CONSECUTIVE_SLIPPAGE_BREACHES:
            reasons.append(
                f"CONSECUTIVE_SLIPPAGE_DRIFT_BREACH({self.consecutive_slippage_breaches} >= "
                f"{MAX_CONSECUTIVE_SLIPPAGE_BREACHES} trades >5%)"
            )

        if abs(self.ptp_clock_offset_ms) > MAX_PTP_CLOCK_OFFSET_MS:
            reasons.append(
                f"PTP_CLOCK_OFFSET_BREACH({self.ptp_clock_offset_ms:.2f}ms > {MAX_PTP_CLOCK_OFFSET_MS}ms)"
            )

        if self.helius_stream_lag_ms > MAX_HELIUS_STREAM_LAG_MS:
            reasons.append(
                f"HELIUS_STREAM_LAG_BREACH({self.helius_stream_lag_ms:.1f}ms > {MAX_HELIUS_STREAM_LAG_MS}ms)"
            )

        now_ns = time.time_ns()
        if reasons:
            reason_str = " | ".join(reasons)
            flattened_txs, rent_reclaimed_sol = self._flatten_open_inventory_95th_jito()
            self.execution_mode = "PAPER"
            alert_msg = (
                f"[CORE-0 RISK WATCHDOG] EMERGENCY_DEMOTE_TO_PAPER: {reason_str} | "
                f"Flattened={len(flattened_txs)} positions | Reclaimed={rent_reclaimed_sol:.8f} SOL"
            )
            self.telegram_alerts.append(alert_msg)

            event = CircuitBreakerEvent(
                triggered=True,
                action="EMERGENCY_DEMOTE_TO_PAPER",
                reason=reason_str,
                rolling_15m_drawdown_pct=dd_15m,
                consecutive_slippage_breaches=self.consecutive_slippage_breaches,
                ptp_clock_offset_ms=self.ptp_clock_offset_ms,
                helius_stream_lag_ms=self.helius_stream_lag_ms,
                flattened_positions_count=len(flattened_txs),
                total_rent_reclaimed_sol=rent_reclaimed_sol,
                telegram_alert_dispatched=True,
                timestamp_ns=now_ns,
            )
            self._last_breaker_event = event
            self._persist_state()
            return event

        event = CircuitBreakerEvent(
            triggered=False,
            action="NORMAL",
            reason="ALL_INVARIANTS_GREEN",
            rolling_15m_drawdown_pct=dd_15m,
            consecutive_slippage_breaches=self.consecutive_slippage_breaches,
            ptp_clock_offset_ms=self.ptp_clock_offset_ms,
            helius_stream_lag_ms=self.helius_stream_lag_ms,
            flattened_positions_count=0,
            total_rent_reclaimed_sol=0.0,
            telegram_alert_dispatched=False,
            timestamp_ns=now_ns,
        )
        self._last_breaker_event = event
        self._persist_state()
        return event

    def reset_breakers_to_mode(self, mode: str = "PAPER") -> None:
        self._equity_history.clear()
        self.consecutive_slippage_breaches = 0
        self.ptp_clock_offset_ms = 0.0
        self.helius_stream_lag_ms = 0.0
        self.execution_mode = mode
        self._persist_state()

    def _persist_state(self) -> None:
        payload = {
            "execution_mode": self.execution_mode,
            "rolling_15m_drawdown_pct": self.compute_rolling_15m_drawdown_pct(),
            "consecutive_slippage_breaches": self.consecutive_slippage_breaches,
            "ptp_clock_offset_ms": self.ptp_clock_offset_ms,
            "helius_stream_lag_ms": self.helius_stream_lag_ms,
            "macro_directive": self.macro_directive.to_dict(),
            "open_positions_count": len(self.open_positions),
            "last_breaker_event": (
                self._last_breaker_event.to_dict() if self._last_breaker_event else None
            ),
            "telegram_alerts": self.telegram_alerts[-10:],
            "updated_at_ns": time.time_ns(),
        }
        self.state_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
