"""Sovereign Titan OS — Sub-2ms Two-Tranche Shadow Executor (`src/execution/shadow_executor.py`).

Pinned to Cores 24–31 (`taskset -c 24-31`).
Listens to Helius `preconfSubscribe` filtered by `signer` for all `ACTIVE_SHADOW_LIST`
and inherited `CHILD_BURNER` wallets.

Hot-Path Execution Rules (T+0ms to T+1.8ms, strictly `< 2.0ms`):
1. Verify `burner_graph.is_bait_trade(master_wallet, token_mint) == False` (`<0.5ms`)
2. Verify `master_sol_spent >= profile.conviction_sizing.lotto_threshold_sol`
3. Verify `live_pool_price <= master_fill_price * 1.08` (+8% max slippage drift)
4. Verify `pHash` 64-bit BK-Tree lookup is `CLEAN` (`<0.3ms`)
5. Case A (Token is `PRE_APPROVED` in `/mnt/ramdisk/pre_approved_tokens`):
   - Fire 100% of target size in `< 2.0ms` inside the same 25ms Jito BAM batch tick with zero LLM wait.
6. Case B (Uncached 0-Second Launch):
   - Fire 25% "Scout Tranche" in `< 2.0ms` on deterministic hard gates, and concurrently query
     Port 8000/8001 (`<=45ms` hard timeout) to either fire the 75% "Conviction Tranche" or
     immediately flatten the Scout Tranche.
7. Asymmetric Exit Front-Running:
   - Set automatic scale-out at `0.90 * profile.exit_signature.first_tp_multiple`.
   - If `preconfSubscribe` detects the master wallet selling `>= 20%` of its bag, fire an
     immediate 95th-percentile Jito exit V0 transaction with `close_account` (`0.00203928 SOL` rent reclaim).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Literal, Optional, Tuple

from solders.hash import Hash
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import (
    ALTManager,
    RAYDIUM_V4_PROGRAM_ID,
    WSOL_MINT_PUBKEY,
    deterministic_pubkey,
)
from src.execution.atomic_tx_builder import (
    ATA_RENT_LAMPORTS,
    AtomicTxBuildResult,
    AtomicV0TransactionBuilder,
    derive_associated_token_address,
)
from src.execution.flash_loan_builder import DEXSwapLegSpec, LAMPORTS_PER_SOL
from src.graph.burner_graph import BurnerGraph
from src.intelligence.playbook_extractor import WalletProfile
from src.intelligence.pre_scorer_cache import BackgroundPreScorerCache
from src.intelligence.vision_scam_filter import VisionScamFilter
from src.llm.swarm_client import SwarmClient


MAX_SLIPPAGE_DRIFT_RATIO = 1.08  # +8% max price drift from master's exact fill
ASYMMETRIC_TP_FRONTRUN_FACTOR = 0.90  # 0.90 * profile.exit_signature.first_tp_multiple
MASTER_DUMP_SELL_THRESHOLD = 0.20  # >=20% master bag sell triggers immediate exit


@dataclass
class PreconfShadowEvent:
    """Incoming sub-slot Helius `preconfSubscribe` notification for a tracked shark."""

    master_wallet: str
    token_mint: str
    side: Literal["BUY", "SELL"]
    master_sol_spent: float
    master_fill_price: float
    live_pool_price: float
    banner_phash_u64: int
    slot: int = 310_000_000
    master_sell_fraction: float = 0.0  # e.g. 0.25 = master sold 25% of token bag


@dataclass
class ActiveShadowPosition:
    """Tracks an open shadow position and its asymmetric exit front-running target."""

    token_mint: str
    master_wallet: str
    entry_price: float
    frontrun_tp_multiple: float
    frontrun_tp_price: float
    sol_allocated: float
    token_ata: Pubkey
    tranche_mode: Literal["FULL_PRE_APPROVED", "SCOUT_25PCT", "FULL_TWO_TRANCHE"]
    opened_at_epoch_s: float = field(default_factory=time.time)


@dataclass
class ShadowExecutionDecision:
    """Output of the `<2.0ms` hot-path Shadow Executor."""

    accepted: bool
    case_type: Literal[
        "CASE_A_PRE_APPROVED_100PCT",
        "CASE_B_UNCACHED_SCOUT_25PCT",
        "ASYMMETRIC_EXIT_95TH_JITO",
        "BLOCKED",
    ]
    reject_reason: Optional[str]
    immediate_sol_dispatched: float
    pending_conviction_sol: float
    frontrun_tp_multiple: float
    hot_path_latency_ms: float
    signed_v0_tx: Optional[AtomicTxBuildResult] = None
    followup_v0_tx: Optional[AtomicTxBuildResult] = None
    jito_95th_tip_lamports: int = 0
    reclaimed_rent_lamports: int = 0


class ShadowExecutor:
    """Sub-2ms Two-Tranche Shadow Executor on Cores 24–31."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        burner_graph: Optional[BurnerGraph] = None,
        pre_scorer_cache: Optional[BackgroundPreScorerCache] = None,
        vision_filter: Optional[VisionScamFilter] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
        swarm_client: Optional[SwarmClient] = None,
        executor_keypair: Optional[Keypair] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.swarm_client = swarm_client or SwarmClient(self.settings)
        self.vision_filter = vision_filter or VisionScamFilter(
            self.settings, self.swarm_client
        )
        self.pre_scorer_cache = pre_scorer_cache or BackgroundPreScorerCache(
            self.settings, self.swarm_client, self.vision_filter
        )
        self.burner_graph = burner_graph or BurnerGraph(self.settings)
        self.alt_manager = ALTManager(self.settings)
        self.alt_manager.load_from_ramdisk()
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(
            self.settings, alt_manager=self.alt_manager
        )
        self.keypair = executor_keypair or Keypair()
        self.payer_pubkey = self.keypair.pubkey()
        self.wsol_ata = derive_associated_token_address(
            self.payer_pubkey, Pubkey.from_string(WSOL_MINT_PUBKEY)
        )
        self.alt_manager.register_custom_addresses([str(self.wsol_ata)])

        self.tracked_profiles: Dict[str, WalletProfile] = {}
        self.open_positions: Dict[str, ActiveShadowPosition] = {}
        self._mint_ata_cache: Dict[str, Tuple[Pubkey, Pubkey]] = {}
        self._cached_blockhash = Hash.default()

        # Pre-resolve pool vault pubkeys so hot path makes zero string parses
        self._raydium_prog_pk = Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID)
        self._pool_state_pk = self.alt_manager.get_pool_vault(0)
        self._pool_auth_pk = self.alt_manager.get_pool_vault(1)
        self._vault_in_pk = self.alt_manager.get_pool_vault(2)
        self._vault_out_pk = self.alt_manager.get_pool_vault(3)

    def register_shadow_wallet(self, profile: WalletProfile) -> None:
        """Registers an `ACTIVE_SHADOW_LIST` wallet (or `CHILD_BURNER`) and pre-warms its profile."""
        self.tracked_profiles[profile.wallet] = profile
        self.burner_graph.register_tracked_shark(profile.wallet, profile)

    def prewarm_token_accounts(self, token_mint: str) -> Tuple[Pubkey, Pubkey]:
        """Pre-computes and registers a token mint's ATA in the warm ALT for `<0.2ms` V0 compilation."""
        cached = self._mint_ata_cache.get(token_mint)
        if cached is not None:
            return cached
        try:
            mint_pk = Pubkey.from_string(token_mint)
        except Exception:
            mint_pk = deterministic_pubkey(f"mint:{token_mint}")
        ata_pk = derive_associated_token_address(self.payer_pubkey, mint_pk)
        self.alt_manager.register_custom_addresses([str(mint_pk), str(ata_pk)])
        self._mint_ata_cache[token_mint] = (mint_pk, ata_pk)
        return mint_pk, ata_pk

    def build_helius_preconf_filter(self) -> Dict[str, Any]:
        """Returns the Helius `preconfSubscribe` payload filtered by all tracked `ACTIVE_SHADOW_LIST` signers."""
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "preconfSubscribe",
            "params": [
                {
                    "commitment": "processed",
                    "signer": list(self.tracked_profiles.keys()),
                    "source": "shadow_executor_cores_24_31",
                }
            ],
        }

    # --------------------------------------------------------------------------
    # T+0ms to T+1.8ms: Sub-2ms Hot-Path Entry & Exit Execution
    # --------------------------------------------------------------------------
    def process_preconf_event_fast_path(
        self,
        event: PreconfShadowEvent,
        target_allocation_sol: float = 2.0,
        now_s: Optional[float] = None,
    ) -> ShadowExecutionDecision:
        """Executes the synchronous `<2.0ms` hot path upon receiving a `preconfSubscribe` packet."""
        t0 = time.perf_counter()

        profile = self.tracked_profiles.get(
            event.master_wallet
        ) or self.burner_graph.get_wallet_profile(event.master_wallet)
        if profile is None:
            return ShadowExecutionDecision(
                accepted=False,
                case_type="BLOCKED",
                reject_reason="UNTRACKED_MASTER_WALLET",
                immediate_sol_dispatched=0.0,
                pending_conviction_sol=0.0,
                frontrun_tp_multiple=0.0,
                hot_path_latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # Handle Master SELL Event -> Asymmetric Exit Front-Running (>= 20% master bag sell)
        if event.side == "SELL":
            if event.master_sell_fraction >= MASTER_DUMP_SELL_THRESHOLD:
                return self._execute_immediate_exit_bundle(
                    token_mint=event.token_mint,
                    master_wallet=event.master_wallet,
                    reason="MASTER_SOLD_GE_20PCT_BAG",
                    t0=t0,
                )
            return ShadowExecutionDecision(
                accepted=False,
                case_type="BLOCKED",
                reject_reason="MASTER_SELL_BELOW_20PCT_THRESHOLD",
                immediate_sol_dispatched=0.0,
                pending_conviction_sol=0.0,
                frontrun_tp_multiple=0.0,
                hot_path_latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # Gate 1: <0.5ms 3-Hop Copy-Farming Bait Check
        is_bait, _bait_ms, bait_reason = self.burner_graph.is_bait_trade(
            master_wallet=event.master_wallet,
            token_mint=event.token_mint,
            now_s=now_s,
        )
        if is_bait:
            return ShadowExecutionDecision(
                accepted=False,
                case_type="BLOCKED",
                reject_reason=f"BAIT_TRADE_DETECTED:{bait_reason}",
                immediate_sol_dispatched=0.0,
                pending_conviction_sol=0.0,
                frontrun_tp_multiple=0.0,
                hot_path_latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # Gate 2: Master Conviction Threshold (`master_sol_spent >= lotto_threshold_sol`)
        if event.master_sol_spent < profile.conviction_sizing.lotto_threshold_sol:
            return ShadowExecutionDecision(
                accepted=False,
                case_type="BLOCKED",
                reject_reason="MASTER_SOL_BELOW_LOTTO_THRESHOLD",
                immediate_sol_dispatched=0.0,
                pending_conviction_sol=0.0,
                frontrun_tp_multiple=0.0,
                hot_path_latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # Gate 3: Slippage Drift Check (`live_pool_price <= P_master * 1.08`)
        if event.live_pool_price > (event.master_fill_price * MAX_SLIPPAGE_DRIFT_RATIO):
            return ShadowExecutionDecision(
                accepted=False,
                case_type="BLOCKED",
                reject_reason="PRICE_DRIFT_EXCEEDED_8PCT_CAP",
                immediate_sol_dispatched=0.0,
                pending_conviction_sol=0.0,
                frontrun_tp_multiple=0.0,
                hot_path_latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # Gate 4: <0.3ms 64-Bit pHash BK-Tree Vampire Clone Check
        phash_res = self.vision_filter.bktree.query_vampire_clone(
            mint=event.token_mint,
            phash_u64=event.banner_phash_u64,
        )
        if phash_res.status == "VAMPIRE_CLONE":
            return ShadowExecutionDecision(
                accepted=False,
                case_type="BLOCKED",
                reject_reason=f"VAMPIRE_CLONE_OF_{phash_res.matched_older_mint}(dist={phash_res.hamming_distance})",
                immediate_sol_dispatched=0.0,
                pending_conviction_sol=0.0,
                frontrun_tp_multiple=0.0,
                hot_path_latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # Compute asymmetric exit front-running target: 0.90 * first_tp_multiple
        frontrun_tp_mult = round(
            ASYMMETRIC_TP_FRONTRUN_FACTOR * profile.exit_signature.first_tp_multiple,
            4,
        )
        effective_target_sol = round(
            target_allocation_sol * profile.priority_multiplier, 6
        )

        _mint_pk, user_token_ata = self.prewarm_token_accounts(event.token_mint)

        # Check `/mnt/ramdisk/pre_approved_tokens` (<0.02ms)
        pre_approved = self.pre_scorer_cache.get_fast(event.token_mint, now_s=now_s)

        if pre_approved is not None:
            # CASE A: Token is PRE_APPROVED -> Fire 100% of target size in <2.0ms
            lamports_in = int(round(effective_target_sol * LAMPORTS_PER_SOL))
            swap_leg = DEXSwapLegSpec(
                program_id=self._raydium_prog_pk,
                pool_state=self._pool_state_pk,
                pool_Authority=self._pool_auth_pk,
                vault_in=self._vault_in_pk,
                vault_out=self._vault_out_pk,
                user_source_token_account=self.wsol_ata,
                user_destination_token_account=user_token_ata,
                amount_in_lamports=lamports_in,
                min_amount_out_lamports=int(lamports_in * 0.95),
                label="Shadow_CaseA_100pct_Buy",
            )
            v0_tx = self.tx_builder.build_directional_buy_v0(
                payer_keypair=self.keypair,
                swap_leg=swap_leg,
                recent_blockhash=self._cached_blockhash,
            )
            self.open_positions[event.token_mint] = ActiveShadowPosition(
                token_mint=event.token_mint,
                master_wallet=event.master_wallet,
                entry_price=event.live_pool_price,
                frontrun_tp_multiple=frontrun_tp_mult,
                frontrun_tp_price=event.live_pool_price * frontrun_tp_mult,
                sol_allocated=effective_target_sol,
                token_ata=user_token_ata,
                tranche_mode="FULL_PRE_APPROVED",
            )
            hot_latency_ms = (time.perf_counter() - t0) * 1000.0
            return ShadowExecutionDecision(
                accepted=True,
                case_type="CASE_A_PRE_APPROVED_100PCT",
                reject_reason=None,
                immediate_sol_dispatched=effective_target_sol,
                pending_conviction_sol=0.0,
                frontrun_tp_multiple=frontrun_tp_mult,
                hot_path_latency_ms=hot_latency_ms,
                signed_v0_tx=v0_tx,
                jito_95th_tip_lamports=pre_approved.jito_tip_lamports,
            )

        # CASE B: Uncached 0-Second Launch -> Fire 25% Scout Tranche in <2.0ms
        scout_sol = round(effective_target_sol * self.settings.SCOUT_TRANCHE_RATIO, 6)
        conviction_sol = round(
            effective_target_sol * self.settings.CONVICTION_TRANCHE_RATIO, 6
        )
        scout_lamports = int(round(scout_sol * LAMPORTS_PER_SOL))

        scout_leg = DEXSwapLegSpec(
            program_id=self._raydium_prog_pk,
            pool_state=self._pool_state_pk,
            pool_Authority=self._pool_auth_pk,
            vault_in=self._vault_in_pk,
            vault_out=self._vault_out_pk,
            user_source_token_account=self.wsol_ata,
            user_destination_token_account=user_token_ata,
            amount_in_lamports=scout_lamports,
            min_amount_out_lamports=int(scout_lamports * 0.95),
            label="Shadow_CaseB_25pct_Scout_Buy",
        )
        scout_v0_tx = self.tx_builder.build_directional_buy_v0(
            payer_keypair=self.keypair,
            swap_leg=scout_leg,
            recent_blockhash=self._cached_blockhash,
        )
        self.open_positions[event.token_mint] = ActiveShadowPosition(
            token_mint=event.token_mint,
            master_wallet=event.master_wallet,
            entry_price=event.live_pool_price,
            frontrun_tp_multiple=frontrun_tp_mult,
            frontrun_tp_price=event.live_pool_price * frontrun_tp_mult,
            sol_allocated=scout_sol,
            token_ata=user_token_ata,
            tranche_mode="SCOUT_25PCT",
        )
        hot_latency_ms = (time.perf_counter() - t0) * 1000.0
        return ShadowExecutionDecision(
            accepted=True,
            case_type="CASE_B_UNCACHED_SCOUT_25PCT",
            reject_reason=None,
            immediate_sol_dispatched=scout_sol,
            pending_conviction_sol=conviction_sol,
            frontrun_tp_multiple=frontrun_tp_mult,
            hot_path_latency_ms=hot_latency_ms,
            signed_v0_tx=scout_v0_tx,
            jito_95th_tip_lamports=100_000,
        )

    async def resolve_case_b_conviction_or_flatten(
        self,
        event: PreconfShadowEvent,
        scout_decision: ShadowExecutionDecision,
        market_snapshot: Dict[str, Any],
        endpoint_override: Optional[str] = None,
    ) -> ShadowExecutionDecision:
        """Concurrently evaluates Port 8000 (`<=45ms` hard timeout) for Case B uncached launches:
        - If `EXECUTE_CONVICTION`: fires the remaining 75% Conviction Tranche V0 transaction.
        - If `ABORT_AND_EXIT` or timeout fallback: immediately flattens the 25% Scout Tranche
          with `close_account` (`0.00203928 SOL` rent reclaim).
        """
        gate_decision = await self.swarm_client.evaluate_tactical_gate(
            mint=event.token_mint,
            market_snapshot=market_snapshot,
            endpoint_override=endpoint_override,
        )
        _mint_pk, user_token_ata = self.prewarm_token_accounts(event.token_mint)

        if gate_decision.action == "EXECUTE_CONVICTION":
            conv_lamports = int(
                round(scout_decision.pending_conviction_sol * LAMPORTS_PER_SOL)
            )
            conv_leg = DEXSwapLegSpec(
                program_id=self._raydium_prog_pk,
                pool_state=self._pool_state_pk,
                pool_Authority=self._pool_auth_pk,
                vault_in=self._vault_in_pk,
                vault_out=self._vault_out_pk,
                user_source_token_account=self.wsol_ata,
                user_destination_token_account=user_token_ata,
                amount_in_lamports=conv_lamports,
                min_amount_out_lamports=int(conv_lamports * 0.95),
                label="Shadow_CaseB_75pct_Conviction_Buy",
            )
            conv_tx = self.tx_builder.build_directional_buy_v0(
                payer_keypair=self.keypair,
                swap_leg=conv_leg,
                recent_blockhash=self._cached_blockhash,
            )
            scout_decision.followup_v0_tx = conv_tx
            if event.token_mint in self.open_positions:
                pos = self.open_positions[event.token_mint]
                pos.sol_allocated += scout_decision.pending_conviction_sol
                pos.tranche_mode = "FULL_TWO_TRANCHE"
            return scout_decision

        # Flatten the 25% Scout Tranche immediately with close_account rent reclaim
        exit_res = self._execute_immediate_exit_bundle(
            token_mint=event.token_mint,
            master_wallet=event.master_wallet,
            reason="FLATTEN_SCOUT_TRANCHE",
            t0=time.perf_counter(),
        )
        scout_decision.followup_v0_tx = exit_res.signed_v0_tx
        scout_decision.reclaimed_rent_lamports = exit_res.reclaimed_rent_lamports
        return scout_decision

    def _execute_immediate_exit_bundle(
        self,
        token_mint: str,
        master_wallet: str,
        reason: str,
        t0: float,
    ) -> ShadowExecutionDecision:
        """Builds an immediate 95th-percentile Jito exit V0 transaction with `close_account` rent reclaim."""
        _mint_pk, user_token_ata = self.prewarm_token_accounts(token_mint)
        pos = self.open_positions.pop(token_mint, None)
        sol_exited = pos.sol_allocated if pos is not None else 1.0
        frontrun_tp = pos.frontrun_tp_multiple if pos is not None else 1.8

        sell_lamports = max(1, int(sol_exited * LAMPORTS_PER_SOL))
        exit_leg = DEXSwapLegSpec(
            program_id=self._raydium_prog_pk,
            pool_state=self._pool_state_pk,
            pool_Authority=self._pool_auth_pk,
            vault_in=self._vault_out_pk,
            vault_out=self._vault_in_pk,
            user_source_token_account=user_token_ata,
            user_destination_token_account=self.wsol_ata,
            amount_in_lamports=sell_lamports,
            min_amount_out_lamports=max(1, int(sell_lamports * 0.965)),
            label=f"Asymmetric_Exit_{reason}",
        )
        exit_v0_tx = self.tx_builder.build_full_token_exit_v0(
            payer_keypair=self.keypair,
            swap_leg=exit_leg,
            token_ata_to_close=user_token_ata,
            priority_micro_lamports=250_000,  # 95th-percentile priority fee
            recent_blockhash=self._cached_blockhash,
        )
        hot_latency_ms = (time.perf_counter() - t0) * 1000.0
        return ShadowExecutionDecision(
            accepted=True,
            case_type="ASYMMETRIC_EXIT_95TH_JITO",
            reject_reason=None,
            immediate_sol_dispatched=sol_exited,
            pending_conviction_sol=0.0,
            frontrun_tp_multiple=frontrun_tp,
            hot_path_latency_ms=hot_latency_ms,
            signed_v0_tx=exit_v0_tx,
            jito_95th_tip_lamports=500_000,
            reclaimed_rent_lamports=ATA_RENT_LAMPORTS,
        )
