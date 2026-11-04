"""Sovereign Titan OS — Engine C: Meteora DLMM 3-Bin JIT Fee Harvester (`src/engines/engine_c_jit_dlmm.py`).

Pinned to Cores 24–31 (`taskset -c 24-31`).

Implements:
- Monitors Meteora DLMM pools where 1m Volume/TVL `> 1.5x` and dynamic fee rate exceeds `150 bps (1.5%)`.
- Constructs 3-bin `[active_bin - 1, active_bin, active_bin + 1]` concentrated `SpotBalanced` LP
  mint & burn bundles (`<=120s` hold or `-35%` volume velocity drop).
- Hard Safety Gate (/AGENTS.md):
  Locked to `PAPER_SIM` mode by default until cumulative realized vault profit across
  `Engine A` + `Engine B` + `Shadow` exceeds `+100.0 SOL`.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import List, Literal, Optional, Tuple

from src.config.settings import Settings, get_settings


EngineCExecutionMode = Literal["PAPER_SIM", "LIVE_UNLOCKED"]


@dataclass
class DLMMJitCandidatePool:
    pool_address: str
    token_mint: str
    active_bin_id: int
    tvl_usd: float
    volume_1m_usd: float
    dynamic_fee_bps: float  # Must be > 150 bps (1.5%)

    @property
    def volume_to_tvl_1m(self) -> float:
        if self.tvl_usd <= 0.0:
            return 0.0
        return self.volume_1m_usd / self.tvl_usd


@dataclass
class DLMM3BinPositionBundle:
    pool_address: str
    token_mint: str
    execution_mode: EngineCExecutionMode
    strategy_type: Literal["SpotBalanced"]
    bins: Tuple[int, int, int]  # [active_bin - 1, active_bin, active_bin + 1]
    sol_deposited: float
    entry_volume_1m_usd: float
    dynamic_fee_bps: float
    max_hold_sec: float = 120.0
    velocity_drop_exit_threshold_pct: float = 35.0
    opened_at_s: float = 0.0


class EngineCJitDLMM:
    """Engine C (Cores 24–31): Meteora DLMM 3-Bin JIT Fee Harvester with +100 SOL Safety Lock."""

    MIN_VOL_TO_TVL_1M = 1.5
    MIN_DYNAMIC_FEE_BPS = 150.0
    MAX_HOLD_SEC = 120.0
    MAX_VELOCITY_DROP_RATIO = 0.35  # -35% volume velocity drop triggers LP burn

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.settings = config or get_settings()
        self.unlock_profit_threshold_sol: float = (
            self.settings.ENGINE_C_UNLOCK_PROFIT_SOL
        )  # +100.0 SOL
        self.cumulative_vault_profit_sol: float = 0.0
        self.active_positions: List[DLMM3BinPositionBundle] = []

    @property
    def effective_execution_mode(self) -> EngineCExecutionMode:
        """Strictly enforces `PAPER_SIM` until cumulative realized profit across Engine A + B + Shadow >= +100.0 SOL."""
        if self.cumulative_vault_profit_sol >= self.unlock_profit_threshold_sol:
            return "LIVE_UNLOCKED"
        return "PAPER_SIM"

    def record_realized_vault_profit(
        self,
        engine_a_profit_sol: float = 0.0,
        engine_b_profit_sol: float = 0.0,
        shadow_profit_sol: float = 0.0,
    ) -> EngineCExecutionMode:
        """Updates cumulative realized vault profit across Engine A + Engine B + Shadow Executor."""
        self.cumulative_vault_profit_sol = round(
            self.cumulative_vault_profit_sol
            + engine_a_profit_sol
            + engine_b_profit_sol
            + shadow_profit_sol,
            6,
        )
        return self.effective_execution_mode

    def evaluate_dlmm_pool_entry(
        self,
        pool: DLMMJitCandidatePool,
        deposit_sol: float = 10.0,
        now_s: Optional[float] = None,
    ) -> Optional[DLMM3BinPositionBundle]:
        """Constructs a 3-bin `[-1, 0, +1]` `SpotBalanced` LP mint bundle when:
        - 1m Volume / TVL > 1.5x
        - Dynamic fee rate > 150 bps (1.5%)
        """
        if pool.volume_to_tvl_1m <= self.MIN_VOL_TO_TVL_1M:
            return None
        if pool.dynamic_fee_bps <= self.MIN_DYNAMIC_FEE_BPS:
            return None

        bins = (pool.active_bin_id - 1, pool.active_bin_id, pool.active_bin_id + 1)
        bundle = DLMM3BinPositionBundle(
            pool_address=pool.pool_address,
            token_mint=pool.token_mint,
            execution_mode=self.effective_execution_mode,
            strategy_type="SpotBalanced",
            bins=bins,
            sol_deposited=deposit_sol,
            entry_volume_1m_usd=pool.volume_1m_usd,
            dynamic_fee_bps=pool.dynamic_fee_bps,
            max_hold_sec=self.MAX_HOLD_SEC,
            velocity_drop_exit_threshold_pct=35.0,
            opened_at_s=now_s if now_s is not None else time.time(),
        )
        self.active_positions.append(bundle)
        return bundle

    def should_burn_and_exit_lp(
        self,
        bundle: DLMM3BinPositionBundle,
        current_volume_1m_usd: float,
        current_time_s: float,
    ) -> Tuple[bool, Optional[str]]:
        """Triggers LP burn & fee claim when hold time >= 120s OR 1m volume velocity drops >= 35%."""
        elapsed_s = current_time_s - bundle.opened_at_s
        if elapsed_s >= self.MAX_HOLD_SEC:
            if bundle in self.active_positions:
                self.active_positions.remove(bundle)
            return True, f"MAX_HOLD_120S_REACHED({elapsed_s:.1f}s)"

        if bundle.entry_volume_1m_usd > 0.0:
            drop_ratio = (
                bundle.entry_volume_1m_usd - current_volume_1m_usd
            ) / bundle.entry_volume_1m_usd
            if drop_ratio >= self.MAX_VELOCITY_DROP_RATIO:
                if bundle in self.active_positions:
                    self.active_positions.remove(bundle)
                return True, f"VOLUME_VELOCITY_DROP_GE_35PCT({drop_ratio * 100:.1f}%)"

        return False, None
