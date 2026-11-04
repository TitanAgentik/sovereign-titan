"""Sovereign Titan OS — Horizon 1: Pre-Bonding Curve Velocity & Migration Scalp Engine (`src/horizons/horizon1_bonding_scalp.py`).

Pinned to Threadripper PRO 9995WX Cores 24–31 (`taskset -c 24-31`).
Listens to `PumpPortal WebSocket` + Helius `preconfSubscribe` on Pump.fun, Moonshot,
and Raydium LaunchLab bonding curves.

Implements:
1. Organic Curve Velocity Detector & Hard Anti-Rug Pre-Filter:
   - Rejects immediately if:
     - Top 5 non-bonding-curve wallets hold `> 18.0%` of supply, OR
     - Same-slot/0-block developer bundle exceeds `12.0%` of supply, OR
     - Creator wallet has sold `> 0.5%` of supply or has a prior rug history in `/mnt/ramdisk/alpha_graph`, OR
     - RAM `pHash` check flags the icon/banner as a `VAMPIRE_CLONE`.
2. Two Pre-Bonding Entry Setups:
   - Setup 1A (`MID_CURVE_VELOCITY_BREAKOUT` — `22.0% to 75.0%` Curve):
     Bonding curve completion surges `>= +12.0%` within a rolling `15-second` window driven by
     `>= 18` independent wallets (verified unlinked in `burner_graph.py`) with `Buy_Volume / Sell_Volume >= 2.8x`.
   - Setup 1B (`PRE_GRADUATION_KOTH_FRONTRUN` — `86.0% to 96.0%` Curve):
     Token with strong X/Telegram narrative velocity (`narrative_score >= 75`) crosses `86.0%`
     bonding curve completion with accelerating buy flow (`Buy_Volume / Sell_Volume >= 2.0x`),
     entering prior to the 100% bonding lock.
3. Pre-Bonding Scalp Exit & Graduation Carry Rule:
   - Scales out `40%` at `+25%` profit (`1.25x`).
   - Scales out `30%` at `98.5%` bonding curve completion.
   - Carries the remaining `30%` ("Risk-Free Graduation Moonbag") across the migration bridge
     into Horizon 2 managed by `TrailWinEngine`.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import time
from typing import Deque, Dict, List, Literal, Optional, Set, Tuple

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
from src.execution.trail_win_engine import (
    PositionTrailState,
    TrailEvaluationDecision,
    TrailWinEngine,
)
from src.graph.burner_graph import BurnerGraph
from src.intelligence.pre_scorer_cache import BackgroundPreScorerCache
from src.intelligence.vision_scam_filter import VisionScamFilter


BondingVenue = Literal["PUMPFUN", "MOONSHOT", "RAYDIUM_LAUNCHLAB"]
Horizon1SetupType = Literal[
    "SETUP_1A_MID_CURVE_VELOCITY",
    "SETUP_1B_KOTH_MIGRATION_FRONTRUN",
    "NONE",
]


@dataclass
class BondingCurveSwapSample:
    """Single bonding-curve swap sample within the rolling 15-second window."""

    timestamp_s: float
    slot: int
    buyer_wallet: str
    side: Literal["BUY", "SELL"]
    sol_amount: float
    curve_completion_pct: float
    price_sol: float


@dataclass
class BondingCurveTokenSnapshot:
    """Real-time Pump.fun / Moonshot / LaunchLab bonding-curve telemetry snapshot."""

    mint: str
    symbol: str
    venue: BondingVenue
    creator_wallet: str
    curve_completion_pct: float  # 0.0 to 100.0
    current_price_sol: float
    market_cap_usd: float
    top5_non_curve_holders_pct: float  # Reject if > 18.0%
    dev_same_slot_bundle_pct: float  # Reject if > 12.0%
    creator_sold_supply_pct: float  # Reject if > 0.5%
    creator_has_prior_rug: bool = False
    banner_phash_u64: int = 0
    narrative_score: float = 82.0  # 0..100 X/Telegram narrative velocity
    timestamp_s: float = field(default_factory=time.time)
    slot: int = 343_000_000


@dataclass
class Horizon1EntryDecision:
    """Output of evaluating a bonding-curve token for Horizon 1 entry."""

    mint: str
    triggered: bool
    setup_type: Horizon1SetupType
    reject_reason: Optional[str]
    curve_completion_pct: float
    curve_velocity_15s_pct: float
    independent_buyers_15s: int
    buy_sell_ratio_15s: float
    sol_allocated: float
    entry_price_sol: float
    trail_state: Optional[PositionTrailState] = None
    v0_buy_tx: Optional[AtomicTxBuildResult] = None
    eval_latency_ms: float = 0.0


class Horizon1BondingScalpEngine:
    """Horizon 1: Pre-Bonding Curve Velocity & Migration Scalp Engine (Cores 24–31)."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        trail_engine: Optional[TrailWinEngine] = None,
        burner_graph: Optional[BurnerGraph] = None,
        pre_scorer_cache: Optional[BackgroundPreScorerCache] = None,
        vision_filter: Optional[VisionScamFilter] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        default_scalp_sol: float = 1.5,
    ) -> None:
        self.settings = config or get_settings()
        self.trail_engine = trail_engine or TrailWinEngine(self.settings)
        self.burner_graph = burner_graph or BurnerGraph(self.settings)
        self.pre_scorer_cache = pre_scorer_cache or BackgroundPreScorerCache(
            self.settings
        )
        self.vision_filter = vision_filter or VisionScamFilter(self.settings)
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(self.settings)
        self.default_scalp_sol = default_scalp_sol

        self._swap_windows: Dict[str, Deque[BondingCurveSwapSample]] = {}
        self._curve_history: Dict[str, Deque[Tuple[float, float]]] = {}
        self._known_rug_creators: Set[str] = set()
        self._payer = Keypair()
        self._pool_pk = deterministic_pubkey("horizon1_bonding_curve_pool")
        self._vault_a = deterministic_pubkey("horizon1_bonding_vault_a")
        self._vault_b = deterministic_pubkey("horizon1_bonding_vault_b")

    def register_rug_creator(self, creator_wallet: str) -> None:
        """Marks a creator wallet as having a prior rug history in `/mnt/ramdisk/alpha_graph`."""
        self._known_rug_creators.add(creator_wallet)

    def ingest_curve_swap(self, mint: str, sample: BondingCurveSwapSample) -> None:
        """Records a real-time bonding curve swap in the 15-second rolling RAM window."""
        q = self._swap_windows.setdefault(mint, deque())
        q.append(sample)
        cutoff = sample.timestamp_s - 15.0
        while q and q[0].timestamp_s < cutoff:
            q.popleft()

        cq = self._curve_history.setdefault(mint, deque())
        cq.append((sample.timestamp_s, sample.curve_completion_pct))
        while cq and cq[0][0] < cutoff:
            cq.popleft()

    def _count_independent_unlinked_buyers(
        self, wallets: List[str]
    ) -> int:
        """Counts unique buyers that are NOT linked to one another in `burner_graph.py`."""
        unique_wallets = list(dict.fromkeys(wallets))
        independent_roots: Set[str] = set()
        for w in unique_wallets:
            idx = self.burner_graph._wallet_to_idx.get(w)
            if idx is not None:
                node = self.burner_graph._nodes[idx]
                root = node.root_shark_wallet or w
                independent_roots.add(root)
            else:
                independent_roots.add(w)
        return len(independent_roots)

    def evaluate_pre_bonding_entry(
        self,
        snapshot: BondingCurveTokenSnapshot,
        sol_allocation: Optional[float] = None,
    ) -> Horizon1EntryDecision:
        """Evaluates hard anti-rug filters and Setups 1A / 1B in `<0.5ms`."""
        t0 = time.perf_counter()
        mint = snapshot.mint

        # ------------------------------------------------------------------
        # 1. HARD ANTI-RUG PRE-FILTER
        # ------------------------------------------------------------------
        if snapshot.top5_non_curve_holders_pct > 18.0:
            return self._reject(
                snapshot,
                f"TOP5_CONCENTRATION_TOO_HIGH ({snapshot.top5_non_curve_holders_pct:.1f}% > 18.0%)",
                t0,
            )

        if snapshot.dev_same_slot_bundle_pct > 12.0:
            return self._reject(
                snapshot,
                f"DEV_0BLOCK_BUNDLE_EXCEEDED ({snapshot.dev_same_slot_bundle_pct:.1f}% > 12.0%)",
                t0,
            )

        if (
            snapshot.creator_sold_supply_pct > 0.5
            or snapshot.creator_has_prior_rug
            or snapshot.creator_wallet in self._known_rug_creators
        ):
            return self._reject(
                snapshot,
                f"CREATOR_SOLD_OR_PRIOR_RUG (sold={snapshot.creator_sold_supply_pct:.2f}%)",
                t0,
            )

        if snapshot.banner_phash_u64 != 0:
            phash_res = self.vision_filter.check_phash_fast(
                mint=mint, phash_u64=snapshot.banner_phash_u64, auto_insert_if_clean=False
            )
            if phash_res.status == "VAMPIRE_CLONE":
                return self._reject(
                    snapshot,
                    f"PHASH_VAMPIRE_CLONE (matched={phash_res.matched_older_mint}, d={phash_res.hamming_distance})",
                    t0,
                )

        # ------------------------------------------------------------------
        # 2. ROLLING 15-SECOND VELOCITY & INDEPENDENT BUYER METRICS
        # ------------------------------------------------------------------
        swaps = list(self._swap_windows.get(mint, ()))
        cutoff = snapshot.timestamp_s - 15.0
        recent_swaps = [s for s in swaps if s.timestamp_s >= cutoff]

        buy_vol = sum(s.sol_amount for s in recent_swaps if s.side == "BUY")
        sell_vol = sum(s.sol_amount for s in recent_swaps if s.side == "SELL")
        buy_sell_ratio = buy_vol / max(0.01, sell_vol) if sell_vol > 0 else (buy_vol * 10.0)

        buyer_wallets = [s.buyer_wallet for s in recent_swaps if s.side == "BUY"]
        independent_buyers = self._count_independent_unlinked_buyers(buyer_wallets)

        curve_hist = list(self._curve_history.get(mint, ()))
        if curve_hist:
            earliest_pct = curve_hist[0][1]
            curve_velocity_15s = snapshot.curve_completion_pct - earliest_pct
        else:
            curve_velocity_15s = 0.0

        # Check cached narrative score if available in /mnt/ramdisk/pre_approved_tokens
        cached_state = self.pre_scorer_cache.get_fast(mint, now_s=snapshot.timestamp_s)
        effective_narrative_score = snapshot.narrative_score
        if cached_state is not None:
            effective_narrative_score = max(
                effective_narrative_score,
                cached_state.vision_narrative_score * 100.0,
            )

        # ------------------------------------------------------------------
        # 3. ENTRY SETUP 1A vs SETUP 1B
        # ------------------------------------------------------------------
        setup_type: Horizon1SetupType = "NONE"
        curve_pct = snapshot.curve_completion_pct

        if (
            22.0 <= curve_pct <= 75.0
            and curve_velocity_15s >= 12.0
            and independent_buyers >= 18
            and buy_sell_ratio >= 2.8
        ):
            setup_type = "SETUP_1A_MID_CURVE_VELOCITY"
        elif (
            86.0 <= curve_pct <= 96.0
            and effective_narrative_score >= 75.0
            and buy_sell_ratio >= 2.0
            and curve_velocity_15s > 0.0
        ):
            setup_type = "SETUP_1B_KOTH_MIGRATION_FRONTRUN"

        if setup_type == "NONE":
            return Horizon1EntryDecision(
                mint=mint,
                triggered=False,
                setup_type="NONE",
                reject_reason="VELOCITY_OR_CURVE_ZONE_NOT_MET",
                curve_completion_pct=curve_pct,
                curve_velocity_15s_pct=round(curve_velocity_15s, 2),
                independent_buyers_15s=independent_buyers,
                buy_sell_ratio_15s=round(buy_sell_ratio, 2),
                sol_allocated=0.0,
                entry_price_sol=snapshot.current_price_sol,
                eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
            )

        alloc_sol = sol_allocation if sol_allocation is not None else self.default_scalp_sol
        trail_state = self.trail_engine.register_position(
            mint=mint,
            entry_price_sol=snapshot.current_price_sol,
            initial_sol_invested=alloc_sol,
            horizon="HORIZON_1_BONDING_SCALP",
            symbol=snapshot.symbol,
            now_s=snapshot.timestamp_s,
        )

        # Build directional V0 buy with mandatory `jitodontfront` in Instruction 0
        mint_pk = deterministic_pubkey(f"mint:{mint}")
        leg = DEXSwapLegSpec(
            program_id=deterministic_pubkey("pumpfun_bonding_program"),
            pool_state=self._pool_pk,
            pool_Authority=deterministic_pubkey("pumpfun_bonding_authority"),
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
            label=setup_type,
        )
        v0_tx = self.tx_builder.build_directional_buy_v0(
            payer_keypair=self._payer,
            swap_leg=leg,
            compute_units=150_000,
            priority_micro_lamports=75_000,
        )

        return Horizon1EntryDecision(
            mint=mint,
            triggered=True,
            setup_type=setup_type,
            reject_reason=None,
            curve_completion_pct=curve_pct,
            curve_velocity_15s_pct=round(curve_velocity_15s, 2),
            independent_buyers_15s=independent_buyers,
            buy_sell_ratio_15s=round(buy_sell_ratio, 2),
            sol_allocated=alloc_sol,
            entry_price_sol=snapshot.current_price_sol,
            trail_state=trail_state,
            v0_buy_tx=v0_tx,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )

    def evaluate_curve_tick_and_carry(
        self,
        mint: str,
        current_price_sol: float,
        curve_completion_pct: float,
        buy_volume_3s_sol: float = 12.0,
        sell_volume_3s_sol: float = 2.0,
        now_s: Optional[float] = None,
    ) -> TrailEvaluationDecision:
        """Evaluates an open Horizon 1 position:
        - Scales out 40% at +25% (1.25x)
        - Scales out 30% at 98.5% bonding curve completion
        - Carries remaining 30% Risk-Free Graduation Moonbag into Horizon 2 upon migration (100%).
        """
        decision = self.trail_engine.evaluate_tick(
            mint=mint,
            current_price_sol=current_price_sol,
            buy_volume_3s_sol=buy_volume_3s_sol,
            sell_volume_3s_sol=sell_volume_3s_sol,
            bonding_curve_pct=curve_completion_pct,
            now_s=now_s,
        )
        pos = self.trail_engine.positions.get(mint)
        if (
            pos is not None
            and not pos.is_closed
            and curve_completion_pct >= 99.5
            and pos.remaining_bag_fraction > 0.0
        ):
            # Transition remaining 30% Risk-Free Moonbag across the migration bridge into Horizon 2
            pos.horizon = "HORIZON_2_GRADUATION_RECLAIM"
            pos.is_risk_free_moonbag = True
        return decision

    @staticmethod
    def _reject(
        snapshot: BondingCurveTokenSnapshot, reason: str, t0: float
    ) -> Horizon1EntryDecision:
        return Horizon1EntryDecision(
            mint=snapshot.mint,
            triggered=False,
            setup_type="NONE",
            reject_reason=reason,
            curve_completion_pct=snapshot.curve_completion_pct,
            curve_velocity_15s_pct=0.0,
            independent_buyers_15s=0,
            buy_sell_ratio_15s=0.0,
            sol_allocated=0.0,
            entry_price_sol=snapshot.current_price_sol,
            eval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )
