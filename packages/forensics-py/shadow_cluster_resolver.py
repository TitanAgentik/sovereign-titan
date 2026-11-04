"""
Step 1.1 & Step 1.2: Zero-Dev Shadow Cluster Resolver, Helius Batch Identity Whitelister,
Louvain Graph Community Detection, CEX Sink Clustering, and Temporal/Wash Detectors.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
import hashlib
import math
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

import networkx as nx
import orjson


HELIUS_BATCH_IDENTITY_ENDPOINT = "https://api.helius.xyz/v1/wallet/batch-identity"
HELIUS_BATCH_IDENTITY_MAX_ADDRS = 100
HELIUS_LABELED_ENTITIES_COUNT = 32_500

TERMINAL_BOUNDARY_CATEGORIES: Set[str] = {
    "CEX_HOT_WALLET",
    "INSTITUTIONAL_MM",
    "PUBLIC_DEFI_VAULT",
    "PUBLIC_BRIDGE",
    "SYSTEM_PROGRAM",
}

# Canonical Helius-labeled entities (modeling Helius 32,500+ entity database)
DEFAULT_HELIUS_ENTITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9": {
        "address": "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
        "name": "Binance Hot Wallet 2",
        "category": "CEX_HOT_WALLET",
        "entity": "Binance",
        "tags": ["cex", "exchange", "hot_wallet"],
    },
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": {
        "address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "name": "Binance Hot Wallet 1",
        "category": "CEX_HOT_WALLET",
        "entity": "Binance",
        "tags": ["cex", "exchange", "hot_wallet"],
    },
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": {
        "address": "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS",
        "name": "Coinbase Hot Wallet 1",
        "category": "CEX_HOT_WALLET",
        "entity": "Coinbase",
        "tags": ["cex", "exchange", "hot_wallet"],
    },
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": {
        "address": "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm",
        "name": "Coinbase Hot Wallet 2",
        "category": "CEX_HOT_WALLET",
        "entity": "Coinbase",
        "tags": ["cex", "exchange", "hot_wallet"],
    },
    "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5": {
        "address": "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5",
        "name": "Kraken Hot Wallet",
        "category": "CEX_HOT_WALLET",
        "entity": "Kraken",
        "tags": ["cex", "exchange", "hot_wallet"],
    },
    "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD": {
        "address": "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD",
        "name": "OKX Hot Wallet",
        "category": "CEX_HOT_WALLET",
        "entity": "OKX",
        "tags": ["cex", "exchange", "hot_wallet"],
    },
    "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2": {
        "address": "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2",
        "name": "Bybit Hot Wallet",
        "category": "CEX_HOT_WALLET",
        "entity": "Bybit",
        "tags": ["cex", "exchange", "hot_wallet"],
    },
    "WintermuteMM1111111111111111111111111111111": {
        "address": "WintermuteMM1111111111111111111111111111111",
        "name": "Wintermute Institutional MM",
        "category": "INSTITUTIONAL_MM",
        "entity": "Wintermute",
        "tags": ["market_maker", "institutional"],
    },
    "JumpTradingMM111111111111111111111111111111": {
        "address": "JumpTradingMM111111111111111111111111111111",
        "name": "Jump Crypto MM",
        "category": "INSTITUTIONAL_MM",
        "entity": "Jump Trading",
        "tags": ["market_maker", "institutional"],
    },
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1": {
        "address": "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
        "name": "Raydium Authority V4",
        "category": "PUBLIC_DEFI_VAULT",
        "entity": "Raydium",
        "tags": ["amm", "defi", "vault"],
    },
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": {
        "address": "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        "name": "Pump.fun Bonding Curve Program",
        "category": "PUBLIC_DEFI_VAULT",
        "entity": "Pump.fun",
        "tags": ["launchpad", "defi", "vault"],
    },
    "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg": {
        "address": "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg",
        "name": "Pump.fun Migration Authority",
        "category": "PUBLIC_DEFI_VAULT",
        "entity": "Pump.fun",
        "tags": ["migration", "defi", "vault"],
    },
    "wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb": {
        "address": "wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb",
        "name": "Wormhole Token Bridge",
        "category": "PUBLIC_BRIDGE",
        "entity": "Wormhole",
        "tags": ["bridge", "cross_chain"],
    },
}

# Canonical case studies modeling the "Zero-Percent Developer Illusion"
CANONICAL_ZERO_DEV_CASE_STUDIES: Dict[str, Dict[str, Any]] = {
    "BATON": {
        "symbol": "BATON",
        "deployer_supply_pct": 0.0,
        "shadow_cluster_supply_pct": 16.0,
        "root_funder_alias": "funderblue",
        "pattern": "COVERT_MULTI_HOP_EARLY_ACCUMULATION",
    },
    "$RL": {
        "symbol": "$RL",
        "deployer_supply_pct": 0.0,
        "shadow_cluster_supply_pct": 95.65,
        "root_funder_alias": "funderblue",
        "pattern": "SLOT0_TOTAL_SUPPLY_LOCK_FRAGMENTED_SYBIL",
    },
}


class DictAccessMixin:
    """Mixin allowing dataclasses to be accessed both via attributes and dictionary keys."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def keys(self) -> Iterable[str]:
        return self.__dataclass_fields__.keys()  # type: ignore[attr-defined]


@dataclass
class FundingTransferEdge(DictAccessMixin):
    """Represents a directed SOL transfer between two wallets."""

    source: str
    target: str
    amount_sol: float
    timestamp: float = 0.0
    slot: int = 0
    tx_signature: str = ""


@dataclass
class EarlyBuyerRecord(DictAccessMixin):
    """Represents one of the top 100 early buyers of a Pump.fun token launch."""

    wallet: str
    supply_pct: float
    buy_sol: float = 0.0
    buy_slot: int = 0
    buy_timestamp: float = 0.0
    tx_signature: str = ""
    rank: int = 0


@dataclass
class TokenLaunchTransaction(DictAccessMixin):
    """Represents a transaction during or shortly after a token launch."""

    tx_signature: str
    trader: str
    tx_type: str  # "buy", "sell", "transfer", "atomic_wash"
    block: int
    amount_sol: float = 0.0
    token_amount: float = 0.0
    supply_pct_acquired: float = 0.0
    timestamp: float = 0.0
    instructions: List[str] = field(default_factory=list)
    downstream_sol_recipient: Optional[str] = None


