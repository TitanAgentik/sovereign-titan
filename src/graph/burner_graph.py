"""Sovereign Titan OS — In-Memory 3-Hop Burner Tracker & `<1ms` Anti-Bait Graph (`src/graph/burner_graph.py`).

Backed by `rustworkx.PyDiGraph` and persisted to `/mnt/ramdisk/alpha_graph/burner_graph_snapshot.json`.

Implements:
1. Burner Rotation Inheritance:
   When any tracked shark transfers SOL (directly or via 1–2 fresh hops within 30 minutes = 1,800s)
   to a fresh wallet (`<15` lifetime txns), links the new address as a `CHILD_BURNER`, inherits the
   parent's `WalletProfile`, sets `fast_bot_followers = 0`, and applies a `2.0x` priority score multiplier.
2. Sub-Millisecond Copy-Farming Bait Check (`is_bait_trade(master_wallet, token_mint) -> bool`):
   Traverses up to 3 hops upstream/downstream in `<0.5ms`. If any linked cluster wallet bought
   `token_mint` in the prior 60 minutes (`3,600s`) or holds `>1.5%` (`0.015`) of token supply,
   returns `True` and hard-blocks the trade.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Dict, List, Optional, Set, Tuple

import orjson
import rustworkx as rx

from src.config.settings import Settings, get_settings
from src.intelligence.playbook_extractor import WalletProfile


BURNER_ROTATION_WINDOW_SEC = 1800.0  # 30 minutes
BAIT_PRIOR_BUY_WINDOW_SEC = 3600.0  # 60 minutes
BAIT_SUPPLY_THRESHOLD_PCT = 1.5  # >1.5% token supply
FRESH_WALLET_MAX_LIFETIME_TXS = 15


@dataclass
class TokenPositionState:
    mint: str
    first_buy_epoch_s: float
    last_buy_epoch_s: float
    supply_pct_held: float  # e.g., 1.8 means 1.8% of total supply


@dataclass
class WalletGraphNode:
    wallet: str
    node_index: int
    lifetime_tx_count: int = 0
    is_tracked_shark: bool = False
    is_child_burner: bool = False
    root_shark_wallet: Optional[str] = None
    hop_distance_from_shark: int = 0
    funded_at_epoch_s: float = 0.0
    profile: Optional[WalletProfile] = None
    token_positions: Dict[str, TokenPositionState] = field(default_factory=dict)


@dataclass
class BurnerLinkEvent:
    from_wallet: str
    to_wallet: str
    sol_amount: float
    hop_distance: int
    root_shark_wallet: str
    promoted_as_child_burner: bool
    priority_multiplier: float
    fast_bot_followers: int


class BurnerGraph:
    """Real-time `rustworkx.PyDiGraph` 3-Hop Burner Tracker & `<0.5ms` Copy-Farming Bait Detector."""

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.settings = config or get_settings()
        self.snapshot_path: Path = (
            self.settings.RAMDISK_ALPHA_GRAPH / "burner_graph_snapshot.json"
        )
        self.graph: rx.PyDiGraph = rx.PyDiGraph()
        self._wallet_to_idx: Dict[str, int] = {}
        self._nodes: Dict[int, WalletGraphNode] = {}

    def _get_or_create_node(
        self, wallet: str, lifetime_tx_count: int = 0
    ) -> WalletGraphNode:
        idx = self._wallet_to_idx.get(wallet)
        if idx is not None:
            node = self._nodes[idx]
            if lifetime_tx_count > node.lifetime_tx_count:
                node.lifetime_tx_count = lifetime_tx_count
            return node

        new_idx = self.graph.add_node(wallet)
        node = WalletGraphNode(
            wallet=wallet,
            node_index=new_idx,
            lifetime_tx_count=lifetime_tx_count,
        )
        self._wallet_to_idx[wallet] = new_idx
        self._nodes[new_idx] = node
        return node

    def register_tracked_shark(
        self, wallet: str, profile: WalletProfile, lifetime_tx_count: int = 250
    ) -> WalletGraphNode:
        """Registers a master `ACTIVE_SHADOW_LIST` shark in the directed graph."""
        node = self._get_or_create_node(wallet, lifetime_tx_count=lifetime_tx_count)
        node.is_tracked_shark = True
        node.root_shark_wallet = wallet
        node.hop_distance_from_shark = 0
        node.profile = profile
        return node

    def ingest_sol_transfer(
        self,
        from_wallet: str,
        to_wallet: str,
        sol_amount: float,
        to_wallet_lifetime_txs: int = 0,
        timestamp_s: Optional[float] = None,
    ) -> Optional[BurnerLinkEvent]:
        """Processes a Helius `SOL_TRANSFER` webhook event and performs Burner Rotation Inheritance
        when a tracked shark (or 1–2 hop intermediate fresh wallet within 30 minutes) funds a
        fresh wallet (`<15` lifetime txns).
        """
        now_s = timestamp_s if timestamp_s is not None else time.time()
        src = self._get_or_create_node(from_wallet)
        dst = self._get_or_create_node(
            to_wallet, lifetime_tx_count=to_wallet_lifetime_txs
        )

        # Add or update directed transfer edge (src -> dst)
        edge_data = {"sol_amount": sol_amount, "timestamp_s": now_s}
        if not self.graph.has_edge(src.node_index, dst.node_index):
            self.graph.add_edge(src.node_index, dst.node_index, edge_data)
        else:
            self.graph.update_edge(src.node_index, dst.node_index, edge_data)

        # Check if `src` is a tracked shark OR a fresh intermediate hop funded within 30 minutes
        can_propagate = False
        next_hop = 0
        root_shark: Optional[str] = None
        parent_profile: Optional[WalletProfile] = None

        if src.is_tracked_shark and src.profile is not None:
            can_propagate = True
            next_hop = 1
            root_shark = src.wallet
            parent_profile = src.profile
        elif (
            src.root_shark_wallet is not None
            and src.hop_distance_from_shark in (1, 2)
            and (now_s - src.funded_at_epoch_s) <= BURNER_ROTATION_WINDOW_SEC
            and src.profile is not None
        ):
            can_propagate = True
            next_hop = src.hop_distance_from_shark + 1
            root_shark = src.root_shark_wallet
            parent_profile = src.profile

        if (
            can_propagate
            and root_shark is not None
            and parent_profile is not None
            and next_hop <= 3
            and to_wallet_lifetime_txs < FRESH_WALLET_MAX_LIFETIME_TXS
        ):
            inherited_profile = parent_profile.clone_for_child_burner(to_wallet)
            dst.is_child_burner = True
            dst.root_shark_wallet = root_shark
            dst.hop_distance_from_shark = next_hop
            dst.funded_at_epoch_s = now_s
            dst.profile = inherited_profile

            return BurnerLinkEvent(
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                sol_amount=sol_amount,
                hop_distance=next_hop,
                root_shark_wallet=root_shark,
                promoted_as_child_burner=True,
                priority_multiplier=inherited_profile.priority_multiplier,  # 2.0x
                fast_bot_followers=inherited_profile.fast_bot_followers,  # 0
            )

        return None

    def record_wallet_token_position(
        self,
        wallet: str,
        token_mint: str,
        supply_pct_held: float,
        buy_timestamp_s: Optional[float] = None,
    ) -> None:
        """Records a token buy or supply holding percentage on a wallet node."""
        now_s = buy_timestamp_s if buy_timestamp_s is not None else time.time()
        node = self._get_or_create_node(wallet)
        existing = node.token_positions.get(token_mint)
        if existing is None:
            node.token_positions[token_mint] = TokenPositionState(
                mint=token_mint,
                first_buy_epoch_s=now_s,
                last_buy_epoch_s=now_s,
                supply_pct_held=supply_pct_held,
            )
        else:
            existing.last_buy_epoch_s = now_s
            existing.supply_pct_held = supply_pct_held

    def get_wallet_profile(self, wallet: str) -> Optional[WalletProfile]:
        idx = self._wallet_to_idx.get(wallet)
        if idx is None:
            return None
        return self._nodes[idx].profile

    # --------------------------------------------------------------------------
    # Sub-Millisecond (<0.5ms) 3-Hop Upstream/Downstream Copy-Farming Bait Check
    # --------------------------------------------------------------------------
    def is_bait_trade(
        self,
        master_wallet: str,
        token_mint: str,
        now_s: Optional[float] = None,
    ) -> Tuple[bool, float, Optional[str]]:
        """Traverses up to 3 hops upstream and downstream in `rustworkx` in `<0.5ms`.

        If any linked cluster wallet bought `token_mint` in the prior 60 minutes (3,600s)
        OR holds `>1.5%` supply, returns `(True, latency_ms, reason)` to hard-block the trade.
        """
        t0 = time.perf_counter()
        current_s = now_s if now_s is not None else time.time()

        start_idx = self._wallet_to_idx.get(master_wallet)
        if start_idx is None:
            return False, (time.perf_counter() - t0) * 1000.0, None

        # Bounded 3-hop bidirectional BFS over rustworkx adjacency indices
        visited: Set[int] = {start_idx}
        queue: deque[Tuple[int, int]] = deque([(start_idx, 0)])

        while queue:
            curr_idx, depth = queue.popleft()
            if curr_idx != start_idx:
                cluster_node = self._nodes[curr_idx]
                pos = cluster_node.token_positions.get(token_mint)
                if pos is not None:
                    if pos.supply_pct_held > BAIT_SUPPLY_THRESHOLD_PCT:
                        latency_ms = (time.perf_counter() - t0) * 1000.0
                        return (
                            True,
                            latency_ms,
                            f"CLUSTER_WALLET_HOLDS_{pos.supply_pct_held:.2f}PCT_SUPPLY({cluster_node.wallet})",
                        )
                    if 0.0 <= (current_s - pos.last_buy_epoch_s) <= BAIT_PRIOR_BUY_WINDOW_SEC:
                        latency_ms = (time.perf_counter() - t0) * 1000.0
                        return (
                            True,
                            latency_ms,
                            f"CLUSTER_WALLET_BOUGHT_WITHIN_60M({cluster_node.wallet})",
                        )

            if depth < 3:
                # Downstream children (out-neighbors)
                for child_idx in self.graph.successor_indices(curr_idx):
                    if child_idx not in visited:
                        visited.add(child_idx)
                        queue.append((child_idx, depth + 1))
                # Upstream funders (in-neighbors)
                for parent_idx in self.graph.predecessor_indices(curr_idx):
                    if parent_idx not in visited:
                        visited.add(parent_idx)
                        queue.append((parent_idx, depth + 1))

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return False, latency_ms, None

    def save_snapshot_to_ramdisk(self) -> Path:
        """Persists graph metadata to `/mnt/ramdisk/alpha_graph/burner_graph_snapshot.json`."""
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at_epoch_s": time.time(),
            "node_count": self.graph.num_nodes(),
            "edge_count": self.graph.num_edges(),
            "child_burners": [
                n.wallet for n in self._nodes.values() if n.is_child_burner
            ],
        }
        self.snapshot_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
        return self.snapshot_path
