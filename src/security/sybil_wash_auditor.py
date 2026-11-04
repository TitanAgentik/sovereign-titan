"""Sovereign Titan OS — Sybil Cabal Cluster & Circular Wash-Volume Stripper (`src/security/sybil_wash_auditor.py`).

Enforces `/AGENTS.md` Rule 19:
Prevents wash-trading bots and bundled developer cabals from tricking Horizons 1–4 or Shadow filters:
  1. Organic-Only Volume Calculator:
     - Strips out circular wash volume before computing `Buy_Sell_Ratio` or `1m_Volume`:
       ignores any swap where the signer bought AND sold inside the last `45 seconds`, OR
       shares a `3-hop` funding ancestor in `burner_graph.py` with the counterparty/deployer.
  2. Bundled Cabal Supply Ceiling:
     - Groups top-50 token holders by (a) shared `2-hop` genesis SOL funder in `burner_graph.py`
       and (b) entry within Slots `[Mint_Slot, Mint_Slot + 2]`.
     - If any single linked cluster controls `>= 14.0%` of total supply, hard-blocks all
       directional entries on that token (`CABAL_BUNDLED_SUPPLY_TRAP`).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
import time
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

import orjson

from src.config.settings import Settings, get_settings
from src.graph.burner_graph import BurnerGraph


WASH_CIRCULAR_WINDOW_SEC = 45.0  # 45-second circular buy+sell wash window
CABAL_CLUSTER_MAX_SUPPLY_PCT = 14.0  # >= 14.0% linked supply triggers hard block
CABAL_BLOCK_REASON = "CABAL_BUNDLED_SUPPLY_TRAP"
LAUNCH_BUNDLE_SLOT_DELTA = 2  # Slots [Mint_Slot, Mint_Slot + 2]


@dataclass
class PoolSwapRecord:
    """Single swap observation used for Organic vs. Wash volume decomposition."""

    signer: str
    side: Literal["BUY", "SELL"]
    amount_sol: float
    timestamp_s: float
    counterparty_or_deployer: Optional[str] = None


@dataclass
class OrganicVolumeAuditResult:
    """Result of stripping circular & 3-hop Sybil wash volume from pool swaps."""

    token_mint: str
    raw_buy_sol: float
    raw_sell_sol: float
    raw_buy_sell_ratio: float
    organic_buy_sol: float
    organic_sell_sol: float
    organic_buy_sell_ratio: float
    organic_1m_volume_sol: float
    wash_volume_stripped_sol: float
    wash_volume_stripped_pct: float
    total_swaps: int
    organic_swaps: int
    wash_swaps_ignored: int
    unique_organic_buyers: int
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TokenHolderRecord:
    """Top-50 holder entry for 2-hop genesis funder & 0-2 slot launch bundle auditing."""

    wallet: str
    supply_pct: float  # e.g., 3.5 means 3.5% of total token supply
    entry_slot: int
    explicit_funder: Optional[str] = None


@dataclass
class CabalSupplyAuditResult:
    """Result of auditing top-50 token holders for `>= 14.0%` Sybil/Bundled Cabal control."""

    passed: bool
    token_mint: str
    status_code: str  # "CLEAN_SUPPLY_DISTRIBUTION" | "CABAL_BUNDLED_SUPPLY_TRAP"
    max_cluster_supply_pct: float
    dominant_cluster_key: str
    dominant_cluster_wallets: List[str]
    funder_cluster_max_pct: float
    slot_0_to_2_bundle_pct: float
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SybilWashAuditor:
    """Sub-millisecond Organic-Only Volume Calculator & 14% Sybil Cabal Supply Auditor."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        burner_graph: Optional[BurnerGraph] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.burner_graph = burner_graph or BurnerGraph(self.settings)
        self.blocklist_path: Path = (
            self.settings.RAMDISK_ALPHA_GRAPH / "sybil_cabal_blocks.json"
        )
        self.blocklist_path.parent.mkdir(parents=True, exist_ok=True)
        self.blocked_cabal_mints: Dict[str, Dict[str, Any]] = {}
        self.sybil_wash_traps_blocked_today: int = 0
        self._load_blocklist()

    def _load_blocklist(self) -> None:
        if not self.blocklist_path.exists():
            return
        try:
            data = orjson.loads(self.blocklist_path.read_bytes())
            self.blocked_cabal_mints = data.get("blocked_cabal_mints", {})
            self.sybil_wash_traps_blocked_today = int(
                data.get(
                    "sybil_wash_traps_blocked_today", len(self.blocked_cabal_mints)
                )
            )
        except Exception:
            self.blocked_cabal_mints = {}

    def _persist_blocklist(self) -> None:
        payload = {
            "updated_at_ns": time.time_ns(),
            "sybil_wash_traps_blocked_today": self.sybil_wash_traps_blocked_today,
            "blocked_cabal_mints": self.blocked_cabal_mints,
        }
        self.blocklist_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))

    def is_token_blocked(self, token_mint: str) -> bool:
        return token_mint in self.blocked_cabal_mints

    # ------------------------------------------------------------------
    # Graph Ancestor Helpers (`burner_graph.py`)
    # ------------------------------------------------------------------
    def get_upstream_ancestors(self, wallet: str, max_hops: int = 3) -> Set[str]:
        """Returns the set of upstream funding ancestors within `max_hops` (including `wallet`)."""
        ancestors: Set[str] = {wallet}
        start_idx = self.burner_graph._wallet_to_idx.get(wallet)
        if start_idx is None:
            return ancestors

        visited: Set[int] = {start_idx}
        queue: deque[Tuple[int, int]] = deque([(start_idx, 0)])
        while queue:
            curr_idx, depth = queue.popleft()
            node = self.burner_graph._nodes.get(curr_idx)
            if node is not None:
                ancestors.add(node.wallet)
                if node.root_shark_wallet:
                    ancestors.add(node.root_shark_wallet)
            if depth < max_hops:
                for pred_idx in self.burner_graph.graph.predecessor_indices(curr_idx):
                    if pred_idx not in visited:
                        visited.add(pred_idx)
                        queue.append((pred_idx, depth + 1))
        return ancestors

    def get_highest_2hop_funder(self, wallet: str) -> str:
        """Finds the root/earliest upstream funder within 2 hops in `burner_graph.py`."""
        start_idx = self.burner_graph._wallet_to_idx.get(wallet)
        if start_idx is None:
            return wallet

        curr_idx = start_idx
        for _ in range(2):
            preds = self.burner_graph.graph.predecessor_indices(curr_idx)
            if not preds:
                break
            curr_idx = preds[0]
        node = self.burner_graph._nodes.get(curr_idx)
        return node.wallet if node is not None else wallet

    def share_3hop_ancestor(self, wallet_a: str, wallet_b: str) -> bool:
        """Returns True if `wallet_a` and `wallet_b` share any `<= 3-hop` funding ancestor."""
        if not wallet_a or not wallet_b:
            return False
        if wallet_a == wallet_b:
            return True
        anc_a = self.get_upstream_ancestors(wallet_a, max_hops=3)
        anc_b = self.get_upstream_ancestors(wallet_b, max_hops=3)
        return bool(anc_a.intersection(anc_b))

    # ------------------------------------------------------------------
    # 1. Organic-Only Volume Calculator (45s Circular + 3-Hop Ancestor Strip)
    # ------------------------------------------------------------------
    def compute_organic_volume(
        self,
        token_mint: str,
        swaps: List[PoolSwapRecord],
        deployer_wallet: Optional[str] = None,
        window_sec: float = WASH_CIRCULAR_WINDOW_SEC,
    ) -> OrganicVolumeAuditResult:
        """Strips circular 45-second buy+sell wash volume and 3-hop ancestor-linked wash swaps."""
        t0 = time.perf_counter_ns()
        if not swaps:
            return OrganicVolumeAuditResult(
                token_mint=token_mint,
                raw_buy_sol=0.0,
                raw_sell_sol=0.0,
                raw_buy_sell_ratio=0.0,
                organic_buy_sol=0.0,
                organic_sell_sol=0.0,
                organic_buy_sell_ratio=0.0,
                organic_1m_volume_sol=0.0,
                wash_volume_stripped_sol=0.0,
                wash_volume_stripped_pct=0.0,
                total_swaps=0,
                organic_swaps=0,
                wash_swaps_ignored=0,
                unique_organic_buyers=0,
                latency_ms=0.0,
            )

        # Group buy and sell timestamps per signer to detect 45s circular roundtrips
        buy_times_by_signer: Dict[str, List[float]] = defaultdict(list)
        sell_times_by_signer: Dict[str, List[float]] = defaultdict(list)
        for sw in swaps:
            if sw.side == "BUY":
                buy_times_by_signer[sw.signer].append(sw.timestamp_s)
            else:
                sell_times_by_signer[sw.signer].append(sw.timestamp_s)

        circular_wash_signers: Set[str] = set()
        for signer, b_times in buy_times_by_signer.items():
            s_times = sell_times_by_signer.get(signer)
            if not s_times:
                continue
            for bt in b_times:
                if any(abs(bt - st) <= window_sec for st in s_times):
                    circular_wash_signers.add(signer)
                    break

        # Also precompute 3-hop ancestor sets for all signers to catch A buys / B sells Sybil wash pairs
        ancestors_by_signer: Dict[str, Set[str]] = {
            sw.signer: self.get_upstream_ancestors(sw.signer, max_hops=3)
            for sw in swaps
        }
        deployer_ancestors: Set[str] = (
            self.get_upstream_ancestors(deployer_wallet, max_hops=3)
            if deployer_wallet
            else set()
        )

        # Flag cross-wallet ancestor overlap when two distinct signers share a 3-hop ancestor
        cross_wallet_wash_signers: Set[str] = set()
        buy_swaps = [sw for sw in swaps if sw.side == "BUY"]
        sell_swaps = [sw for sw in swaps if sw.side != "BUY"]
        for sw_b in buy_swaps:
            anc_b = ancestors_by_signer[sw_b.signer]
            for sw_s in sell_swaps:
                if sw_b.signer != sw_s.signer:
                    if anc_b.intersection(ancestors_by_signer[sw_s.signer]):
                        cross_wallet_wash_signers.add(sw_b.signer)
                        cross_wallet_wash_signers.add(sw_s.signer)
                elif abs(sw_b.timestamp_s - sw_s.timestamp_s) <= window_sec:
                    circular_wash_signers.add(sw_b.signer)

        raw_buy = 0.0
        raw_sell = 0.0
        org_buy = 0.0
        org_sell = 0.0
        org_swaps = 0
        wash_swaps = 0
        organic_buyers: Set[str] = set()

        for sw in swaps:
            amt = max(0.0, float(sw.amount_sol))
            if sw.side == "BUY":
                raw_buy += amt
            else:
                raw_sell += amt

            is_wash = False
            if sw.signer in circular_wash_signers or sw.signer in cross_wallet_wash_signers:
                is_wash = True
            elif sw.counterparty_or_deployer and self.share_3hop_ancestor(
                sw.signer, sw.counterparty_or_deployer
            ):
                is_wash = True
            elif deployer_ancestors and bool(
                ancestors_by_signer[sw.signer].intersection(deployer_ancestors)
            ):
                is_wash = True

            if is_wash:
                wash_swaps += 1
            else:
                org_swaps += 1
                if sw.side == "BUY":
                    org_buy += amt
                    organic_buyers.add(sw.signer)
                else:
                    org_sell += amt

        raw_total = raw_buy + raw_sell
        org_total = org_buy + org_sell
        stripped_sol = max(0.0, raw_total - org_total)
        stripped_pct = (stripped_sol / raw_total * 100.0) if raw_total > 0.0 else 0.0

        raw_ratio = raw_buy / max(raw_sell, 0.05)
        org_ratio = org_buy / max(org_sell, 0.05) if org_buy > 0.0 else 0.0

        if stripped_pct >= 35.0:
            self.sybil_wash_traps_blocked_today += 1

        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return OrganicVolumeAuditResult(
            token_mint=token_mint,
            raw_buy_sol=round(raw_buy, 4),
            raw_sell_sol=round(raw_sell, 4),
            raw_buy_sell_ratio=round(raw_ratio, 3),
            organic_buy_sol=round(org_buy, 4),
            organic_sell_sol=round(org_sell, 4),
            organic_buy_sell_ratio=round(org_ratio, 3),
            organic_1m_volume_sol=round(org_total, 4),
            wash_volume_stripped_sol=round(stripped_sol, 4),
            wash_volume_stripped_pct=round(stripped_pct, 2),
            total_swaps=len(swaps),
            organic_swaps=org_swaps,
            wash_swaps_ignored=wash_swaps,
            unique_organic_buyers=len(organic_buyers),
            latency_ms=round(elapsed_ms, 4),
        )

    # ------------------------------------------------------------------
    # 2. Bundled Cabal Supply Ceiling (>= 14.0% Linked Cluster Block)
    # ------------------------------------------------------------------
    def audit_token_holder_cabal(
        self,
        token_mint: str,
        holders: List[TokenHolderRecord],
        mint_slot: int,
    ) -> CabalSupplyAuditResult:
        """Groups top-50 holders by (a) shared 2-hop genesis SOL funder in `burner_graph.py`
        and (b) entry within Slots `[mint_slot, mint_slot + 2]`.
        Blocks the token if any cluster controls `>= 14.0%` of total supply.
        """
        t0 = time.perf_counter_ns()
        top50 = holders[:50]

        funder_clusters: Dict[str, List[TokenHolderRecord]] = defaultdict(list)
        slot02_wallets: List[TokenHolderRecord] = []

        for h in top50:
            funder = h.explicit_funder or self.get_highest_2hop_funder(h.wallet)
            funder_clusters[funder].append(h)
            if mint_slot <= h.entry_slot <= (mint_slot + LAUNCH_BUNDLE_SLOT_DELTA):
                slot02_wallets.append(h)

        max_funder_pct = 0.0
        max_funder_key = "NONE"
        max_funder_wallets: List[str] = []

        for funder, group in funder_clusters.items():
            # A single unlinked retail holder (<14%) is only a cluster if >= 2 wallets share the funder or single holder >= 14%
            cluster_pct = sum(float(x.supply_pct) for x in group)
            if len(group) >= 2 and cluster_pct > max_funder_pct:
                max_funder_pct = cluster_pct
                max_funder_key = f"2HOP_FUNDER:{funder}"
                max_funder_wallets = [x.wallet for x in group]

        slot02_pct = (
            sum(float(x.supply_pct) for x in slot02_wallets)
            if len(slot02_wallets) >= 2
            else 0.0
        )

        if max_funder_pct >= slot02_pct:
            dominant_pct = max_funder_pct
            dominant_key = max_funder_key
            dominant_wallets = max_funder_wallets
        else:
            dominant_pct = slot02_pct
            dominant_key = f"LAUNCH_SLOT_BUNDLE:[{mint_slot}..{mint_slot + LAUNCH_BUNDLE_SLOT_DELTA}]"
            dominant_wallets = [x.wallet for x in slot02_wallets]

        passed = dominant_pct < CABAL_CLUSTER_MAX_SUPPLY_PCT
        status_code = (
            "CLEAN_SUPPLY_DISTRIBUTION" if passed else CABAL_BLOCK_REASON
        )

        if not passed:
            if token_mint not in self.blocked_cabal_mints:
                self.sybil_wash_traps_blocked_today += 1
            self.blocked_cabal_mints[token_mint] = {
                "token_mint": token_mint,
                "reason": CABAL_BLOCK_REASON,
                "max_cluster_supply_pct": round(dominant_pct, 3),
                "dominant_cluster_key": dominant_key,
                "wallet_count": len(dominant_wallets),
                "blocked_at_ns": time.time_ns(),
            }
            self._persist_blocklist()

        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return CabalSupplyAuditResult(
            passed=passed,
            token_mint=token_mint,
            status_code=status_code,
            max_cluster_supply_pct=round(dominant_pct, 3),
            dominant_cluster_key=dominant_key,
            dominant_cluster_wallets=dominant_wallets,
            funder_cluster_max_pct=round(max_funder_pct, 3),
            slot_0_to_2_bundle_pct=round(slot02_pct, 3),
            latency_ms=round(elapsed_ms, 4),
        )