@dataclass
class ShadowClusterResolutionResult(DictAccessMixin):
    """Result of Step 1.1 Zero-Dev Shadow Cluster Resolution."""

    token_mint: str
    deployer_wallet: str
    deployer_supply_pct: float
    root_funder_wallet: Optional[str]
    root_funder_alias: str
    hop_distance_to_deployer: int
    backward_funding_path: List[str]
    shadow_cluster_wallets: List[str]
    shadow_cluster_supply_pct: float
    zero_dev_illusion_detected: bool
    illusion_archetype: str
    terminal_boundary_nodes_pruned: List[str]
    top_early_buyers_scanned: int
    cluster_id: str


@dataclass
class Slot0BundleBotDetectionResult(DictAccessMixin):
    """Result of Algorithm 1 (Slot 0 Bundle Bot Detection)."""

    token_mint: str
    deployer_wallet: str
    launch_block: int
    indicator: int
    is_bundle_bot: bool
    bundled_wallets: List[str]
    slot0_non_creator_buy_txs: List[Dict[str, Any]]
    bundle_supply_pct: float
    is_primary_single_block_rug_indicator: bool


@dataclass
class EarlyBlockSniperDetectionResult(DictAccessMixin):
    """Result of Algorithm 2 (Early Block Sniper Bot Detection, K=5 blocks)."""

    token_mint: str
    deployer_wallet: str
    launch_block: int
    k_blocks: int
    indicator: int
    is_sniper_bot: bool
    sniper_wallets: List[str]
    early_sniper_txs: List[Dict[str, Any]]
    sniper_supply_pct: float


@dataclass
class WashTradingDetectionResult(DictAccessMixin):
    """Result of WT1 (Smart-Contract Atomic Wash) and WT2 (High-Frequency Bump Bot) detectors."""

    token_mint: str
    wt1_atomic_wash_detected: bool
    wt1_offending_txs: List[str]
    wt1_wash_signers: List[str]
    wt2_bump_bot_detected: bool
    wt2_tx_count: int
    wt2_total_sol_volume: float
    wt2_tx_to_sol_volume_ratio: float
    wt2_avg_trade_size_sol: float
    wt2_bump_bot_wallets: List[str]


@dataclass
class PersistentClusterResolution(DictAccessMixin):
    """Result of Step 1.2 Louvain Graph + CEX Sink Clustering + Cross-Token Co-Holding Scan."""

    token_mint: str
    cluster_id: str
    louvain_communities: List[List[str]]
    primary_shadow_community: List[str]
    cex_sink_clusters: Dict[str, List[str]]
    cross_token_coholding_wallets: List[str]
    coholding_wallet_count: int
    is_recurring_syndicate_15_30: bool
    total_clustered_wallets: List[str]


