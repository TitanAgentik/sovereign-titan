"""Sovereign Titan OS — 4-Stage Ratcheting "Trail-Win" & Scale-Out Engine (`src/execution/trail_win_engine.py`).

Pinned to Threadripper PRO 9995WX Cores 24–31 (`taskset -c 24-31`).
Evaluates every open position across all 4 Lifecycle Horizons + Shadow Trades on every
incoming gRPC shred update in `< 0.05ms` (`50 microseconds`), backed by a zero-copy
memory-mapped state array at `/mnt/ramdisk/execution_state/active_trails.mmap`.

Enforces the 4-Stage Ratcheting Trail-Win Invariants (/AGENTS.md Section 4):
- Stage 0: Initial Hard Stop (`-10%` Micro-Scalp, `-14%` Bonding Scalp, `-18%` Post-Grad/Swing)
  + Time-Decay Stall Exit (`18s` Bonding/Micro-Scalp, `180s` Post-Grad, `1800s` Mid-Cap Swing).
- Stage 1: First Scalp & Breakeven+ Fee Lock (`Entry_Price * 1.04`) at `+12%` (Micro-Scalp),
  `+25%` (Bonding Scalp), or `+35%` (Post-Grad/Swing).
- Stage 2: Principal Recovery (`realized_sol_recovered >= 1.10 * initial_sol_invested`) &
  Dynamic High-Water-Mark (HWM) Chandelier Trail Activation at `2.0x` (`+100%`).
- Stage 3: Parabolic Compression Ratchet (`14%` -> `18%` -> `11%` at 5x -> `6%` at 15x+)
  + Tick-Level Order-Flow Climax Front-Run Exit (95th-percentile Jito exit bundle +
  `spl_token::instruction::close_account` `0.00203928 SOL` ATA rent reclaim).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import mmap
import os
from pathlib import Path
import struct
import time
from typing import Dict, List, Literal, Optional

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import (
    RAYDIUM_V4_PROGRAM_ID,
    WSOL_MINT_PUBKEY,
    deterministic_pubkey,
)
from src.execution.atomic_tx_builder import (
    ATA_RENT_LAMPORTS,
    AtomicTxBuildResult,
    AtomicV0TransactionBuilder,
    derive_associated_token_address,
)
from src.execution.flash_loan_builder import DEXSwapLegSpec, LAMPORTS_PER_SOL


HorizonType = Literal[
    "HORIZON_1_BONDING_SCALP",
    "HORIZON_2_GRADUATION_RECLAIM",
    "HORIZON_3_MIDCAP_SWING",
    "HORIZON_4_WICK_MICROSCALP",
    "SHADOW_TRADE",
]

TrailActionType = Literal[
    "HOLD",
    "STAGE1_PARTIAL_SCALP",
    "HORIZON1_985_BONDING_SCALE_OUT",
    "STAGE2_PRINCIPAL_RECOVERY_2X",
    "STAGE3_PARABOLIC_RATCHET_UPDATE",
    "ORDER_FLOW_CLIMAX_EXIT",
    "TRAIL_STOP_HIT_EXIT",
    "HARD_STOP_LOSS_EXIT",
    "STALL_KILL_SWITCH_EXIT",
    "ZERO_VELOCITY_4S_SCRATCH_EXIT",
    "MANUAL_TURBO_TRAIL_UPDATE",
]

MAX_ACTIVE_TRAIL_SLOTS = 256
# 64-byte binary mmap slot per active trail:
# [slot_idx:I, stage:I, entry_price:d, current_price:d, hwm_price:d, trail_stop_price:d, realized_sol:d, remaining_frac:d, updated_ns:Q]
TRAIL_MMAP_STRUCT = struct.Struct("<IIddddddQ")
TRAIL_MMAP_SLOT_SIZE = TRAIL_MMAP_STRUCT.size  # 64 bytes

# Instant Break-Even Principal Ratchet ("Zero-Loss Lock") Constants:
# Triggers at +3.0% unrealized gain (1.030x) and locks stop floor at +0.85% (1.0085x) above entry
ZERO_LOSS_LOCK_TRIGGER_MULTIPLE: float = 1.030
COPY_SNIPER_FAST_RATCHET_TRIGGER_MULTIPLE: float = 1.025
ZERO_LOSS_LOCK_STOP_MULTIPLE: float = 1.0085

# 4-Second Zero-Velocity Time-Stop ("Zero-Velocity Scratch") & Automatic CloseAccount ATA Rent Harvester:
ZERO_VELOCITY_TIME_STOP_SEC: float = 4.0
ATA_RENT_RECLAIM_LAMPORTS: int = 2_039_280
ATA_RENT_RECLAIM_SOL: float = 0.00203928


@dataclass
class PositionTrailState:
    """Per-position state tracked in RAM and mirrored to `/mnt/ramdisk/execution_state/active_trails.mmap`."""

    mint: str
    symbol: str
    horizon: HorizonType
    entry_price_sol: float
    current_price_sol: float
    high_water_mark_price_sol: float
    unrealized_multiple: float
    initial_sol_invested: float
    initial_tokens: float
    remaining_tokens: float
    remaining_bag_fraction: float
    realized_sol_recovered: float
    current_stage: int  # 0, 1, 2, 3
    active_trail_stop_price: float
    atr_15s: float = 0.0
    time_in_trade_sec: float = 0.0
    opened_at_timestamp: float = field(default_factory=time.time)
    last_new_high_timestamp: float = field(default_factory=time.time)
    dynamic_trail_pct: float = 0.14
    manual_trail_override_pct: Optional[float] = None
    turbo_scalp_Active: bool = False
    stage1_executed: bool = False
    stage2_executed: bool = False
    bonding_985_executed: bool = False
    is_risk_free_moonbag: bool = False
    zero_loss_ratchet_locked: bool = False
    zero_loss_stop_price_sol: float = 0.0
    copy_sniper_fast_ratchet: bool = False
    opened_at_ts_ms: int = 0
    ata_rent_reclaimed_sol: float = 0.0
    zero_velocity_scratched: bool = False
    is_closed: bool = False
    close_reason: Optional[str] = None
    slot_index: int = 0
    step_history: List[Dict[str, float]] = field(default_factory=list)

    @property
    def turbo_scalp_active(self) -> bool:
        return self.turbo_scalp_Active

    @turbo_scalp_active.setter
    def turbo_scalp_active(self, value: bool) -> None:
        self.turbo_scalp_Active = bool(value)

    @property
    def hwm_multiple(self) -> float:
        if self.entry_price_sol <= 0.0:
            return 1.0
        return self.high_water_mark_price_sol / self.entry_price_sol

    @property
    def locked_profit_pct(self) -> float:
        if self.entry_price_sol <= 0.0:
            return 0.0
        return ((self.active_trail_stop_price / self.entry_price_sol) - 1.0) * 100.0

    def to_gui_dict(self) -> Dict[str, object]:
        return {
            "mint": self.mint,
            "symbol": self.symbol,
            "horizon": self.horizon,
            "entry_price_sol": round(self.entry_price_sol, 8),
            "current_price_sol": round(self.current_price_sol, 8),
            "high_water_mark_price_sol": round(self.high_water_mark_price_sol, 8),
            "unrealized_multiple": round(self.unrealized_multiple, 4),
            "hwm_multiple": round(self.hwm_multiple, 4),
            "initial_sol_invested": round(self.initial_sol_invested, 4),
            "realized_sol_recovered": round(self.realized_sol_recovered, 4),
            "remaining_bag_fraction": round(self.remaining_bag_fraction, 4),
            "current_stage": self.current_stage,
            "active_trail_stop_price": round(self.active_trail_stop_price, 8),
            "locked_profit_pct": round(self.locked_profit_pct, 2),
            "dynamic_trail_pct": round(self.dynamic_trail_pct, 4),
            "manual_trail_override_pct": (
                round(self.manual_trail_override_pct, 4)
                if self.manual_trail_override_pct is not None
                else None
            ),
            "turbo_scalp_Active": self.turbo_scalp_Active,
            "turbo_scalp_active": self.turbo_scalp_Active,
            "is_risk_free_moonbag": self.is_risk_free_moonbag,
            "zero_loss_ratchet_locked": self.zero_loss_ratchet_locked,
            "zero_loss_stop_price_sol": round(self.zero_loss_stop_price_sol, 8),
            "opened_at_ts_ms": self.opened_at_ts_ms,
            "ata_rent_reclaimed_sol": round(self.ata_rent_reclaimed_sol, 8),
            "zero_velocity_scratched": self.zero_velocity_scratched,
            "time_in_trade_sec": round(self.time_in_trade_sec, 2),
            "is_closed": self.is_closed,
            "close_reason": self.close_reason,
            "step_history": self.step_history[-25:],
        }


@dataclass
class TrailEvaluationDecision:
    """Result of evaluating a single shred tick against `PositionTrailState` in `< 0.05ms`."""

    mint: str
    action: TrailActionType
    stage_before: int
    stage_after: int
    previous_stop_price: float
    new_stop_price: float
    stop_ratcheted_up: bool
    tokens_sold: float
    sol_received: float
    cumulative_sol_recovered: float
    remaining_bag_fraction: float
    position_closed: bool
    reclaimed_rent_lamports: int
    jito_tip_lamports: int
    eval_latency_ms: float
    v0_tx: Optional[AtomicTxBuildResult] = None
    reason: str = ""
    zero_loss_ratchet_locked: bool = False
    zero_loss_stop_price_sol: float = 0.0
    ata_rent_reclaimed_sol: float = 0.0
    close_account_instruction_bundled: bool = False
    zero_velocity_scratched: bool = False


TrailEvaluationResult = TrailEvaluationDecision


class TrailWinEngine:
    """Sub-millisecond 4-Stage Ratcheting Trail-Win & Scale-Out Engine on Cores 24–31."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        mmap_path: Optional[Path] = None,
        build_live_v0_txs: bool = True,
    ) -> None:
        self.settings = config or get_settings()
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(self.settings)
        self.build_live_v0_txs = build_live_v0_txs
        self.mmap_path: Path = mmap_path or (
            self.settings.RAMDISK_EXECUTION_STATE / "active_trails.mmap"
        )
        self.mmap_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_mmap()

        self.positions: Dict[str, PositionTrailState] = {}
        self.cumulative_ata_rent_reclaimed_sol: float = 0.0
        self.ata_accounts_closed_count: int = 0
        self.zero_velocity_scratches_count: int = 0
        self._next_slot_index: int = 0
        self._payer = Keypair()
        self._raydium_v4_program_id = Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID)
        self._pool_pubkey = deterministic_pubkey("trail_win_engine_pool_v1")
        self._vault_a = deterministic_pubkey("trail_win_engine_vault_a")
        self._vault_b = deterministic_pubkey("trail_win_engine_vault_b")

    @staticmethod
    def pin_to_cores_24_to_31() -> bool:
        """Pins the current worker process to Threadripper Cores 24–31."""
        try:
            os.sched_setaffinity(0, set(range(24, 32)))
            return True
        except Exception:
            return False

    def _init_mmap(self) -> None:
        total_bytes = MAX_ACTIVE_TRAIL_SLOTS * TRAIL_MMAP_SLOT_SIZE
        if not self.mmap_path.exists() or self.mmap_path.stat().st_size < total_bytes:
            with open(self.mmap_path, "wb") as f:
                f.write(b"\x00" * total_bytes)
        self._mmap_file = open(self.mmap_path, "r+b")
        self._mmap = mmap.mmap(
            self._mmap_file.fileno(),
            total_bytes,
            access=mmap.ACCESS_WRITE,
        )

    def _sync_slot_to_mmap(self, pos: PositionTrailState) -> None:
        offset = (pos.slot_index % MAX_ACTIVE_TRAIL_SLOTS) * TRAIL_MMAP_SLOT_SIZE
        TRAIL_MMAP_STRUCT.pack_into(
            self._mmap,
            offset,
            pos.slot_index,
            pos.current_stage,
            pos.entry_price_sol,
            pos.current_price_sol,
            pos.high_water_mark_price_sol,
            pos.active_trail_stop_price,
            pos.realized_sol_recovered,
            pos.remaining_bag_fraction,
            time.time_ns(),
        )

    def read_slot_from_mmap(self, slot_index: int) -> Dict[str, float | int]:
        offset = (slot_index % MAX_ACTIVE_TRAIL_SLOTS) * TRAIL_MMAP_SLOT_SIZE
        unpacked = TRAIL_MMAP_STRUCT.unpack_from(self._mmap, offset)
        return {
            "slot_index": int(unpacked[0]),
            "current_stage": int(unpacked[1]),
            "entry_price_sol": float(unpacked[2]),
            "current_price_sol": float(unpacked[3]),
            "high_water_mark_price_sol": float(unpacked[4]),
            "active_trail_stop_price": float(unpacked[5]),
            "realized_sol_recovered": float(unpacked[6]),
            "remaining_bag_fraction": float(unpacked[7]),
            "updated_ns": int(unpacked[8]),
        }

    @staticmethod
    def validate_horizon1_bonding_entry_gate(
        bonding_curve_pct: float,
    ) -> tuple[bool, str]:
        """Enforces the tightened Horizon 1 Pre-Graduation Squeeze Gate (88.0% - 99.5% only).
        Eliminates 15%-87.9% mid-curve entries where 98.6% of tokens fail to graduate and bleed 200bps roundtrip fees.
        """
        if bonding_curve_pct < 88.0:
            return (
                False,
                f"BLOCKED_H1_MID_CURVE_BLEED ({bonding_curve_pct:.1f}% < 88.0% Pre-Grad Squeeze Floor)",
            )
        if bonding_curve_pct > 99.5:
            return (
                False,
                f"HANDOFF_TO_ZERO_SLOT_MIGRATION_ARB ({bonding_curve_pct:.2f}% > 99.5%)",
            )
        return (
            True,
            f"APPROVED_H1_PRE_GRAD_SQUEEZE ({bonding_curve_pct:.2f}% in [88.0%, 99.5%])",
        )

    @staticmethod
    def _initial_hard_stop_pct(horizon: HorizonType) -> float:
        if horizon == "HORIZON_4_WICK_MICROSCALP":
            return 0.10  # -10% hard stop for micro-scalps
        if horizon == "HORIZON_1_BONDING_SCALP":
            return 0.08  # Tightened -8% hard stop for 88%-99.5% pre-graduation squeezes
        return 0.18  # -18% hard stop for Post-Graduation & Mid-Cap Swings

    @staticmethod
    def _stall_timeout_sec(horizon: HorizonType) -> float:
        if horizon in ("HORIZON_1_BONDING_SCALP", "HORIZON_4_WICK_MICROSCALP"):
            return 18.0
        if horizon == "HORIZON_2_GRADUATION_RECLAIM":
            return 180.0
        return 1800.0

    @staticmethod
    def _stage1_trigger_multiple(horizon: HorizonType) -> float:
        if horizon == "HORIZON_4_WICK_MICROSCALP":
            return 1.12  # +12% snap-back bounce
        if horizon == "HORIZON_1_BONDING_SCALP":
            return 1.25  # +25% bonding curve gain
        return 1.35  # +35% post-graduation / mid-cap swing

    @staticmethod
    def _stage1_scale_out_fraction(horizon: HorizonType) -> float:
        if horizon == "HORIZON_4_WICK_MICROSCALP":
            return 0.70  # Takes 70% profit on +8% to +18% snap-back bounce
        if horizon == "HORIZON_1_BONDING_SCALP":
            return 0.40  # Sells 40% at +25% gain (1.25x)
        return 0.35  # Sells 35% at +35% gain

    @staticmethod
    def compute_dynamic_trail_pct(
        horizon: HorizonType,
        hwm_multiple: float,
        atr_15s_pct: float = 0.04,
        manual_override_pct: Optional[float] = None,
    ) -> float:
        """Computes the Stage 2/3 dynamic trailing distance below High-Water Mark."""
        if manual_override_pct is not None:
            return max(0.01, min(0.35, manual_override_pct))
        if horizon == "HORIZON_4_WICK_MICROSCALP" and hwm_multiple < 2.0:
            return 0.035  # Tight 3.5% tick-level trailing stop for micro-scalps
        if hwm_multiple > 15.0:
            return 0.06  # >15x blow-off top: razor-tight 6.0% trail below HWM
        if hwm_multiple >= 5.0:
            return 0.11  # 5x to 15x: ratchet tighter to 11% below HWM
        if hwm_multiple >= 2.0:
            # 2x to 5x: max(18%, 2.5 * atr_15s_pct), capped at 20%
            return min(0.20, max(0.18, 2.5 * atr_15s_pct))
        return 0.14  # 1.3x to 2.0x: 14% trail

    def register_position(
        self,
        mint: str,
        entry_price_sol: float,
        initial_sol_invested: float,
        horizon: HorizonType = "HORIZON_1_BONDING_SCALP",
        symbol: str = "RUNNER/SOL",
        atr_15s: float = 0.0,
        now_s: Optional[float] = None,
        copy_sniper_fast_ratchet: bool = False,
        opened_at_ts_ms: int = 0,
    ) -> PositionTrailState:
        """Registers a newly opened position into `/mnt/ramdisk/execution_state/active_trails.mmap`."""
        ts = now_s if now_s is not None else time.time()
        resolved_opened_at_ms = (
            int(opened_at_ts_ms)
            if int(opened_at_ts_ms) > 0
            else int(ts * 1000)
        )
        hard_stop_pct = self._initial_hard_stop_pct(horizon)
        initial_stop = entry_price_sol * (1.0 - hard_stop_pct)
        initial_tokens = (
            initial_sol_invested / entry_price_sol if entry_price_sol > 0.0 else 0.0
        )
        slot_idx = self._next_slot_index
        self._next_slot_index += 1

        state = PositionTrailState(
            mint=mint,
            symbol=symbol,
            horizon=horizon,
            entry_price_sol=entry_price_sol,
            current_price_sol=entry_price_sol,
            high_water_mark_price_sol=entry_price_sol,
            unrealized_multiple=1.0,
            initial_sol_invested=initial_sol_invested,
            initial_tokens=initial_tokens,
            remaining_tokens=initial_tokens,
            remaining_bag_fraction=1.0,
            realized_sol_recovered=0.0,
            current_stage=0,
            active_trail_stop_price=initial_stop,
            atr_15s=atr_15s,
            time_in_trade_sec=0.0,
            opened_at_timestamp=ts,
            last_new_high_timestamp=ts,
            dynamic_trail_pct=self.compute_dynamic_trail_pct(horizon, 1.0),
            copy_sniper_fast_ratchet=bool(copy_sniper_fast_ratchet),
            opened_at_ts_ms=resolved_opened_at_ms,
            slot_index=slot_idx,
            step_history=[
                {
                    "timestamp": ts,
                    "price": entry_price_sol,
                    "stop_price": initial_stop,
                    "stage": 0,
                }
            ],
        )
        self.positions[mint] = state
        self._sync_slot_to_mmap(state)
        return state

    def set_manual_trail_override(
        self,
        mint: str,
        trail_pct: Optional[float] = None,
        direct_stop_price: Optional[float] = None,
        activate_turbo_4pct: bool = False,
    ) -> Optional[PositionTrailState]:
        """Allows the Tauri v2 GUI to drag the Trail-Win Stop Line (`1%` to `35%`) or trigger
        the 1-click `[ Activate Turbo Scalp Trail (4% HWM) ]` button.
        """
        pos = self.positions.get(mint)
        if pos is None or pos.is_closed:
            return None

        if activate_turbo_4pct:
            pos.manual_trail_override_pct = 0.04
            pos.turbo_scalp_Active = True
            pos.dynamic_trail_pct = 0.04
            computed_stop = pos.high_water_mark_price_sol * (1.0 - 0.04)
            if pos.zero_loss_ratchet_locked and pos.zero_loss_stop_price_sol > 0.0:
                computed_stop = max(computed_stop, pos.zero_loss_stop_price_sol)
            pos.active_trail_stop_price = max(pos.active_trail_stop_price, computed_stop)
        elif trail_pct is not None:
            clamped = max(0.01, min(0.35, float(trail_pct)))
            pos.manual_trail_override_pct = clamped
            pos.dynamic_trail_pct = clamped
            computed_stop = pos.high_water_mark_price_sol * (
                1.0 - clamped
            )
            if pos.zero_loss_ratchet_locked and pos.zero_loss_stop_price_sol > 0.0:
                computed_stop = max(computed_stop, pos.zero_loss_stop_price_sol)
            pos.active_trail_stop_price = computed_stop
        elif direct_stop_price is not None and direct_stop_price > 0.0:
            implied_pct = 1.0 - (direct_stop_price / max(1e-12, pos.high_water_mark_price_sol))
            clamped_pct = max(0.01, min(0.35, implied_pct))
            pos.manual_trail_override_pct = clamped_pct
            pos.dynamic_trail_pct = clamped_pct
            computed_stop = pos.high_water_mark_price_sol * (
                1.0 - clamped_pct
            )
            if pos.zero_loss_ratchet_locked and pos.zero_loss_stop_price_sol > 0.0:
                computed_stop = max(computed_stop, pos.zero_loss_stop_price_sol)
            pos.active_trail_stop_price = computed_stop

        pos.step_history.append(
            {
                "timestamp": time.time(),
                "price": pos.current_price_sol,
                "stop_price": pos.active_trail_stop_price,
                "stage": float(pos.current_stage),
            }
        )
        self._sync_slot_to_mmap(pos)
        return pos

    def _build_exit_v0_tx(
        self, mint: str, sol_notional: float, is_full_exit: bool
    ) -> Optional[AtomicTxBuildResult]:
        if not self.build_live_v0_txs and not is_full_exit:
            return None
        try:
            mint_pk = Pubkey.from_string(mint)
        except ValueError:
            mint_pk = deterministic_pubkey(f"mint:{mint}")
        token_ata = derive_associated_token_address(self._payer.pubkey(), mint_pk)
        if (
            mint in self.positions
            and getattr(self.positions[mint], "remaining_tokens", 0.0) > 0.0
        ):
            raw_token_units = int(
                round(self.positions[mint].remaining_tokens * 1_000_000)
            )
        else:
            raw_token_units = int(
                round(max(0.0001, sol_notional) * LAMPORTS_PER_SOL)
            )
        leg = DEXSwapLegSpec(
            program_id=Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID),
            pool_state=self._pool_pubkey,
            pool_Authority=deterministic_pubkey("raydium_v4_authority"),
            vault_in=self._vault_a,
            vault_out=self._vault_b,
            user_source_token_account=token_ata,
            user_destination_token_account=derive_associated_token_address(
                self._payer.pubkey(), Pubkey.from_string(WSOL_MINT_PUBKEY)
            ),
            amount_in_lamports=max(1, raw_token_units),
            min_amount_out_lamports=max(
                1, int(sol_notional * 0.95 * LAMPORTS_PER_SOL)
            ),
            label="TrailWinExit",
        )
        if is_full_exit:
            return self.tx_builder.build_full_token_exit_v0(
                payer_keypair=self._payer,
                swap_leg=leg,
                token_ata_to_close=token_ata,
                compute_units=165_000,
                priority_micro_lamports=95_000,
            )
        return self.tx_builder.build_partial_token_sell_v0(
            payer_keypair=self._payer,
            swap_leg=leg,
            compute_units=150_000,
            priority_micro_lamports=65_000,
        )

    def _build_hold_result(
        self,
        pos: PositionTrailState,
        stage_before: int,
        prev_stop: float,
        eval_latency_ms: float,
        action: TrailActionType = "HOLD",
        reason: str = "HOLD_ACTIVE_TRAIL",
    ) -> TrailEvaluationDecision:
        return TrailEvaluationDecision(
            mint=pos.mint,
            action=action,
            stage_before=stage_before,
            stage_after=pos.current_stage,
            previous_stop_price=prev_stop,
            new_stop_price=pos.active_trail_stop_price,
            stop_ratcheted_up=pos.active_trail_stop_price > prev_stop,
            tokens_sold=0.0,
            sol_received=0.0,
            cumulative_sol_recovered=pos.realized_sol_recovered,
            remaining_bag_fraction=pos.remaining_bag_fraction,
            position_closed=pos.is_closed,
            reclaimed_rent_lamports=0,
            jito_tip_lamports=0,
            eval_latency_ms=round(eval_latency_ms, 5),
            v0_tx=None,
            reason=reason,
            zero_loss_ratchet_locked=pos.zero_loss_ratchet_locked,
            zero_loss_stop_price_sol=pos.zero_loss_stop_price_sol,
            ata_rent_reclaimed_sol=0.0,
            close_account_instruction_bundled=False,
            zero_velocity_scratched=pos.zero_velocity_scratched,
        )

    def _execute_partial_scale_out(
        self,
        pos: PositionTrailState,
        action: TrailActionType,
        stage_before: int,
        prev_stop: float,
        tokens_sold: float,
        sol_received: float,
        eval_latency_ms: float,
        v0_tx: Optional[AtomicTxBuildResult],
        reason: str,
    ) -> TrailEvaluationDecision:
        return TrailEvaluationDecision(
            mint=pos.mint,
            action=action,
            stage_before=stage_before,
            stage_after=pos.current_stage,
            previous_stop_price=prev_stop,
            new_stop_price=pos.active_trail_stop_price,
            stop_ratcheted_up=pos.active_trail_stop_price > prev_stop,
            tokens_sold=tokens_sold,
            sol_received=sol_received,
            cumulative_sol_recovered=pos.realized_sol_recovered,
            remaining_bag_fraction=pos.remaining_bag_fraction,
            position_closed=False,
            reclaimed_rent_lamports=0,
            jito_tip_lamports=0,
            eval_latency_ms=round(eval_latency_ms, 5),
            v0_tx=v0_tx,
            reason=reason,
            zero_loss_ratchet_locked=pos.zero_loss_ratchet_locked,
            zero_loss_stop_price_sol=pos.zero_loss_stop_price_sol,
            ata_rent_reclaimed_sol=0.0,
            close_account_instruction_bundled=False,
            zero_velocity_scratched=pos.zero_velocity_scratched,
        )

    def _execute_full_exit(
        self,
        pos: PositionTrailState,
        action: TrailActionType,
        stage_before: int,
        prev_stop: float,
        tokens_sold: float,
        sol_received: float,
        reclaimed_rent_lamports: int,
        jito_tip_lamports: int,
        eval_latency_ms: float,
        v0_tx: Optional[AtomicTxBuildResult],
        reason: str,
    ) -> TrailEvaluationDecision:
        if action in (
            "ZERO_VELOCITY_4S_SCRATCH_EXIT",
            "HARD_STOP_LOSS_EXIT",
            "STALL_KILL_SWITCH_EXIT",
        ):
            jito_tip_lamports = min(int(jito_tip_lamports), 100_000)
        pos.is_closed = True
        pos.ata_rent_reclaimed_sol = ATA_RENT_RECLAIM_SOL
        self.cumulative_ata_rent_reclaimed_sol = round(
            self.cumulative_ata_rent_reclaimed_sol + ATA_RENT_RECLAIM_SOL, 8
        )
        self.ata_accounts_closed_count += 1
        effective_reclaimed_lamports = (
            reclaimed_rent_lamports
            if reclaimed_rent_lamports > 0
            else ATA_RENT_RECLAIM_LAMPORTS
        )
        return TrailEvaluationDecision(
            mint=pos.mint,
            action=action,
            stage_before=stage_before,
            stage_after=pos.current_stage,
            previous_stop_price=prev_stop,
            new_stop_price=pos.active_trail_stop_price,
            stop_ratcheted_up=pos.active_trail_stop_price > prev_stop,
            tokens_sold=tokens_sold,
            sol_received=sol_received,
            cumulative_sol_recovered=pos.realized_sol_recovered,
            remaining_bag_fraction=pos.remaining_bag_fraction,
            position_closed=True,
            reclaimed_rent_lamports=effective_reclaimed_lamports,
            jito_tip_lamports=jito_tip_lamports,
            eval_latency_ms=round(eval_latency_ms, 5),
            v0_tx=v0_tx,
            reason=reason,
            zero_loss_ratchet_locked=pos.zero_loss_ratchet_locked,
            zero_loss_stop_price_sol=pos.zero_loss_stop_price_sol,
            ata_rent_reclaimed_sol=ATA_RENT_RECLAIM_SOL,
            close_account_instruction_bundled=True,
            zero_velocity_scratched=pos.zero_velocity_scratched,
        )

    def evaluate_zero_velocity_4s_scratch(
        self,
        token_mint: str,
        current_price_sol: float,
        elapsed_sec: float,
        buys_5s: int = 0,
        sells_5s: int = 0,
    ) -> TrailEvaluationResult:
        """Evaluates the 4.0-Second Zero-Velocity Time-Stop ("Zero-Velocity Scratch"):
        If a position is still in Stage 0 after >= 4.0 seconds with < +0.5% price progress
        (`current_price_sol / pos.entry_price_sol < 1.005`) and stalled/negative orderflow
        (`buys_5s <= sells_5s` or `current_price_sol / pos.entry_price_sol <= 0.996`),
        immediately executes a 100% scratch exit + automatic `CloseAccount` ATA rent reclaim.
        """
        t0 = time.perf_counter()
        pos = self.positions.get(token_mint)
        if pos is None:
            pos = self.register_position(
                mint=token_mint,
                entry_price_sol=max(1e-12, float(current_price_sol)),
                initial_sol_invested=1.0,
            )

        stage_before = pos.current_stage
        prev_stop = pos.active_trail_stop_price
        pos.current_price_sol = float(current_price_sol)
        pos.time_in_trade_sec = max(0.0, float(elapsed_sec))
        price_ratio = (
            pos.current_price_sol / pos.entry_price_sol
            if pos.entry_price_sol > 0.0
            else 1.0
        )
        pos.unrealized_multiple = price_ratio
        if pos.current_price_sol > pos.high_water_mark_price_sol:
            pos.high_water_mark_price_sol = pos.current_price_sol

        if (
            not pos.is_closed
            and float(elapsed_sec) >= ZERO_VELOCITY_TIME_STOP_SEC
            and pos.current_stage == 0
            and price_ratio < 1.005
            and (int(buys_5s) <= int(sells_5s) or price_ratio <= 0.996)
        ):
            pos.zero_velocity_scratched = True
            self.zero_velocity_scratches_count += 1
            tokens_to_sell = pos.remaining_tokens
            sol_received = tokens_to_sell * pos.current_price_sol
            v0_tx = (
                self._build_exit_v0_tx(
                    token_mint, max(0.01, sol_received), is_full_exit=True
                )
                if self.build_live_v0_txs
                else None
            )
            pos.realized_sol_recovered += sol_received
            pos.remaining_tokens = 0.0
            pos.remaining_bag_fraction = 0.0
            pos.is_closed = True
            scratch_reason = (
                "ZERO_VELOCITY_4S_TIME_STOP_SCRATCH: Stalled orderflow after 4.0s -> "
                "100% scratch exit + ATA rent reclaim"
            )
            pos.close_reason = scratch_reason
            self._sync_slot_to_mmap(pos)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return self._execute_full_exit(
                pos=pos,
                action="ZERO_VELOCITY_4S_SCRATCH_EXIT",
                stage_before=stage_before,
                prev_stop=prev_stop,
                tokens_sold=tokens_to_sell,
                sol_received=sol_received,
                reclaimed_rent_lamports=ATA_RENT_RECLAIM_LAMPORTS,
                jito_tip_lamports=100_000,
                eval_latency_ms=elapsed_ms,
                v0_tx=v0_tx,
                reason=scratch_reason,
            )

        self._sync_slot_to_mmap(pos)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return self._build_hold_result(
            pos=pos,
            stage_before=stage_before,
            prev_stop=prev_stop,
            eval_latency_ms=elapsed_ms,
            action="HOLD",
            reason="ZERO_VELOCITY_4S_CHECK_PASSED_HOLD",
        )

    def evaluate_tick(
        self,
        mint: str,
        current_price_sol: float,
        buy_volume_3s_sol: float = 10.0,
        sell_volume_3s_sol: float = 2.0,
        bonding_curve_pct: Optional[float] = None,
        whale_dump_supply_pct: float = 0.0,
        atr_15s: Optional[float] = None,
        now_s: Optional[float] = None,
        compile_tx: bool = False,
        copy_sniper_fast_ratchet: bool = False,
    ) -> Optional[TrailEvaluationDecision]:
        """Evaluates a single shred price/order-flow update in `< 0.05ms` (`50 microseconds`).
        Strictly enforces monotonic upward ratcheting of `active_trail_stop_price`.
        """
        t0 = time.perf_counter()
        pos = self.positions.get(mint)
        if pos is None or pos.is_closed:
            return None
        ts = now_s if now_s is not None else time.time()

        stage_before = pos.current_stage
        prev_stop = pos.active_trail_stop_price

        pos.current_price_sol = current_price_sol
        current_multiple = (
            current_price_sol / pos.entry_price_sol if pos.entry_price_sol > 0.0 else 1.0
        )
        pos.unrealized_multiple = current_multiple
        pos.time_in_trade_sec = max(0.0, ts - pos.opened_at_timestamp)
        if atr_15s is not None:
            pos.atr_15s = atr_15s
        if copy_sniper_fast_ratchet:
            pos.copy_sniper_fast_ratchet = True

        # Update High-Water Mark (HWM) on new peak
        if current_price_sol > pos.high_water_mark_price_sol:
            pos.high_water_mark_price_sol = current_price_sol
            pos.last_new_high_timestamp = ts

        hwm_mult = pos.hwm_multiple

        # ------------------------------------------------------------------
        # 0. INSTANT BREAK-EVEN PRINCIPAL RATCHET ("Zero-Loss Lock" at +3.0% or +2.5% fast ratchet)
        # ------------------------------------------------------------------
        ratchet_trigger_mult = (
            COPY_SNIPER_FAST_RATCHET_TRIGGER_MULTIPLE
            if (copy_sniper_fast_ratchet or pos.copy_sniper_fast_ratchet)
            else ZERO_LOSS_LOCK_TRIGGER_MULTIPLE
        )
        if (
            hwm_mult >= ratchet_trigger_mult
            or current_multiple >= ratchet_trigger_mult
        ):
            pos.zero_loss_ratchet_locked = True
            pos.zero_loss_stop_price_sol = round(
                pos.entry_price_sol * ZERO_LOSS_LOCK_STOP_MULTIPLE, 12
            )
            pos.active_trail_stop_price = max(
                pos.active_trail_stop_price, pos.zero_loss_stop_price_sol
            )
        elif pos.zero_loss_ratchet_locked and pos.zero_loss_stop_price_sol > 0.0:
            pos.active_trail_stop_price = max(
                pos.active_trail_stop_price, pos.zero_loss_stop_price_sol
            )

        atr_pct = (
            pos.atr_15s / pos.current_price_sol
            if (pos.atr_15s > 0.0 and pos.current_price_sol > 0.0)
            else 0.04
        )

        action: TrailActionType = "HOLD"
        tokens_sold = 0.0
        sol_received = 0.0
        reclaimed_rent = 0
        jito_tip = 0
        reason = "HOLD_ACTIVE_TRAIL"
        v0_tx: Optional[AtomicTxBuildResult] = None

        # ------------------------------------------------------------------
        # 1. STAGE 1: First Scalp & Breakeven+ Fee Lock (+12% / +25% / +35%)
        # ------------------------------------------------------------------
        stage1_mult = self._stage1_trigger_multiple(pos.horizon)
        if not pos.stage1_executed and hwm_mult >= stage1_mult:
            pos.stage1_executed = True
            pos.current_stage = max(pos.current_stage, 1)
            sell_frac_of_initial = self._stage1_scale_out_fraction(pos.horizon)
            tokens_to_sell = min(
                pos.remaining_tokens, pos.initial_tokens * sell_frac_of_initial
            )
            tokens_sold += tokens_to_sell
            pos.remaining_tokens -= tokens_to_sell
            pos.remaining_bag_fraction = (
                pos.remaining_tokens / pos.initial_tokens
                if pos.initial_tokens > 0.0
                else 0.0
            )
            tranche_sol = tokens_to_sell * current_price_sol
            sol_received += tranche_sol
            pos.realized_sol_recovered += tranche_sol

            # Ratchet stop-loss floor up to Entry_Price * 1.04 (guaranteed profitable trade)
            breakeven_plus_stop = pos.entry_price_sol * 1.04
            if pos.horizon == "HORIZON_4_WICK_MICROSCALP":
                # Micro-scalp immediately activates tight 3.5% HWM trail above 1.04x floor
                breakeven_plus_stop = max(
                    breakeven_plus_stop, pos.high_water_mark_price_sol * (1.0 - 0.035)
                )
            pos.active_trail_stop_price = max(
                pos.active_trail_stop_price, breakeven_plus_stop
            )
            action = "STAGE1_PARTIAL_SCALP"
            reason = f"Stage 1 (+{(stage1_mult - 1.0) * 100:.0f}%) tranche sold; stop ratcheted to 1.04x entry"

        # ------------------------------------------------------------------
        # 2. HORIZON 1 SPECIAL: 98.5% Bonding Curve Pre-Migration 30% Scale-Out
        # ------------------------------------------------------------------
        if (
            pos.horizon == "HORIZON_1_BONDING_SCALP"
            and bonding_curve_pct is not None
            and bonding_curve_pct >= 98.5
            and not pos.bonding_985_executed
            and not pos.is_closed
        ):
            pos.bonding_985_executed = True
            # Scale out 30% of initial bag leaving 30% Risk-Free Graduation Moonbag
            target_remaining_tokens = pos.initial_tokens * 0.30
            tokens_to_sell = max(0.0, pos.remaining_tokens - target_remaining_tokens)
            if tokens_to_sell > 0.0:
                tokens_sold += tokens_to_sell
                pos.remaining_tokens -= tokens_to_sell
                pos.remaining_bag_fraction = (
                    pos.remaining_tokens / pos.initial_tokens
                    if pos.initial_tokens > 0.0
                    else 0.0
                )
                tranche_sol = tokens_to_sell * current_price_sol
                sol_received += tranche_sol
                pos.realized_sol_recovered += tranche_sol
            pos.is_risk_free_moonbag = True
            # Ratchet stop to at least 1.08x entry prior to migration bridge
            pos.active_trail_stop_price = max(
                pos.active_trail_stop_price, pos.entry_price_sol * 1.08
            )
            action = "HORIZON1_985_BONDING_SCALE_OUT"
            reason = "98.5% bonding curve completion: scaled out 30%, carrying 30% Risk-Free Moonbag into Horizon 2"

        # ------------------------------------------------------------------
        # 3. STAGE 2: 2.0x (+100%) Principal + 10% Recovery & HWM Chandelier Trail
        # ------------------------------------------------------------------
        if not pos.stage2_executed and hwm_mult >= 2.0 and not pos.is_closed:
            pos.stage2_executed = True
            pos.current_stage = max(pos.current_stage, 2)

            target_recovered_sol = 1.10 * pos.initial_sol_invested
            sol_shortfall = max(0.0, target_recovered_sol - pos.realized_sol_recovered)
            # Sell at least 25% of remaining bag or enough to guarantee >= 110% of initial SOL recovered
            min_stage2_tokens = pos.remaining_tokens * 0.30
            needed_tokens = (
                sol_shortfall / current_price_sol if current_price_sol > 0.0 else 0.0
            )
            tokens_to_sell = min(
                pos.remaining_tokens * 0.75, max(min_stage2_tokens, needed_tokens)
            )
            if tokens_to_sell > 0.0:
                tokens_sold += tokens_to_sell
                pos.remaining_tokens -= tokens_to_sell
                pos.remaining_bag_fraction = (
                    pos.remaining_tokens / pos.initial_tokens
                    if pos.initial_tokens > 0.0
                    else 0.0
                )
                tranche_sol = tokens_to_sell * current_price_sol
                sol_received += tranche_sol
                pos.realized_sol_recovered += tranche_sol

            pos.is_risk_free_moonbag = (
                pos.realized_sol_recovered >= 1.10 * pos.initial_sol_invested
            )
            pos.dynamic_trail_pct = self.compute_dynamic_trail_pct(
                pos.horizon, hwm_mult, atr_pct, pos.manual_trail_override_pct
            )
            candidate_stop = pos.high_water_mark_price_sol * (
                1.0 - pos.dynamic_trail_pct
            )
            pos.active_trail_stop_price = max(
                pos.active_trail_stop_price, candidate_stop
            )
            action = "STAGE2_PRINCIPAL_RECOVERY_2X"
            reason = (
                f"Stage 2 (2.0x) locked {pos.realized_sol_recovered:.3f} SOL "
                f"({(pos.realized_sol_recovered / max(1e-9, pos.initial_sol_invested)) * 100:.1f}% of principal); "
                f"Chandelier HWM trail active"
            )

        # ------------------------------------------------------------------
        # 4. STAGE 3: Parabolic Compression Ratchet (1.3x -> 2x -> 5x -> 15x+)
        # ------------------------------------------------------------------
        if pos.current_stage >= 1 and hwm_mult >= 1.30 and not pos.is_closed:
            if hwm_mult >= 2.5:
                pos.current_stage = 3
            pos.dynamic_trail_pct = self.compute_dynamic_trail_pct(
                pos.horizon, hwm_mult, atr_pct, pos.manual_trail_override_pct
            )
            candidate_stop = pos.high_water_mark_price_sol * (
                1.0 - pos.dynamic_trail_pct
            )
            if candidate_stop > pos.active_trail_stop_price:
                pos.active_trail_stop_price = candidate_stop
                if action == "HOLD":
                    action = "STAGE3_PARABOLIC_RATCHET_UPDATE"
                    reason = (
                        f"Parabolic ratchet stepped UP to {pos.active_trail_stop_price:.8f} SOL "
                        f"(HWM={hwm_mult:.2f}x, trail={pos.dynamic_trail_pct * 100:.1f}%)"
                    )

        # ------------------------------------------------------------------
        # 5. TICK-LEVEL ORDER-FLOW CLIMAX DETECTOR (>=3.0x + 3.2x Sell Delta or Whale Dump)
        # ------------------------------------------------------------------
        near_peak = current_price_sol >= pos.high_water_mark_price_sol * 0.90
        sell_ratio = sell_volume_3s_sol / max(0.001, buy_volume_3s_sol)
        if (
            not pos.is_closed
            and hwm_mult >= 3.0
            and (
                (sell_ratio >= 3.0 and near_peak)
                or whale_dump_supply_pct >= 1.5
            )
        ):
            tokens_to_sell = pos.remaining_tokens
            tokens_sold += tokens_to_sell
            tranche_sol = tokens_to_sell * current_price_sol
            sol_received += tranche_sol
            if compile_tx or self.build_live_v0_txs:
                v0_tx = self._build_exit_v0_tx(mint, max(0.01, tranche_sol), is_full_exit=True)
            pos.realized_sol_recovered += tranche_sol
            pos.remaining_tokens = 0.0
            pos.remaining_bag_fraction = 0.0
            pos.is_closed = True
            pos.close_reason = "ORDER_FLOW_CLIMAX_EXIT"
            reclaimed_rent = ATA_RENT_LAMPORTS
            jito_tip = 3_000_000  # 95th-percentile Jito exit tip (0.003 SOL)
            action = "ORDER_FLOW_CLIMAX_EXIT"
            reason = (
                f"Order-Flow Exhaustion Climax at {pos.unrealized_multiple:.2f}x "
                f"(Sell/Buy={sell_ratio:.2f}x, WhaleDump={whale_dump_supply_pct:.2f}%): "
                f"100% front-run exit + ATA rent reclaim"
            )

        # ------------------------------------------------------------------
        # 6. HARD STOP / RATCHETED TRAIL STOP HIT EXIT
        # ------------------------------------------------------------------
        elif not pos.is_closed and current_price_sol <= pos.active_trail_stop_price:
            tokens_to_sell = pos.remaining_tokens
            tokens_sold += tokens_to_sell
            tranche_sol = tokens_to_sell * current_price_sol
            sol_received += tranche_sol
            if compile_tx or self.build_live_v0_txs:
                v0_tx = self._build_exit_v0_tx(mint, max(0.01, tranche_sol), is_full_exit=True)
            pos.realized_sol_recovered += tranche_sol
            pos.remaining_tokens = 0.0
            pos.remaining_bag_fraction = 0.0
            pos.is_closed = True
            reclaimed_rent = ATA_RENT_LAMPORTS
            jito_tip = 100_000 if pos.current_stage == 0 else 1_500_000
            if pos.current_stage == 0:
                if pos.zero_loss_ratchet_locked:
                    action = "TRAIL_STOP_HIT_EXIT"
                    stop_reason = (
                        f"ZERO_LOSS_BREAKEVEN_RATCHET_STOP_HIT: Stage 0 Zero-Loss Lock (+0.85% floor) "
                        f"hit at {current_price_sol:.8f} SOL (stop={pos.zero_loss_stop_price_sol:.8f} SOL); "
                        f"100% exit + ATA rent reclaim"
                    )
                    pos.close_reason = stop_reason
                    reason = stop_reason
                else:
                    action = "HARD_STOP_LOSS_EXIT"
                    jito_tip = 100_000
                    stop_reason = f"Stage 0 Hard Stop hit at {current_price_sol:.8f} SOL; 100% exit + ATA rent reclaim"
                    pos.close_reason = "HARD_STOP_LOSS_EXIT"
                    reason = stop_reason
            else:
                action = "TRAIL_STOP_HIT_EXIT"
                stop_reason = (
                    f"Stage {pos.current_stage} Ratcheted Trail-Win Stop hit at {current_price_sol:.8f} SOL "
                    f"(Locked +{pos.locked_profit_pct:.1f}%); 100% exit + ATA rent reclaim"
                )
                pos.close_reason = "TRAIL_STOP_HIT_EXIT"
                reason = stop_reason

        # ------------------------------------------------------------------
        # 7. STAGE 0 TIME-DECAY STALL KILL-SWITCH & H3 45-MIN PRINCIPAL-FREE RULE
        # ------------------------------------------------------------------
        elif not pos.is_closed:
            stall_limit = self._stall_timeout_sec(pos.horizon)
            since_high = ts - pos.last_new_high_timestamp
            # H3 45-Minute Principal-Free Rule: Never carry raw unrecovered principal > 45m (2,700s)
            h3_raw_principal_expired = (
                pos.horizon == "HORIZON_3_MIDCAP_SWING"
                and pos.time_in_trade_sec >= 2700.0
                and not pos.is_risk_free_moonbag
            )
            if h3_raw_principal_expired or (
                since_high > stall_limit and pos.unrealized_multiple < 1.15
            ):
                tokens_to_sell = pos.remaining_tokens
                tokens_sold += tokens_to_sell
                tranche_sol = tokens_to_sell * current_price_sol
                sol_received += tranche_sol
                if compile_tx or self.build_live_v0_txs:
                    v0_tx = self._build_exit_v0_tx(mint, max(0.01, tranche_sol), is_full_exit=True)
                pos.realized_sol_recovered += tranche_sol
                pos.remaining_tokens = 0.0
                pos.remaining_bag_fraction = 0.0
                pos.is_closed = True
                pos.close_reason = (
                    "H3_45M_RAW_PRINCIPAL_PROTECTION_EXIT"
                    if h3_raw_principal_expired
                    else "STALL_KILL_SWITCH_EXIT"
                )
                reclaimed_rent = ATA_RENT_LAMPORTS
                jito_tip = 100_000
                action = "STALL_KILL_SWITCH_EXIT"
                reason = (
                    f"H3 45-Min Principal-Free Rule: exited raw principal at {pos.time_in_trade_sec:.0f}s "
                    f"(Stage 2 2.0x Moonbag not reached; zero raw principal held >45m)"
                    if h3_raw_principal_expired
                    else f"Time-Decay Stall Exit: no new high for {since_high:.1f}s "
                    f"(limit {stall_limit:.0f}s) at {pos.unrealized_multiple:.2f}x"
                )

        if not pos.is_closed and tokens_sold > 0.0 and (compile_tx or self.build_live_v0_txs):
            v0_tx = self._build_exit_v0_tx(mint, max(0.01, sol_received), is_full_exit=False)

        stop_ratcheted = pos.active_trail_stop_price > prev_stop
        if stop_ratcheted:
            pos.step_history.append(
                {
                    "timestamp": ts,
                    "price": current_price_sol,
                    "stop_price": pos.active_trail_stop_price,
                    "stage": float(pos.current_stage),
                }
            )

        self._sync_slot_to_mmap(pos)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if pos.is_closed:
            return self._execute_full_exit(
                pos=pos,
                action=action,
                stage_before=stage_before,
                prev_stop=prev_stop,
                tokens_sold=tokens_sold,
                sol_received=sol_received,
                reclaimed_rent_lamports=reclaimed_rent,
                jito_tip_lamports=jito_tip,
                eval_latency_ms=elapsed_ms,
                v0_tx=v0_tx,
                reason=reason,
            )
        if tokens_sold > 0.0:
            return self._execute_partial_scale_out(
                pos=pos,
                action=action,
                stage_before=stage_before,
                prev_stop=prev_stop,
                tokens_sold=tokens_sold,
                sol_received=sol_received,
                eval_latency_ms=elapsed_ms,
                v0_tx=v0_tx,
                reason=reason,
            )
        return self._build_hold_result(
            pos=pos,
            stage_before=stage_before,
            prev_stop=prev_stop,
            eval_latency_ms=elapsed_ms,
            action=action,
            reason=reason,
        )


RatchetingTrailWinEngine = TrailWinEngine

