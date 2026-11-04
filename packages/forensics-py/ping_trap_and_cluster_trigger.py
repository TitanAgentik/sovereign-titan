"""
Step 1.4: Multi-Wallet Cluster Trigger, Zero-Risk Recon Ping Trap & OFI/VPIN Gatekeeper.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Union


CLUSTER_CONFLUENCE_SNIPE_SIGNAL = "CLUSTER_CONFLUENCE_SNIPE_SIGNAL"
NO_CONFLUENCE_WAIT_SIGNAL = "NO_CONFLUENCE_WAIT_SIGNAL"

ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE = "ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE"
HOLD_POSITION_HEALTHY_FLOW = "HOLD_POSITION_HEALTHY_FLOW"

DEFAULT_MIN_CLUSTER_WALLETS = 3
DEFAULT_CLUSTER_WINDOW_SECONDS = 15.0
DEFAULT_MIN_WALLET_SCORE = 6.0
MAX_RECON_PING_SLIPPAGE_EXCLUSIVE = 0.000001
EXTERNAL_MARKET_PHASE1_COLLAPSE_PCT = 80.0


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
class ShadowWalletPurchaseEvent(DictAccessMixin):
    """Represents a real-time purchase event by a watched shadow cluster wallet."""

    wallet: str
    token_mint: str
    timestamp: float
    wallet_score: float
    amount_sol: float = 1.0
    cluster_id: str = ""
    is_whitelisted_runner: bool = True
    tx_signature: str = ""


@dataclass
class RootFunderSeedEvent(DictAccessMixin):
    """Represents a whitelisted root funder seeding a fresh deployer wallet."""

    root_funder_wallet: str
    fresh_deployer_wallet: str
    amount_sol: float
    timestamp: float
    cluster_id: str = ""
    is_whitelisted_runner_root: bool = True
    tx_signature: str = ""


@dataclass
class ClusterConfluenceTriggerResult(DictAccessMixin):
    """Result of Step 1.4 Multi-Wallet Cluster Trigger evaluation."""

    signal: str
    triggered: bool
    trigger_mode: str
    token_mint: str
    cluster_id: str
    qualifying_wallets: List[str]
    qualifying_wallet_count: int
    window_span_seconds: float
    min_wallets_required: int
    max_window_seconds: float
    min_wallet_score_required: float
    seeded_fresh_deployer: Optional[str] = None
    root_funder_wallet: Optional[str] = None


@dataclass
class ReconPingTrapProbe(DictAccessMixin):
    """Result of `build_zero_risk_recon_ping_trap`."""

    target_wallet: str
    token_mint: str
    max_slippage: float
    slippage_bps: float
    probe_lamports: int
    minimum_amount_out_raw: int
    expected_error_code: str
    guaranteed_onchain_revert: bool
    capital_at_risk_sol: float
    rpc_execution_alert_armed: bool
    probe_id: str
    simulation_only_flag: bool


@dataclass
class OrderFlowTick(DictAccessMixin):
    """Represents a trade or order book tick for 1m OFI and VPIN calculation."""

    timestamp: float
    side: str  # "buy" or "sell"
    volume_sol: float
    price_delta: float = 0.0
    signer: str = ""
    tx_type: str = "swap"  # "swap", "spl_transfer", "burn"
    recipient: Optional[str] = None
    tx_signature: str = ""


@dataclass
class OfiVpinGatekeeperResult(DictAccessMixin):
    """Result of 1-minute OFI, VPIN, and shadow-cluster outbound transfer tripwire gatekeeper."""

    token_mint: str
    action: str
    trigger_atomic_exit: bool
    ofi_1m_raw: float
    ofi_1m_normalized: float
    vpin_score: float
    toxic_order_flow_detected: bool
    shadow_cluster_sell_detected: bool
    shadow_cluster_outbound_transfer_detected: bool
    tripped_shadow_wallets: List[str]
    tripped_tx_signatures: List[str]
    external_market_phase1_collapse_avoided_pct: float
    exit_reasons: List[str] = field(default_factory=list)


def _coerce_purchase_event(
    ev: Union[ShadowWalletPurchaseEvent, Mapping[str, Any]]
) -> ShadowWalletPurchaseEvent:
    if isinstance(ev, ShadowWalletPurchaseEvent):
        return ev
    return ShadowWalletPurchaseEvent(
        wallet=str(ev.get("wallet", ev.get("trader", ""))),
        token_mint=str(ev.get("token_mint", "")),
        timestamp=float(ev.get("timestamp", 0.0)),
        wallet_score=float(ev.get("wallet_score", ev.get("score", 0.0))),
        amount_sol=float(ev.get("amount_sol", 1.0)),
        cluster_id=str(ev.get("cluster_id", "")),
        is_whitelisted_runner=bool(ev.get("is_whitelisted_runner", True)),
        tx_signature=str(ev.get("tx_signature", "")),
    )


def _coerce_seed_event(
    ev: Union[RootFunderSeedEvent, Mapping[str, Any]]
) -> RootFunderSeedEvent:
    if isinstance(ev, RootFunderSeedEvent):
        return ev
    return RootFunderSeedEvent(
        root_funder_wallet=str(ev.get("root_funder_wallet", ev.get("source", ""))),
        fresh_deployer_wallet=str(ev.get("fresh_deployer_wallet", ev.get("target", ""))),
        amount_sol=float(ev.get("amount_sol", 0.0)),
        timestamp=float(ev.get("timestamp", 0.0)),
        cluster_id=str(ev.get("cluster_id", "")),
        is_whitelisted_runner_root=bool(ev.get("is_whitelisted_runner_root", True)),
        tx_signature=str(ev.get("tx_signature", "")),
    )


def evaluate_multi_wallet_cluster_trigger(
    purchase_events: Sequence[Union[ShadowWalletPurchaseEvent, Mapping[str, Any]]],
    token_mint: str = "",
    cluster_id: str = "",
    min_wallets: int = DEFAULT_MIN_CLUSTER_WALLETS,
    window_seconds: float = DEFAULT_CLUSTER_WINDOW_SECONDS,
    min_wallet_score: float = DEFAULT_MIN_WALLET_SCORE,
    whitelisted_clusters: Optional[Set[str]] = None,
    root_seed_event: Optional[Union[RootFunderSeedEvent, Mapping[str, Any]]] = None,
) -> ClusterConfluenceTriggerResult:
    """
    Step 1.4 Multi-Wallet Cluster Trigger:
    Fires `CLUSTER_CONFLUENCE_SNIPE_SIGNAL` when:
      1. M >= 3 high-score shadow wallets (S >= 6.0) from a whitelisted
         `SERIAL_RUNNER_SYNDICATE` purchase within Delta t <= 15.0 seconds, OR
      2. A whitelisted root funder seeds a fresh deployer address.
    """
    # Check condition 2 first: whitelisted root funder seeding a fresh deployer address
    if root_seed_event is not None:
        seed = _coerce_seed_event(root_seed_event)
        root_allowed = seed.is_whitelisted_runner_root and (
            whitelisted_clusters is None
            or not seed.cluster_id
            or seed.cluster_id in whitelisted_clusters
        )
        if root_allowed and seed.fresh_deployer_wallet and seed.amount_sol > 0.0:
            return ClusterConfluenceTriggerResult(
                signal=CLUSTER_CONFLUENCE_SNIPE_SIGNAL,
                triggered=True,
                trigger_mode="WHITELISTED_ROOT_FUNDER_FRESH_DEPLOYER_SEED",
                token_mint=token_mint or "PRE_MINT_FRESH_DEPLOYER",
                cluster_id=seed.cluster_id or cluster_id or "whitelisted_runner_cluster",
                qualifying_wallets=[seed.root_funder_wallet, seed.fresh_deployer_wallet],
                qualifying_wallet_count=1,
                window_span_seconds=0.0,
                min_wallets_required=min_wallets,
                max_window_seconds=window_seconds,
                min_wallet_score_required=min_wallet_score,
                seeded_fresh_deployer=seed.fresh_deployer_wallet,
                root_funder_wallet=seed.root_funder_wallet,
            )

    coerced = [_coerce_purchase_event(e) for e in purchase_events]
    qualifying = [
        e
        for e in coerced
        if e.wallet_score >= min_wallet_score
        and e.is_whitelisted_runner
        and (not token_mint or not e.token_mint or e.token_mint == token_mint)
        and (
            whitelisted_clusters is None
            or not e.cluster_id
            or e.cluster_id in whitelisted_clusters
        )
    ]
    qualifying.sort(key=lambda e: e.timestamp)

    resolved_mint = token_mint or (qualifying[0].token_mint if qualifying else "unknown_mint")
    resolved_cluster = cluster_id or (qualifying[0].cluster_id if qualifying else "unknown_cluster")

    # Group by token_mint (and cluster_id when unspecified) so distinct mints are never conflated
    mint_groups: Dict[str, List[ShadowWalletPurchaseEvent]] = {}
    if token_mint:
        mint_groups[token_mint] = qualifying
    else:
        for ev in qualifying:
            m_key = ev.token_mint or "unknown_mint"
            mint_groups.setdefault(m_key, []).append(ev)

    # Sliding window search for >= min_wallets distinct wallets within <= window_seconds
    best_wallets: List[str] = []
    best_span: float = float("inf")
    best_mint: str = resolved_mint
    best_cluster: str = resolved_cluster

    for group_mint, group_events in mint_groups.items():
        n = len(group_events)
        for i in range(n):
            t_start = group_events[i].timestamp
            window_wallets: List[str] = []
            last_ts = t_start
            for j in range(i, n):
                span = group_events[j].timestamp - t_start
                if span <= window_seconds + 1e-9:
                    if group_events[j].wallet not in window_wallets:
                        window_wallets.append(group_events[j].wallet)
                        last_ts = group_events[j].timestamp
                    if len(window_wallets) >= min_wallets:
                        actual_span = max(0.0, last_ts - t_start)
                        if len(window_wallets) > len(best_wallets) or (
                            len(window_wallets) == len(best_wallets) and actual_span < best_span
                        ):
                            best_wallets = list(window_wallets)
                            best_span = actual_span
                            best_mint = token_mint or group_mint
                            best_cluster = cluster_id or (
                                group_events[i].cluster_id or resolved_cluster
                            )
                else:
                    break

    if len(best_wallets) >= min_wallets and best_span <= window_seconds + 1e-9:
        return ClusterConfluenceTriggerResult(
            signal=CLUSTER_CONFLUENCE_SNIPE_SIGNAL,
            triggered=True,
            trigger_mode="MULTI_WALLET_SHADOW_CONFLUENCE",
            token_mint=best_mint,
            cluster_id=best_cluster,
            qualifying_wallets=best_wallets,
            qualifying_wallet_count=len(best_wallets),
            window_span_seconds=round(best_span, 4),
            min_wallets_required=min_wallets,
            max_window_seconds=window_seconds,
            min_wallet_score_required=min_wallet_score,
        )

    distinct_qualifying = list(dict.fromkeys(e.wallet for e in qualifying))
    overall_span = (
        max(0.0, qualifying[-1].timestamp - qualifying[0].timestamp)
        if len(qualifying) >= 2
        else 0.0
    )
    return ClusterConfluenceTriggerResult(
        signal=NO_CONFLUENCE_WAIT_SIGNAL,
        triggered=False,
        trigger_mode="NONE",
        token_mint=resolved_mint,
        cluster_id=resolved_cluster,
        qualifying_wallets=distinct_qualifying,
        qualifying_wallet_count=len(distinct_qualifying),
        window_span_seconds=round(overall_span, 4),
        min_wallets_required=min_wallets,
        max_window_seconds=window_seconds,
        min_wallet_score_required=min_wallet_score,
    )


def build_zero_risk_recon_ping_trap(
    target_wallet: str,
    token_mint: str,
    max_slippage: float = 0.0000005,
    probe_lamports: int = 10_000,
) -> ReconPingTrapProbe:
    """
    Step 1.4 Recon Ping Trap:
    Builds a mirror recon probe with deliberately insufficient slippage (`< 0.000001`)
    so it generates an instant RPC execution alert while guaranteed to safely revert
    on-chain (`guaranteed_onchain_revert == True`, `capital_at_risk_sol == 0.0`).
    """
    if max_slippage <= 0.0 or max_slippage >= MAX_RECON_PING_SLIPPAGE_EXCLUSIVE:
        raise ValueError(
            f"Recon ping trap requires 0.0 < max_slippage < {MAX_RECON_PING_SLIPPAGE_EXCLUSIVE} "
            f"(got {max_slippage})"
        )
    if not target_wallet or not token_mint:
        raise ValueError("target_wallet and token_mint must be non-empty strings")

    # Set minimum_amount_out_raw to impossible ceiling so Pump.fun / PumpSwap / Raydium
    # program deterministically reverts with SlippageExceeded (Custom 6002) after firing RPC alert.
    impossible_min_out = (1 << 64) - 1
    slippage_bps = round(max_slippage * 10_000.0, 6)
    probe_hash = hashlib.sha256(
        f"{target_wallet}:{token_mint}:{max_slippage:.10f}:{probe_lamports}".encode("utf-8")
    ).hexdigest()[:16]

    return ReconPingTrapProbe(
        target_wallet=target_wallet,
        token_mint=token_mint,
        max_slippage=max_slippage,
        slippage_bps=slippage_bps,
        probe_lamports=int(probe_lamports),
        minimum_amount_out_raw=impossible_min_out,
        expected_error_code="Custom(6002):SlippageExceeded",
        guaranteed_onchain_revert=True,
        capital_at_risk_sol=0.0,
        rpc_execution_alert_armed=True,
        probe_id=f"recon_trap_{probe_hash}",
        simulation_only_flag=True,
    )


def _coerce_flow_tick(tick: Union[OrderFlowTick, Mapping[str, Any]]) -> OrderFlowTick:
    if isinstance(tick, OrderFlowTick):
        return tick
    return OrderFlowTick(
        timestamp=float(tick.get("timestamp", 0.0)),
        side=str(tick.get("side", "buy")).lower(),
        volume_sol=float(tick.get("volume_sol", tick.get("amount_sol", 0.0))),
        price_delta=float(tick.get("price_delta", 0.0)),
        signer=str(tick.get("signer", tick.get("wallet", tick.get("trader", "")))),
        tx_type=str(tick.get("tx_type", "swap")).lower(),
        recipient=tick.get("recipient"),
        tx_signature=str(tick.get("tx_signature", "")),
    )


def compute_1m_order_flow_imbalance(
    ticks: Sequence[Union[OrderFlowTick, Mapping[str, Any]]],
    window_seconds: float = 60.0,
) -> Tuple[float, float]:
    """
    Computes 1-minute Order Flow Imbalance (OFI):
      - `ofi_raw`: signed net volume (V_buy - V_sell) over the trailing 60s window
      - `ofi_normalized`: (V_buy - V_sell) / (V_buy + V_sell) in [-1.0, +1.0].
    """
    coerced = [_coerce_flow_tick(t) for t in ticks]
    if not coerced:
        return 0.0, 0.0

    latest_ts = max(t.timestamp for t in coerced)
    cutoff_ts = latest_ts - window_seconds
    window_ticks = [t for t in coerced if t.timestamp >= cutoff_ts]

    buy_vol = sum(max(0.0, t.volume_sol) for t in window_ticks if t.side == "buy")
    sell_vol = sum(max(0.0, t.volume_sol) for t in window_ticks if t.side == "sell")

    ofi_raw = buy_vol - sell_vol
    total_vol = buy_vol + sell_vol
    ofi_norm = (ofi_raw / total_vol) if total_vol > 1e-9 else 0.0
    return round(ofi_raw, 6), round(ofi_norm, 6)


def compute_vpin(
    ticks: Sequence[Union[OrderFlowTick, Mapping[str, Any]]],
    bucket_volume_sol: float = 10.0,
    num_buckets: int = 10,
) -> float:
    """
    Computes Volume-Synchronized Probability of Informed Trading (VPIN):
      VPIN = sum_{tau=1..N} |V_tau^buy - V_tau^sell| / (N * V_bucket) in [0.0, 1.0].
    """
    coerced_all = [_coerce_flow_tick(t) for t in ticks]
    coerced = [
        t for t in coerced_all if t.side in {"buy", "sell"} and t.volume_sol > 0.0
    ]
    if not coerced:
        return 0.0

    bucket_vol = max(0.1, float(bucket_volume_sol))
    buckets: List[Tuple[float, float]] = []
    curr_buy = 0.0
    curr_sell = 0.0
    curr_fill = 0.0

    for tick in coerced:
        rem = tick.volume_sol
        while rem > 1e-9:
            space = bucket_vol - curr_fill
            take = min(rem, space)
            if tick.side == "buy":
                curr_buy += take
            else:
                curr_sell += take
            curr_fill += take
            rem -= take
            if curr_fill >= bucket_vol - 1e-9:
                buckets.append((curr_buy, curr_sell))
                curr_buy = 0.0
                curr_sell = 0.0
                curr_fill = 0.0

    if curr_fill > 1e-9 and not buckets:
        # Single partial bucket fallback normalized by actual fill
        return round(min(1.0, abs(curr_buy - curr_sell) / curr_fill), 6)

    recent_buckets = buckets[-max(1, num_buckets) :]
    imbalance_sum = sum(abs(b - s) for b, s in recent_buckets)
    vpin_val = imbalance_sum / (len(recent_buckets) * bucket_vol)
    return round(max(0.0, min(1.0, vpin_val)), 6)


def evaluate_ofi_vpin_and_exit_tripwires(
    token_mint: str,
    ticks: Sequence[Union[OrderFlowTick, Mapping[str, Any]]],
    watched_shadow_wallets: Sequence[str],
    ofi_norm_exit_threshold: float = -0.35,
    vpin_toxic_threshold: float = 0.70,
    bucket_volume_sol: float = 10.0,
) -> OfiVpinGatekeeperResult:
    """
    Step 1.4 OFI/VPIN & Shadow-Cluster Outbound Transfer Exit Gatekeeper:
    Computes 1-minute OFI and VPIN plus shadow-cluster sell / outbound SPL transfer
    tripwires to trigger atomic Jito exit (`ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE`)
    before the 80% External Market Phase 1 PVP collapse.
    """
    coerced = [_coerce_flow_tick(t) for t in ticks]
    watched_set = {w.strip() for w in watched_shadow_wallets if w.strip()}

    ofi_raw, ofi_norm = compute_1m_order_flow_imbalance(coerced, window_seconds=60.0)
    vpin_val = compute_vpin(coerced, bucket_volume_sol=bucket_volume_sol)

    shadow_sell_detected = False
    shadow_outbound_transfer_detected = False
    tripped_wallets: List[str] = []
    tripped_sigs: List[str] = []

    for tick in coerced:
        if tick.signer in watched_set:
            if tick.side == "sell" and tick.tx_type == "swap":
                shadow_sell_detected = True
                if tick.signer not in tripped_wallets:
                    tripped_wallets.append(tick.signer)
                if tick.tx_signature and tick.tx_signature not in tripped_sigs:
                    tripped_sigs.append(tick.tx_signature)
            elif tick.tx_type in {"spl_transfer", "transfer", "outbound_transfer"}:
                shadow_outbound_transfer_detected = True
                if tick.signer not in tripped_wallets:
                    tripped_wallets.append(tick.signer)
                if tick.tx_signature and tick.tx_signature not in tripped_sigs:
                    tripped_sigs.append(tick.tx_signature)

    toxic_flow = bool(
        (ofi_norm <= ofi_norm_exit_threshold and vpin_val >= vpin_toxic_threshold)
        or (vpin_val >= 0.85 and ofi_norm < 0.0)
    )

    reasons: List[str] = []
    if shadow_sell_detected:
        reasons.append(f"SHADOW_CLUSTER_DIRECT_SELL_TRIPWIRE({len(tripped_wallets)} wallets)")
    if shadow_outbound_transfer_detected:
        reasons.append("SHADOW_CLUSTER_OUTBOUND_SPL_TRANSFER_TRIPWIRE")
    if toxic_flow:
        reasons.append(
            f"TOXIC_OFI_VPIN_REGIME(ofi_norm={ofi_norm:.3f}<={ofi_norm_exit_threshold:.2f}, vpin={vpin_val:.3f}>={vpin_toxic_threshold:.2f})"
        )

    should_exit = bool(
        shadow_sell_detected or shadow_outbound_transfer_detected or toxic_flow
    )
    action = (
        ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE
        if should_exit
        else HOLD_POSITION_HEALTHY_FLOW
    )

    return OfiVpinGatekeeperResult(
        token_mint=token_mint,
        action=action,
        trigger_atomic_exit=should_exit,
        ofi_1m_raw=ofi_raw,
        ofi_1m_normalized=ofi_norm,
        vpin_score=vpin_val,
        toxic_order_flow_detected=toxic_flow,
        shadow_cluster_sell_detected=shadow_sell_detected,
        shadow_cluster_outbound_transfer_detected=shadow_outbound_transfer_detected,
        tripped_shadow_wallets=tripped_wallets,
        tripped_tx_signatures=tripped_sigs,
        external_market_phase1_collapse_avoided_pct=(
            EXTERNAL_MARKET_PHASE1_COLLAPSE_PCT if should_exit else 0.0
        ),
        exit_reasons=reasons,
    )