def _classify_identity_entry(address: str, raw: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Normalizes a Helius identity record and determines if it is a terminal boundary node."""
    if raw is not None:
        category = str(raw.get("category", "UNKNOWN")).upper()
        name = str(raw.get("name", address))
        entity = str(raw.get("entity", name))
        tags = list(raw.get("tags", []))
        is_terminal = bool(
            raw.get(
                "is_terminal_boundary",
                category in TERMINAL_BOUNDARY_CATEGORIES
                or any(t in {"cex", "exchange", "market_maker", "bridge", "vault"} for t in tags),
            )
        )
        return {
            "address": address,
            "name": name,
            "category": category,
            "entity": entity,
            "tags": tags,
            "is_terminal_boundary": is_terminal,
            "prune_from_shadow_clustering": is_terminal,
            "labeled_database_size": HELIUS_LABELED_ENTITIES_COUNT,
        }

    addr_lower = address.lower()
    if addr_lower.endswith(".sol") or addr_lower.endswith(".bonk"):
        domain_type = "SNS_SOL_DOMAIN" if addr_lower.endswith(".sol") else "ANS_BONK_DOMAIN"
        is_exchange_domain = any(
            ex in addr_lower for ex in ("binance", "coinbase", "kraken", "okx", "bybit", "wintermute")
        )
        category = "CEX_HOT_WALLET" if is_exchange_domain else "DOMAIN_IDENTITY"
        return {
            "address": address,
            "name": address,
            "category": category,
            "entity": address.split(".")[0],
            "tags": ["domain", domain_type.lower()],
            "is_terminal_boundary": is_exchange_domain,
            "prune_from_shadow_clustering": is_exchange_domain,
            "labeled_database_size": HELIUS_LABELED_ENTITIES_COUNT,
        }

    if any(tag in addr_lower for tag in ("deposit", "subaccount", "sink", "otc")):
        return {
            "address": address,
            "name": f"Dedicated CEX Deposit / OTC Sink ({address[:8]})",
            "category": "CEX_DEPOSIT_SINK",
            "entity": "CEX_USER_DEPOSIT_SINK",
            "tags": ["cex_deposit_sink", "otc_sink"],
            "is_terminal_boundary": False,
            "prune_from_shadow_clustering": False,
            "labeled_database_size": HELIUS_LABELED_ENTITIES_COUNT,
        }

    if any(tag in addr_lower for tag in ("binance", "coinbase", "kraken", "okx", "bybit", "cex_hot")):
        return {
            "address": address,
            "name": f"Labeled CEX Hot Wallet ({address[:8]})",
            "category": "CEX_HOT_WALLET",
            "entity": "CEX",
            "tags": ["cex", "exchange", "hot_wallet"],
            "is_terminal_boundary": True,
            "prune_from_shadow_clustering": True,
            "labeled_database_size": HELIUS_LABELED_ENTITIES_COUNT,
        }

    if any(tag in addr_lower for tag in ("wintermute", "jumptrading", "institutional_mm", "gsr_mm")):
        return {
            "address": address,
            "name": f"Institutional Market Maker ({address[:8]})",
            "category": "INSTITUTIONAL_MM",
            "entity": "Institutional MM",
            "tags": ["market_maker", "institutional"],
            "is_terminal_boundary": True,
            "prune_from_shadow_clustering": True,
            "labeled_database_size": HELIUS_LABELED_ENTITIES_COUNT,
        }

    if any(tag in addr_lower for tag in ("raydium_vault", "pumpswap_vault", "defi_vault", "wormhole_bridge")):
        return {
            "address": address,
            "name": f"Public DeFi Vault/Bridge ({address[:8]})",
            "category": "PUBLIC_DEFI_VAULT",
            "entity": "Public Protocol",
            "tags": ["defi", "vault", "bridge"],
            "is_terminal_boundary": True,
            "prune_from_shadow_clustering": True,
            "labeled_database_size": HELIUS_LABELED_ENTITIES_COUNT,
        }

    return {
        "address": address,
        "name": "Unlabeled Solana Wallet",
        "category": "UNLABELED_EOA",
        "entity": "Unknown",
        "tags": [],
        "is_terminal_boundary": False,
        "prune_from_shadow_clustering": False,
        "labeled_database_size": HELIUS_LABELED_ENTITIES_COUNT,
    }


def batch_resolve_helius_identities(
    addresses: Sequence[str],
    api_key: Optional[str] = None,
    custom_registry: Optional[Mapping[str, Mapping[str, Any]]] = None,
    transport: Optional[Callable[[str, bytes, Mapping[str, str]], Mapping[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Models POST https://api.helius.xyz/v1/wallet/batch-identity processing up to 100
    Solana addresses or .sol/.bonk domains per batch against 32,500+ labeled entities.

    Tags CEX hot wallets (Binance, Coinbase, etc.), institutional market makers,
    and public DeFi vaults as terminal boundary nodes (`is_terminal_boundary = True`)
    so multi-hop graph traversal never conflates independent exchange users.
    """
    unique_addresses: List[str] = []
    seen: Set[str] = set()
    for addr in addresses:
        cleaned = str(addr).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique_addresses.append(cleaned)

    merged_registry: Dict[str, Dict[str, Any]] = dict(DEFAULT_HELIUS_ENTITY_REGISTRY)
    if custom_registry:
        for addr, meta in custom_registry.items():
            merged_registry[addr] = dict(meta)

    resolved: Dict[str, Dict[str, Any]] = {}
    total_batches = math.ceil(len(unique_addresses) / HELIUS_BATCH_IDENTITY_MAX_ADDRS) if unique_addresses else 0

    for batch_idx in range(total_batches):
        batch = unique_addresses[
            batch_idx * HELIUS_BATCH_IDENTITY_MAX_ADDRS : (batch_idx + 1) * HELIUS_BATCH_IDENTITY_MAX_ADDRS
        ]
        assert len(batch) <= HELIUS_BATCH_IDENTITY_MAX_ADDRS

        payload_bytes = orjson.dumps(
            {
                "addresses": batch,
                "includeDomains": True,
                "batchIndex": batch_idx,
            }
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'helius-offline-deterministic-key'}",
            "X-Helius-Batch-Size": str(len(batch)),
        }

        transport_results: Dict[str, Any] = {}
        if transport is not None:
            resp = transport(HELIUS_BATCH_IDENTITY_ENDPOINT, payload_bytes, headers)
            if isinstance(resp, Mapping):
                transport_results = dict(resp.get("identities", resp))

        for addr in batch:
            raw_entry = transport_results.get(addr) or merged_registry.get(addr)
            entry = _classify_identity_entry(addr, raw_entry)
            entry["batch_index"] = batch_idx
            entry["batch_size"] = len(batch)
            resolved[addr] = entry

    return resolved


def _coerce_funding_edge(edge: Union[FundingTransferEdge, Mapping[str, Any]]) -> FundingTransferEdge:
    if isinstance(edge, FundingTransferEdge):
        return edge
    return FundingTransferEdge(
        source=str(edge["source"]),
        target=str(edge["target"]),
        amount_sol=float(edge.get("amount_sol", edge.get("weight", 0.0))),
        timestamp=float(edge.get("timestamp", 0.0)),
        slot=int(edge.get("slot", 0)),
        tx_signature=str(edge.get("tx_signature", "")),
    )


def _coerce_early_buyer(
    buyer: Union[EarlyBuyerRecord, Mapping[str, Any]], idx: int
) -> EarlyBuyerRecord:
    if isinstance(buyer, EarlyBuyerRecord):
        return buyer
    return EarlyBuyerRecord(
        wallet=str(buyer["wallet"]),
        supply_pct=float(buyer.get("supply_pct", 0.0)),
        buy_sol=float(buyer.get("buy_sol", 0.0)),
        buy_slot=int(buyer.get("buy_slot", 0)),
        buy_timestamp=float(buyer.get("buy_timestamp", 0.0)),
        tx_signature=str(buyer.get("tx_signature", "")),
        rank=int(buyer.get("rank", idx + 1)),
    )


def _coerce_launch_tx(
    tx: Union[TokenLaunchTransaction, Mapping[str, Any]]
) -> TokenLaunchTransaction:
    if isinstance(tx, TokenLaunchTransaction):
        return tx
    return TokenLaunchTransaction(
        tx_signature=str(tx.get("tx_signature", tx.get("signature", ""))),
        trader=str(tx.get("trader", tx.get("signer", tx.get("wallet", "")))),
        tx_type=str(tx.get("tx_type", tx.get("type", "buy"))).lower(),
        block=int(tx.get("block", tx.get("slot", 0))),
        amount_sol=float(tx.get("amount_sol", tx.get("sol_amount", 0.0))),
        token_amount=float(tx.get("token_amount", 0.0)),
        supply_pct_acquired=float(tx.get("supply_pct_acquired", tx.get("supply_pct", 0.0))),
        timestamp=float(tx.get("timestamp", 0.0)),
        instructions=list(tx.get("instructions", [])),
        downstream_sol_recipient=tx.get("downstream_sol_recipient"),
    )


def compute_deterministic_cluster_id(wallets: Iterable[str], root_funder: Optional[str] = None) -> str:
    """Computes a canonical persistent cluster_id (C_k) from member wallets and root funder."""
    canonical = sorted({str(w).strip() for w in wallets if str(w).strip()})
    seed_str = f"root={root_funder or 'none'}|members={','.join(canonical)}"
    digest = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:12]
    return f"cluster_{digest}"


