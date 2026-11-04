"""Sovereign Titan OS — Horizon 3 & 4: Mid-Cap Second-Wave Swing Trader & Sub-Minute Wick Micro-Scalper (`src/horizons/horizon3_4_swing_and_scalp.py`).

Pinned to Threadripper PRO 9995WX Cores 24–31 (`taskset -c 24-31`).

Implements:
1. Horizon 3 — Mid-Cap Consolidation Breakout (`MC $400k to $50M+`, Age `1h to 14d`, `LP >= $75,000`):
   - Detects Multi-Hour Volatility Compression Boxes (4-hour high-low range `< 35%` while holder count and X mention velocity climb).
   - Triggers a Mid-Cap Swing Entry when price breaks above the consolidation box high + 4h Anchored VWAP
     on `>= 2.5x` average 5-minute volume (or when `>= 2` Mid-Cap Shadow Sharks accumulate within 10 minutes).
2. Horizon 4 — High-Frequency "Panic-Wick Absorption" Micro-Scalper (Hold `1s to 45s`):
   - Monitors mirrored pools (`LP >= $35,000`, 5m Volume `>= $50,000`) in an active uptrend (`Pre-Wick Price > 5m EMA-21`).
   - Detects a single non-deployer whale market-sell (`>= 3.0%` of pool LP) causing an instant `-10% to -22%`
     single-slot dislocation wick below the 30s EMA with zero dev rug flags.
   - Buys the bottom of the liquidation wick in the next 25ms Jito BAM batch tick, auto-scalps `70%` on a
     `+8% to +16%` snap-back bounce, and trails the remaining `30%` with a tight `3.5%` tick-level trailing stop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Optional

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


@dataclass
class MidCapConsolidationCandidate:
    """Telemetry snapshot for a Horizon 3 Mid-Cap Second-Wave Swing candidate."""

    mint: str
    symbol: str
    market_cap_usd: float  # $400k to $50M+
    pool_liquidity_usd: float  # >= $75,000
    token_age_hours: float  # 1.0h to 336.0h (14d)
    box_4h_high_price_sol: float
    box_4h_low_price_sol: float
    vwap_4h_price_sol: float
    current_price_sol: float
    current_5m_volume_usd: float
    avg_5m_volume_usd: float
    holder_count_growing: bool = True
    x_velocity_growing: bool = True
    midcap_shadow_sharks_10m: int = 0
    atr_1m_sol: float = 0.0
    timestamp_s: float = field(default_factory=time.time)

    @property
    def box_range_pct(self) -> float:
        if self.box_4h_low_price_sol <= 0.0:
            return 100.0
        return (
            (self.box_4h_high_price_sol - self.box_4h_low_price_sol)
            / self.box_4h_low_price_sol
        ) * 100.0

    @property
    def volume_5m_multiple(self) -> float:
        if self.avg_5m_volume_usd <= 0.0:
            return 0.0
        return self.current_5m_volume_usd / self.avg_5m_volume_usd


@dataclass
class Horizon3SwingDecision:
    """Output of evaluating a Horizon 3 Mid-Cap Consolidation Breakout."""

    mint: str
    triggered: bool
    reject_reason: Optional[str]
    box_range_pct: float
    volume_5m_multiple: float
    midcap_shadow_sharks_10m: int
    sol_allocated: float
    entry_price_sol: float
    trail_state: Optional[PositionTrailState] = None
    v0_buy_tx: Optional[AtomicTxBuildResult] = None
    eval_latency_ms: float = 0.0


@dataclass
class PanicWickDislocationEvent:
    """Single-slot non-deployer whale liquidation wick event for Horizon 4 Micro-Scalping."""

    mint: str
    symbol: str
    pool_liquidity_usd: float  # >= $35,000
    volume_5m_usd: float  # >= $50,000
    pre_wick_price_sol: float
    wick_bottom_price_sol: float
    ema_21_5m_price_sol: float
    ema_30s_price_sol: float
    whale_sell_lp_impact_pct: float  # >= 3.0% of pool LP
    is_deployer_or_insider_sell: bool = False
    has_dev_rug_flags: bool = False
    holder_count_rising: bool = True
    social_velocity_rising: bool = True
    slot: int = 343_000_100
    timestamp_s: float = field(default_factory=time.time)

    @property
    def wick_dislocation_pct(self) -> float:
        ref = max(self.pre_wick_price_sol, self.ema_30s_price_sol)
        if ref <= 0.0:
            return 0.0
        return ((ref - self.wick_bottom_price_sol) / ref) * 100.0


@dataclass
class Horizon4MicroScalpDecision:
    """Output of evaluating a Horizon 4 Panic-Wick Absorption Micro-Scalp."""

    mint: str
    triggered: bool
    reject_reason: Optional[str]
    wick_dislocation_pct: float
    whale_sell_lp_impact_pct: float
    target_snapback_price_sol: float
    sol_allocated: float
    entry_price_sol: float
    bam_tick_window_ms: int = 25
    trail_state: Optional[PositionTrailState] = None
    v0_buy_tx: Optional[AtomicTxBuildResult] = None
    eval_latency_ms: float = 0.0


class Horizon3And4SwingScalpEngine:
    """Combined Horizon 3 (Mid-Cap Second-Wave Swing) & Horizon 4 (Panic-Wick Micro-Scalper) Engine."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        trail_engine: Optional[TrailWinEngine] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        default_swing_sol: float = 4.0,
        default_microscalp_sol: float = 2.0,
    ) -> None:
        self.settings = config or get_settings()
        self.trail_engine = trail_engine or TrailWinEngine(self.settings)
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(self.settings)
        self.default_swing_sol = default_swing_sol
        self.default_microscalp_sol = default_microscalp_sol
        self._payer = Keypair()
        self._pool_pk = deterministic_pubkey("horizon3_4_pool_v1")
        self._vault_a = deterministic_pubkey("horizon3_4_vault_a")
        self._vault_b = deterministic_pubkey("horizon3_4_vault_b")

    def evaluate_horizon3_midcap_breakout(
        self,
        candidate: MidCapConsolidationCandidate,
        sol_allocation: Optional[float] = None,
    ) -> Horizon3SwingDecision:
        """Evaluates a Mid-Cap Volatility Compression Box breakout in `<0.5ms`."""
        t0 = time.perf_counter()

        if candidate.market_cap_usd < 400_000.0:
            return self._reject_h3(candidate, "MCAP_BELOW_400K", t0)

        if candidate.pool_liquidity_usd < 75_000.0:
            return self._reject_h3(candidate, "POOL_LP_BELOW_75K", t0)

        if not (1.0 <= candidate.token_age_hours <= 336.0):
            return self._reject_h3(candidate, "AGE_OUTSIDE_1H_TO_14D_WINDOW", t0)

        if candidate.box_range_pct >= 35.0:
            return self._reject_h3(
                candidate,
                f"4H_BOX_RANGE_TOO_WIDE ({candidate.box_range_pct:.1f}% >= 35.0%)",
                t0,
            )

        if not (candidate.holder_count_growing and candidate.x_velocity_growing):
            return self._reject_h3(
                candidate, "HOLDER_OR_X_VELOCITY_NOT_CLIMBING", t0
            )

        # Breakout above 4h box high AND 4h Anchored VWAP
        if (
            candidate.current_price_sol <= candidate.box_4h_high_price_sol
            or candidate.current_price_sol <= candidate.vwap_4h_price_sol
        ):
            return self._reject_h3(
                candidate, "PRICE_HAS_NOT_BROKEN_BOX_HIGH_AND_4H_VWAP", t0
            )

        # Volume >= 2.5x average 5m volume OR >= 2 Mid-Cap Shadow Sharks within 10m
        if (
            candidate.volume_5m_multiple < 2.5
            and candidate.midcap_shadow_sharks_10m < 2
        ):
            return self._reject_h3(
                candidate,
                f"INSUFFICIENT_BREAKOUT_VOLUME_OR_SHARKS (vol={candidate.volume_5m_multiple:.2f}x, sharks={candidate.midcap_shadow_sharks_10m})",
                t0,
            )

        alloc_sol = (
            sol_allocation if sol_allocation is not None else self.default_swing_sol
        )
        trail_state = self.trail_engine.register_position(
            mint=candidate.mint,
            entry_price_sol=candidate.current_price_sol,
            initial_sol_invested=alloc_sol,
            horizon="HORIZON_3_MIDCAP_SWING",
            symbol=candidate.symbol,
            atr_15s=candidate.atr_1m_sol,
            now_s=candidate.timestamp_s,
        )

        mint_pk = deterministic_pubkey(f"mint:{candidate.mint}")
        leg = DEXSwapLegSpec(
            program_id=deterministic_pubkey("raydium_v4_program"),
            pool_state=self._pool_pk,
            pool_Authority=deterministic_pubkey("raydium_v4_authority"),
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
            label="Horizon3MidCapSwingBuy",
        )
        v0_tx = self.tx_builder.build_directional_buy_v0(
            payer_keypair=self._payer,
            swap_leg=leg,
            compute_units=165_000,
            priority_micro_lamports=80_000,
        )

        return Horizon3SwingDecision(
            mint=candidate.mint,
            triggered=True,
            reject_reason=None,
            box_range_pct=round(candidate.box_range_pct, 2),
            volume_5m_multiple=round(candidate.volume_5m_multiple, 2),
            midcap_shadow_sharks_10m=candidate.midcap_shadow_sharks_10m,
            sol_allocated=alloc_sol,
            entry_price_sol=candidate.current_price_sol,
            trail_state=trail_state,
            v0_buy_tx=v0_tx,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )

    def evaluate_horizon4_wick_microscalp(
        self,
        event: PanicWickDislocationEvent,
        sol_allocation: Optional[float] = None,
    ) -> Horizon4MicroScalpDecision:
        """Evaluates a single-slot non-deployer whale liquidation wick in `<0.25ms`
        for immediate 25ms Jito BAM batch absorption.
        """
        t0 = time.perf_counter()

        if event.is_deployer_or_insider_sell or event.has_dev_rug_flags:
            return self._reject_h4(event, "DEPLOYER_OR_DEV_RUG_SELL", t0)

        if event.pool_liquidity_usd < 35_000.0 or event.volume_5m_usd < 50_000.0:
            return self._reject_h4(
                event,
                f"INSUFFICIENT_POOL_LP_OR_5M_VOL (LP=${event.pool_liquidity_usd:,.0f}, Vol5m=${event.volume_5m_usd:,.0f})",
                t0,
            )

        # Must be in active 5m uptrend prior to the single-slot liquidation wick
        if event.pre_wick_price_sol <= event.ema_21_5m_price_sol:
            return self._reject_h4(event, "NOT_IN_ACTIVE_5M_EMA21_UPTREND", t0)

        if event.whale_sell_lp_impact_pct < 3.0:
            return self._reject_h4(
                event,
                f"WHALE_SELL_LP_IMPACT_BELOW_3PCT ({event.whale_sell_lp_impact_pct:.2f}%)",
                t0,
            )

        dislocation = event.wick_dislocation_pct
        if not (10.0 <= dislocation <= 25.0):
            return self._reject_h4(
                event,
                f"WICK_DISLOCATION_OUTSIDE_10_TO_25PCT ({dislocation:.2f}%)",
                t0,
            )

        if not (event.holder_count_rising and event.social_velocity_rising):
            return self._reject_h4(
                event, "HOLDER_OR_SOCIAL_VELOCITY_DECLINING", t0
            )

        alloc_sol = (
            sol_allocation
            if sol_allocation is not None
            else self.default_microscalp_sol
        )
        trail_state = self.trail_engine.register_position(
            mint=event.mint,
            entry_price_sol=event.wick_bottom_price_sol,
            initial_sol_invested=alloc_sol,
            horizon="HORIZON_4_WICK_MICROSCALP",
            symbol=event.symbol,
            now_s=event.timestamp_s,
        )

        mint_pk = deterministic_pubkey(f"mint:{event.mint}")
        leg = DEXSwapLegSpec(
            program_id=deterministic_pubkey("raydium_v4_program"),
            pool_state=self._pool_pk,
            pool_Authority=deterministic_pubkey("raydium_v4_authority"),
            vault_in=self._vault_a,
            vault_out=self._vault_b,
            user_source_token_account=derive_associated_token_address(
                self._payer.pubkey(), Pubkey.from_string(WSOL_MINT_PUBKEY)
            ),
            user_destination_token_account=derive_associated_token_address(
                self._payer.pubkey(), mint_pk
            ),
            amount_in_lamports=int(alloc_sol * LAMPORTS_PER_SOL),
            min_amount_out_lamports=int(alloc_sol * 0.97 * LAMPORTS_PER_SOL),
            label="Horizon4WickMicroScalpBuy",
        )
        v0_tx = self.tx_builder.build_directional_buy_v0(
            payer_keypair=self._payer,
            swap_leg=leg,
            compute_units=145_000,
            priority_micro_lamports=95_000,
        )

        return Horizon4MicroScalpDecision(
            mint=event.mint,
            triggered=True,
            reject_reason=None,
            wick_dislocation_pct=round(dislocation, 2),
            whale_sell_lp_impact_pct=round(event.whale_sell_lp_impact_pct, 2),
            target_snapback_price_sol=round(event.wick_bottom_price_sol * 1.12, 8),
            sol_allocated=alloc_sol,
            entry_price_sol=event.wick_bottom_price_sol,
            bam_tick_window_ms=25,
            trail_state=trail_state,
            v0_buy_tx=v0_tx,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )

    @staticmethod
    def _reject_h3(
        c: MidCapConsolidationCandidate, reason: str, t0: float
    ) -> Horizon3SwingDecision:
        return Horizon3SwingDecision(
            mint=c.mint,
            triggered=False,
            reject_reason=reason,
            box_range_pct=round(c.box_range_pct, 2),
            volume_5m_multiple=round(c.volume_5m_multiple, 2),
            midcap_shadow_sharks_10m=c.midcap_shadow_sharks_10m,
            sol_allocated=0.0,
            entry_price_sol=c.current_price_sol,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )

    @staticmethod
    def _reject_h4(
        e: PanicWickDislocationEvent, reason: str, t0: float
    ) -> Horizon4MicroScalpDecision:
        return Horizon4MicroScalpDecision(
            mint=e.mint,
            triggered=False,
            reject_reason=reason,
            wick_dislocation_pct=round(e.wick_dislocation_pct, 2),
            whale_sell_lp_impact_pct=round(e.whale_sell_lp_impact_pct, 2),
            target_snapback_price_sol=round(e.wick_bottom_price_sol * 1.12, 8),
            sol_allocated=0.0,
            entry_price_sol=e.wick_bottom_price_sol,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )
