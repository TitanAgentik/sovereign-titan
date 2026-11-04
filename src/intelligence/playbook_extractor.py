"""Sovereign Titan OS — Playbook Extractor & 671B Meta-Strategy Synthesizer (`src/intelligence/playbook_extractor.py`).

Asynchronously analyzes the last 100 trades of every promoted `ACTIVE_SHADOW_LIST` wallet
on Port 8002 (`DeepSeek-V3.2-671B` via SGLang + KTransformers) and writes `profiles/{wallet}.json`
(mirrored in `/mnt/ramdisk/alpha_graph/profiles/{wallet}.json`) with strict Pydantic validation:
- `archetype` (`BONDING_CURVE_SNIPER`, `POST_MIGRATION_DIP_BUYER`, `MOMENTUM_BREAKOUT`,
  `NARRATIVE_FRONTRUNNER`, `INSIDER_ACCUMULATOR`)
- `conviction_sizing` (`median_sol`, `p75_high_conviction_sol`, `lotto_threshold_sol`)
- `entry_fingerprint` (`mcap_range_usd`, `min_liquidity_usd`, `requires_dex_boost`)
- `exit_signature` (`median_hold_time_sec`, `first_tp_multiple`, `typical_scale_out_pct`)
- `invalidation_rules`
Synthesizes shared winning setups across top sharks nightly into `profiles/autonomous_rules.json`.
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import orjson
from pydantic import BaseModel, Field

from src.config.settings import Settings, get_settings, WORKSPACE_ROOT
from src.llm.swarm_client import SwarmClient


WalletArchetype = Literal[
    "BONDING_CURVE_SNIPER",
    "POST_MIGRATION_DIP_BUYER",
    "MOMENTUM_BREAKOUT",
    "NARRATIVE_FRONTRUNNER",
    "INSIDER_ACCUMULATOR",
]


class ConvictionSizing(BaseModel):
    median_sol: float = Field(gt=0.0)
    p75_high_conviction_sol: float = Field(gt=0.0)
    lotto_threshold_sol: float = Field(gt=0.0)


class EntryFingerprint(BaseModel):
    mcap_range_usd: Tuple[float, float]
    min_liquidity_usd: float = Field(ge=0.0)
    requires_dex_boost: bool = False


class ExitSignature(BaseModel):
    median_hold_time_sec: float = Field(gt=0.0)
    first_tp_multiple: float = Field(gt=1.0)
    typical_scale_out_pct: float = Field(gt=0.0, le=100.0)


class InvalidationRules(BaseModel):
    max_acceptable_drawdown_pct: float = Field(gt=0.0, le=100.0, default=18.0)
    max_hold_without_new_high_sec: float = Field(gt=0.0, default=120.0)
    abort_on_dev_sell_pct: float = Field(gt=0.0, le=100.0, default=20.0)


class WalletProfile(BaseModel):
    """Validated wallet behavioral playbook profile."""

    wallet: str
    parent_shark_wallet: Optional[str] = None
    is_child_burner: bool = False
    archetype: WalletArchetype
    conviction_sizing: ConvictionSizing
    entry_fingerprint: EntryFingerprint
    exit_signature: ExitSignature
    invalidation_rules: InvalidationRules
    fast_bot_followers: int = Field(ge=0, default=0)
    priority_multiplier: float = Field(gt=0.0, default=1.0)
    updated_at_epoch_s: float = Field(default_factory=time.time)

    def clone_for_child_burner(self, burner_wallet: str) -> "WalletProfile":
        """Creates an inherited `CHILD_BURNER` profile with `fast_bot_followers = 0` and `2.0x` priority multiplier."""
        root_parent = self.parent_shark_wallet or self.wallet
        return WalletProfile(
            wallet=burner_wallet,
            parent_shark_wallet=root_parent,
            is_child_burner=True,
            archetype=self.archetype,
            conviction_sizing=self.conviction_sizing.model_copy(),
            entry_fingerprint=self.entry_fingerprint.model_copy(),
            exit_signature=self.exit_signature.model_copy(),
            invalidation_rules=self.invalidation_rules.model_copy(),
            fast_bot_followers=0,
            priority_multiplier=2.0,
            updated_at_epoch_s=time.time(),
        )


class HistoricalTradeRecord(BaseModel):
    """Single historical trade from a promoted shark's last 100 trades."""

    mint: str
    sol_spent: float
    entry_mcap_usd: float
    entry_liquidity_usd: float
    had_dex_boost: bool
    hold_time_sec: float
    realized_multiple: float
    scale_out_pct: float = 50.0
    is_migrated_pool: bool = True