def build_forensic_digraph(
    funding_edges: Sequence[Union[FundingTransferEdge, Mapping[str, Any]]],
    identities: Optional[Mapping[str, Mapping[str, Any]]] = None,
    deployer_wallet: Optional[str] = None,
    early_buyers: Optional[Sequence[Union[EarlyBuyerRecord, Mapping[str, Any]]]] = None,
) -> nx.DiGraph:
    """
    Constructs a directed NetworkX graph G = (V, E) with edges e_ij = (v_i, v_j, w, t).
    """
    graph = nx.DiGraph()
    coerced_edges = [_coerce_funding_edge(e) for e in funding_edges]
    if early_buyers:
        all_coerced_buyers = [_coerce_early_buyer(b, i) for i, b in enumerate(early_buyers)]
        all_coerced_buyers.sort(key=lambda b: (b.buy_slot, b.buy_timestamp, b.rank))
        coerced_buyers = all_coerced_buyers[:100]
    else:
        coerced_buyers = []

    all_addrs: List[str] = []
    for edge in coerced_edges:
        all_addrs.append(edge.source)
        all_addrs.append(edge.target)
    if deployer_wallet:
        all_addrs.append(deployer_wallet)
    for buyer in coerced_buyers:
        all_addrs.append(buyer.wallet)

    resolved_ids = (
        dict(identities)
        if identities is not None
        else batch_resolve_helius_identities(all_addrs)
    )

    buyer_map = {b.wallet: b for b in coerced_buyers}

    for addr in set(all_addrs):
        id_meta = resolved_ids.get(addr) or _classify_identity_entry(addr)
        buyer_info = buyer_map.get(addr)
        graph.add_node(
            addr,
            is_deployer=(addr == deployer_wallet),
            is_early_buyer=(addr in buyer_map),
            supply_pct=(buyer_info.supply_pct if buyer_info else 0.0),
            is_terminal_boundary=bool(id_meta.get("is_terminal_boundary", False)),
            category=id_meta.get("category", "UNLABELED_EOA"),
            entity_name=id_meta.get("name", "Unlabeled Solana Wallet"),
        )

    for edge in coerced_edges:
        if graph.has_edge(edge.source, edge.target):
            existing = graph[edge.source][edge.target]
            existing["weight"] = float(existing.get("weight", 0.0)) + edge.amount_sol
            existing["amount_sol"] = existing["weight"]
            existing["tx_count"] = int(existing.get("tx_count", 1)) + 1
            existing["timestamp"] = max(float(existing.get("timestamp", 0.0)), edge.timestamp)
            existing["t"] = existing["timestamp"]
            existing["w"] = existing["weight"]
            existing.setdefault("signatures", []).append(edge.tx_signature)
        else:
            graph.add_edge(
                edge.source,
                edge.target,
                weight=edge.amount_sol,
                amount_sol=edge.amount_sol,
                w=edge.amount_sol,
                timestamp=edge.timestamp,
                t=edge.timestamp,
                slot=edge.slot,
                tx_count=1,
                signatures=[edge.tx_signature] if edge.tx_signature else [],
            )

    return graph


def resolve_zero_dev_shadow_cluster(
    token_mint: str,
    deployer_wallet: str,
    funding_edges: Sequence[Union[FundingTransferEdge, Mapping[str, Any]]],
    early_buyers: Sequence[Union[EarlyBuyerRecord, Mapping[str, Any]]],
    deployer_supply_pct: float = 0.0,
    max_hops: int = 5,
    custom_identities: Optional[Mapping[str, Mapping[str, Any]]] = None,
    root_funder_alias: str = "funderblue",
) -> ShadowClusterResolutionResult:
    """
    Step 1.1: Zero-Dev Shadow Cluster Resolver & Helius Batch Identity Whitelister.

    Given a Pump.fun token mint A and deployer address w_c holding 0% of supply
    ("Zero-Percent Developer Illusion", modeling BATON and $RL), traces SOL funding
    origins 1 to 5 hops backward to identify the root parent treasury P_root ("funderblue")
    and performs a forward reachability scan (1 to 5 hops) from P_root across the top 100
    early buyers while pruning Helius-labeled CEX hot wallets, institutional market makers,
    and public DeFi vaults (`is_terminal_boundary = True`).
    """
    max_hops = max(1, min(int(max_hops), 5))
    all_buyers = [_coerce_early_buyer(b, idx) for idx, b in enumerate(early_buyers)]
    all_buyers.sort(key=lambda b: (b.buy_slot, b.buy_timestamp, b.rank))
    top_100_buyers = all_buyers[:100]
    coerced_edges = [_coerce_funding_edge(e) for e in funding_edges]

    all_addresses: List[str] = [deployer_wallet]
    for edge in coerced_edges:
        all_addresses.extend([edge.source, edge.target])
    for buyer in top_100_buyers:
        all_addresses.append(buyer.wallet)

    identities = batch_resolve_helius_identities(
        all_addresses,
        custom_registry=custom_identities,
    )
    graph = build_forensic_digraph(
        funding_edges=coerced_edges,
        identities=identities,
        deployer_wallet=deployer_wallet,
        early_buyers=top_100_buyers,
    )

    terminal_nodes_pruned: Set[str] = {
        addr for addr, meta in identities.items() if meta.get("is_terminal_boundary", False)
    }

    # 1. Trace backward 1..max_hops from deployer_wallet (w_c) to locate root parent treasury P_root
    best_root: Optional[str] = None
    best_depth: int = 0
    best_path: List[str] = [deployer_wallet]

    # BFS backward on predecessor edges, stopping at terminal boundary nodes
    queue: deque[Tuple[str, int, List[str]]] = deque([(deployer_wallet, 0, [deployer_wallet])])
    visited_backward: Dict[str, int] = {deployer_wallet: 0}

    candidate_ancestors: List[Tuple[str, int, List[str]]] = []
    while queue:
        curr, depth, path = queue.popleft()
        if depth >= max_hops:
            continue
        if curr not in graph:
            continue
        for pred in graph.predecessors(curr):
            if pred in terminal_nodes_pruned:
                continue
            next_depth = depth + 1
            if pred not in visited_backward or next_depth < visited_backward[pred]:
                visited_backward[pred] = next_depth
                next_path = [pred] + path
                candidate_ancestors.append((pred, next_depth, next_path))
                queue.append((pred, next_depth, next_path))

    buyer_wallet_set: Set[str] = {
        b.wallet for b in top_100_buyers if b.wallet not in terminal_nodes_pruned
    }

    def _reachable_buyers_from(start_node: str) -> Set[str]:
        if start_node not in graph or start_node in terminal_nodes_pruned:
            return set()
        q: deque[Tuple[str, int]] = deque([(start_node, 0)])
        seen: Dict[str, int] = {start_node: 0}
        reached: Set[str] = set()
        while q:
            curr_n, d = q.popleft()
            if d >= max_hops:
                continue
            for succ in graph.successors(curr_n):
                if succ in terminal_nodes_pruned:
                    continue
                nd = d + 1
                if succ not in seen or nd < seen[succ]:
                    seen[succ] = nd
                    if succ in buyer_wallet_set:
                        reached.add(succ)
                    q.append((succ, nd))
        return reached

    if candidate_ancestors:
        # Prefer non-terminal ancestor with substantial SOL funding (>= 0.1 SOL),
        # maximum downstream early-buyer reachability count, zero meaningful non-terminal
        # predecessors (true root treasury), and deepest hop reach.
        def _ancestor_rank(item: Tuple[str, int, List[str]]) -> Tuple[int, int, int, int, int, float]:
            node, depth, _ = item
            out_sol = sum(
                float(graph[node][s].get("amount_sol", 0.0))
                for s in graph.successors(node)
                if s not in terminal_nodes_pruned
            )
            has_substantial_sol = 1 if out_sol >= 0.1 else 0
            reachable_buyers_count = len(_reachable_buyers_from(node))
            non_terminal_preds = [
                p
                for p in graph.predecessors(node)
                if p not in terminal_nodes_pruned
                and float(graph[p][node].get("amount_sol", 0.0)) >= 0.1
            ]
            is_true_root = 1 if len(non_terminal_preds) == 0 else 0
            out_deg = sum(
                1
                for s in graph.successors(node)
                if s not in terminal_nodes_pruned
                and float(graph[node][s].get("amount_sol", 0.0)) >= 0.1
            )
            return (
                has_substantial_sol,
                reachable_buyers_count,
                is_true_root,
                out_deg,
                depth,
                out_sol,
            )

        best_root, best_depth, best_path = max(candidate_ancestors, key=_ancestor_rank)
    else:
        # Fallback: check if early buyers share a non-terminal root ancestor within 1..max_hops
        ancestor_to_buyers: Dict[str, Set[str]] = defaultdict(set)
        for buyer in top_100_buyers:
            if buyer.wallet in terminal_nodes_pruned or buyer.wallet not in graph:
                continue
            b_queue: deque[Tuple[str, int]] = deque([(buyer.wallet, 0)])
            b_seen: Set[str] = {buyer.wallet}
            while b_queue:
                node, d = b_queue.popleft()
                if d >= max_hops:
                    continue
                for pred in graph.predecessors(node):
                    if pred in terminal_nodes_pruned or pred in b_seen:
                        continue
                    b_seen.add(pred)
                    ancestor_to_buyers[pred].add(buyer.wallet)
                    b_queue.append((pred, d + 1))
        if ancestor_to_buyers:
            best_root = max(
                ancestor_to_buyers.keys(),
                key=lambda k: (len(ancestor_to_buyers[k]), graph.out_degree(k)),
            )
            best_depth = 1
            best_path = [best_root, deployer_wallet]

    # 2. Forward reachability scan (1..max_hops) from P_root across top 100 early buyers
    reachable_from_root: Set[str] = set()
    if best_root and best_root in graph and best_root not in terminal_nodes_pruned:
        fwd_queue: deque[Tuple[str, int]] = deque([(best_root, 0)])
        visited_forward: Dict[str, int] = {best_root: 0}
        while fwd_queue:
            curr, depth = fwd_queue.popleft()
            if depth >= max_hops:
                continue
            for succ in graph.successors(curr):
                if succ in terminal_nodes_pruned:
                    continue
                next_depth = depth + 1
                if succ not in visited_forward or next_depth < visited_forward[succ]:
                    visited_forward[succ] = next_depth
                    reachable_from_root.add(succ)
                    fwd_queue.append((succ, next_depth))

    # Also include any early buyer funded directly/transitively by deployer_wallet within max_hops
    if deployer_wallet in graph and deployer_wallet not in terminal_nodes_pruned:
        dep_queue: deque[Tuple[str, int]] = deque([(deployer_wallet, 0)])
        dep_seen: Set[str] = {deployer_wallet}
        while dep_queue:
            curr, depth = dep_queue.popleft()
            if depth >= max_hops:
                continue
            for succ in graph.successors(curr):
                if succ in terminal_nodes_pruned or succ in dep_seen:
                    continue
                dep_seen.add(succ)
                reachable_from_root.add(succ)
                dep_queue.append((succ, depth + 1))

    shadow_wallets: List[str] = []
    shadow_wallets_set: Set[str] = set()
    shadow_supply_pct = 0.0
    for buyer in top_100_buyers:
        if buyer.wallet in reachable_from_root and buyer.wallet not in terminal_nodes_pruned:
            if buyer.wallet not in shadow_wallets_set:
                shadow_wallets_set.add(buyer.wallet)
                shadow_wallets.append(buyer.wallet)
                shadow_supply_pct += buyer.supply_pct

    shadow_supply_pct = round(min(100.0, shadow_supply_pct), 4)
    zero_dev_illusion = bool(deployer_supply_pct == 0.0 and shadow_supply_pct > 0.0)

    if shadow_supply_pct >= 80.0:
        archetype = "RL_STYLE_TOTAL_SUPPLY_LOCK_95PCT"
    elif shadow_supply_pct >= 15.0:
        archetype = "BATON_STYLE_COVERT_SHADOW_CLUSTER_16PCT"
    elif shadow_supply_pct > 0.0:
        archetype = "LOW_DENSITY_SHADOW_CLUSTER"
    else:
        archetype = "CLEAN_INDEPENDENT_DISTRIBUTION"

    cluster_id = compute_deterministic_cluster_id(
        shadow_wallets or [deployer_wallet],
        root_funder=best_root,
    )

    return ShadowClusterResolutionResult(
        token_mint=token_mint,
        deployer_wallet=deployer_wallet,
        deployer_supply_pct=round(deployer_supply_pct, 4),
        root_funder_wallet=best_root,
        root_funder_alias=root_funder_alias if best_root else "none",
        hop_distance_to_deployer=best_depth,
        backward_funding_path=best_path,
        shadow_cluster_wallets=shadow_wallets,
        shadow_cluster_supply_pct=shadow_supply_pct,
        zero_dev_illusion_detected=zero_dev_illusion,
        illusion_archetype=archetype,
        terminal_boundary_nodes_pruned=sorted(terminal_nodes_pruned),
        top_early_buyers_scanned=len(top_100_buyers),
        cluster_id=cluster_id,
    )


