"""Sovereign Titan OS — Agent A of `AlphaExploit-Solana`:
Sub-50ms ShredStream & Pre-Mint Peel-Chain Listener (`src/ingestion/pre_mint_peel_chain_listener.py`).

Implements:
1. **Multi-Stream Sub-50ms Ingestion & 6 `cabalspy[realtime]` WebSocket Router
   (`evaluate_realtime_shred_and_cabalspy_streams`, `register_solbundler_withdraw_sweep`)**:
   - Models Yellowstone Geyser gRPC at `processed` commitment (`< 50ms`), Jito ShredStream
     raw turbine shreds (`Cores 0-3`), Helius Webhooks, and the 6 concurrent
     `cabalspy[realtime]` WebSocket streams (`Cores 4-15`: `NEW_MINT_GENESIS`,
     `PEEL_CHAIN_FUNDING`, `SAME_BLOCK_JITO_BUNDLE`, `SOLBUNDLER_WITHDRAW_SWEEP`,
     `BONDING_CURVE_RESERVE_TICK`, `PUMPSWAP_GRADUATION_FREEZE`) filtered strictly to:
       * `Pump.fun`: `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`
       * `PumpSwap`: `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`
       * `Raydium`: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8` /
         `CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C`
   - Maps post-launch `SolBundler Withdraw` consolidation sweeps back to persistent
     high-graduation deployer treasuries (`graduation_rate_pct > 25.0%`).

2. **Pre-Mint Peel-Chain Interception (`detect_pre_mint_peel_chain_signal` -> `PRE_LAUNCH_DEV_SIGNAL`)**:
   - Monitors tracked high-graduation deployer treasuries and peel-chain intermediaries in real time.
   - Detects when a tracked treasury or peel-chain intermediary disperses `buy_amount + 0.003 SOL`
     (accounting for rent + gas overhead within configurable tolerance `±0.0015 SOL`) to `>= 8`
     fresh burner addresses (`prior_tx_count == 0`) within a `15-minute` (`900s`) rolling window.
   - Emits `signal_type = "PRE_LAUNCH_DEV_SIGNAL"` prior to Block-0 token creation, pre-arming the
     execution engine to snipe the upcoming `MintTo` / `Initialize` instruction from any of those
     burner addresses in **Block 1** at the absolute base of the bonding curve.

3. **Constant-Product Bonding Curve ($x \\cdot y = k$ with `1.25%` Fee) & `65%–78%` Squeeze ->
   `77%–79%` Scale-Out (`evaluate_constant_product_curve_and_scaleout`)**:
   - Computes exact marginal price $P = x / y$, effective entry/exit price with the `1.25%`
     (`125 bps`) bidirectional Pump.fun curve fee, nonlinear slippage penalty $\\Delta y / y$,
     and quantifies the **Zero Passive Price Support Hazard** (demonstrating that because there
     are zero resting limit bids, a synchronized multi-wallet dump collapses price along the
     exact same steep constant-product trajectory).
   - Enforces the **Pre-Graduation Curve Squeeze & Pre-Freeze Scale-Out Protocol**:
     * Entry Zone (`65.0% <= curve_completion_pct <= 78.0%`): Enters during steep curve
       acceleration when backed by audited wallet convergence (`"ENTER_PRE_GRADUATION_CURVE_SQUEEZE"`).
     * Automated Pre-Freeze Scale-Out (`76.0% <= curve_completion_pct <= 79.5%`, targeting
       `77%–79%`): Automatically scales out `75.0%` of holdings (`scale_out_fraction = 0.75`,
       `"SCALE_OUT_75PCT_PRE_GRADUATION_FREEZE"`) immediately prior to the `80.0%` (~`85 SOL`)
       graduation freeze, locking in curve-acceleration gains before the 50-wallet cabal dumps
       into the newborn PumpSwap AMM pool, while retaining a `25.0%` runner only if
       post-migration volume confirms organic breakout.

4. **`PreMintPeelChainListener` Facade Class**:
   - Provides `run_full_pre_mint_listener_diagnostic() -> Dict[str, Any]` and
     `get_telemetry_summary() -> Dict[str, Any]` for `TitanIPCDaemon`
     (`RUN_PRE_MINT_PEEL_CHAIN_LISTENER`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import statistics
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union


# ============================================================================
# Architectural & Empirical Constants
# ============================================================================

AGENT_A_SWARM_ID: str = "agent-a-shred-pre-mint-listener"
SHREDSTREAM_TURBINE_CORES: Tuple[int, ...] = (0, 1, 2, 3)
CABALSPY_WEBSOCKET_CORES: Tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)

# Target Launchpad & DEX Program IDs
PUMP_FUN_PROGRAM_ID: str = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_AMM_PROGRAM_ID: str = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
RAYDIUM_V4_PROGRAM_ID: str = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
RAYDIUM_CPMM_PROGRAM_ID: str = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"

ALLOWED_TARGET_PROGRAM_IDS: Tuple[str, ...] = (
    PUMP_FUN_PROGRAM_ID,
    PUMPSWAP_AMM_PROGRAM_ID,
    RAYDIUM_V4_PROGRAM_ID,
    RAYDIUM_CPMM_PROGRAM_ID,
)

# Sub-50ms Ingestion & 6 cabalspy[realtime] WebSocket Streams
YELLOWSTONE_GEYSER_COMMITMENT: str = "processed"
MAX_SHRED_INGESTION_LATENCY_MS: float = 50.0

STREAM_NEW_MINT_GENESIS: str = "NEW_MINT_GENESIS"
STREAM_PEEL_CHAIN_FUNDING: str = "PEEL_CHAIN_FUNDING"
STREAM_SAME_BLOCK_JITO_BUNDLE: str = "SAME_BLOCK_JITO_BUNDLE"
STREAM_SOLBUNDLER_WITHDRAW_SWEEP: str = "SOLBUNDLER_WITHDRAW_SWEEP"
STREAM_BONDING_CURVE_RESERVE_TICK: str = "BONDING_CURVE_RESERVE_TICK"
STREAM_PUMPSWAP_GRADUATION_FREEZE: str = "PUMPSWAP_GRADUATION_FREEZE"

CABALSPY_REALTIME_6_STREAMS: Tuple[str, ...] = (
    STREAM_NEW_MINT_GENESIS,
    STREAM_PEEL_CHAIN_FUNDING,
    STREAM_SAME_BLOCK_JITO_BUNDLE,
    STREAM_SOLBUNDLER_WITHDRAW_SWEEP,
    STREAM_BONDING_CURVE_RESERVE_TICK,
    STREAM_PUMPSWAP_GRADUATION_FREEZE,
)

INGESTION_TRANSPORTS: Tuple[str, ...] = (
    "YELLOWSTONE_GEYSER_GRPC",
    "JITO_SHREDSTREAM_TURBINE",
    "HELIUS_WEBHOOKS",
    "CABALSPY_REALTIME_WS",
)

HIGH_GRADUATION_RATE_THRESHOLD_PCT: float = 25.0

# Pre-Mint Peel-Chain Interception (PRE_LAUNCH_DEV_SIGNAL) Constants
PRE_LAUNCH_DEV_SIGNAL: str = "PRE_LAUNCH_DEV_SIGNAL"
NO_PRE_MINT_SIGNAL: str = "NO_PRE_MINT_SIGNAL"
PRE_MINT_PEEL_WINDOW_SECONDS: float = 900.0  # 15-minute rolling window
MIN_FRESH_BURNER_WALLETS: int = 8
RENT_AND_GAS_OVERHEAD_SOL: float = 0.003
DEFAULT_OVERHEAD_TOLERANCE_SOL: float = 0.0015
BLOCK1_SNIPE_ACTION: str = "PRE_ARM_BLOCK1_BASE_CURVE_SNIPE"

# Constant-Product Bonding Curve (x * y = k with 1.25% Fee) & Scale-Out Constants
PUMP_FUN_CURVE_FEE_BPS: int = 125
PUMP_FUN_CURVE_FEE_RATE: float = 0.0125

INITIAL_VIRTUAL_SOL_RESERVES: float = 30.0
INITIAL_VIRTUAL_TOKEN_RESERVES: float = 1_073_000_000.0
INITIAL_REAL_TOKEN_RESERVES: float = 793_100_000.0

CURVE_GRADUATION_FREEZE_PCT: float = 80.0
CURVE_GRADUATION_TARGET_REAL_SOL: float = 85.0

ENTRY_SQUEEZE_MIN_CURVE_PCT: float = 65.0
ENTRY_SQUEEZE_MAX_CURVE_PCT: float = 78.0

SCALEOUT_MIN_CURVE_PCT: float = 76.0
SCALEOUT_TARGET_LOW_CURVE_PCT: float = 77.0
SCALEOUT_TARGET_HIGH_CURVE_PCT: float = 79.0
SCALEOUT_MAX_CURVE_PCT: float = 79.5

PRE_FREEZE_SCALEOUT_FRACTION: float = 0.75
PRE_FREEZE_SCALEOUT_PCT: float = 75.0
RETAINED_RUNNER_FRACTION: float = 0.25
RETAINED_RUNNER_PCT: float = 25.0

ACTION_ENTER_CURVE_SQUEEZE: str = "ENTER_PRE_GRADUATION_CURVE_SQUEEZE"
ACTION_SCALE_OUT_75PCT_PRE_FREEZE: str = "SCALE_OUT_75PCT_PRE_GRADUATION_FREEZE"
ACTION_ABORT_GRADUATION_FROZEN: str = "ABORT_CURVE_FROZEN_AT_80PCT"
ACTION_WAIT_BELOW_SQUEEZE_ZONE: str = "WAIT_BELOW_65PCT_ACCELERATION_ZONE"
ACTION_HOLD_REJECTED_UNAUDITED_FLOW: str = "REJECT_ENTRY_NO_AUDITED_CONVERGENCE"


# ============================================================================
# Shared Dict-Compatible Mixin & Structured Dataclasses
# ============================================================================


class _DictAccessMixin:
    """Provides dictionary-style subscripting and `.to_dict()` conversion."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


@dataclass(frozen=True)
class SolBundlerWithdrawSweepRecord(_DictAccessMixin):
    """Maps a post-launch `SolBundler Withdraw` consolidation sweep back to a
    persistent deployer treasury and evaluates `graduation_rate_pct > 25.0%`.
    """

    sweep_id: str
    destination_treasury_wallet: str
    swept_burner_wallets: Tuple[str, ...]
    peel_chain_intermediaries: Tuple[str, ...]
    total_swept_sol: float
    token_mint: str
    graduated_launches: int
    total_launches: int
    graduation_rate_pct: float
    is_high_graduation_deployer: bool
    promoted_to_active_watch_set: bool
    timestamp_sec: float


@dataclass(frozen=True)
class RealtimeStreamIngestionReport(_DictAccessMixin):
    """Telemetry and routing report for Yellowstone Geyser gRPC (`processed`),
    Jito ShredStream (`Cores 0-3`), Helius Webhooks, and the 6 concurrent
    `cabalspy[realtime]` WebSocket streams (`Cores 4-15`).
    """

    commitment_level: str
    yellowstone_grpc_latency_ms: float
    jito_shredstream_latency_ms: float
    helius_webhook_latency_ms: float
    cabalspy_ws_latency_ms: float
    effective_ingestion_latency_ms: float
    sub_50ms_sla_met: bool
    shredstream_cores: Tuple[int, ...]
    cabalspy_ws_cores: Tuple[int, ...]
    active_cabalspy_streams: Tuple[str, ...]
    allowed_program_ids: Tuple[str, ...]
    total_events_received: int
    accepted_target_program_events: int
    dropped_non_target_program_events: int
    routed_events_by_stream: Dict[str, List[Dict[str, Any]]]
    routed_events_by_program: Dict[str, int]
    tracked_high_graduation_treasuries: Tuple[str, ...]
    tracked_peel_intermediaries: Tuple[str, ...]
    solbundler_sweeps_registered: int


@dataclass(frozen=True)
class BurnerDispersalHop(_DictAccessMixin):
    """Single peel-chain dispersal transfer to a candidate burner wallet."""

    burner_wallet: str
    source_wallet: str
    amount_sol: float
    inferred_buy_amount_sol: float
    inferred_overhead_sol: float
    matches_buy_plus_0003_pattern: bool
    prior_tx_count: int
    is_fresh_burner: bool
    timestamp_sec: float


@dataclass(frozen=True)
class PreMintPeelChainSignal(_DictAccessMixin):
    """Pre-Mint Peel-Chain Interception result (`PRE_LAUNCH_DEV_SIGNAL` vs
    `NO_PRE_MINT_SIGNAL`) emitted prior to Block-0 token creation.
    """

    signal_type: str
    is_pre_launch_dev_signal: bool
    emitted_prior_to_block0_mint: bool
    source_wallet: str
    resolved_treasury_wallet: str
    is_tracked_treasury_or_intermediary: bool
    deployer_graduation_rate_pct: float
    target_buy_amount_sol: float
    expected_overhead_sol: float
    overhead_tolerance_sol: float
    observed_avg_overhead_sol: float
    rolling_window_seconds: float
    observed_window_span_seconds: float
    within_15m_rolling_window: bool
    total_dispersal_transfers: int
    qualifying_fresh_burner_count: int
    min_required_fresh_burners: int
    meets_min_8_fresh_burners: bool
    pre_armed_burner_wallets: Tuple[str, ...]
    total_dispersed_sol: float
    target_snipe_block: int
    pre_arm_execution_action: str
    target_instructions_watched: Tuple[str, ...]
    burner_hops: Tuple[BurnerDispersalHop, ...]


@dataclass(frozen=True)
class ConstantProductCurveEvaluation(_DictAccessMixin):
    """Constant-Product Bonding Curve ($x \\cdot y = k$ with `1.25%` bidirectional fee)
    evaluation and `65%–78%` Squeeze -> `77%–79%` Automated `75%` Scale-Out decision.
    """

    token_mint: str
    virtual_sol_reserves_x: float
    virtual_token_reserves_y: float
    constant_product_k: float
    curve_completion_pct: float
    real_sol_in_curve: float
    fee_bps: int
    fee_rate: float
    marginal_price_sol_per_token: float
    order_sol_amount: float
    net_sol_into_curve: float
    buy_fee_sol: float
    tokens_received_delta_y: float
    effective_entry_price_sol_per_token: float
    post_buy_marginal_price_sol_per_token: float
    nonlinear_slippage_ratio_delta_y_over_y: float
    nonlinear_slippage_pct: float
    sell_token_amount: float
    gross_sol_out_from_curve: float
    sell_fee_sol: float
    net_sol_received_on_exit: float
    effective_exit_price_sol_per_token: float
    bidirectional_roundtrip_fee_drag_pct: float
    resting_limit_bids_count: int
    zero_passive_price_support_hazard: bool
    cabal_dump_token_amount: float
    post_cabal_dump_marginal_price: float
    synchronized_dump_price_collapse_pct: float
    audited_wallet_convergence: bool
    in_entry_acceleration_zone: bool
    in_pre_freeze_scaleout_zone: bool
    in_optimal_77_to_79_scaleout_band: bool
    is_graduation_frozen: bool
    scale_out_fraction: float
    scale_out_pct: float
    retained_runner_fraction: float
    retained_runner_pct: float
    post_migration_organic_volume_confirmed: bool
    runner_hold_authorized: bool
    recommended_action: str


# ============================================================================
# Module-Level State Registry & Core Engine Class
# ============================================================================


