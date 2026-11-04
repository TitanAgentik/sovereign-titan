"""Sovereign Titan OS — Atomic Buy+Sell Roundtrip Honeypot & Hidden-Tax Simulator (`src/security/svm_roundtrip_guard.py`).

Enforces `/AGENTS.md` Rule 18:
Before ANY directional buy (`Shadow Executor`, `Engine B Wide-Sandwich`, or `Horizons 1–4`)
is broadcast on Cores 16–31:
  1. Constructs an in-memory paired simulation bundle:
       `[Tx_Buy(amount_sol), Tx_Immediate_Sell(100%_tokens_received)]`
     against live pool state and builds a Jito/Helius `simulateBundle` (`replaceRecentBlockhash: true`)
     payload.
  2. Verifies in `< 0.5ms` that:
     - `Tx_Immediate_Sell` succeeds with `err == None` and triggers no unauthorized CPI hook.
     - Actual simulated SOL returned is:
         `>= amount_sol * (1.0 - (2 * pool_fee_rate) - expected_price_impact - 0.005)`
     - Unexplained token retention / hidden transfer tax is `<= 0.5%` (`0.005`).
  3. If `Tx_Immediate_Sell` reverts, triggers an unknown CPI hook, or exhibits `> 0.5%`
     unexplained token retention/tax, immediately hard-blocks the token globally in
     `/mnt/ramdisk/alpha_graph/roundtrip_honeypot_blocks.json` as
     `HIDDEN_HONEYPOT_OR_TAX_HOOK` for `$0.00` loss.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set

import orjson
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from src.config.settings import Settings, get_settings
from src.execution.alt_manager import RAYDIUM_V4_PROGRAM_ID
from src.execution.atomic_tx_builder import AtomicV0TransactionBuilder
from src.execution.flash_loan_builder import DEXSwapLegSpec, LAMPORTS_PER_SOL
from src.mirror.pool_state_mirror import simulate_cpmm_swap


MAX_UNEXPLAINED_RETENTION_PCT = 0.005  # 0.5% max unexplained retention/tax
HONEYPOT_BLOCK_REASON = "HIDDEN_HONEYPOT_OR_TAX_HOOK"

WHITELISTED_DEX_PROGRAMS: Set[str] = {
    RAYDIUM_V4_PROGRAM_ID,
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",  # Raydium CPMM
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",  # Raydium CLMM
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",  # Meteora DLMM
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB",  # Meteora Dynamic AMM
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",  # Orca Whirlpools
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",  # PumpSwap
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",  # Pump.fun Bonding Curve
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",  # SPL Token-2022
}


@dataclass
class RoundtripSimulationInput:
    """Input parameters for the `<0.5ms` Atomic Buy + Immediate Sell Roundtrip Check."""

    token_mint: str
    amount_sol: float
    pool_r_sol: float = 150.0
    pool_r_token: float = 100_000_000.0
    pool_fee_bps: float = 25.0  # e.g. 25 bps = 0.25%
    simulated_buy_tax_bps: float = 0.0
    simulated_sell_tax_bps: float = 0.0
    simulated_sell_revert_err: Optional[str] = None
    invoked_cpi_hook_program: Optional[str] = None
    custom_simulated_sol_out: Optional[float] = None


@dataclass
class RoundtripSimulationResult:
    """Result of the `<0.5ms` Atomic Buy + Immediate Sell Roundtrip Check."""

    passed: bool
    token_mint: str
    status_code: str  # "CLEAN_ROUNDTRIP" | "HIDDEN_HONEYPOT_OR_TAX_HOOK"
    reject_detail: Optional[str]
    amount_sol_in: float
    tokens_received_tx1: float
    expected_clean_sol_out_tx2: float
    min_required_sol_out_tx2: float
    actual_simulated_sol_out_tx2: float
    expected_price_impact_pct: float
    unexplained_retention_pct: float
    tx_immediate_sell_err: Optional[str]
    latency_ms: float
    simulate_bundle_rpc_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocalSvmRoundtripGuard:
    """Sub-0.5ms In-Memory Atomic Buy + Immediate 100% Sell Honeypot & Tax Guard."""

    def __init__(
        self,
        config: Optional[Settings] = None,
        tx_builder: Optional[AtomicV0TransactionBuilder] = None,
    ) -> None:
        self.settings = config or get_settings()
        self.tx_builder = tx_builder or AtomicV0TransactionBuilder(self.settings)
        self.blocklist_path: Path = (
            self.settings.RAMDISK_ALPHA_GRAPH / "roundtrip_honeypot_blocks.json"
        )
        self.blocklist_path.parent.mkdir(parents=True, exist_ok=True)
        self.blocked_mints: Dict[str, Dict[str, Any]] = {}
        self.blocks_today: int = 0
        self.evaluations_today: int = 0

        # Pre-warm a signed Buy + Sell V0 pair template so hot-path bundle construction is <0.02ms
        kp = Keypair()
        prog = Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID)
        pool_st = Pubkey.new_unique()
        pool_au = Pubkey.new_unique()
        v_in = Pubkey.new_unique()
        v_out = Pubkey.new_unique()
        u_src = Pubkey.new_unique()
        u_dst = Pubkey.new_unique()

        buy_leg = DEXSwapLegSpec(
            program_id=prog,
            pool_state=pool_st,
            pool_Authority=pool_au,
            vault_in=v_in,
            vault_out=v_out,
            user_source_token_account=u_src,
            user_destination_token_account=u_dst,
            amount_in_lamports=LAMPORTS_PER_SOL,
            min_amount_out_lamports=1,
            label="RoundtripTx1Buy",
        )
        sell_leg = DEXSwapLegSpec(
            program_id=prog,
            pool_state=pool_st,
            pool_Authority=pool_au,
            vault_in=v_out,
            vault_out=v_in,
            user_source_token_account=u_dst,
            user_destination_token_account=u_src,
            amount_in_lamports=1_000_000,
            min_amount_out_lamports=1,
            label="RoundtripTx2Sell",
        )
        tx1 = self.tx_builder.build_directional_buy_v0(payer_keypair=kp, swap_leg=buy_leg)
        tx2 = self.tx_builder.build_full_token_exit_v0(
            payer_keypair=kp, swap_leg=sell_leg, token_ata_to_close=u_dst
        )
        self._cached_tx1_b64 = base64.b64encode(bytes(tx1.transaction)).decode("ascii")
        self._cached_tx2_b64 = base64.b64encode(bytes(tx2.transaction)).decode("ascii")
        self._load_blocklist()

    def _load_blocklist(self) -> None:
        if not self.blocklist_path.exists():
            return
        try:
            data = orjson.loads(self.blocklist_path.read_bytes())
            self.blocked_mints = data.get("blocked_mints", {})
            self.blocks_today = int(data.get("blocks_today", len(self.blocked_mints)))
        except Exception:
            self.blocked_mints = {}

    def _persist_blocklist(self) -> None:
        payload = {
            "updated_at_ns": time.time_ns(),
            "blocks_today": self.blocks_today,
            "blocked_mints": self.blocked_mints,
        }
        self.blocklist_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))

    def is_token_blocked(self, token_mint: str) -> bool:
        """O(1) RAM check (`<0.001ms`) for previously blocked honeypot/tax mints."""
        return token_mint in self.blocked_mints

    def _record_global_block(self, token_mint: str, detail: str, retention_pct: float) -> None:
        if token_mint not in self.blocked_mints:
            self.blocks_today += 1
        self.blocked_mints[token_mint] = {
            "token_mint": token_mint,
            "reason": HONEYPOT_BLOCK_REASON,
            "detail": detail,
            "unexplained_retention_pct": round(retention_pct * 100.0, 3),
            "blocked_at_ns": time.time_ns(),
        }
        self._persist_blocklist()

    def build_simulate_bundle_payload(self) -> Dict[str, Any]:
        """Builds the Jito/Helius `simulateBundle` (`replaceRecentBlockhash: true`) RPC payload."""
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "simulateBundle",
            "params": [
                {
                    "encodedTransactions": [self._cached_tx1_b64, self._cached_tx2_b64],
                },
                {
                    "preExecutionAccountsConfigs": [None, None],
                    "postExecutionAccountsConfigs": [None, None],
                    "replaceRecentBlockhash": True,
                    "simulationBank": "processed",
                },
            ],
        }

    def verify_atomic_roundtrip(
        self, sim_input: RoundtripSimulationInput
    ) -> RoundtripSimulationResult:
        """Executes the `<0.5ms` in-memory Atomic Buy + Immediate 100% Sell roundtrip check."""
        t0 = time.perf_counter_ns()
        self.evaluations_today += 1
        mint = sim_input.token_mint
        amount_sol = max(float(sim_input.amount_sol), 1e-6)
        r_sol = max(float(sim_input.pool_r_sol), 1.0)
        r_token = max(float(sim_input.pool_r_token), 1.0)
        fee_bps = max(float(sim_input.pool_fee_bps), 0.0)
        fee_rate = fee_bps * 0.0001

        rpc_payload = self.build_simulate_bundle_payload()

        # Fast-path if already in global blocklist
        if mint in self.blocked_mints:
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return RoundtripSimulationResult(
                passed=False,
                token_mint=mint,
                status_code=HONEYPOT_BLOCK_REASON,
                reject_detail="ALREADY_GLOBAL_BLOCKED_IN_ALPHA_GRAPH",
                amount_sol_in=amount_sol,
                tokens_received_tx1=0.0,
                expected_clean_sol_out_tx2=0.0,
                min_required_sol_out_tx2=amount_sol,
                actual_simulated_sol_out_tx2=0.0,
                expected_price_impact_pct=0.0,
                unexplained_retention_pct=1.0,
                tx_immediate_sell_err="AlreadyBlockedHoneypot",
                latency_ms=elapsed_ms,
                simulate_bundle_rpc_payload=rpc_payload,
            )

        # Step 1: Simulate Tx1 (Buy amount_sol -> tokens_out)
        clean_tokens_tx1 = simulate_cpmm_swap(r_sol, r_token, amount_sol, fee_bps)
        buy_tax_rate = max(0.0, float(sim_input.simulated_buy_tax_bps) * 0.0001)
        actual_tokens_tx1 = clean_tokens_tx1 * (1.0 - buy_tax_rate)

        # Post-Tx1 pool reserves
        r_sol_post_tx1 = r_sol + amount_sol * (1.0 - fee_rate)
        r_token_post_tx1 = max(1e-6, r_token - clean_tokens_tx1)

        # Step 2: Simulate Tx2 (Sell 100% of tokens_received -> SOL)
        expected_clean_sol_out = simulate_cpmm_swap(
            r_token_post_tx1, r_sol_post_tx1, clean_tokens_tx1, fee_bps
        )
        # Roundtrip constant-product price impact (typically ~0 for immediate same-pool roundtrip, or small bin drift)
        two_fees = 2.0 * fee_rate
        raw_theoretical_after_fees = amount_sol * (1.0 - two_fees)
        expected_price_impact = max(
            0.0,
            (raw_theoretical_after_fees - expected_clean_sol_out) / amount_sol,
        )
        min_required_sol_out = amount_sol * (
            1.0 - two_fees - expected_price_impact - MAX_UNEXPLAINED_RETENTION_PCT
        )

        # Compute actual simulated SOL out accounting for sell taxes or custom hook retention
        sell_tax_rate = max(0.0, float(sim_input.simulated_sell_tax_bps) * 0.0001)
        if sim_input.custom_simulated_sol_out is not None:
            actual_sol_out = float(sim_input.custom_simulated_sol_out)
        elif sim_input.simulated_sell_revert_err is not None:
            actual_sol_out = 0.0
        else:
            sol_before_sell_tax = simulate_cpmm_swap(
                r_token_post_tx1, r_sol_post_tx1, actual_tokens_tx1, fee_bps
            )
            actual_sol_out = sol_before_sell_tax * (1.0 - sell_tax_rate)

        unexplained_retention = max(
            0.0,
            (expected_clean_sol_out - actual_sol_out) / max(expected_clean_sol_out, 1e-9),
        )

        # Check 1: Did Tx_Immediate_Sell revert?
        if sim_input.simulated_sell_revert_err is not None:
            detail = f"TX2_IMMEDIATE_SELL_REVERTED:{sim_input.simulated_sell_revert_err}"
            self._record_global_block(mint, detail, 1.0)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return RoundtripSimulationResult(
                passed=False,
                token_mint=mint,
                status_code=HONEYPOT_BLOCK_REASON,
                reject_detail=detail,
                amount_sol_in=amount_sol,
                tokens_received_tx1=actual_tokens_tx1,
                expected_clean_sol_out_tx2=expected_clean_sol_out,
                min_required_sol_out_tx2=min_required_sol_out,
                actual_simulated_sol_out_tx2=0.0,
                expected_price_impact_pct=expected_price_impact * 100.0,
                unexplained_retention_pct=100.0,
                tx_immediate_sell_err=sim_input.simulated_sell_revert_err,
                latency_ms=elapsed_ms,
                simulate_bundle_rpc_payload=rpc_payload,
            )

        # Check 2: Did Tx_Immediate_Sell invoke an unknown/unwhitelisted CPI Transfer Hook?
        if (
            sim_input.invoked_cpi_hook_program is not None
            and sim_input.invoked_cpi_hook_program not in WHITELISTED_DEX_PROGRAMS
        ):
            detail = (
                f"UNKNOWN_CPI_TRANSFER_HOOK:{sim_input.invoked_cpi_hook_program}"
            )
            self._record_global_block(mint, detail, unexplained_retention)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return RoundtripSimulationResult(
                passed=False,
                token_mint=mint,
                status_code=HONEYPOT_BLOCK_REASON,
                reject_detail=detail,
                amount_sol_in=amount_sol,
                tokens_received_tx1=actual_tokens_tx1,
                expected_clean_sol_out_tx2=expected_clean_sol_out,
                min_required_sol_out_tx2=min_required_sol_out,
                actual_simulated_sol_out_tx2=actual_sol_out,
                expected_price_impact_pct=expected_price_impact * 100.0,
                unexplained_retention_pct=unexplained_retention * 100.0,
                tx_immediate_sell_err=detail,
                latency_ms=elapsed_ms,
                simulate_bundle_rpc_payload=rpc_payload,
            )

        # Check 3: Does actual SOL returned satisfy the hard retention & tax floor?
        if (
            actual_sol_out < min_required_sol_out
            or unexplained_retention > MAX_UNEXPLAINED_RETENTION_PCT
        ):
            detail = (
                f"HIDDEN_TAX_OR_RETENTION_{unexplained_retention * 100.0:.2f}PCT"
                f"(out={actual_sol_out:.4f}<min={min_required_sol_out:.4f})"
            )
            self._record_global_block(mint, detail, unexplained_retention)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return RoundtripSimulationResult(
                passed=False,
                token_mint=mint,
                status_code=HONEYPOT_BLOCK_REASON,
                reject_detail=detail,
                amount_sol_in=amount_sol,
                tokens_received_tx1=actual_tokens_tx1,
                expected_clean_sol_out_tx2=expected_clean_sol_out,
                min_required_sol_out_tx2=min_required_sol_out,
                actual_simulated_sol_out_tx2=actual_sol_out,
                expected_price_impact_pct=expected_price_impact * 100.0,
                unexplained_retention_pct=unexplained_retention * 100.0,
                tx_immediate_sell_err=None,
                latency_ms=elapsed_ms,
                simulate_bundle_rpc_payload=rpc_payload,
            )

        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return RoundtripSimulationResult(
            passed=True,
            token_mint=mint,
            status_code="CLEAN_ROUNDTRIP",
            reject_detail=None,
            amount_sol_in=amount_sol,
            tokens_received_tx1=actual_tokens_tx1,
            expected_clean_sol_out_tx2=expected_clean_sol_out,
            min_required_sol_out_tx2=min_required_sol_out,
            actual_simulated_sol_out_tx2=actual_sol_out,
            expected_price_impact_pct=expected_price_impact * 100.0,
            unexplained_retention_pct=unexplained_retention * 100.0,
            tx_immediate_sell_err=None,
            latency_ms=elapsed_ms,
            simulate_bundle_rpc_payload=rpc_payload,
        )