def detect_slot0_bundle_bot(
    token_mint: str,
    deployer_wallet: str,
    launch_block: int,
    transactions: Sequence[Union[TokenLaunchTransaction, Mapping[str, Any]]],
    rug_indicator_supply_threshold_pct: float = 10.0,
) -> Slot0BundleBotDetectionResult:
    """
    Step 1.2 Algorithm 1 (Slot 0 Bundle Bot Detection):
      1_{BundleBot}(A) = 1 if exists tx in T_launch s.t. tx.type == 'buy' and tx.trader != w_c else 0
    Flags `bundle_supply_pct > 10.0` as a primary single-block rug-pull indicator.
    """
    coerced = [_coerce_launch_tx(tx) for tx in transactions]
    slot0_buys = [
        tx
        for tx in coerced
        if tx.block == launch_block and tx.tx_type == "buy" and tx.trader != deployer_wallet
    ]

    indicator = 1 if len(slot0_buys) > 0 else 0
    bundled_wallets: List[str] = []
    bundled_set: Set[str] = set()
    for tx in slot0_buys:
        if tx.trader not in bundled_set:
            bundled_set.add(tx.trader)
            bundled_wallets.append(tx.trader)

    bundle_supply_pct = round(sum(tx.supply_pct_acquired for tx in slot0_buys), 4)
    is_primary_rug_indicator = bool(bundle_supply_pct > rug_indicator_supply_threshold_pct)

    return Slot0BundleBotDetectionResult(
        token_mint=token_mint,
        deployer_wallet=deployer_wallet,
        launch_block=launch_block,
        indicator=indicator,
        is_bundle_bot=bool(indicator == 1),
        bundled_wallets=bundled_wallets,
        slot0_non_creator_buy_txs=[tx.to_dict() for tx in slot0_buys],
        bundle_supply_pct=bundle_supply_pct,
        is_primary_single_block_rug_indicator=is_primary_rug_indicator,
    )


def detect_early_block_sniper_bot(
    token_mint: str,
    deployer_wallet: str,
    launch_block: int,
    transactions: Sequence[Union[TokenLaunchTransaction, Mapping[str, Any]]],
    k_blocks: int = 5,
) -> EarlyBlockSniperDetectionResult:
    """
    Step 1.2 Algorithm 2 (Early Block Sniper Bot Detection, K = 5 blocks):
      1_{SniperBot}(A, K=5) = 1 if exists tx in T_early s.t. tx.type == 'buy' and tx.trader != w_c else 0
    where T_early = {tx in T | b_launch < tx.block <= b_launch + K}.
    """
    coerced = [_coerce_launch_tx(tx) for tx in transactions]
    early_buys = [
        tx
        for tx in coerced
        if (launch_block < tx.block <= launch_block + k_blocks)
        and tx.tx_type == "buy"
        and tx.trader != deployer_wallet
    ]

    indicator = 1 if len(early_buys) > 0 else 0
    sniper_wallets: List[str] = []
    sniper_set: Set[str] = set()
    for tx in early_buys:
        if tx.trader not in sniper_set:
            sniper_set.add(tx.trader)
            sniper_wallets.append(tx.trader)

    sniper_supply_pct = round(sum(tx.supply_pct_acquired for tx in early_buys), 4)

    return EarlyBlockSniperDetectionResult(
        token_mint=token_mint,
        deployer_wallet=deployer_wallet,
        launch_block=launch_block,
        k_blocks=k_blocks,
        indicator=indicator,
        is_sniper_bot=bool(indicator == 1),
        sniper_wallets=sniper_wallets,
        early_sniper_txs=[tx.to_dict() for tx in early_buys],
        sniper_supply_pct=sniper_supply_pct,
    )


