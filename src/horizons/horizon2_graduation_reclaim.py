"""Sovereign Titan OS — Horizon 2: Post-Bonding & Post-Graduation "First-Flush Reclaim" Engine (`src/horizons/horizon2_graduation_reclaim.py`).

Pinned to Threadripper PRO 9995WX Cores 24–31 (`taskset -c 24-31`).
Tracks newly graduated tokens across Raydium, PumpSwap, and Meteora for 60 minutes (`3,600s`) post-migration.

Implements:
1. Phase A (The Graduation Sniper-Flush Watch):
   - Records `graduation_open_mcap`, `post_grad_peak_mcap`, and initial top-20 bonding-curve holder concentration.
   - Never buys second-0 graduation candle tops blindly.
   - Waits for the mandatory sniper flush where price retraces `-30% to -65%` from `post_grad_peak_mcap`
     AND early top-20 bonding-curve holders reduce their concentration by `>= 25%`.
2. Phase B (The Higher-Low + 1m VWAP Reclaim Trigger):
   - Fires a Horizon 2 Post-Graduation Entry on the exact 200ms slot when ALL 4 conditions align:
     1. Price forms a Higher Low on the `15s / 1m` structure and reclaims the Post-Graduation 1-Minute Anchored VWAP.
     2. Rolling 15-second order flow flips strongly bullish (`Buy_SOL_Volume >= 1.8x Sell_SOL_Volume` across `>= 10` unique buyers).
     3. `DexScreener Paid / Boost` status is verified active (or `>= 1` tracked `<2 Fast-Bot` Post-Migration Shark from `ACTIVE_SHADOW_LIST` enters the dip).
     4. Pool liquidity is `>= $22,000` with Mint/Freeze authority revoked.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import time
from typing import Deque, Dict, Literal, Optional, Set

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import WSOL_MINT_PUBKEY, deterministic_pubkey
from src.execution.atomic_tx_builder import (
    AtomicTxBuildResult,
    AtomicV0TransactionBuilder,
    derive_associated_token_address,
)
from src.execution.flash_loan_builder import DEXSwapLegSpec, LAMPORTS_PER_SOL
from src.execution.trail_win_engine import PositionTrailState, TrailWinEngine


GraduationVenue = Literal["RAYDIUM_V4", "RAYDIUM_CPMM", "PUMPSWAP", "METEORA_DLMM"]
FlushPhase = Literal[
    "WATCHING_INITIAL_CANDLE",
    "FLUSH_ZONE_ARMED",
    "RECLAIM_TRIGGERED",
    "EXPIRED",
]

POST_GRAD_WATCH_WINDOW_SEC = 3600.0  # 60 minutes


@dataclass
class PostGradSwapTick:
    """Single post-graduation swap tick for anchored 1m VWAP and 15s order-flow calculation."""

    timestamp_s: float
    slot: int
    wallet: str
    side: Literal["BUY", "SELL"]
    sol_amount: float
    price_sol: float
    market_cap_usd: float


@dataclass
class GraduatedTokenWatchState:
    """State machine tracking a graduated token through Phase A (Sniper Flush) and Phase B (1m VWAP Reclaim)."""

    mint: str
    symbol: str
    venue: GraduationVenue
    graduated_at_s: float
    graduation_open_mcap: float
    post_grad_peak_mcap: float
    graduation_open_price_sol: float
    post_grad_peak_price_sol: float
    flush_low_mcap: float
    flush_low_price_sol: float
    higher_low_price_sol: float
    initial_top20_holder_pct: float
    current_top20_holder_pct: float
    flush_zone_reached: bool = False
    higher_low_confirmed: bool = False
    phase: FlushPhase = "WATCHING_INITIAL_CANDLE"
    swaps_1m: Deque[PostGradSwapTick] = field(default_factory=deque)

    @property
    def max_flush_drawdown_pct(self) -> float:
        if self.post_grad_peak_mcap <= 0.0:
            return 0.0
        return (
            (self.post_grad_peak_mcap - self.flush_low_mcap)
            / self.post_grad_peak_mcap
        ) * 100.0

    @property
    def top20_holder_reduction_pct(self) -> float:
        if self.initial_top20_holder_pct <= 0.0:
            return 0.0
        return (
            (self.initial_top20_holder_pct - self.current_top20_holder_pct)
            / self.initial_top20_holder_pct
        ) * 100.0


@dataclass
class Horizon2ReclaimDecision:
    """Result of evaluating a graduated token for a Horizon 2 First-Flush Reclaim entry."""

    mint: str
    triggered: bool
    phase: FlushPhase
    reject_reason: Optional[str]
    flush_drawdown_pct: float
    top20_reduction_pct: float
    vwap_1m_sol: float
    current_price_sol: float
    buy_sell_ratio_15s: float
    unique_buyers_15s: int
    sol_allocated: float
    trail_state: Optional[PositionTrailState] = None
    v0_buy_tx: Optional[AtomicTxBuildResult] = None
    eval_latency_ms: float = 0.0


class Horizon2GraduationReclaimEngine:
    """Horizon 2: Post-Bonding & Post-Graduation 'First-Flush Reclaim' Engine (Cores 24–31)."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        trail_engine: Optional[TrailWinEngine] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        default_reclaim_sol: float = 2.5,
    ) -> None:
        self.settings = config or get_settings()
        self.trail_engine = trail_engine or TrailWinEngine(self.settings)
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(self.settings)
        self.default_reclaim_sol = default_reclaim_sol
        self.watched_tokens: Dict[str, GraduatedTokenWatchState] = {}
        self._payer = Keypair()
        self._pool_pk = deterministic_pubkey("horizon2_grad_reclaim_pool")
        self._vault_a = deterministic_pubkey("horizon2_grad_vault_a")
        self._vault_b = deterministic_pubkey("horizon2_grad_vault_b")

    def register_graduation(
        self,
        mint: str,
        symbol: str,
        venue: GraduationVenue,
        graduation_open_mcap: float,
        graduation_open_price_sol: float,
        initial_top20_holder_pct: float = 48.0,
        graduated_at_s: Optional[float] = None,
    ) -> GraduatedTokenWatchState:
        """Registers a token at the moment it graduates to Raydium, PumpSwap, or Meteora."""
        ts = graduated_at_s if graduated_at_s is not None else time.time()
        state = GraduatedTokenWatchState(
            mint=mint,
            symbol=symbol,
            venue=venue,
            graduated_at_s=ts,
            graduation_open_mcap=graduation_open_mcap,
            post_grad_peak_mcap=graduation_open_mcap,
            graduation_open_price_sol=graduation_open_price_sol,
            post_grad_peak_price_sol=graduation_open_price_sol,
            flush_low_mcap=graduation_open_mcap,
            flush_low_price_sol=graduation_open_price_sol,
            higher_low_price_sol=graduation_open_price_sol,
            initial_top20_holder_pct=initial_top20_holder_pct,
            current_top20_holder_pct=initial_top20_holder_pct,
        )
        self.watched_tokens[mint] = state
        return state

    def ingest_post_grad_swap(
        self,
        mint: str,
        tick: PostGradSwapTick,
        current_top20_holder_pct: Optional[float] = None,
    ) -> Optional[GraduatedTokenWatchState]:
        """Updates Phase A peak/flush tracking and 1m anchored VWAP window."""
        state = self.watched_tokens.get(mint)
        if state is None:
            return None

        if (tick.timestamp_s - state.graduated_at_s) > POST_GRAD_WATCH_WINDOW_SEC:
            state.phase = "EXPIRED"
            return state

        if current_top20_holder_pct is not None:
            state.current_top20_holder_pct = current_top20_holder_pct

        state.swaps_1m.append(tick)
        cutoff_1m = tick.timestamp_s - 60.0
        while state.swaps_1m and state.swaps_1m[0].timestamp_s < cutoff_1m:
            state.swaps_1m.popleft()

        # Track post-graduation peak prior to flush
        if not state.flush_zone_reached and tick.market_cap_usd > state.post_grad_peak_mcap:
            state.post_grad_peak_mcap = tick.market_cap_usd
            state.post_grad_peak_price_sol = tick.price_sol
            state.flush_low_mcap = tick.market_cap_usd
            state.flush_low_price_sol = tick.price_sol

        # Track sniper-flush low
        if tick.market_cap_usd < state.flush_low_mcap:
            state.flush_low_mcap = tick.market_cap_usd
            state.flush_low_price_sol = tick.price_sol

        flush_dd = state.max_flush_drawdown_pct
        holder_red = state.top20_holder_reduction_pct

        # Phase A: -30% to -65% retracement from post_grad_peak_mcap AND >= 25% top-20 reduction
        if 30.0 <= flush_dd <= 65.0 and holder_red >= 25.0:
            state.flush_zone_reached = True
            if state.phase == "WATCHING_INITIAL_CANDLE":
                state.phase = "FLUSH_ZONE_ARMED"

        # Detect Higher Low formation after flush low
        if (
            state.flush_zone_reached
            and tick.price_sol > state.flush_low_price_sol * 1.03
        ):
            state.higher_low_price_sol = max(
                state.flush_low_price_sol * 1.03,
                min(tick.price_sol, state.post_grad_peak_price_sol),
            )
            state.higher_low_confirmed = True

        return state

    def compute_anchored_1m_vwap(self, mint: str) -> float:
        state = self.watched_tokens.get(mint)
        if state is None or not state.swaps_1m:
            return 0.0
        total_pv = sum(t.price_sol * max(0.01, t.sol_amount) for t in state.swaps_1m)
        total_v = sum(max(0.01, t.sol_amount) for t in state.swaps_1m)
        return total_pv / total_v if total_v > 0.0 else 0.0

    def evaluate_reclaim_entry(
        self,
        mint: str,
        current_price_sol: float,
        current_mcap_usd: float,
        pool_liquidity_usd: float,
        mint_freeze_revoked: bool = True,
        dexscreener_paid_or_boosted: bool = False,
        active_shadow_shark_buys: int = 0,
        override_vwap_1m_sol: Optional[float] = None,
        sol_allocation: Optional[float] = None,
        now_s: Optional[float] = None,
    ) -> Horizon2ReclaimDecision:
        """Evaluates Phase A & Phase B conditions in `<0.5ms` and fires a Horizon 2 Reclaim Entry."""
        t0 = time.perf_counter()
        state = self.watched_tokens.get(mint)
        if state is None:
            return Horizon2ReclaimDecision(
                mint=mint,
                triggered=False,
                phase="WATCHING_INITIAL_CANDLE",
                reject_reason="TOKEN_NOT_REGISTERED_IN_GRADUATION_WATCH",
                flush_drawdown_pct=0.0,
                top20_reduction_pct=0.0,
                vwap_1m_sol=0.0,
                current_price_sol=current_price_sol,
                buy_sell_ratio_15s=0.0,
                unique_buyers_15s=0,
                sol_allocated=0.0,
                eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
            )

        ts = now_s if now_s is not None else (
            state.swaps_1m[-1].timestamp_s if state.swaps_1m else time.time()
        )
        vwap_1m = (
            override_vwap_1m_sol
            if override_vwap_1m_sol is not None
            else self.compute_anchored_1m_vwap(mint)
        )

        cutoff_15s = ts - 15.0
        swaps_15s = [s for s in state.swaps_1m if s.timestamp_s >= cutoff_15s]
        buy_vol_15s = sum(s.sol_amount for s in swaps_15s if s.side == "BUY")
        sell_vol_15s = sum(s.sol_amount for s in swaps_15s if s.side == "SELL")
        buy_sell_ratio = (
            buy_vol_15s / max(0.01, sell_vol_15s)
            if sell_vol_15s > 0.0
            else buy_vol_15s * 10.0
        )
        unique_buyers: Set[str] = {
            s.wallet for s in swaps_15s if s.side == "BUY"
        }

        # Guard against buying second-0 graduation top before Phase A Sniper Flush completes
        if not state.flush_zone_reached:
            return self._reject(
                state,
                "PHASE_A_SNIPER_FLUSH_NOT_COMPLETE",
                vwap_1m,
                current_price_sol,
                buy_sell_ratio,
                len(unique_buyers),
                t0,
            )

        # Condition 1: Higher Low on 15s/1m structure + 1m Anchored VWAP Reclaim
        if not state.higher_low_confirmed or current_price_sol <= state.flush_low_price_sol:
            return self._reject(
                state,
                "HIGHER_LOW_NOT_CONFIRMED",
                vwap_1m,
                current_price_sol,
                buy_sell_ratio,
                len(unique_buyers),
                t0,
            )

        if vwap_1m <= 0.0 or current_price_sol < vwap_1m:
            return self._reject(
                state,
                f"BELOW_1M_ANCHORED_VWAP ({current_price_sol:.8f} < {vwap_1m:.8f})",
                vwap_1m,
                current_price_sol,
                buy_sell_ratio,
                len(unique_buyers),
                t0,
            )

        # Condition 2: 15s Buy_SOL_Volume >= 1.8x Sell_SOL_Volume across >= 10 unique buyers
        if buy_sell_ratio < 1.8 or len(unique_buyers) < 10:
            return self._reject(
                state,
                f"INSUFFICIENT_15S_ORDER_FLOW (ratio={buy_sell_ratio:.2f}x, buyers={len(unique_buyers)})",
                vwap_1m,
                current_price_sol,
                buy_sell_ratio,
                len(unique_buyers),
                t0,
            )

        # Condition 3: DexScreener Paid/Boost active OR >= 1 tracked Active Shadow Shark buy
        if not dexscreener_paid_or_boosted and active_shadow_shark_buys < 1:
            return self._reject(
                state,
                "NO_DEXSCREENER_BOOST_OR_SHADOW_SHARK_CONFIRMATION",
                vwap_1m,
                current_price_sol,
                buy_sell_ratio,
                len(unique_buyers),
                t0,
            )

        # Condition 4: Pool liquidity >= $22,000 with Mint/Freeze authority revoked
        if pool_liquidity_usd < 22_000.0 or not mint_freeze_revoked:
            return self._reject(
                state,
                f"POOL_LIQUIDITY_OR_AUTHORITY_FAIL (LP=${pool_liquidity_usd:,.0f}, revoked={mint_freeze_revoked})",
                vwap_1m,
                current_price_sol,
                buy_sell_ratio,
                len(unique_buyers),
                t0,
            )

        state.phase = "RECLAIM_TRIGGERED"
        alloc_sol = (
            sol_allocation if sol_allocation is not None else self.default_reclaim_sol
        )

        # If Horizon 1 already carried a 30% moonbag for this mint, add to or register position
        existing_pos = self.trail_engine.positions.get(mint)
        if existing_pos is not None and not existing_pos.is_closed:
            add_tokens = alloc_sol / current_price_sol
            existing_pos.initial_sol_invested += alloc_sol
            existing_pos.initial_tokens += add_tokens
            existing_pos.remaining_tokens += add_tokens
            existing_pos.horizon = "HORIZON_2_GRADUATION_RECLAIM"
            trail_state = existing_pos
        else:
            trail_state = self.trail_engine.register_position(
                mint=mint,
                entry_price_sol=current_price_sol,
                initial_sol_invested=alloc_sol,
                horizon="HORIZON_2_GRADUATION_RECLAIM",
                symbol=state.symbol,
                now_s=ts,
            )

        mint_pk = deterministic_pubkey(f"mint:{mint}")
        leg = DEXSwapLegSpec(
            program_id=deterministic_pubkey("pumpswap_amm_program"),
            pool_state=self._pool_pk,
            pool_Authority=deterministic_pubkey("pumpswap_amm_authority"),
            vault_in=self._vault_a,
            vault_out=self._vault_b,
            user_source_token_account=derive_associated_token_address(
                self._payer.pubkey(), Pubkey.from_string(WSOL_MINT_PUBKEY)
            ),
            user_destination_token_account=derive_associated_token_address(
                self._payer.pubkey(), mint_pk
            ),
            amount_in_lamports=int(alloc_sol * LAMPORTS_PER_SOL),
            min_amount_out_lamports=int(alloc_sol * 0.96 * LAMPORTS_PER_SOL),
            label="Horizon2ReclaimBuy",
        )
        v0_tx = self.tx_builder.build_directional_buy_v0(
            payer_keypair=self._payer,
            swap_leg=leg,
            compute_units=165_000,
            priority_micro_lamports=85_000,
        )

        return Horizon2ReclaimDecision(
            mint=mint,
            triggered=True,
            phase="RECLAIM_TRIGGERED",
            reject_reason=None,
            flush_drawdown_pct=round(state.max_flush_drawdown_pct, 2),
            top20_reduction_pct=round(state.top20_holder_reduction_pct, 2),
            vwap_1m_sol=round(vwap_1m, 8),
            current_price_sol=current_price_sol,
            buy_sell_ratio_15s=round(buy_sell_ratio, 2),
            unique_buyers_15s=len(unique_buyers),
            sol_allocated=alloc_sol,
            trail_state=trail_state,
            v0_buy_tx=v0_tx,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )

    @staticmethod
    def _reject(
        state: GraduatedTokenWatchState,
        reason: str,
        vwap_1m: float,
        current_price: float,
        buy_sell_ratio: float,
        unique_buyers: int,
        t0: float,
    ) -> Horizon2ReclaimDecision:
        return Horizon2ReclaimDecision(
            mint=state.mint,
            triggered=False,
            phase=state.phase,
            reject_reason=reason,
            flush_drawdown_pct=round(state.max_flush_drawdown_pct, 2),
            top20_reduction_pct=round(state.top20_holder_reduction_pct, 2),
            vwap_1m_sol=round(vwap_1m, 8),
            current_price_sol=current_price,
            buy_sell_ratio_15s=round(buy_sell_ratio, 2),
            unique_buyers_15s=unique_buyers,
            sol_allocated=0.0,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )
