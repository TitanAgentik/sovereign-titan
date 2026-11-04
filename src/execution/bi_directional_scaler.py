"""Sovereign Titan OS — Bi-Directional Scaler (`src/execution/bi_directional_scaler.py`).

Unifies:
  1. `VelocityScratchGuard` (3.0s / 15-Alpenglow-Slot Green-or-Scratch Order-Flow Invalidator)
     so stalled momentum entries exit at `~0.0% to -0.9%` scratch + `close_account` ATA rent reclaim
     instead of waiting to hit `-5.5% / -10.5% / -15.5%` drawdown rungs.
  2. 3-Step Fractional Drawdown Cut Rungs (for trades that validated initial momentum and later
     reverse before reaching Stage 1 breakeven+ lock):
     - Rung D1 (`-5.5%`): Cut `33%` of position (`1/3`).
     - Rung D2 (`-10.5%`): Cut `50%` of remaining position (`1/3` of original).
     - Rung D3 (`-15.5%`): Cut `100%` of remaining position + `close_account` ATA rent reclaim.
  3. 4-Stage Upward Ratcheting `TrailWinEngine` scale-outs (`+25%`, `2.0x`, `5.0x`, `15.0x+`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import RAYDIUM_V4_PROGRAM_ID, WSOL_MINT_PUBKEY, deterministic_pubkey
from src.execution.atomic_tx_builder import (
    ATA_RENT_LAMPORTS,
    AtomicTxBuildResult,
    AtomicV0TransactionBuilder,
    derive_associated_token_address,
)
from src.execution.flash_loan_builder import DEXSwapLegSpec, LAMPORTS_PER_SOL
from src.execution.trail_win_engine import HorizonType, TrailEvaluationDecision, TrailWinEngine
from src.execution.velocity_scratch_guard import VelocityScratchDecision, VelocityScratchGuard


DRAWDOWN_RUNG_D1_PCT = -5.5  # -5.5% -> cut 33%
DRAWDOWN_RUNG_D2_PCT = -10.5  # -10.5% -> cut 50% of remainder
DRAWDOWN_RUNG_D3_PCT = -15.5  # -15.5% -> cut 100% + close_account


@dataclass
class BiDirectionalScaleDecision:
    """Unified output of the Bi-Directional Scaler on each market tick."""

    token_mint: str
    decision_source: Literal[
        "VELOCITY_SCRATCH_3S",
        "DRAWDOWN_RUNG_D1",
        "DRAWDOWN_RUNG_D2",
        "DRAWDOWN_RUNG_D3_FINAL",
        "TRAIL_WIN_ENGINE",
    ]
    action: str
    fraction_sold: float
    remaining_bag_fraction: float
    reclaimed_rent_lamports: int
    pnl_pct: float
    scratch_decision: Optional[VelocityScratchDecision] = None
    trail_decision: Optional[TrailEvaluationDecision] = None
    signed_v0_tx: Optional[AtomicTxBuildResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_mint": self.token_mint,
            "decision_source": self.decision_source,
            "action": self.action,
            "fraction_sold": self.fraction_sold,
            "remaining_bag_fraction": self.remaining_bag_fraction,
            "reclaimed_rent_lamports": self.reclaimed_rent_lamports,
            "pnl_pct": self.pnl_pct,
        }


class BiDirectionalScaler:
    """Combines 3-Second Velocity Scratch Guard, 3-Rung Drawdown Cuts, and 4-Stage Trail-Win Engine."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        scratch_guard: Optional[VelocityScratchGuard] = None,
        trail_engine: Optional[TrailWinEngine] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        payer_keypair: Optional[Keypair] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(self.settings)
        self.keypair = payer_keypair or Keypair()
        self.scratch_guard = scratch_guard or VelocityScratchGuard(
            self.settings, tx_builder=self.tx_builder, payer_keypair=self.keypair
        )
        self.trail_engine = trail_engine or TrailWinEngine(
            self.settings, tx_builder=self.tx_builder
        )
        self.d1_executed: Dict[str, bool] = {}
        self.d2_executed: Dict[str, bool] = {}
        self.d3_executed: Dict[str, bool] = {}

    def register_position(
        self,
        token_mint: str,
        entry_price_sol: float,
        initial_sol_invested: float,
        horizon: HorizonType = "HORIZON_1_BONDING_SCALP",
        entry_slot: int = 342_815_000,
        symbol: str = "TOKEN / SOL",
    ) -> None:
        """Registers an open directional position in both VelocityScratchGuard and TrailWinEngine."""
        self.scratch_guard.register_entry(
            token_mint=token_mint,
            entry_price_sol=entry_price_sol,
            our_position_sol=initial_sol_invested,
            entry_slot=entry_slot,
            engine_source=horizon,
        )
        self.trail_engine.register_position(
            mint=token_mint,
            entry_price_sol=entry_price_sol,
            initial_sol_invested=initial_sol_invested,
            horizon=horizon,
            symbol=symbol,
        )
        self.d1_executed[token_mint] = False
        self.d2_executed[token_mint] = False
        self.d3_executed[token_mint] = False

    def evaluate_tick(
        self,
        token_mint: str,
        current_price_sol: float,
        net_organic_buy_flow_sol_delta: float = 0.0,
        elapsed_seconds: Optional[float] = None,
        current_slot: Optional[int] = None,
    ) -> BiDirectionalScaleDecision:
        """Evaluates 3-second Green-or-Scratch first, then fractional drawdown rungs, then TrailWinEngine."""
        watch = self.scratch_guard.watches.get(token_mint)
        pos = self.trail_engine.positions.get(token_mint)

        # 1. Check 3-Second (15-Slot) Green-or-Scratch Order-Flow Invalidator first
        if watch is not None and not watch.evaluated_3s_gate and not watch.scratched:
            scratch_res = self.scratch_guard.evaluate_post_entry_flow(
                token_mint=token_mint,
                current_price_sol=current_price_sol,
                net_organic_buy_flow_sol_delta=net_organic_buy_flow_sol_delta,
                elapsed_seconds=elapsed_seconds,
                current_slot=current_slot,
            )
            if scratch_res.triggered_scratch:
                if pos is not None:
                    pos.remaining_bag_fraction = 0.0
                    pos.remaining_tokens = 0.0
                    pos.is_closed = True
                    pos.close_reason = scratch_res.reason
                    self.trail_engine._sync_slot_to_mmap(pos)
                return BiDirectionalScaleDecision(
                    token_mint=token_mint,
                    decision_source="VELOCITY_SCRATCH_3S",
                    action="SCRATCH_EXIT_100PCT_WITH_RENT",
                    fraction_sold=1.0,
                    remaining_bag_fraction=0.0,
                    reclaimed_rent_lamports=scratch_res.reclaimed_rent_lamports,
                    pnl_pct=scratch_res.scratch_exit_pnl_pct,
                    scratch_decision=scratch_res,
                    signed_v0_tx=scratch_res.signed_exit_v0_tx,
                )

        # 2. If in Stage 0 (before Stage 1 breakeven+ lock) and price drops into fractional drawdown rungs
        zero_loss_locked = bool(
            pos is not None
            and (
                getattr(pos, "zero_loss_ratchet_locked", False)
                or pos.high_water_mark_price_sol >= pos.entry_price_sol * 1.030
                or current_price_sol >= pos.entry_price_sol * 1.030
            )
        )
        if (
            pos is not None
            and pos.current_stage == 0
            and not pos.is_closed
            and not zero_loss_locked
        ):
            pnl_pct = ((current_price_sol - pos.entry_price_sol) / max(pos.entry_price_sol, 1e-12)) * 100.0
            if pnl_pct <= DRAWDOWN_RUNG_D3_PCT and not self.d3_executed.get(token_mint, False):
                self.d3_executed[token_mint] = True
                frac = pos.remaining_bag_fraction
                pos.remaining_bag_fraction = 0.0
                pos.remaining_tokens = 0.0
                pos.is_closed = True
                pos.close_reason = "DRAWDOWN_RUNG_D3_FINAL_15_5PCT"
                self.trail_engine._sync_slot_to_mmap(pos)
                v0_tx = self.trail_engine._build_exit_v0_tx(
                    mint=token_mint,
                    sol_notional=max(0.05, pos.initial_sol_invested * frac),
                    is_full_exit=True,
                )
                return BiDirectionalScaleDecision(
                    token_mint=token_mint,
                    decision_source="DRAWDOWN_RUNG_D3_FINAL",
                    action="CUT_100PCT_REMAINDER_AT_MINUS_15_5PCT",
                    fraction_sold=frac,
                    remaining_bag_fraction=0.0,
                    reclaimed_rent_lamports=ATA_RENT_LAMPORTS,
                    pnl_pct=round(pnl_pct, 3),
                    signed_v0_tx=v0_tx,
                )
            if pnl_pct <= DRAWDOWN_RUNG_D2_PCT and not self.d2_executed.get(token_mint, False):
                self.d2_executed[token_mint] = True
                cut_frac = round(pos.remaining_bag_fraction * 0.50, 4)
                pos.remaining_bag_fraction = round(pos.remaining_bag_fraction - cut_frac, 4)
                pos.remaining_tokens *= 0.50
                self.trail_engine._sync_slot_to_mmap(pos)
                v0_tx = self.trail_engine._build_exit_v0_tx(
                    mint=token_mint,
                    sol_notional=max(0.05, pos.initial_sol_invested * cut_frac),
                    is_full_exit=False,
                )
                return BiDirectionalScaleDecision(
                    token_mint=token_mint,
                    decision_source="DRAWDOWN_RUNG_D2",
                    action="CUT_50PCT_REMAINDER_AT_MINUS_10_5PCT",
                    fraction_sold=cut_frac,
                    remaining_bag_fraction=pos.remaining_bag_fraction,
                    reclaimed_rent_lamports=0,
                    pnl_pct=round(pnl_pct, 3),
                    signed_v0_tx=v0_tx,
                )
            if pnl_pct <= DRAWDOWN_RUNG_D1_PCT and not self.d1_executed.get(token_mint, False):
                self.d1_executed[token_mint] = True
                cut_frac = round(pos.remaining_bag_fraction * (1.0 / 3.0), 4)
                pos.remaining_bag_fraction = round(pos.remaining_bag_fraction - cut_frac, 4)
                pos.remaining_tokens *= 2.0 / 3.0
                self.trail_engine._sync_slot_to_mmap(pos)
                v0_tx = self.trail_engine._build_exit_v0_tx(
                    mint=token_mint,
                    sol_notional=max(0.05, pos.initial_sol_invested * cut_frac),
                    is_full_exit=False,
                )
                return BiDirectionalScaleDecision(
                    token_mint=token_mint,
                    decision_source="DRAWDOWN_RUNG_D1",
                    action="CUT_33PCT_AT_MINUS_5_5PCT",
                    fraction_sold=cut_frac,
                    remaining_bag_fraction=pos.remaining_bag_fraction,
                    reclaimed_rent_lamports=0,
                    pnl_pct=round(pnl_pct, 3),
                    signed_v0_tx=v0_tx,
                )

        # 3. Delegate to 4-Stage Ratcheting TrailWinEngine
        prev_bag = pos.remaining_bag_fraction if pos is not None else 1.0
        now_s_val = (
            (pos.opened_at_timestamp + elapsed_seconds)
            if (pos is not None and elapsed_seconds is not None)
            else None
        )
        trail_dec = self.trail_engine.evaluate_tick(
            mint=token_mint,
            current_price_sol=current_price_sol,
            now_s=now_s_val,
        )
        pos_after = self.trail_engine.positions.get(token_mint)
        pnl_now = (
            ((current_price_sol - pos_after.entry_price_sol) / max(pos_after.entry_price_sol, 1e-12)) * 100.0
            if pos_after is not None
            else 0.0
        )
        if trail_dec is None:
            return BiDirectionalScaleDecision(
                token_mint=token_mint,
                decision_source="TRAIL_WIN_ENGINE",
                action="POSITION_CLOSED",
                fraction_sold=0.0,
                remaining_bag_fraction=pos_after.remaining_bag_fraction if pos_after is not None else 0.0,
                reclaimed_rent_lamports=0,
                pnl_pct=round(pnl_now, 3),
                trail_decision=None,
                signed_v0_tx=None,
            )
        frac_sold = max(0.0, round(prev_bag - trail_dec.remaining_bag_fraction, 4))
        return BiDirectionalScaleDecision(
            token_mint=token_mint,
            decision_source="TRAIL_WIN_ENGINE",
            action=trail_dec.action,
            fraction_sold=frac_sold,
            remaining_bag_fraction=trail_dec.remaining_bag_fraction,
            reclaimed_rent_lamports=trail_dec.reclaimed_rent_lamports,
            pnl_pct=round(pnl_now, 3),
            trail_decision=trail_dec,
            signed_v0_tx=trail_dec.v0_tx,
        )

