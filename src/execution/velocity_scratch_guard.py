"""Sovereign Titan OS — "3-Second Green-or-Scratch" Order-Flow Invalidator (`src/execution/velocity_scratch_guard.py`).

Enforces `/AGENTS.md` Rule 20:
During the first `3.0 seconds (15 Alpenglow slots at 200ms/slot)` after any directional fill
(`Shadow Executor`, `Horizon 1`, `Horizon 4`):
  1. Tracks `net_organic_buy_flow_after_entry_sol` and `max_favorable_excursion_pct`:
       `((high_water_mark_price - entry_price) / entry_price) * 100.0`
  2. Instant Scratch Rule:
     If at `T + 3.0s` (`>= 15 Alpenglow slots`),
       `max_favorable_excursion_pct < +1.8%` AND
       `net_organic_buy_flow_after_entry_sol < 1.2 * our_position_sol`
     (meaning no follow-through buyers joined behind us and momentum stalled):
     - Immediately fires a **100% Scratch Exit V0 Transaction + `close_account` ATA rent reclaim**
       (`0.00203928 SOL` / `2,039,280 lamports`) while price is hovering near `0.0% to -0.9%`
       breakeven, before the stalled candle rolls over into a real loss.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import time
from typing import Any, Dict, Literal, Optional

import orjson
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


SCRATCH_WINDOW_SECONDS = 3.0  # 3.0 seconds = 15 Alpenglow 200ms slots
SCRATCH_WINDOW_SLOTS = 15  # 15 * 200ms = 3,000ms
MIN_REQUIRED_MFE_PCT = 1.8  # +1.8% minimum favorable excursion
MIN_REQUIRED_ORGANIC_FLOW_MULT = 1.2  # >= 1.2x our_position_sol net organic buy inflow


@dataclass
class VelocityPositionWatch:
    """Tracks post-entry order flow and excursion during the first 15 Alpenglow slots (3.0s)."""

    token_mint: str
    engine_source: str  # "SHADOW" | "HORIZON_1" | "HORIZON_4"
    entry_price_sol: float
    current_price_sol: float
    high_water_mark_price_sol: float
    our_position_sol: float
    entry_slot: int
    current_slot: int
    opened_at_s: float
    net_organic_buy_flow_after_entry_sol: float = 0.0
    evaluated_3s_gate: bool = False
    scratched: bool = False
    scratch_reason: Optional[str] = None

    @property
    def max_favorable_excursion_pct(self) -> float:
        if self.entry_price_sol <= 0.0:
            return 0.0
        return ((self.high_water_mark_price_sol - self.entry_price_sol) / max(1e-12, self.entry_price_sol)) * 100.0

    @property
    def current_pnl_pct(self) -> float:
        if self.entry_price_sol <= 0.0:
            return 0.0
        return ((self.current_price_sol - self.entry_price_sol) / max(1e-12, self.entry_price_sol)) * 100.0


@dataclass
class VelocityScratchDecision:
    """Output of the 3-second (`15 Alpenglow slots`) Green-or-Scratch evaluation."""

    token_mint: str
    action: Literal["HOLD_PENDING_3S", "THESIS_CONFIRMED_CONTINUE", "SCRATCH_EXIT_100PCT_WITH_RENT"]
    triggered_scratch: bool
    reason: str
    elapsed_seconds: float
    slots_elapsed: int
    max_favorable_excursion_pct: float
    net_organic_buy_flow_after_entry_sol: float
    required_organic_flow_sol: float
    scratch_exit_pnl_pct: float
    reclaimed_rent_lamports: int
    latency_ms: float
    signed_exit_v0_tx: Optional[AtomicTxBuildResult] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["v0_tx_bytes"] = (
            self.signed_exit_v0_tx.serialized_size_bytes
            if self.signed_exit_v0_tx is not None
            else 0
        )
        d.pop("signed_exit_v0_tx", None)
        return d


class VelocityScratchGuard:
    """Sub-millisecond 3-Second (`15 Alpenglow Slots`) Green-or-Scratch Order-Flow Invalidator."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        payer_keypair: Optional[Keypair] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(self.settings)
        self.keypair = payer_keypair or Keypair()
        self.payer_pk = self.keypair.pubkey()
        self.wsol_ata = derive_associated_token_address(
            self.payer_pk, Pubkey.from_string(WSOL_MINT_PUBKEY)
        )
        self._raydium_prog_pk = Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID)
        self._pool_state_pk = self.tx_builder.alt_manager.get_pool_vault(0)
        self._pool_auth_pk = self.tx_builder.alt_manager.get_pool_vault(1)
        self._vault_in_pk = self.tx_builder.alt_manager.get_pool_vault(2)
        self._vault_out_pk = self.tx_builder.alt_manager.get_pool_vault(3)

        self.state_path: Path = (
            self.settings.RAMDISK_EXECUTION_STATE / "velocity_scratch_state.json"
        )
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.watches: Dict[str, VelocityPositionWatch] = {}
        self.scratch_saves_today: int = 0
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = orjson.loads(self.state_path.read_bytes())
            self.scratch_saves_today = int(data.get("scratch_saves_today", 0))
        except Exception:
            self.scratch_saves_today = 0

    def _persist_state(self) -> None:
        payload = {
            "updated_at_ns": time.time_ns(),
            "scratch_saves_today": self.scratch_saves_today,
            "active_watches": len(self.watches),
        }
        self.state_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))

    def register_entry(
        self,
        token_mint: str,
        entry_price_sol: float,
        our_position_sol: float,
        entry_slot: int = 342_815_000,
        engine_source: str = "SHADOW",
        opened_at_s: Optional[float] = None,
    ) -> VelocityPositionWatch:
        """Registers a newly filled directional trade for 15-slot (3.0s) velocity monitoring."""
        now_s = opened_at_s if opened_at_s is not None else time.time()
        watch = VelocityPositionWatch(
            token_mint=token_mint,
            engine_source=engine_source,
            entry_price_sol=float(entry_price_sol),
            current_price_sol=float(entry_price_sol),
            high_water_mark_price_sol=float(entry_price_sol),
            our_position_sol=float(our_position_sol),
            entry_slot=int(entry_slot),
            current_slot=int(entry_slot),
            opened_at_s=float(now_s),
        )
        self.watches[token_mint] = watch
        return watch

    def evaluate_post_entry_flow(
        self,
        token_mint: str,
        current_price_sol: float,
        net_organic_buy_flow_sol_delta: float = 0.0,
        elapsed_seconds: Optional[float] = None,
        current_slot: Optional[int] = None,
    ) -> VelocityScratchDecision:
        """Evaluates post-entry price excursion and organic buy inflow across the first 3.0s (15 slots)."""
        t0 = time.perf_counter_ns()
        watch = self.watches.get(token_mint)
        if watch is None:
            watch = self.register_entry(
                token_mint=token_mint,
                entry_price_sol=current_price_sol,
                our_position_sol=1.0,
            )

        watch.current_price_sol = float(current_price_sol)
        if current_price_sol > watch.high_water_mark_price_sol:
            watch.high_water_mark_price_sol = float(current_price_sol)
        watch.net_organic_buy_flow_after_entry_sol += float(net_organic_buy_flow_sol_delta)

        if current_slot is not None:
            watch.current_slot = int(current_slot)
            slots_elapsed = max(0, watch.current_slot - watch.entry_slot)
        else:
            slots_elapsed = int(((elapsed_seconds or 0.0) * 1000.0) // 200)

        if elapsed_seconds is not None:
            el_sec = float(elapsed_seconds)
        elif current_slot is not None:
            el_sec = slots_elapsed * 0.200
        else:
            el_sec = max(0.0, time.time() - watch.opened_at_s)

        mfe_pct = watch.max_favorable_excursion_pct
        req_flow_sol = MIN_REQUIRED_ORGANIC_FLOW_MULT * watch.our_position_sol
        net_flow = watch.net_organic_buy_flow_after_entry_sol

        # If momentum already confirmed before or at 3.0s, mark confirmed
        if mfe_pct >= MIN_REQUIRED_MFE_PCT or net_flow >= req_flow_sol:
            if el_sec >= SCRATCH_WINDOW_SECONDS or slots_elapsed >= SCRATCH_WINDOW_SLOTS:
                watch.evaluated_3s_gate = True
            lat_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return VelocityScratchDecision(
                token_mint=token_mint,
                action="THESIS_CONFIRMED_CONTINUE",
                triggered_scratch=False,
                reason=f"MOMENTUM_VALIDATED(MFE={mfe_pct:+.2f}%,Flow={net_flow:.2f}/{req_flow_sol:.2f}SOL)",
                elapsed_seconds=round(el_sec, 3),
                slots_elapsed=slots_elapsed,
                max_favorable_excursion_pct=round(mfe_pct, 3),
                net_organic_buy_flow_after_entry_sol=round(net_flow, 4),
                required_organic_flow_sol=round(req_flow_sol, 4),
                scratch_exit_pnl_pct=round(watch.current_pnl_pct, 3),
                reclaimed_rent_lamports=0,
                latency_ms=round(lat_ms, 4),
                signed_exit_v0_tx=None,
            )

        # Still inside the <3.0s (<15 slots) observation window
        if el_sec < SCRATCH_WINDOW_SECONDS and slots_elapsed < SCRATCH_WINDOW_SLOTS:
            lat_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return VelocityScratchDecision(
                token_mint=token_mint,
                action="HOLD_PENDING_3S",
                triggered_scratch=False,
                reason=f"OBSERVING_FIRST_15_SLOTS(t={el_sec:.2f}s/3.0s)",
                elapsed_seconds=round(el_sec, 3),
                slots_elapsed=slots_elapsed,
                max_favorable_excursion_pct=round(mfe_pct, 3),
                net_organic_buy_flow_after_entry_sol=round(net_flow, 4),
                required_organic_flow_sol=round(req_flow_sol, 4),
                scratch_exit_pnl_pct=round(watch.current_pnl_pct, 3),
                reclaimed_rent_lamports=0,
                latency_ms=round(lat_ms, 4),
                signed_exit_v0_tx=None,
            )

        # At T >= 3.0s (15 Alpenglow slots): BOTH MFE < +1.8% AND net_organic_buy_flow < 1.2 * our_position_sol
        # -> Fire instant 100% Scratch Exit + close_account ATA rent reclaim!
        watch.evaluated_3s_gate = True
        watch.scratched = True
        reason = (
            f"3S_VELOCITY_SCRATCH_INVALIDATED:"
            f"MFE={mfe_pct:+.2f}%<+1.80%_AND_Flow={net_flow:.2f}SOL<{req_flow_sol:.2f}SOL"
        )
        watch.scratch_reason = reason
        self.scratch_saves_today += 1
        self._persist_state()

        try:
            mint_pk = Pubkey.from_string(token_mint)
        except Exception:
            mint_pk = deterministic_pubkey(f"mint:{token_mint}")
        token_ata = derive_associated_token_address(self.payer_pk, mint_pk)
        self.tx_builder.alt_manager.register_custom_addresses([str(mint_pk), str(token_ata)])

        sell_lamports = max(1, int(watch.our_position_sol * LAMPORTS_PER_SOL))
        scratch_leg = DEXSwapLegSpec(
            program_id=self._raydium_prog_pk,
            pool_state=self._pool_state_pk,
            pool_authority=self._pool_auth_pk,
            vault_in=self._vault_out_pk,
            vault_out=self._vault_in_pk,
            user_source_token_account=token_ata,
            user_destination_token_account=self.wsol_ata,
            amount_in_lamports=sell_lamports,
            min_amount_out_lamports=int(sell_lamports * 0.985),
            label="3sVelocityScratchExit100Pct",
        )
        v0_tx = self.tx_builder.build_full_token_exit_v0(
            payer_keypair=self.keypair,
            swap_leg=scratch_leg,
            token_ata_to_close=token_ata,
        )

        lat_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return VelocityScratchDecision(
            token_mint=token_mint,
            action="SCRATCH_EXIT_100PCT_WITH_RENT",
            triggered_scratch=True,
            reason=reason,
            elapsed_seconds=round(el_sec, 3),
            slots_elapsed=max(slots_elapsed, SCRATCH_WINDOW_SLOTS),
            max_favorable_excursion_pct=round(mfe_pct, 3),
            net_organic_buy_flow_after_entry_sol=round(net_flow, 4),
            required_organic_flow_sol=round(req_flow_sol, 4),
            scratch_exit_pnl_pct=round(watch.current_pnl_pct, 3),
            reclaimed_rent_lamports=ATA_RENT_LAMPORTS,
            latency_ms=round(lat_ms, 4),
            signed_exit_v0_tx=v0_tx,
        )