def detect_wash_trading_wt1_wt2(
    token_mint: str,
    transactions: Sequence[Union[TokenLaunchTransaction, Mapping[str, Any]]],
    wt2_ratio_threshold: float = 20.0,
    wt2_min_tx_count: int = 5,
) -> WashTradingDetectionResult:
    """
    Step 1.2 Wash Trading Detectors:
      - WT1 Smart-Contract Wash Trading: Same signer executing opposing buy and sell inside
        one atomic transaction (either via instructions containing both buy & sell, or duplicate
        tx_signature with opposing buy/sell legs by the same signer).
      - WT2 High-Frequency Bump Botting: Anomalous tx-count-to-SOL-volume ratio (micro-buys/sells
        flooding the Pump.fun front-page ticker).
    """
    coerced = [_coerce_launch_tx(tx) for tx in transactions]

    # WT1 detection:
    # Case A: Single transaction object with instructions containing both buy and sell or tx_type == "atomic_wash"
    # Case B: Multiple legs sharing the same tx_signature & signer with both "buy" and "sell"
    wt1_txs: List[str] = []
    wt1_txs_set: Set[str] = set()
    wt1_signers: List[str] = []
    wt1_signers_set: Set[str] = set()

    by_sig_and_signer: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    for tx in coerced:
        ix_tokens = {
            tok.strip()
            for raw_ix in tx.instructions
            for tok in raw_ix.lower().replace("::", ":").replace(".", ":").replace("/", ":").split(":")
            if tok.strip()
        }
        has_buy_ix = any(ix in {"buy", "swap_buy"} for ix in ix_tokens)
        has_sell_ix = any(ix in {"sell", "swap_sell"} for ix in ix_tokens)
        if tx.tx_type in {"atomic_wash", "wash"} or (has_buy_ix and has_sell_ix):
            if tx.tx_signature not in wt1_txs_set:
                wt1_txs_set.add(tx.tx_signature)
                wt1_txs.append(tx.tx_signature)
            if tx.trader not in wt1_signers_set:
                wt1_signers_set.add(tx.trader)
                wt1_signers.append(tx.trader)
        if tx.tx_signature:
            by_sig_and_signer[(tx.tx_signature, tx.trader)].add(tx.tx_type)

    for (sig, signer), types in by_sig_and_signer.items():
        if "buy" in types and "sell" in types:
            if sig not in wt1_txs_set:
                wt1_txs_set.add(sig)
                wt1_txs.append(sig)
            if signer not in wt1_signers_set:
                wt1_signers_set.add(signer)
                wt1_signers.append(signer)

    # WT2 detection: Anomalous tx-count-to-SOL-volume ratio
    trade_txs = [tx for tx in coerced if tx.tx_type in {"buy", "sell", "bump", "atomic_wash"}]
    tx_count = len(trade_txs)
    total_sol_vol = sum(max(0.0, tx.amount_sol) for tx in trade_txs)
    tx_to_vol_ratio = tx_count / max(total_sol_vol, 1e-6) if tx_count > 0 else 0.0
    avg_trade_sol = total_sol_vol / tx_count if tx_count > 0 else 0.0

    # Per-wallet micro-bump tracking
    wallet_tx_counts: Dict[str, int] = defaultdict(int)
    wallet_sol_vols: Dict[str, float] = defaultdict(float)
    for tx in trade_txs:
        wallet_tx_counts[tx.trader] += 1
        wallet_sol_vols[tx.trader] += max(0.0, tx.amount_sol)

    bump_wallets: List[str] = []
    for wallet, count in wallet_tx_counts.items():
        w_vol = wallet_sol_vols[wallet]
        w_ratio = count / max(w_vol, 1e-6)
        if count >= 2 and w_ratio >= wt2_ratio_threshold:
            bump_wallets.append(wallet)

    wt2_detected = bool(
        (tx_count >= wt2_min_tx_count and tx_to_vol_ratio >= wt2_ratio_threshold)
        or len(bump_wallets) > 0
    )

    return WashTradingDetectionResult(
        token_mint=token_mint,
        wt1_atomic_wash_detected=bool(len(wt1_txs) > 0),
        wt1_offending_txs=wt1_txs,
        wt1_wash_signers=wt1_signers,
        wt2_bump_bot_detected=wt2_detected,
        wt2_tx_count=tx_count,
        wt2_total_sol_volume=round(total_sol_vol, 6),
        wt2_tx_to_sol_volume_ratio=round(tx_to_vol_ratio, 4),
        wt2_avg_trade_size_sol=round(avg_trade_sol, 6),
        wt2_bump_bot_wallets=sorted(bump_wallets),
    )


def detect_cex_deposit_sink_clusters(
    post_sell_transfers: Sequence[Union[FundingTransferEdge, Mapping[str, Any]]],
    early_buyer_wallets: Optional[Sequence[str]] = None,
    identities: Optional[Mapping[str, Mapping[str, Any]]] = None,
    min_shared_depositors: int = 2,
) -> Dict[str, List[str]]:
    """
    Step 1.2 CEX Deposit Address Sink Clustering:
    Correlates post-sell SOL transfers from early buyers into a shared downstream
    user-specific CEX deposit address or OTC treasury sink address.
    Note: Excludes main omnibus CEX hot wallets (`is_terminal_boundary = True`) unless
    tagged as a user-specific deposit sink, preventing false conflation.
    """
    coerced = [_coerce_funding_edge(e) for e in post_sell_transfers]
    early_set = set(early_buyer_wallets) if early_buyer_wallets is not None else None

    all_addrs = [e.source for e in coerced] + [e.target for e in coerced]
    resolved_ids = (
        dict(identities)
        if identities is not None
        else batch_resolve_helius_identities(all_addrs)
    )

    sink_to_depositors: Dict[str, Set[str]] = defaultdict(set)
    for edge in coerced:
        if early_set is not None and edge.source not in early_set:
            continue
        target_meta = resolved_ids.get(edge.target, {})
        # Main omnibus CEX hot wallets are terminal boundaries; dedicated user CEX deposit
        # sub-accounts or OTC treasury sinks are NOT omnibus hot wallets.
        if target_meta.get("is_terminal_boundary", False):
            continue
        sink_to_depositors[edge.target].add(edge.source)

    return {
        sink: sorted(depositors)
        for sink, depositors in sink_to_depositors.items()
        if len(depositors) >= min_shared_depositors
    }