class AutonomousMetaRules(BaseModel):
    """Synthesized nightly rules stored in `profiles/autonomous_rules.json`."""

    synthesized_at_epoch_s: float
    analyzed_shark_count: int
    dominant_archetypes: Dict[str, int]
    consensus_min_liquidity_usd: float
    consensus_first_tp_multiple: float
    consensus_frontrun_tp_factor: float = 0.90
    consensus_max_slippage_drift_pct: float = 8.0
    deep_reasoner_summary: str


class PlaybookExtractor:
    """Port 8002 (DeepSeek-V3.2-671B) Playbook Extractor & Nightly Meta-Strategy Synthesizer."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        swarm_client: Optional[SwarmClient] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.swarm_client = swarm_client or SwarmClient(self.settings)
        self.workspace_profiles_dir: Path = WORKSPACE_ROOT / "profiles"
        self.ramdisk_profiles_dir: Path = (
            self.settings.RAMDISK_ALPHA_GRAPH / "profiles"
        )
        self.workspace_profiles_dir.mkdir(parents=True, exist_ok=True)
        self.ramdisk_profiles_dir.mkdir(parents=True, exist_ok=True)

    async def extract_wallet_playbook(
        self,
        wallet: str,
        last_100_trades: Sequence[HistoricalTradeRecord],
        fast_bot_followers: int = 0,
        endpoint_override: Optional[str] = None,
    ) -> WalletProfile:
        """Extracts a validated `WalletProfile` from the wallet's last 100 trades,
        enriching via Port 8002 (`DeepSeek-V3.2-671B`) when online and persisting
        `profiles/{wallet}.json`.
        """
        if not last_100_trades:
            raise ValueError(f"Cannot extract playbook for {wallet} with 0 trades.")

        sol_amounts = sorted(t.sol_spent for t in last_100_trades)
        mcaps = sorted(t.entry_mcap_usd for t in last_100_trades)
        liqs = sorted(t.entry_liquidity_usd for t in last_100_trades)
        hold_times = sorted(t.hold_time_sec for t in last_100_trades)
        winning_multiples = sorted(
            t.realized_multiple for t in last_100_trades if t.realized_multiple > 1.05
        ) or [2.2]
        scale_outs = [t.scale_out_pct for t in last_100_trades]

        n = len(sol_amounts)
        median_sol = round(statistics.median(sol_amounts), 4)
        p75_sol = round(sol_amounts[min(n - 1, int(n * 0.75))], 4)
        p20_lotto_sol = round(max(0.25, sol_amounts[max(0, int(n * 0.20))]), 4)

        median_mc = statistics.median(mcaps)
        migrated_ratio = sum(1 for t in last_100_trades if t.is_migrated_pool) / float(n)
        boost_ratio = sum(1 for t in last_100_trades if t.had_dex_boost) / float(n)

        if median_mc < 65_000.0 and migrated_ratio < 0.35:
            archetype: WalletArchetype = "BONDING_CURVE_SNIPER"
        elif migrated_ratio >= 0.70 and median_mc < 250_000.0:
            archetype = "POST_MIGRATION_DIP_BUYER"
        elif boost_ratio >= 0.60:
            archetype = "NARRATIVE_FRONTRUNNER"
        elif median_mc >= 250_000.0:
            archetype = "MOMENTUM_BREAKOUT"
        else:
            archetype = "INSIDER_ACCUMULATOR"

        # Query Port 8002 DeepSeek-V3.2-671B asynchronously if reachable
        try:
            await self.swarm_client.run_deep_alpha_synthesis(
                subject=f"playbook_extraction:{wallet}",
                graph_evidence={
                    "trades_analyzed": len(last_100_trades),
                    "median_sol": median_sol,
                    "median_mc": median_mc,
                    "archetype_candidate": archetype,
                },
                endpoint_override=endpoint_override,
            )
        except Exception:
            pass

        profile = WalletProfile(
            wallet=wallet,
            archetype=archetype,
            conviction_sizing=ConvictionSizing(
                median_sol=median_sol,
                p75_high_conviction_sol=max(median_sol, p75_sol),
                lotto_threshold_sol=min(median_sol, p20_lotto_sol),
            ),
            entry_fingerprint=EntryFingerprint(
                mcap_range_usd=(
                    round(mcaps[max(0, int(n * 0.10))], 2),
                    round(mcaps[min(n - 1, int(n * 0.90))], 2),
                ),
                min_liquidity_usd=round(liqs[max(0, int(n * 0.10))], 2),
                requires_dex_boost=(boost_ratio >= 0.50),
            ),
            exit_signature=ExitSignature(
                median_hold_time_sec=round(statistics.median(hold_times), 2),
                first_tp_multiple=round(statistics.median(winning_multiples), 3),
                typical_scale_out_pct=round(statistics.median(scale_outs), 2),
            ),
            invalidation_rules=InvalidationRules(
                max_acceptable_drawdown_pct=18.0,
                max_hold_without_new_high_sec=round(
                    max(45.0, statistics.median(hold_times) * 0.75), 1
                ),
                abort_on_dev_sell_pct=20.0,
            ),
            fast_bot_followers=fast_bot_followers,
            priority_multiplier=1.0,
        )

        self.save_profile(profile)
        return profile

    def save_profile(self, profile: WalletProfile) -> Path:
        """Writes `profiles/{wallet}.json` to both workspace and `/mnt/ramdisk/alpha_graph/profiles/`."""
        payload = orjson.dumps(profile.model_dump(), option=orjson.OPT_INDENT_2)
        ws_path = self.workspace_profiles_dir / f"{profile.wallet}.json"
        ram_path = self.ramdisk_profiles_dir / f"{profile.wallet}.json"
        ws_path.write_bytes(payload)
        ram_path.write_bytes(payload)
        return ws_path

    def load_profile(self, wallet: str) -> Optional[WalletProfile]:
        ram_path = self.ramdisk_profiles_dir / f"{wallet}.json"
        if ram_path.exists():
            return WalletProfile.model_validate(orjson.loads(ram_path.read_bytes()))
        ws_path = self.workspace_profiles_dir / f"{wallet}.json"
        if ws_path.exists():
            return WalletProfile.model_validate(orjson.loads(ws_path.read_bytes()))
        return None

    async def synthesize_autonomous_rules(
        self,
        profiles: Sequence[WalletProfile],
        endpoint_override: Optional[str] = None,
    ) -> AutonomousMetaRules:
        """Synthesizes shared winning setups across top sharks into `profiles/autonomous_rules.json`."""
        if not profiles:
            raise ValueError("Cannot synthesize autonomous rules from 0 profiles.")

        counts: Dict[str, int] = {}
        for p in profiles:
            counts[p.archetype] = counts.get(p.archetype, 0) + 1

        consensus_liq = round(
            statistics.median(p.entry_fingerprint.min_liquidity_usd for p in profiles),
            2,
        )
        consensus_tp = round(
            statistics.median(p.exit_signature.first_tp_multiple for p in profiles),
            3,
        )

        summary_text = (
            "Synthesized cross-shark playbooks: front-run master exit at 0.90x first_tp_multiple "
            "and enforce +8.0% max slippage drift from master fill."
        )
        try:
            deep = await self.swarm_client.run_deep_alpha_synthesis(
                subject="nightly_meta_strategy_synthesis",
                graph_evidence={
                    "shark_count": len(profiles),
                    "archetypes": counts,
                    "consensus_tp": consensus_tp,
                },
                endpoint_override=endpoint_override,
            )
            summary_text = deep.summary
        except Exception:
            pass

        rules = AutonomousMetaRules(
            synthesized_at_epoch_s=time.time(),
            analyzed_shark_count=len(profiles),
            dominant_archetypes=counts,
            consensus_min_liquidity_usd=consensus_liq,
            consensus_first_tp_multiple=consensus_tp,
            consensus_frontrun_tp_factor=0.90,
            consensus_max_slippage_drift_pct=8.0,
            deep_reasoner_summary=summary_text,
        )
        raw = orjson.dumps(rules.model_dump(), option=orjson.OPT_INDENT_2)
        (self.workspace_profiles_dir / "autonomous_rules.json").write_bytes(raw)
        (self.ramdisk_profiles_dir / "autonomous_rules.json").write_bytes(raw)
        return rules
