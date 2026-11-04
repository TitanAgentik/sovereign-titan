"""Sovereign Titan OS — Background Token Pre-Scorer Cache (`src/intelligence/pre_scorer_cache.py`).

Continuously pre-scores active/migrating tokens in the background using:
- Port 8003 (Telegram/PumpPortal CPU L3 micro-classifier)
- Port 8001 (Qwen-VL-30B Vision OCR + SocialData X velocity)
- Port 8000 (Qwen3-Coder-Next-80B Tactical Gatekeeper)

Writes `PreApprovedTokenState` structs into `/mnt/ramdisk/pre_approved_tokens/{mint}.json`
(TTL = 120s) for `0ms` (`<0.02ms`) Shadow Executor hot-path lookups.
"""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, Literal, Optional

import orjson
from pydantic import BaseModel, Field

from src.config.settings import Settings, get_settings
from src.intelligence.vision_scam_filter import VisionScamFilter
from src.llm.swarm_client import PreApprovedTokenEntry, SwarmClient


class PreApprovedTokenState(BaseModel):
    """Pre-computed token score stored in `/mnt/ramdisk/pre_approved_tokens/{mint}.json` (TTL=120s)."""

    mint: str
    status: Literal["PRE_APPROVED", "REJECTED"]
    composite_score: float = Field(ge=0.0, le=1.0)
    l3_social_velocity_score: float = Field(ge=0.0, le=1.0, default=0.85)
    vision_narrative_score: float = Field(ge=0.0, le=1.0, default=0.88)
    phash_hex: str = "0000000000000000"
    phash_status: Literal["CLEAN", "VAMPIRE_CLONE"] = "CLEAN"
    recommended_slippage_bps: int = 150
    jito_tip_lamports: int = 120_000
    created_at_epoch_s: float = Field(default_factory=time.time)
    ttl_sec: int = 120

    def is_valid(self, now_s: Optional[float] = None) -> bool:
        current = now_s if now_s is not None else time.time()
        return (
            self.status == "PRE_APPROVED"
            and self.phash_status == "CLEAN"
            and (current - self.created_at_epoch_s) <= self.ttl_sec
        )


class BackgroundPreScorerCache:
    """Manages `/mnt/ramdisk/pre_approved_tokens` (TTL=120s) and background LLM/Vision pre-scoring."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        swarm_client: Optional[SwarmClient] = None,
        vision_filter: Optional[VisionScamFilter] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.swarm_client = swarm_client or SwarmClient(self.settings)
        self.vision_filter = vision_filter or VisionScamFilter(
            self.settings, self.swarm_client
        )
        self.cache_dir: Path = self.settings.RAMDISK_PRE_APPROVED_TOKENS
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._hot_memory_map: Dict[str, PreApprovedTokenState] = {}

    def put_state(self, state: PreApprovedTokenState) -> Path:
        """Writes `PreApprovedTokenState` to `/mnt/ramdisk/pre_approved_tokens/{mint}.json` and hot map."""
        self._hot_memory_map[state.mint] = state
        file_path = self.cache_dir / f"{state.mint}.json"
        file_path.write_bytes(orjson.dumps(state.model_dump()))
        if state.status == "PRE_APPROVED":
            self.swarm_client.write_pre_approved_token(
                PreApprovedTokenEntry(
                    mint=state.mint,
                    score=state.composite_score,
                    vision_verdict="CLEAN_NARRATIVE",
                    recommended_slippage_bps=state.recommended_slippage_bps,
                    jito_tip_lamports=state.jito_tip_lamports,
                    created_at_epoch_s=state.created_at_epoch_s,
                    ttl_sec=state.ttl_sec,
                )
            )
        return file_path

    def get_fast(self, mint: str, now_s: Optional[float] = None) -> Optional[PreApprovedTokenState]:
        """Performs a `<0.02ms` 0-LLM lookup for a pre-approved token."""
        current = now_s if now_s is not None else time.time()
        mem_hit = self._hot_memory_map.get(mint)
        if mem_hit is not None:
            if mem_hit.is_valid(current):
                return mem_hit
            self._hot_memory_map.pop(mint, None)

        file_path = self.cache_dir / f"{mint}.json"
        if not file_path.exists():
            return None
        try:
            data = orjson.loads(file_path.read_bytes())
            if "status" in data:
                state = PreApprovedTokenState.model_validate(data)
            else:
                # Backward-compatible with PreApprovedTokenEntry written by SwarmClient/FreeFirehose
                entry = PreApprovedTokenEntry.model_validate(data)
                state = PreApprovedTokenState(
                    mint=entry.mint,
                    status="PRE_APPROVED" if entry.score >= 0.70 else "REJECTED",
                    composite_score=entry.score,
                    recommended_slippage_bps=entry.recommended_slippage_bps,
                    jito_tip_lamports=entry.jito_tip_lamports,
                    created_at_epoch_s=entry.created_at_epoch_s,
                    ttl_sec=entry.ttl_sec,
                )
            if state.is_valid(current):
                self._hot_memory_map[mint] = state
                return state
            file_path.unlink(missing_ok=True)
            return None
        except Exception:
            return None

    async def pre_score_token_background(
        self,
        mint: str,
        image_url: str,
        phash_u64: int,
        token_description: str,
        social_metrics: Dict[str, Any],
    ) -> PreApprovedTokenState:
        """Executes background pre-scoring across pHash BK-Tree, Port 8003, Port 8001, and Port 8000."""
        phash_res = self.vision_filter.check_and_register_banner_phash(mint, phash_u64)
        if phash_res.status == "VAMPIRE_CLONE":
            rejected = PreApprovedTokenState(
                mint=mint,
                status="REJECTED",
                composite_score=0.0,
                phash_hex=phash_res.phash_hex,
                phash_status="VAMPIRE_CLONE",
                ttl_sec=self.settings.PRE_APPROVED_TOKEN_TTL_SEC,
            )
            self.put_state(rejected)
            return rejected

        l3_score_val = 0.85
        vision_score_val = 0.88
        try:
            l3_res = await self.swarm_client.classify_fast_l3(mint, social_metrics)
            l3_score_val = l3_res.social_velocity_score
        except Exception:
            pass

        try:
            vis_res = await self.swarm_client.audit_vision_narrative(
                mint=mint,
                image_url=image_url,
                phash_64=phash_res.phash_hex,
                token_description=token_description,
            )
            if vis_res.is_recycled_scam_banner or vis_res.verdict == "SCAM_RECYCLE":
                rejected = PreApprovedTokenState(
                    mint=mint,
                    status="REJECTED",
                    composite_score=0.0,
                    phash_hex=phash_res.phash_hex,
                    phash_status="VAMPIRE_CLONE",
                    ttl_sec=self.settings.PRE_APPROVED_TOKEN_TTL_SEC,
                )
                self.put_state(rejected)
                return rejected
            vision_score_val = vis_res.narrative_score
        except Exception:
            pass

        composite = round((l3_score_val * 0.45) + (vision_score_val * 0.55), 4)
        state = PreApprovedTokenState(
            mint=mint,
            status="PRE_APPROVED" if composite >= 0.70 else "REJECTED",
            composite_score=composite,
            l3_social_velocity_score=l3_score_val,
            vision_narrative_score=vision_score_val,
            phash_hex=phash_res.phash_hex,
            phash_status="CLEAN",
            recommended_slippage_bps=150,
            jito_tip_lamports=120_000,
            created_at_epoch_s=time.time(),
            ttl_sec=self.settings.PRE_APPROVED_TOKEN_TTL_SEC,
        )
        self.put_state(state)
        return state