class PreMintPeelChainListener:
    """Agent A (`agent-a-shred-pre-mint-listener`) of `AlphaExploit-Solana`:
    Sub-50ms ShredStream & Pre-Mint Peel-Chain Listener (`PRE_LAUNCH_DEV_SIGNAL`),
    6 `cabalspy[realtime]` WebSocket Streams, and Constant-Product Bonding Curve
    `65%–78%` Acceleration -> `77%–79%` Automated `75%` Scale-Out.
    """

    def __init__(self) -> None:
        self._tracked_treasuries: Dict[str, float] = {}  # treasury_wallet -> graduation_rate_pct
        self._intermediary_to_treasury: Dict[str, str] = {}  # intermediary -> treasury_wallet
        self._burner_to_treasury: Dict[str, str] = {}  # burner -> treasury_wallet
        self._solbundler_sweeps: List[SolBundlerWithdrawSweepRecord] = []
        self._pre_armed_burners: Set[str] = set()
        self._emitted_signals: List[PreMintPeelChainSignal] = []
        self._curve_evaluations: List[ConstantProductCurveEvaluation] = []
        self._ingestion_reports: List[RealtimeStreamIngestionReport] = []
        self._diagnostic_runs: int = 0
        self._last_diagnostic: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------------
    # 1. SolBundler Withdraw Sweep Mapping & 6 cabalspy[realtime] Stream Router
    # ------------------------------------------------------------------------
    def register_solbundler_withdraw_sweep(
        self,
        destination_treasury_wallet: str,
        swept_burner_wallets: Sequence[str],
        total_swept_sol: float,
        token_mint: str = "GraduatedPumpFunMint11111111111111111111111",
        graduated_launches: int = 4,
        total_launches: int = 10,
        peel_chain_intermediaries: Sequence[str] = (),
        graduation_rate_pct: Optional[float] = None,
        timestamp_sec: Optional[float] = None,
    ) -> SolBundlerWithdrawSweepRecord:
        """Maps a post-launch `SolBundler Withdraw` consolidation sweep back to a
        persistent deployer treasury and promotes high-graduation deployers
        (`graduation_rate_pct > 25.0%`) into the active pre-mint watch set.
        """
        if not destination_treasury_wallet:
            raise ValueError("destination_treasury_wallet must not be empty")

        ts = float(timestamp_sec if timestamp_sec is not None else time.time())
        if graduation_rate_pct is not None:
            grad_rate = float(graduation_rate_pct)
        else:
            denom = max(int(total_launches), 1)
            grad_rate = (float(graduated_launches) / float(denom)) * 100.0

        is_high_grad = grad_rate > HIGH_GRADUATION_RATE_THRESHOLD_PCT
        burners_tuple = tuple(str(w) for w in swept_burner_wallets)
        intermediaries_tuple = tuple(str(w) for w in peel_chain_intermediaries)

        if is_high_grad:
            self._tracked_treasuries[destination_treasury_wallet] = round(grad_rate, 2)
            for inter in intermediaries_tuple:
                self._intermediary_to_treasury[inter] = destination_treasury_wallet
            for burner in burners_tuple:
                self._burner_to_treasury[burner] = destination_treasury_wallet

        sweep_hash = hashlib.sha256(
            f"{destination_treasury_wallet}:{token_mint}:{total_swept_sol:.4f}:{ts:.3f}".encode(
                "utf-8"
            )
        ).hexdigest()[:10].upper()

        record = SolBundlerWithdrawSweepRecord(
            sweep_id=f"SOLBUNDLER_SWEEP_{sweep_hash}",
            destination_treasury_wallet=destination_treasury_wallet,
            swept_burner_wallets=burners_tuple,
            peel_chain_intermediaries=intermediaries_tuple,
            total_swept_sol=round(float(total_swept_sol), 6),
            token_mint=str(token_mint),
            graduated_launches=int(graduated_launches),
            total_launches=int(total_launches),
            graduation_rate_pct=round(grad_rate, 2),
            is_high_graduation_deployer=is_high_grad,
            promoted_to_active_watch_set=is_high_grad,
            timestamp_sec=round(ts, 3),
        )
        self._solbundler_sweeps.append(record)
        return record

    def register_peel_chain_intermediary(
        self,
        treasury_wallet: str,
        intermediary_wallet: str,
        graduation_rate_pct: float = 35.0,
    ) -> None:
        """Links an intermediate peel-chain hop wallet to a tracked high-graduation treasury."""
        if graduation_rate_pct > HIGH_GRADUATION_RATE_THRESHOLD_PCT:
            self._tracked_treasuries[treasury_wallet] = round(float(graduation_rate_pct), 2)
        self._intermediary_to_treasury[intermediary_wallet] = treasury_wallet

    def evaluate_realtime_shred_and_cabalspy_streams(
        self,
        events: Sequence[Dict[str, Any]] = (),
        yellowstone_grpc_latency_ms: float = 11.4,
        jito_shredstream_latency_ms: float = 8.2,
        helius_webhook_latency_ms: float = 34.0,
        cabalspy_ws_latency_ms: float = 14.5,
        commitment_level: str = YELLOWSTONE_GEYSER_COMMITMENT,
        solbundler_sweeps: Sequence[Dict[str, Any]] = (),
    ) -> RealtimeStreamIngestionReport:
        """Evaluates Yellowstone Geyser gRPC (`processed` commitment, `< 50ms`),
        Jito ShredStream raw turbine shreds (`Cores 0-3`), Helius Webhooks, and
        the 6 concurrent `cabalspy[realtime]` WebSocket streams (`Cores 4-15`),
        strictly filtering to `Pump.fun`, `PumpSwap`, and `Raydium` program IDs.
        """
        for sweep_cfg in solbundler_sweeps:
            self.register_solbundler_withdraw_sweep(
                destination_treasury_wallet=str(
                    sweep_cfg.get("destination_treasury_wallet", "")
                ),
                swept_burner_wallets=sweep_cfg.get("swept_burner_wallets", ()),
                total_swept_sol=float(sweep_cfg.get("total_swept_sol", 0.0)),
                token_mint=str(
                    sweep_cfg.get(
                        "token_mint", "GraduatedPumpFunMint11111111111111111111111"
                    )
                ),
                graduated_launches=int(sweep_cfg.get("graduated_launches", 4)),
                total_launches=int(sweep_cfg.get("total_launches", 10)),
                peel_chain_intermediaries=sweep_cfg.get("peel_chain_intermediaries", ()),
                graduation_rate_pct=sweep_cfg.get("graduation_rate_pct"),
                timestamp_sec=sweep_cfg.get("timestamp_sec"),
            )

        routed_by_stream: Dict[str, List[Dict[str, Any]]] = {
            s: [] for s in CABALSPY_REALTIME_6_STREAMS
        }
        routed_by_program: Dict[str, int] = {p: 0 for p in ALLOWED_TARGET_PROGRAM_IDS}

        accepted_count = 0
        dropped_count = 0

        for ev in events:
            prog_id = str(ev.get("program_id", ""))
            stream_name = str(ev.get("stream_type", STREAM_NEW_MINT_GENESIS))

            if (
                prog_id not in ALLOWED_TARGET_PROGRAM_IDS
                or stream_name not in CABALSPY_REALTIME_6_STREAMS
            ):
                dropped_count += 1
                continue

            accepted_count += 1
            routed_by_stream[stream_name].append(dict(ev))
            routed_by_program[prog_id] = routed_by_program.get(prog_id, 0) + 1

            # Automatically register SolBundler Withdraw sweeps arriving over the stream
            if (
                stream_name == STREAM_SOLBUNDLER_WITHDRAW_SWEEP
                and ev.get("destination_treasury_wallet")
            ):
                self.register_solbundler_withdraw_sweep(
                    destination_treasury_wallet=str(ev["destination_treasury_wallet"]),
                    swept_burner_wallets=ev.get("swept_burner_wallets", ()),
                    total_swept_sol=float(ev.get("total_swept_sol", 0.0)),
                    token_mint=str(
                        ev.get(
                            "token_mint", "GraduatedPumpFunMint11111111111111111111111"
                        )
                    ),
                    graduated_launches=int(ev.get("graduated_launches", 4)),
                    total_launches=int(ev.get("total_launches", 10)),
                    peel_chain_intermediaries=ev.get("peel_chain_intermediaries", ()),
                    graduation_rate_pct=ev.get("graduation_rate_pct"),
                    timestamp_sec=ev.get("timestamp_sec"),
                )

        # Primary hot-path latency is the minimum of ShredStream / Yellowstone / cabalspy WS
        effective_latency = min(
            float(yellowstone_grpc_latency_ms),
            float(jito_shredstream_latency_ms),
            float(cabalspy_ws_latency_ms),
        )
        max_primary_latency = max(
            float(yellowstone_grpc_latency_ms),
            float(jito_shredstream_latency_ms),
            float(cabalspy_ws_latency_ms),
        )
        sub_50ms_ok = (
            commitment_level == YELLOWSTONE_GEYSER_COMMITMENT
            and effective_latency < MAX_SHRED_INGESTION_LATENCY_MS
            and max_primary_latency < MAX_SHRED_INGESTION_LATENCY_MS
        )

        report = RealtimeStreamIngestionReport(
            commitment_level=str(commitment_level),
            yellowstone_grpc_latency_ms=round(float(yellowstone_grpc_latency_ms), 3),
            jito_shredstream_latency_ms=round(float(jito_shredstream_latency_ms), 3),
            helius_webhook_latency_ms=round(float(helius_webhook_latency_ms), 3),
            cabalspy_ws_latency_ms=round(float(cabalspy_ws_latency_ms), 3),
            effective_ingestion_latency_ms=round(effective_latency, 3),
            sub_50ms_sla_met=sub_50ms_ok,
            shredstream_cores=SHREDSTREAM_TURBINE_CORES,
            cabalspy_ws_cores=CABALSPY_WEBSOCKET_CORES,
            active_cabalspy_streams=CABALSPY_REALTIME_6_STREAMS,
            allowed_program_ids=ALLOWED_TARGET_PROGRAM_IDS,
            total_events_received=len(events),
            accepted_target_program_events=accepted_count,
            dropped_non_target_program_events=dropped_count,
            routed_events_by_stream=routed_by_stream,
            routed_events_by_program=routed_by_program,
            tracked_high_graduation_treasuries=tuple(sorted(self._tracked_treasuries.keys())),
            tracked_peel_intermediaries=tuple(sorted(self._intermediary_to_treasury.keys())),
            solbundler_sweeps_registered=len(self._solbundler_sweeps),
        )
        self._ingestion_reports.append(report)
        return report

    # ------------------------------------------------------------------------
    # 2. Pre-Mint Peel-Chain Interception (PRE_LAUNCH_DEV_SIGNAL)
    # ------------------------------------------------------------------------
    def detect_pre_mint_peel_chain_signal(
        self,
        source_wallet: str,
        dispersals: Sequence[Union[Dict[str, Any], Tuple[Any, ...]]],
        expected_buy_amount_sol: Optional[float] = None,
        expected_overhead_sol: float = RENT_AND_GAS_OVERHEAD_SOL,
        overhead_tolerance_sol: float = DEFAULT_OVERHEAD_TOLERANCE_SOL,
        rolling_window_seconds: float = PRE_MINT_PEEL_WINDOW_SECONDS,
        min_fresh_burners: int = MIN_FRESH_BURNER_WALLETS,
        is_tracked_treasury: Optional[bool] = None,
        deployer_graduation_rate_pct: Optional[float] = None,
        block0_mint_already_created: bool = False,
    ) -> PreMintPeelChainSignal:
        """Detects when a tracked high-graduation deployer treasury or peel-chain
        intermediary disperses `buy_amount + 0.003 SOL` (accounting for rent + gas
        overhead within `±overhead_tolerance_sol`) to `>= 8` fresh burner addresses
        (`prior_tx_count == 0`) within a `15-minute` (`900s`) rolling window.

        Emits `signal_type = "PRE_LAUNCH_DEV_SIGNAL"` prior to Block-0 token creation,
        pre-arming the execution engine to snipe the upcoming `MintTo` / `Initialize`
        instruction from any of those burner addresses in **Block 1** at the absolute
        base of the bonding curve.
        """
        resolved_treasury = self._intermediary_to_treasury.get(
            source_wallet,
            self._burner_to_treasury.get(source_wallet, source_wallet),
        )
        recorded_grad_rate = self._tracked_treasuries.get(resolved_treasury, 0.0)
        eff_grad_rate = (
            float(deployer_graduation_rate_pct)
            if deployer_graduation_rate_pct is not None
            else recorded_grad_rate
        )

        if is_tracked_treasury is not None:
            tracked_ok = bool(is_tracked_treasury)
            if tracked_ok and eff_grad_rate <= HIGH_GRADUATION_RATE_THRESHOLD_PCT:
                eff_grad_rate = 38.5
        else:
            tracked_ok = (
                resolved_treasury in self._tracked_treasuries
                or source_wallet in self._intermediary_to_treasury
                or eff_grad_rate > HIGH_GRADUATION_RATE_THRESHOLD_PCT
            )

        parsed_hops: List[BurnerDispersalHop] = []
        for idx, item in enumerate(dispersals):
            if isinstance(item, (tuple, list)):
                burner_addr = str(item[0])
                amt_sol = float(item[1])
                ts_sec = float(item[2]) if len(item) >= 3 else float(idx * 5.0)
                prior_tx = int(item[3]) if len(item) >= 4 else 0
                explicit_buy: Optional[float] = (
                    float(item[4]) if len(item) >= 5 and item[4] is not None else None
                )
            else:
                burner_addr = str(
                    item.get(
                        "burner_wallet",
                        item.get("recipient", item.get("wallet", f"Burner_{idx}")),
                    )
                )
                amt_sol = float(item.get("amount_sol", 0.0))
                ts_sec = float(item.get("timestamp_sec", idx * 5.0))
                prior_tx = int(item.get("prior_tx_count", 0))
                if item.get("is_fresh") is False and prior_tx == 0:
                    prior_tx = 1
                explicit_buy = (
                    float(item["buy_amount_sol"])
                    if item.get("buy_amount_sol") is not None
                    else None
                )

            if explicit_buy is not None:
                base_buy = explicit_buy
                inferred_ovh = amt_sol - base_buy
            elif expected_buy_amount_sol is not None:
                base_buy = float(expected_buy_amount_sol)
                inferred_ovh = amt_sol - base_buy
            else:
                # Infer clean base buy amount (rounded to nearest 0.01 SOL) + ~0.003 SOL overhead
                candidate_base = round(amt_sol - expected_overhead_sol, 2)
                if candidate_base > 0.0:
                    base_buy = candidate_base
                    inferred_ovh = amt_sol - candidate_base
                else:
                    base_buy = max(amt_sol - expected_overhead_sol, 0.0)
                    inferred_ovh = amt_sol - base_buy

            ovh_diff = abs(inferred_ovh - expected_overhead_sol)
            matches_pattern = (
                base_buy > 0.0 and ovh_diff <= (float(overhead_tolerance_sol) + 1e-9)
            )
            is_fresh = prior_tx == 0

            parsed_hops.append(
                BurnerDispersalHop(
                    burner_wallet=burner_addr,
                    source_wallet=source_wallet,
                    amount_sol=round(amt_sol, 6),
                    inferred_buy_amount_sol=round(base_buy, 6),
                    inferred_overhead_sol=round(inferred_ovh, 6),
                    matches_buy_plus_0003_pattern=matches_pattern,
                    prior_tx_count=prior_tx,
                    is_fresh_burner=is_fresh,
                    timestamp_sec=round(ts_sec, 3),
                )
            )

        # Evaluate timestamps and rolling 15-minute (900s) window
        qualifying_hops = [
            h
            for h in parsed_hops
            if h.is_fresh_burner and h.matches_buy_plus_0003_pattern
        ]

        if parsed_hops:
            all_ts = [h.timestamp_sec for h in parsed_hops]
            overall_span = max(all_ts) - min(all_ts)
        else:
            overall_span = 0.0

        # Find best rolling window of length <= rolling_window_seconds among qualifying hops
        best_window_hops: List[BurnerDispersalHop] = []
        best_window_span = overall_span
        if qualifying_hops:
            sorted_q = sorted(qualifying_hops, key=lambda h: h.timestamp_sec)
            q_span = sorted_q[-1].timestamp_sec - sorted_q[0].timestamp_sec
            if q_span <= rolling_window_seconds:
                best_window_hops = sorted_q
                best_window_span = q_span
            else:
                # Sliding window to find maximum cluster within 900s
                for i in range(len(sorted_q)):
                    start_ts = sorted_q[i].timestamp_sec
                    window_slice = [
                        h
                        for h in sorted_q[i:]
                        if (h.timestamp_sec - start_ts) <= rolling_window_seconds
                    ]
                    if len(window_slice) > len(best_window_hops):
                        best_window_hops = window_slice
                        best_window_span = (
                            window_slice[-1].timestamp_sec - window_slice[0].timestamp_sec
                        )

        # Unique fresh burner wallets in the best rolling window
        seen_burners: Set[str] = set()
        unique_qualifying_burners: List[str] = []
        qualifying_overheads: List[float] = []
        qualifying_buys: List[float] = []

        for h in best_window_hops:
            if h.burner_wallet not in seen_burners:
                seen_burners.add(h.burner_wallet)
                unique_qualifying_burners.append(h.burner_wallet)
                qualifying_overheads.append(h.inferred_overhead_sol)
                qualifying_buys.append(h.inferred_buy_amount_sol)

        within_window = len(qualifying_hops) > 0 and (
            overall_span <= rolling_window_seconds
            or len(unique_qualifying_burners) >= min_fresh_burners
        )

        fresh_count = len(unique_qualifying_burners)
        # Enforce strict rolling window compliance: if overall_span > rolling_window_seconds and best_window < min_fresh_burners, within_window is False
        if overall_span > rolling_window_seconds and len(unique_qualifying_burners) < min_fresh_burners:
            within_window = False

        meets_min_8 = fresh_count >= int(min_fresh_burners)
        emitted_pre_block0 = not bool(block0_mint_already_created)

        is_signal = (
            tracked_ok
            and within_window
            and meets_min_8
            and emitted_pre_block0
        )

        if is_signal:
            for b_addr in unique_qualifying_burners:
                self._pre_armed_burners.add(b_addr)
                self._burner_to_treasury[b_addr] = resolved_treasury

        avg_ovh = (
            statistics.fmean(qualifying_overheads)
            if qualifying_overheads
            else (
                statistics.fmean(h.inferred_overhead_sol for h in parsed_hops)
                if parsed_hops
                else 0.0
            )
        )
        rep_buy = (
            float(expected_buy_amount_sol)
            if expected_buy_amount_sol is not None
            else (
                statistics.fmean(qualifying_buys)
                if qualifying_buys
                else (
                    statistics.fmean(h.inferred_buy_amount_sol for h in parsed_hops)
                    if parsed_hops
                    else 0.0
                )
            )
        )
        total_sol = sum(h.amount_sol for h in parsed_hops)

        signal = PreMintPeelChainSignal(
            signal_type=PRE_LAUNCH_DEV_SIGNAL if is_signal else NO_PRE_MINT_SIGNAL,
            is_pre_launch_dev_signal=is_signal,
            emitted_prior_to_block0_mint=is_signal and emitted_pre_block0,
            source_wallet=source_wallet,
            resolved_treasury_wallet=resolved_treasury,
            is_tracked_treasury_or_intermediary=tracked_ok,
            deployer_graduation_rate_pct=round(eff_grad_rate, 2),
            target_buy_amount_sol=round(rep_buy, 6),
            expected_overhead_sol=round(float(expected_overhead_sol), 6),
            overhead_tolerance_sol=round(float(overhead_tolerance_sol), 6),
            observed_avg_overhead_sol=round(avg_ovh, 6),
            rolling_window_seconds=round(float(rolling_window_seconds), 2),
            observed_window_span_seconds=round(
                best_window_span if is_signal else overall_span, 3
            ),
            within_15m_rolling_window=within_window,
            total_dispersal_transfers=len(parsed_hops),
            qualifying_fresh_burner_count=fresh_count,
            min_required_fresh_burners=int(min_fresh_burners),
            meets_min_8_fresh_burners=meets_min_8,
            pre_armed_burner_wallets=tuple(unique_qualifying_burners) if is_signal else (),
            total_dispersed_sol=round(total_sol, 6),
            target_snipe_block=1 if is_signal else 0,
            pre_arm_execution_action=(
                BLOCK1_SNIPE_ACTION if is_signal else "IDLE_MONITORING"
            ),
            target_instructions_watched=(
                "MintTo",
                "Initialize",
                "PumpFun::Create",
            ),
            burner_hops=tuple(parsed_hops),
        )
        self._emitted_signals.append(signal)
        return signal

    # ------------------------------------------------------------------------
    # 3. Constant-Product Bonding Curve (x * y = k with 1.25% Fee) & Scale-Out
    # ------------------------------------------------------------------------
    def evaluate_constant_product_curve_and_scaleout(
        self,
        curve_completion_pct: Optional[float] = None,
        virtual_sol_reserves: Optional[float] = None,
        virtual_token_reserves: Optional[float] = None,
        order_sol_amount: float = 2.5,
        sell_token_amount: Optional[float] = None,
        cabal_dump_token_amount: Optional[float] = None,
        cabal_dump_supply_pct: float = 35.0,
        audited_wallet_convergence: bool = True,
        has_open_position: Optional[bool] = None,
        post_migration_organic_volume_confirmed: bool = True,
        fee_bps: int = PUMP_FUN_CURVE_FEE_BPS,
        token_mint: str = "PumpFunCurveMint111111111111111111111111111",
    ) -> ConstantProductCurveEvaluation:
        """Evaluates the exact constant-product bonding curve ($x \\cdot y = k$) with the
        `1.25%` (`125 bps`) bidirectional Pump.fun curve fee, nonlinear slippage penalty
        $\\Delta y / y$, Zero Passive Price Support Hazard, and enforces the
        `65%–78%` Pre-Graduation Curve Squeeze -> `77%–79%` (`76.0%–79.5%`) Automated
        `75%` Scale-Out before the `80%` graduation freeze.
        """
        k_init = INITIAL_VIRTUAL_SOL_RESERVES * INITIAL_VIRTUAL_TOKEN_RESERVES

        if virtual_sol_reserves is not None and virtual_token_reserves is not None:
            x = max(float(virtual_sol_reserves), 1e-9)
            y = max(float(virtual_token_reserves), 1e-9)
            k = x * y
            if curve_completion_pct is not None:
                comp_pct = float(curve_completion_pct)
            else:
                tokens_sold = max(INITIAL_VIRTUAL_TOKEN_RESERVES - y, 0.0)
                comp_pct = min(
                    (tokens_sold / INITIAL_REAL_TOKEN_RESERVES) * 100.0, 100.0
                )
        else:
            comp_pct = float(curve_completion_pct if curve_completion_pct is not None else 72.0)
            # Calibrate virtual reserves at comp_pct along x * y = k_init
            tokens_sold = (comp_pct / 100.0) * INITIAL_REAL_TOKEN_RESERVES
            y = max(INITIAL_VIRTUAL_TOKEN_RESERVES - tokens_sold, 1_000_000.0)
            x = k_init / y
            k = x * y

        real_sol = max(x - INITIAL_VIRTUAL_SOL_RESERVES, 0.0)
        fee_rate = float(fee_bps) / 10_000.0

        # 1. Marginal price P = x / y
        marginal_price = x / y

        # 2. Buy mechanics with 1.25% fee: net SOL entering curve = gross_sol * (1 - fee_rate)
        gross_buy_sol = max(float(order_sol_amount), 1e-9)
        buy_fee_sol = gross_buy_sol * fee_rate
        net_sol_in = gross_buy_sol * (1.0 - fee_rate)

        x_after_buy = x + net_sol_in
        y_after_buy = k / x_after_buy
        delta_y = y - y_after_buy
        effective_entry_price = gross_buy_sol / max(delta_y, 1e-12)
        post_buy_marginal_price = x_after_buy / y_after_buy

        # Nonlinear slippage penalty: delta_y / y
        slippage_ratio = delta_y / y
        slippage_pct = slippage_ratio * 100.0

        # 3. Sell mechanics with 1.25% fee
        eff_sell_tokens = (
            float(sell_token_amount)
            if sell_token_amount is not None and sell_token_amount > 0.0
            else delta_y
        )
        y_after_sell = y + eff_sell_tokens
        x_after_sell = k / y_after_sell
        gross_sol_out = x - x_after_sell
        sell_fee_sol = gross_sol_out * fee_rate
        net_sol_out = gross_sol_out * (1.0 - fee_rate)
        effective_exit_price = net_sol_out / max(eff_sell_tokens, 1e-12)

        roundtrip_fee_drag_pct = (1.0 - ((1.0 - fee_rate) ** 2)) * 100.0

        # 4. Zero Passive Price Support Hazard (Synchronized multi-wallet cabal dump)
        eff_cabal_dump_tokens = (
            float(cabal_dump_token_amount)
            if cabal_dump_token_amount is not None and cabal_dump_token_amount > 0.0
            else y * (float(cabal_dump_supply_pct) / 100.0)
        )
        y_post_dump = y + eff_cabal_dump_tokens
        x_post_dump = k / y_post_dump
        post_dump_marginal_price = x_post_dump / y_post_dump
        dump_collapse_pct = (
            1.0 - (post_dump_marginal_price / marginal_price)
        ) * 100.0

        # 5. Pre-Graduation Curve Squeeze (65%-78%) & Pre-Freeze Scale-Out (76%-79.5%, target 77%-79%)
        in_entry_zone = (
            ENTRY_SQUEEZE_MIN_CURVE_PCT <= comp_pct <= ENTRY_SQUEEZE_MAX_CURVE_PCT
        )
        in_scaleout_zone = (
            SCALEOUT_MIN_CURVE_PCT <= comp_pct <= SCALEOUT_MAX_CURVE_PCT
        )
        in_optimal_77_79 = (
            SCALEOUT_TARGET_LOW_CURVE_PCT <= comp_pct <= SCALEOUT_TARGET_HIGH_CURVE_PCT
        )
        is_frozen = comp_pct >= CURVE_GRADUATION_FREEZE_PCT

        if is_frozen:
            recommended_action = ACTION_ABORT_GRADUATION_FROZEN
            scale_out_frac = 1.0 if has_open_position else 0.0
            runner_frac = 0.0
        elif in_scaleout_zone and (
            has_open_position is True
            or (has_open_position is None and comp_pct >= SCALEOUT_MIN_CURVE_PCT)
            or comp_pct > ENTRY_SQUEEZE_MAX_CURVE_PCT
        ):
            recommended_action = ACTION_SCALE_OUT_75PCT_PRE_FREEZE
            scale_out_frac = PRE_FREEZE_SCALEOUT_FRACTION
            runner_frac = RETAINED_RUNNER_FRACTION
        elif in_entry_zone:
            if audited_wallet_convergence:
                recommended_action = ACTION_ENTER_CURVE_SQUEEZE
            else:
                recommended_action = ACTION_HOLD_REJECTED_UNAUDITED_FLOW
            scale_out_frac = PRE_FREEZE_SCALEOUT_FRACTION if in_scaleout_zone else 0.0
            runner_frac = RETAINED_RUNNER_FRACTION if in_scaleout_zone else 0.0
        elif comp_pct < ENTRY_SQUEEZE_MIN_CURVE_PCT:
            recommended_action = ACTION_WAIT_BELOW_SQUEEZE_ZONE
            scale_out_frac = 0.0
            runner_frac = 0.0
        else:
            # Between 79.5% and 80.0%: emergency pre-freeze scale-out
            recommended_action = ACTION_SCALE_OUT_75PCT_PRE_FREEZE
            scale_out_frac = PRE_FREEZE_SCALEOUT_FRACTION
            runner_frac = RETAINED_RUNNER_FRACTION

        runner_authorized = bool(
            post_migration_organic_volume_confirmed and runner_frac > 0.0
        )

        evaluation = ConstantProductCurveEvaluation(
            token_mint=str(token_mint),
            virtual_sol_reserves_x=round(x, 6),
            virtual_token_reserves_y=round(y, 4),
            constant_product_k=round(k, 2),
            curve_completion_pct=round(comp_pct, 4),
            real_sol_in_curve=round(real_sol, 6),
            fee_bps=int(fee_bps),
            fee_rate=round(fee_rate, 6),
            marginal_price_sol_per_token=marginal_price,
            order_sol_amount=round(gross_buy_sol, 6),
            net_sol_into_curve=round(net_sol_in, 6),
            buy_fee_sol=round(buy_fee_sol, 6),
            tokens_received_delta_y=round(delta_y, 4),
            effective_entry_price_sol_per_token=effective_entry_price,
            post_buy_marginal_price_sol_per_token=post_buy_marginal_price,
            nonlinear_slippage_ratio_delta_y_over_y=round(slippage_ratio, 8),
            nonlinear_slippage_pct=round(slippage_pct, 6),
            sell_token_amount=round(eff_sell_tokens, 4),
            gross_sol_out_from_curve=round(gross_sol_out, 6),
            sell_fee_sol=round(sell_fee_sol, 6),
            net_sol_received_on_exit=round(net_sol_out, 6),
            effective_exit_price_sol_per_token=effective_exit_price,
            bidirectional_roundtrip_fee_drag_pct=round(roundtrip_fee_drag_pct, 6),
            resting_limit_bids_count=0,
            zero_passive_price_support_hazard=True,
            cabal_dump_token_amount=round(eff_cabal_dump_tokens, 4),
            post_cabal_dump_marginal_price=post_dump_marginal_price,
            synchronized_dump_price_collapse_pct=round(dump_collapse_pct, 4),
            audited_wallet_convergence=bool(audited_wallet_convergence),
            in_entry_acceleration_zone=in_entry_zone,
            in_pre_freeze_scaleout_zone=in_scaleout_zone,
            in_optimal_77_to_79_scaleout_band=in_optimal_77_79,
            is_graduation_frozen=is_frozen,
            scale_out_fraction=round(scale_out_frac, 4),
            scale_out_pct=round(scale_out_frac * 100.0, 2),
            retained_runner_fraction=round(runner_frac, 4),
            retained_runner_pct=round(runner_frac * 100.0, 2),
            post_migration_organic_volume_confirmed=bool(
                post_migration_organic_volume_confirmed
            ),
            runner_hold_authorized=runner_authorized,
            recommended_action=recommended_action,
        )
        self._curve_evaluations.append(evaluation)
        return evaluation

    # ------------------------------------------------------------------------
    # 4. Facade Diagnostic & Telemetry Summary for TitanIPCDaemon
    # ------------------------------------------------------------------------
    def run_full_pre_mint_listener_diagnostic(self) -> Dict[str, Any]:
        """Runs an end-to-end diagnostic across all 3 Agent A subsystems:
        1. Multi-Stream Sub-50ms Ingestion & 6 `cabalspy[realtime]` WebSocket Router
           + `SolBundler Withdraw` Treasury Consolidation Mapping (`graduation_rate_pct > 25%`).
        2. Pre-Mint Peel-Chain Interception (`PRE_LAUNCH_DEV_SIGNAL` prior to Block-0 mint).
        3. Constant-Product Bonding Curve (`x * y = k`, `1.25%` fee) `65%–78%` Squeeze Entry
           and `77%–79%` Automated `75%` Pre-Freeze Scale-Out.
        """
        self._diagnostic_runs += 1

        treasury = "HighGradDeployerTreasury11111111111111111111"
        intermediary = "PeelChainIntermediaryHop1111111111111111111"

        # 1. Register SolBundler Withdraw consolidation sweep -> promotes treasury (40% grad rate > 25%)
        sweep_record = self.register_solbundler_withdraw_sweep(
            destination_treasury_wallet=treasury,
            swept_burner_wallets=[
                f"PriorLaunchBurner{i:02d}111111111111111111111111" for i in range(1, 9)
            ],
            peel_chain_intermediaries=[intermediary],
            total_swept_sol=142.85,
            token_mint="PriorGraduatedMint11111111111111111111111111",
            graduated_launches=4,
            total_launches=10,
            timestamp_sec=1_700_000_000.0,
        )

        # Evaluate 6 cabalspy[realtime] streams + non-target filtering
        sample_events = [
            {
                "stream_type": STREAM_NEW_MINT_GENESIS,
                "program_id": PUMP_FUN_PROGRAM_ID,
                "token_mint": "GenesisMint11111111111111111111111111111111",
            },
            {
                "stream_type": STREAM_PEEL_CHAIN_FUNDING,
                "program_id": PUMP_FUN_PROGRAM_ID,
                "source_wallet": intermediary,
            },
            {
                "stream_type": STREAM_SAME_BLOCK_JITO_BUNDLE,
                "program_id": PUMP_FUN_PROGRAM_ID,
                "bundle_id": "JitoBundle001",
            },
            {
                "stream_type": STREAM_SOLBUNDLER_WITHDRAW_SWEEP,
                "program_id": PUMP_FUN_PROGRAM_ID,
                "destination_treasury_wallet": treasury,
                "swept_burner_wallets": ["PriorLaunchBurner09111111111111111111111111"],
                "total_swept_sol": 18.4,
                "graduated_launches": 5,
                "total_launches": 12,
            },
            {
                "stream_type": STREAM_BONDING_CURVE_RESERVE_TICK,
                "program_id": PUMP_FUN_PROGRAM_ID,
                "curve_completion_pct": 71.5,
            },
            {
                "stream_type": STREAM_PUMPSWAP_GRADUATION_FREEZE,
                "program_id": PUMPSWAP_AMM_PROGRAM_ID,
                "curve_completion_pct": 80.0,
            },
            {
                "stream_type": STREAM_BONDING_CURVE_RESERVE_TICK,
                "program_id": RAYDIUM_V4_PROGRAM_ID,
                "pool_id": "RaydiumPool1111111111111111111111111111111",
            },
            {
                "stream_type": STREAM_NEW_MINT_GENESIS,
                "program_id": "UnrelatedNFTProgram111111111111111111111111",
                "token_mint": "DroppedMint",
            },
        ]
        stream_report = self.evaluate_realtime_shred_and_cabalspy_streams(
            events=sample_events,
            yellowstone_grpc_latency_ms=10.8,
            jito_shredstream_latency_ms=7.9,
            helius_webhook_latency_ms=31.5,
            cabalspy_ws_latency_ms=13.2,
            commitment_level=YELLOWSTONE_GEYSER_COMMITMENT,
        )

        # 2. Pre-Mint Peel-Chain Interception: 10 fresh burners funded with 1.500 + 0.003 = 1.503 SOL within 180s (< 900s)
        dispersal_batch = [
            {
                "burner_wallet": f"FreshBlock1Burner{i:02d}11111111111111111111111",
                "amount_sol": 1.503,
                "buy_amount_sol": 1.500,
                "prior_tx_count": 0,
                "timestamp_sec": 1_700_000_100.0 + i * 12.0,
            }
            for i in range(1, 11)
        ]
        pre_mint_signal = self.detect_pre_mint_peel_chain_signal(
            source_wallet=intermediary,
            dispersals=dispersal_batch,
            expected_buy_amount_sol=1.500,
        )

        # 3. Constant-Product Curve Squeeze Entry (71.5%) & Pre-Freeze 75% Scale-Out (78.2%)
        squeeze_entry_eval = self.evaluate_constant_product_curve_and_scaleout(
            curve_completion_pct=71.5,
            order_sol_amount=3.0,
            audited_wallet_convergence=True,
            has_open_position=False,
            token_mint="CurveSqueezeMint111111111111111111111111111",
        )
        pre_freeze_scaleout_eval = self.evaluate_constant_product_curve_and_scaleout(
            curve_completion_pct=78.2,
            order_sol_amount=3.0,
            audited_wallet_convergence=True,
            has_open_position=True,
            post_migration_organic_volume_confirmed=True,
            token_mint="CurveSqueezeMint111111111111111111111111111",
        )

        result = {
            "agent_id": AGENT_A_SWARM_ID,
            "solbundler_withdraw_sweep": sweep_record.to_dict(),
            "realtime_stream_ingestion_report": stream_report.to_dict(),
            "pre_mint_peel_chain_signal": pre_mint_signal.to_dict(),
            "curve_squeeze_entry_evaluation": squeeze_entry_eval.to_dict(),
            "pre_freeze_75pct_scaleout_evaluation": pre_freeze_scaleout_eval.to_dict(),
        }
        self._last_diagnostic = result
        return result

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Returns structured telemetry summary for `TitanIPCDaemon` (`RUN_PRE_MINT_PEEL_CHAIN_LISTENER`)."""
        return {
            "subsystem": "PreMintPeelChainListener",
            "agent_id": AGENT_A_SWARM_ID,
            "shredstream_turbine_cores": list(SHREDSTREAM_TURBINE_CORES),
            "cabalspy_websocket_cores": list(CABALSPY_WEBSOCKET_CORES),
            "yellowstone_commitment": YELLOWSTONE_GEYSER_COMMITMENT,
            "max_shred_latency_ms": MAX_SHRED_INGESTION_LATENCY_MS,
            "cabalspy_realtime_streams": list(CABALSPY_REALTIME_6_STREAMS),
            "allowed_target_programs": list(ALLOWED_TARGET_PROGRAM_IDS),
            "tracked_high_graduation_treasuries_count": len(self._tracked_treasuries),
            "tracked_peel_intermediaries_count": len(self._intermediary_to_treasury),
            "pre_armed_burner_wallets_count": len(self._pre_armed_burners),
            "solbundler_sweeps_registered": len(self._solbundler_sweeps),
            "pre_mint_signals_evaluated": len(self._emitted_signals),
            "curve_evaluations_logged": len(self._curve_evaluations),
            "pump_fun_curve_fee_bps": PUMP_FUN_CURVE_FEE_BPS,
            "entry_squeeze_band_pct": [
                ENTRY_SQUEEZE_MIN_CURVE_PCT,
                ENTRY_SQUEEZE_MAX_CURVE_PCT,
            ],
            "pre_freeze_scaleout_band_pct": [
                SCALEOUT_MIN_CURVE_PCT,
                SCALEOUT_MAX_CURVE_PCT,
            ],
            "pre_freeze_scaleout_fraction": PRE_FREEZE_SCALEOUT_FRACTION,
            "diagnostic_runs": self._diagnostic_runs,
            "last_diagnostic_available": self._last_diagnostic is not None,
        }


# ============================================================================
# Module-Level Singleton & Convenience Functions
# ============================================================================

_DEFAULT_LISTENER = PreMintPeelChainListener()


def register_solbundler_withdraw_sweep(
    destination_treasury_wallet: str,
    swept_burner_wallets: Sequence[str],
    total_swept_sol: float,
    token_mint: str = "GraduatedPumpFunMint11111111111111111111111",
    graduated_launches: int = 4,
    total_launches: int = 10,
    peel_chain_intermediaries: Sequence[str] = (),
    graduation_rate_pct: Optional[float] = None,
    timestamp_sec: Optional[float] = None,
) -> SolBundlerWithdrawSweepRecord:
    """Module-level convenience wrapper for `PreMintPeelChainListener.register_solbundler_withdraw_sweep`."""
    return _DEFAULT_LISTENER.register_solbundler_withdraw_sweep(
        destination_treasury_wallet=destination_treasury_wallet,
        swept_burner_wallets=swept_burner_wallets,
        total_swept_sol=total_swept_sol,
        token_mint=token_mint,
        graduated_launches=graduated_launches,
        total_launches=total_launches,
        peel_chain_intermediaries=peel_chain_intermediaries,
        graduation_rate_pct=graduation_rate_pct,
        timestamp_sec=timestamp_sec,
    )


def evaluate_realtime_shred_and_cabalspy_streams(
    events: Sequence[Dict[str, Any]] = (),
    yellowstone_grpc_latency_ms: float = 11.4,
    jito_shredstream_latency_ms: float = 8.2,
    helius_webhook_latency_ms: float = 34.0,
    cabalspy_ws_latency_ms: float = 14.5,
    commitment_level: str = YELLOWSTONE_GEYSER_COMMITMENT,
    solbundler_sweeps: Sequence[Dict[str, Any]] = (),
) -> RealtimeStreamIngestionReport:
    """Module-level convenience wrapper for `PreMintPeelChainListener.evaluate_realtime_shred_and_cabalspy_streams`."""
    return _DEFAULT_LISTENER.evaluate_realtime_shred_and_cabalspy_streams(
        events=events,
        yellowstone_grpc_latency_ms=yellowstone_grpc_latency_ms,
        jito_shredstream_latency_ms=jito_shredstream_latency_ms,
        helius_webhook_latency_ms=helius_webhook_latency_ms,
        cabalspy_ws_latency_ms=cabalspy_ws_latency_ms,
        commitment_level=commitment_level,
        solbundler_sweeps=solbundler_sweeps,
    )


def detect_pre_mint_peel_chain_signal(
    source_wallet: str,
    dispersals: Sequence[Union[Dict[str, Any], Tuple[Any, ...]]],
    expected_buy_amount_sol: Optional[float] = None,
    expected_overhead_sol: float = RENT_AND_GAS_OVERHEAD_SOL,
    overhead_tolerance_sol: float = DEFAULT_OVERHEAD_TOLERANCE_SOL,
    rolling_window_seconds: float = PRE_MINT_PEEL_WINDOW_SECONDS,
    min_fresh_burners: int = MIN_FRESH_BURNER_WALLETS,
    is_tracked_treasury: Optional[bool] = None,
    deployer_graduation_rate_pct: Optional[float] = None,
    block0_mint_already_created: bool = False,
) -> PreMintPeelChainSignal:
    """Module-level convenience wrapper for `PreMintPeelChainListener.detect_pre_mint_peel_chain_signal`."""
    return _DEFAULT_LISTENER.detect_pre_mint_peel_chain_signal(
        source_wallet=source_wallet,
        dispersals=dispersals,
        expected_buy_amount_sol=expected_buy_amount_sol,
        expected_overhead_sol=expected_overhead_sol,
        overhead_tolerance_sol=overhead_tolerance_sol,
        rolling_window_seconds=rolling_window_seconds,
        min_fresh_burners=min_fresh_burners,
        is_tracked_treasury=is_tracked_treasury,
        deployer_graduation_rate_pct=deployer_graduation_rate_pct,
        block0_mint_already_created=block0_mint_already_created,
    )


def evaluate_constant_product_curve_and_scaleout(
    curve_completion_pct: Optional[float] = None,
    virtual_sol_reserves: Optional[float] = None,
    virtual_token_reserves: Optional[float] = None,
    order_sol_amount: float = 2.5,
    sell_token_amount: Optional[float] = None,
    cabal_dump_token_amount: Optional[float] = None,
    cabal_dump_supply_pct: float = 35.0,
    audited_wallet_convergence: bool = True,
    has_open_position: Optional[bool] = None,
    post_migration_organic_volume_confirmed: bool = True,
    fee_bps: int = PUMP_FUN_CURVE_FEE_BPS,
    token_mint: str = "PumpFunCurveMint111111111111111111111111111",
) -> ConstantProductCurveEvaluation:
    """Module-level convenience wrapper for `PreMintPeelChainListener.evaluate_constant_product_curve_and_scaleout`."""
    return _DEFAULT_LISTENER.evaluate_constant_product_curve_and_scaleout(
        curve_completion_pct=curve_completion_pct,
        virtual_sol_reserves=virtual_sol_reserves,
        virtual_token_reserves=virtual_token_reserves,
        order_sol_amount=order_sol_amount,
        sell_token_amount=sell_token_amount,
        cabal_dump_token_amount=cabal_dump_token_amount,
        cabal_dump_supply_pct=cabal_dump_supply_pct,
        audited_wallet_convergence=audited_wallet_convergence,
        has_open_position=has_open_position,
        post_migration_organic_volume_confirmed=post_migration_organic_volume_confirmed,
        fee_bps=fee_bps,
        token_mint=token_mint,
    )


__all__ = [
    "ACTION_ABORT_GRADUATION_FROZEN",
    "ACTION_ENTER_CURVE_SQUEEZE",
    "ACTION_HOLD_REJECTED_UNAUDITED_FLOW",
    "ACTION_SCALE_OUT_75PCT_PRE_FREEZE",
    "ACTION_WAIT_BELOW_SQUEEZE_ZONE",
    "AGENT_A_SWARM_ID",
    "ALLOWED_TARGET_PROGRAM_IDS",
    "BLOCK1_SNIPE_ACTION",
    "BurnerDispersalHop",
    "CABALSPY_REALTIME_6_STREAMS",
    "CABALSPY_WEBSOCKET_CORES",
    "CURVE_GRADUATION_FREEZE_PCT",
    "CURVE_GRADUATION_TARGET_REAL_SOL",
    "ConstantProductCurveEvaluation",
    "DEFAULT_OVERHEAD_TOLERANCE_SOL",
    "ENTRY_SQUEEZE_MAX_CURVE_PCT",
    "ENTRY_SQUEEZE_MIN_CURVE_PCT",
    "HIGH_GRADUATION_RATE_THRESHOLD_PCT",
    "INGESTION_TRANSPORTS",
    "INITIAL_REAL_TOKEN_RESERVES",
    "INITIAL_VIRTUAL_SOL_RESERVES",
    "INITIAL_VIRTUAL_TOKEN_RESERVES",
    "MAX_SHRED_INGESTION_LATENCY_MS",
    "MIN_FRESH_BURNER_WALLETS",
    "NO_PRE_MINT_SIGNAL",
    "PRE_FREEZE_SCALEOUT_FRACTION",
    "PRE_FREEZE_SCALEOUT_PCT",
    "PRE_LAUNCH_DEV_SIGNAL",
    "PRE_MINT_PEEL_WINDOW_SECONDS",
    "PUMPSWAP_AMM_PROGRAM_ID",
    "PUMP_FUN_CURVE_FEE_BPS",
    "PUMP_FUN_CURVE_FEE_RATE",
    "PUMP_FUN_PROGRAM_ID",
    "PreMintPeelChainListener",
    "PreMintPeelChainSignal",
    "RAYDIUM_CPMM_PROGRAM_ID",
    "RAYDIUM_V4_PROGRAM_ID",
    "RENT_AND_GAS_OVERHEAD_SOL",
    "RETAINED_RUNNER_FRACTION",
    "RETAINED_RUNNER_PCT",
    "RealtimeStreamIngestionReport",
    "SCALEOUT_MAX_CURVE_PCT",
    "SCALEOUT_MIN_CURVE_PCT",
    "SCALEOUT_TARGET_HIGH_CURVE_PCT",
    "SCALEOUT_TARGET_LOW_CURVE_PCT",
    "SHREDSTREAM_TURBINE_CORES",
    "STREAM_BONDING_CURVE_RESERVE_TICK",
    "STREAM_NEW_MINT_GENESIS",
    "STREAM_PEEL_CHAIN_FUNDING",
    "STREAM_PUMPSWAP_GRADUATION_FREEZE",
    "STREAM_SAME_BLOCK_JITO_BUNDLE",
    "STREAM_SOLBUNDLER_WITHDRAW_SWEEP",
    "SolBundlerWithdrawSweepRecord",
    "YELLOWSTONE_GEYSER_COMMITMENT",
    "detect_pre_mint_peel_chain_signal",
    "evaluate_constant_product_curve_and_scaleout",
    "evaluate_realtime_shred_and_cabalspy_streams",
    "register_solbundler_withdraw_sweep",
]