def resolve_persistent_cluster_id(
    token_mint: str,
    funding_edges: Sequence[Union[FundingTransferEdge, Mapping[str, Any]]],
    post_sell_transfers: Optional[Sequence[Union[FundingTransferEdge, Mapping[str, Any]]]] = None,
    historical_token_holders: Optional[Mapping[str, Sequence[str]]] = None,
    deployer_wallet: Optional[str] = None,
    early_buyers: Optional[Sequence[Union[EarlyBuyerRecord, Mapping[str, Any]]]] = None,
    custom_identities: Optional[Mapping[str, Mapping[str, Any]]] = None,
    min_coholding_launches: int = 2,
    resolution: float = 1.0,
) -> PersistentClusterResolution:
    """
    Step 1.2 Louvain Community Detection + CEX Sink Clustering + Cross-Token Co-Holding Deep Scan:
      - Constructs directed forensic graph G = (V, E) with edges e_ij = (v_i, v_j, w, t)
      - Prunes terminal boundary nodes (CEX hot wallets, institutional MMs, DeFi vaults)
      - Runs `networkx.community.louvain_communities` weighted by SOL transfer volume & temporal proximity
      - Incorporates CEX deposit sink clusters and cross-token co-holding deep scans (15-30 recurring wallets)
      - Resolves a persistent `cluster_id` (C_k).
    """
    coerced_edges = [_coerce_funding_edge(e) for e in funding_edges]
    coerced_post_sell = [_coerce_funding_edge(e) for e in (post_sell_transfers or [])]

    all_addrs: List[str] = []
    for e in coerced_edges + coerced_post_sell:
        all_addrs.extend([e.source, e.target])
    if deployer_wallet:
        all_addrs.append(deployer_wallet)
    if early_buyers:
        for b in early_buyers:
            all_addrs.append(_coerce_early_buyer(b, 0).wallet)

    identities = batch_resolve_helius_identities(all_addrs, custom_registry=custom_identities)
    digraph = build_forensic_digraph(
        funding_edges=coerced_edges,
        identities=identities,
        deployer_wallet=deployer_wallet,
        early_buyers=early_buyers,
    )

    early_buyer_addrs = (
        [_coerce_early_buyer(b, i).wallet for i, b in enumerate(early_buyers)]
        if early_buyers
        else None
    )
    sink_clusters = detect_cex_deposit_sink_clusters(
        post_sell_transfers=coerced_post_sell,
        early_buyer_wallets=early_buyer_addrs,
        identities=identities,
    )

    # Build weighted undirected projection excluding terminal boundary nodes for Louvain
    undirected = nx.Graph()
    for node, data in digraph.nodes(data=True):
        if not data.get("is_terminal_boundary", False):
            undirected.add_node(node)

    timestamps = [e.timestamp for e in coerced_edges if e.timestamp > 0]
    ref_time = max(timestamps) if timestamps else 0.0

    for u, v, data in digraph.edges(data=True):
        if u not in undirected or v not in undirected or u == v:
            continue
        sol_weight = max(0.01, float(data.get("weight", 1.0)))
        edge_ts = float(data.get("timestamp", 0.0))
        delta_t = max(0.0, ref_time - edge_ts) if (ref_time > 0 and edge_ts > 0) else 0.0
        temporal_factor = math.exp(-delta_t / 3600.0) if delta_t > 0 else 1.0
        combined_weight = sol_weight * (1.0 + temporal_factor)
        if undirected.has_edge(u, v):
            undirected[u][v]["weight"] += combined_weight
        else:
            undirected.add_edge(u, v, weight=combined_weight)

    # Add sink cluster co-sweep edges into undirected graph
    for sink, depositors in sink_clusters.items():
        if len(depositors) <= 30:
            for i in range(len(depositors)):
                for j in range(i + 1, len(depositors)):
                    d1, d2 = depositors[i], depositors[j]
                    if d1 in undirected and d2 in undirected:
                        if undirected.has_edge(d1, d2):
                            undirected[d1][d2]["weight"] += 10.0
                        else:
                            undirected.add_edge(d1, d2, weight=10.0)
        else:
            hub = depositors[0]
            n_dep = len(depositors)
            for i in range(n_dep):
                d_curr = depositors[i]
                d_next = depositors[(i + 1) % n_dep]
                for u_node, v_node in ((hub, d_curr), (d_curr, d_next)):
                    if u_node != v_node and u_node in undirected and v_node in undirected:
                        if undirected.has_edge(u_node, v_node):
                            undirected[u_node][v_node]["weight"] += 10.0
                        else:
                            undirected.add_edge(u_node, v_node, weight=10.0)

    # Cross-token co-holding deep scan (15-30 recurring wallets across launches)
    wallet_launch_counts: Dict[str, int] = defaultdict(int)
    if historical_token_holders:
        for _mint, holders in historical_token_holders.items():
            for holder in set(holders):
                if not identities.get(holder, {}).get("is_terminal_boundary", False):
                    wallet_launch_counts[holder] += 1

    coholding_wallets = sorted(
        w for w, count in wallet_launch_counts.items() if count >= min_coholding_launches
    )
    for w in coholding_wallets:
        if not identities.get(w, {}).get("is_terminal_boundary", False):
            undirected.add_node(w)

    if len(coholding_wallets) <= 30:
        for i in range(len(coholding_wallets)):
            for j in range(i + 1, len(coholding_wallets)):
                w1, w2 = coholding_wallets[i], coholding_wallets[j]
                if w1 in undirected and w2 in undirected:
                    if undirected.has_edge(w1, w2):
                        undirected[w1][w2]["weight"] += 5.0
                    else:
                        undirected.add_edge(w1, w2, weight=5.0)
    else:
        hub = coholding_wallets[0]
        n_coh = len(coholding_wallets)
        for i in range(n_coh):
            w_curr = coholding_wallets[i]
            w_next = coholding_wallets[(i + 1) % n_coh]
            for u_node, v_node in ((hub, w_curr), (w_curr, w_next)):
                if u_node != v_node and u_node in undirected and v_node in undirected:
                    if undirected.has_edge(u_node, v_node):
                        undirected[u_node][v_node]["weight"] += 5.0
                    else:
                        undirected.add_edge(u_node, v_node, weight=5.0)


    if undirected.number_of_nodes() > 0 and undirected.number_of_edges() > 0:
        raw_communities = nx.community.louvain_communities(
            undirected,
            weight="weight",
            resolution=resolution,
            seed=42,
        )
        communities = [sorted(list(c)) for c in raw_communities if len(c) > 0]
        communities.sort(key=lambda c: (-len(c), c[0]))
    elif undirected.number_of_nodes() > 0:
        communities = [[n] for n in sorted(undirected.nodes())]
    else:
        communities = []

    primary_community: List[str] = []
    if deployer_wallet:
        for comm in communities:
            if deployer_wallet in comm:
                primary_community = comm
                break
    if not primary_community and communities:
        primary_community = communities[0]

    merged_members = sorted(
        set(primary_community)
        | set(coholding_wallets)
        | {w for deps in sink_clusters.values() for w in deps}
    )

    is_recurring_15_30 = 15 <= len(coholding_wallets) <= 30 or len(coholding_wallets) >= 15
    cluster_id = compute_deterministic_cluster_id(merged_members or [token_mint])

    return PersistentClusterResolution(
        token_mint=token_mint,
        cluster_id=cluster_id,
        louvain_communities=communities,
        primary_shadow_community=primary_community,
        cex_sink_clusters=sink_clusters,
        cross_token_coholding_wallets=coholding_wallets,
        coholding_wallet_count=len(coholding_wallets),
        is_recurring_syndicate_15_30=is_recurring_15_30,
        total_clustered_wallets=merged_members,
    )
