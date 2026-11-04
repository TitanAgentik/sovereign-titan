"""
Autonomous Experiential Learning Pool (`src/memory/experience_pool.py`).

Synthesizes:
  - ACE (Generator / Reflector / Curator) incremental rule curation
  - ExpeL (ADD, EDIT, UPVOTE, DOWNVOTE + k-NN vector similarity trajectory recall)
  - Reflexion (Immediate verbal self-critique + counterfactual fix in SQLite & JSONL)
  - Voyager (Executable CLI skill validation integration)
  - FinMem (Two-mode `train` shadow/replay vs `test` live capital promotion gate)
"""

from __future__ import annotations

import contextlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
from typing import Any, Dict, Iterator, List, Literal, Mapping, Optional, Sequence, Tuple, Union

import orjson


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TELEMETRY_DB_PATH = WORKSPACE_ROOT / "memory" / "telemetry.db"
DEFAULT_EPISODIC_JSONL_PATH = WORKSPACE_ROOT / "memory" / "episodic_failures.jsonl"
DEFAULT_HEURISTICS_RULE_PATH = WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md"
DEFAULT_ARCHIVED_RULES_PATH = (
    WORKSPACE_ROOT
    / ".agents"
    / "skills"
    / "experiential-learning-loop"
    / "references"
    / "archived-heuristics.md"
)

RULE_FILE_HARD_LIMIT_BYTES = 24_000
RULE_FILE_PRUNE_THRESHOLD_BYTES = 20_000
REFERENCE_FILE_MAX_CHARS = 60_000

SIX_STAGE_LATENCY_BUDGET_MS: Dict[str, Tuple[float, float]] = {
    "stage1_grpc_ingest_ms": (30.0, 80.0),
    "stage2_idl_parse_ms": (0.0, 15.0),
    "stage3_wallet_hash_match_ms": (0.0, 1.0),
    "stage4_jupiter_rug_gate_ms": (20.0, 40.0),
    "stage5_route_and_fee_build_ms": (10.0, 20.0),
    "stage6_jito_bundle_land_ms": (80.0, 150.0),
    "competitive_p50_total_ms": (200.0, 300.0),
    "degraded_slippage_cliff_ms": (800.0, float("inf")),
}

CANONICAL_FAILURE_CATEGORIES: Tuple[str, ...] = (
    "Thesis Error",
    "Graduation Race Condition",
    "Priority Fee Cliff",
    "Jupiter Slippage Drift",
    "Sell-Side Execution Amnesia",
    "Token-2022/SPL Rug Vector",
)

INITIAL_SEEDED_HEURISTICS: Tuple[Dict[str, Any], ...] = (
    {
        "rule_id": "RULE-EXEC-01",
        "category": "EXECUTION_LATENCY",
        "upvotes": 16,
        "downvotes": 2,
        "utility_score": 14,
        "status": "active",
        "rule_text": (
            "Maintain Yellowstone gRPC subscription filters vote=false, failed=false on program "
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P and abort any copy-trade entry if "
            "cumulative pre-submission latency exceeds 250ms, preventing >800ms fill degradation."
        ),
    },
    {
        "rule_id": "RULE-EXEC-02",
        "category": "EXECUTION_LATENCY",
        "upvotes": 20,
        "downvotes": 1,
        "utility_score": 19,
        "status": "active",
        "rule_text": (
            "Graduation Race Gate: When bonding curve invariant k = vSOL * vTokens indicates "
            "reserve accumulation between 82 SOL and 85 SOL (96.5% to 100% completion), halt "
            "direct bonding-curve buys and wait for the on-chain Raydium CPMM / PumpSwap "
            "migration instruction discriminator before routing via Jupiter."
        ),
    },
    {
        "rule_id": "RULE-EXEC-03",
        "category": "EXECUTION_LATENCY",
        "upvotes": 13,
        "downvotes": 2,
        "utility_score": 11,
        "status": "active",
        "rule_text": (
            "Dynamic Priority Fee & Jito Tip Scaling: Never use static SOL tips. Query current-slot "
            "priority fee percentiles; during quiet slots use the 50th percentile, and when target "
            "wallet competition or slot congestion spikes, cap tips at the 80th percentile or 1.5% "
            "of trade principal, whichever is lower."
        ),
    },
    {
        "rule_id": "RULE-EXEC-04",
        "category": "EXECUTION_LATENCY",
        "upvotes": 14,
        "downvotes": 1,
        "utility_score": 13,
        "status": "active",
        "rule_text": (
            "Jupiter Slippage Drift & ExactIn Protection: Build swap instructions with swap_mode=ExactIn "
            "and enforce the trader's true maximum slippage tolerance (<= 250 bps) against expected quote "
            "output at t=0ms so Jupiter deterministically aborts swaps that drift by t=150ms."
        ),
    },
    {
        "rule_id": "RULE-EXEC-05",
        "category": "EXECUTION_LATENCY",
        "upvotes": 16,
        "downvotes": 1,
        "utility_score": 15,
        "status": "active",
        "rule_text": (
            "Sell-Side Execution Parity: Mirror target wallet sells and stop-loss triggers through the "
            "same sub-300ms colocated gRPC + Jito single-transaction bundle pipeline (80-150ms slot "
            "inclusion, max 1 auto-retry) to eliminate sell-side execution amnesia."
        ),
    },
    {
        "rule_id": "RULE-RUG-01",
        "category": "ONCHAIN_RUG_TOKEN2022",
        "upvotes": 25,
        "downvotes": 0,
        "utility_score": 25,
        "status": "active",
        "rule_text": (
            "Authority Invariant: Immediately reject any SPL mint where mint_authority != null "
            "or freeze_authority != null."
        ),
    },
    {
        "rule_id": "RULE-RUG-02",
        "category": "ONCHAIN_RUG_TOKEN2022",
        "upvotes": 19,
        "downvotes": 1,
        "utility_score": 18,
        "status": "active",
        "rule_text": (
            "Token-2022 Extension Gate: Inspect all Token-2022 mint accounts for transfer_hook and "
            "transfer_fee. Reject any token with a non-empty transfer_hook program address or a mutable "
            "transfer_fee configuration unless the hook program is on the verified protocol allowlist."
        ),
    },
    {
        "rule_id": "RULE-RUG-03",
        "category": "ONCHAIN_RUG_TOKEN2022",
        "upvotes": 17,
        "downvotes": 1,
        "utility_score": 16,
        "status": "active",
        "rule_text": (
            "Direct Vault LP Burn Check: Because DexScreener indexing lags fresh LP burns by 15-30 "
            "minutes, verify lpBurnedOrLocked directly via RPC account balance inspection on the "
            "Raydium/PumpSwap LP mint immediately upon graduation."
        ),
    },
    {
        "rule_id": "RULE-RUG-04",
        "category": "ONCHAIN_RUG_TOKEN2022",
        "upvotes": 16,
        "downvotes": 1,
        "utility_score": 15,
        "status": "active",
        "rule_text": (
            "Holder Concentration & Sybil Deployer Gate: Require Top-10 non-pool holders <= 15% of "
            "total supply and zero prior deployer rugs, running scripts/sybil_check.py to unmask "
            "bundled Jito multi-wallet distributions."
        ),
    },
    {
        "rule_id": "RULE-RUG-05",
        "category": "ONCHAIN_RUG_TOKEN2022",
        "upvotes": 13,
        "downvotes": 1,
        "utility_score": 12,
        "status": "active",
        "rule_text": (
            "Metaplex Metadata Mutability & Anti-Vampire Gate: Require metadata_mutable: false and "
            "unique metadata URI cross-verified against official social contract-address announcements."
        ),
    },
)


@dataclass
class TradeTrajectory:
    """Represents a single 6-stage Solana memecoin execution trajectory."""

    tx_signature: str
    mint_address: str
    mode: Literal["train", "test"] = "train"
    curve_progress_pct: float = 35.0
    latency_grpc_ms: float = 48.0
    latency_parse_ms: float = 4.2
    latency_rug_gate_ms: float = 28.0
    latency_jito_ms: float = 110.0
    total_latency_ms: float = 205.0
    jito_tip_sol: float = 0.008
    priority_fee_sol: float = 0.012
    expected_slippage_bps: float = 85.0
    realized_slippage_bps: float = 95.0
    pnl_sol: float = 0.45
    failure_category: str = "NONE"
    embedding_json: str = "[]"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EpisodicReflection:
    """Represents a Reflexion verbal self-critique and counterfactual fix."""

    id: Optional[int]
    tx_signature: str
    verbal_critique: str
    counterfactual_fix: str
    created_at: str
    failure_category: str = "Thesis Error"
    recommended_rule_id: str = "RULE-EXEC-01"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HeuristicRuleEntry:
    """Represents an ExpeL-scored rule in `heuristic_ledger`."""

    rule_id: str
    rule_text: str
    category: str
    upvotes: int
    downvotes: int
    utility_score: int
    status: Literal["shadow", "active", "archived"] = "shadow"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShadowValidationResult:
    """Result of FinMem `train` (shadow) mode backtest & promotion evaluation."""

    rule_id: str
    evaluated_trajectories: int
    matched_failures_prevented: int
    counterfactual_pnl_delta_sol: float
    win_rate_delta_pct: float
    promoted_to_active: bool
    new_status: str
    utility_score: int
    rule_file_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_trajectory_embedding(
    curve_progress_pct: float,
    latency_grpc_ms: float,
    latency_parse_ms: float,
    latency_rug_gate_ms: float,
    latency_jito_ms: float,
    total_latency_ms: float,
    jito_tip_sol: float,
    priority_fee_sol: float,
    expected_slippage_bps: float,
    realized_slippage_bps: float,
    pnl_sol: float,
) -> List[float]:
    """
    Computes an L2-normalized 11-dimensional microstructure feature vector for ExpeL
    k-NN cosine similarity retrieval across bonding-curve and latency regimes.
    """
    raw = [
        float(curve_progress_pct) / 100.0,
        float(latency_grpc_ms) / 100.0,
        float(latency_parse_ms) / 20.0,
        float(latency_rug_gate_ms) / 50.0,
        float(latency_jito_ms) / 200.0,
        float(total_latency_ms) / 500.0,
        min(1.0, float(jito_tip_sol) * 20.0),
        min(1.0, float(priority_fee_sol) * 20.0),
        min(2.0, float(expected_slippage_bps) / 500.0),
        min(2.0, float(realized_slippage_bps) / 500.0),
        math.tanh(float(pnl_sol)),
    ]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [round(v / norm, 6) for v in raw]


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Computes cosine similarity between two equal-length vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(float(a) * float(a) for a in vec_a))
    norm_b = math.sqrt(sum(float(b) * float(b) for b in vec_b))
    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0
    return round(dot / (norm_a * norm_b), 6)


class ExperiencePool:
    """
    Embedded SQLite + Vector Store (`memory/telemetry.db`) implementing ACE, ExpeL,
    Reflexion, Voyager, and FinMem.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        episodic_jsonl_path: Optional[Union[str, Path]] = None,
        heuristics_rule_path: Optional[Union[str, Path]] = None,
        archived_rules_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_TELEMETRY_DB_PATH
        is_custom_db = (
            db_path is not None
            and self.db_path.resolve() != DEFAULT_TELEMETRY_DB_PATH.resolve()
        )
        self.episodic_jsonl_path = (
            Path(episodic_jsonl_path)
            if episodic_jsonl_path is not None
            else (self.db_path.parent / "episodic_failures.jsonl")
        )
        if heuristics_rule_path is not None:
            self.heuristics_rule_path = Path(heuristics_rule_path)
        elif is_custom_db:
            self.heuristics_rule_path = self.db_path.parent / "solana-heuristics.md"
        else:
            self.heuristics_rule_path = DEFAULT_HEURISTICS_RULE_PATH

        if archived_rules_path is not None:
            self.archived_rules_path = Path(archived_rules_path)
        elif is_custom_db:
            self.archived_rules_path = self.db_path.parent / "archived-heuristics.md"
        else:
            self.archived_rules_path = DEFAULT_ARCHIVED_RULES_PATH

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.episodic_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        if (
            is_custom_db
            and heuristics_rule_path is None
            and not self.heuristics_rule_path.exists()
            and DEFAULT_HEURISTICS_RULE_PATH.exists()
        ):
            self.heuristics_rule_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DEFAULT_HEURISTICS_RULE_PATH, self.heuristics_rule_path)
        self._init_schema_and_seed()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema_and_seed(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trade_trajectories (
                    tx_signature TEXT PRIMARY KEY,
                    mint_address TEXT NOT NULL,
                    mode TEXT NOT NULL CHECK(mode IN ('train', 'test')),
                    curve_progress_pct REAL NOT NULL,
                    latency_grpc_ms REAL NOT NULL,
                    latency_parse_ms REAL NOT NULL,
                    latency_rug_gate_ms REAL NOT NULL,
                    latency_jito_ms REAL NOT NULL,
                    total_latency_ms REAL NOT NULL,
                    jito_tip_sol REAL NOT NULL,
                    priority_fee_sol REAL NOT NULL,
                    expected_slippage_bps REAL NOT NULL,
                    realized_slippage_bps REAL NOT NULL,
                    pnl_sol REAL NOT NULL,
                    failure_category TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS episodic_reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_signature TEXT NOT NULL,
                    verbal_critique TEXT NOT NULL,
                    counterfactual_fix TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    failure_category TEXT NOT NULL DEFAULT '',
                    recommended_rule_id TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS heuristic_ledger (
                    rule_id TEXT PRIMARY KEY,
                    rule_text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    upvotes INTEGER NOT NULL DEFAULT 0,
                    downvotes INTEGER NOT NULL DEFAULT 0,
                    utility_score INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL CHECK(status IN ('shadow', 'active', 'archived'))
                );
                """
            )
            for item in INITIAL_SEEDED_HEURISTICS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO heuristic_ledger (
                        rule_id, rule_text, category, upvotes, downvotes, utility_score, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["rule_id"],
                        item["rule_text"],
                        item["category"],
                        int(item["upvotes"]),
                        int(item["downvotes"]),
                        int(item["utility_score"]),
                        item["status"],
                    ),
                )
            conn.commit()

    def classify_failure_mode(
        self,
        trajectory: Union[TradeTrajectory, Mapping[str, Any]],
    ) -> Tuple[str, str, str, str]:
        """
        Audits a trade trajectory across the 6-stage Pump.fun/Raydium latency budget
        and on-chain Token-2022/SPL invariants, returning:
          `(failure_category, verbal_critique, counterfactual_fix, recommended_rule_id)`.
        """
        t = self._coerce_trajectory(trajectory)
        meta = dict(t.metadata or {})
        slippage_drift = t.realized_slippage_bps - t.expected_slippage_bps

        # 1. Check Token-2022 / SPL On-Chain Rug Vectors first
        has_token2022_or_spl_rug = bool(
            meta.get("mint_authority") not in (None, "", "null")
            or meta.get("freeze_authority") not in (None, "", "null")
            or bool(meta.get("transfer_hook"))
            or float(meta.get("transfer_fee_bps", 0.0)) > 0.0
            or bool(meta.get("transfer_fee_mutable", False))
            or str(meta.get("non_transferable", "0")) not in ("0", "false", "False")
            or meta.get("lp_burned_or_locked") is False
            or float(meta.get("top10_holder_pct", 0.0)) > 15.0
            or bool(meta.get("token2022_rug_vector", False))
        )
        if has_token2022_or_spl_rug or t.failure_category == "Token-2022/SPL Rug Vector":
            hook_prog = meta.get("transfer_hook") or "malicious_extension"
            critique = (
                f"Trade {t.tx_signature} on {t.mint_address} suffered a Token-2022/SPL Rug Vector "
                f"(pnl={t.pnl_sol:+.4f} SOL): detected unsafe mint/extension invariant "
                f"(transfer_hook={hook_prog}, fee_bps={meta.get('transfer_fee_bps', 0)}, "
                f"top10_pct={meta.get('top10_holder_pct', 0.0)}%)."
            )
            fix = (
                "Enforce [RULE-RUG-02] pre-trade Token-2022 extension gate: hard-block any mint "
                "with non-empty transfer_hook, non-zero/mutable transfer_fee, unburned LP, or "
                "non-null mint/freeze authority before Stage 5 route construction."
            )
            return ("Token-2022/SPL Rug Vector", critique, fix, "RULE-RUG-02")

        # 2. Check Graduation Race Condition (82-85 SOL / 96.5%-100% curve progress)
        if (
            96.5 <= t.curve_progress_pct <= 100.0
            or bool(meta.get("graduation_race", False))
            or t.failure_category == "Graduation Race Condition"
        ) and t.pnl_sol <= 0.0:
            critique = (
                f"Trade {t.tx_signature} on {t.mint_address} hit a Graduation Race Condition at "
                f"curve_progress={t.curve_progress_pct:.2f}% (82-85 SOL handoff window), routing "
                f"into a draining bonding curve during the 1-2 slot Raydium/PumpSwap migration "
                f"(realized_slippage={t.realized_slippage_bps:.0f} bps, pnl={t.pnl_sol:+.4f} SOL)."
            )
            fix = (
                "Apply [RULE-EXEC-02]: halt direct Pump.fun bonding-curve buys when curve progress "
                "is between 96.5% and 100% (82-85 SOL) and wait for the Raydium CPMM / PumpSwap "
                "migration discriminator before executing via Jupiter."
            )
            return ("Graduation Race Condition", critique, fix, "RULE-EXEC-02")

        # 3. Check Sell-Side Execution Amnesia
        if (
            float(meta.get("exit_latency_ms", 0.0)) > 300.0
            or bool(meta.get("sell_side_amnesia", False))
            or bool(meta.get("missed_target_sell", False))
            or t.failure_category == "Sell-Side Execution Amnesia"
        ) and t.pnl_sol <= 0.0:
            exit_lat = float(meta.get("exit_latency_ms", t.total_latency_ms))
            critique = (
                f"Trade {t.tx_signature} on {t.mint_address} suffered Sell-Side Execution Amnesia: "
                f"exit path took {exit_lat:.1f}ms (>300ms budget) after target wallet sell signal, "
                f"resulting in {t.pnl_sol:+.4f} SOL loss."
            )
            fix = (
                "Apply [RULE-EXEC-05]: route all mirror exits and stop-losses through the same "
                "colocated gRPC + single-tx Jito bundle pipeline (<300ms budget) used for entries."
            )
            return ("Sell-Side Execution Amnesia", critique, fix, "RULE-EXEC-05")

        # 4. Check Priority Fee Cliff (slot congestion spike with static/low priority fee or Jito latency spike)
        if (
            (t.latency_jito_ms > 150.0 and (t.priority_fee_sol < 0.005 or t.jito_tip_sol < 0.005))
            or bool(meta.get("priority_fee_cliff", False))
            or t.failure_category == "Priority Fee Cliff"
        ) and t.pnl_sol <= 0.0:
            critique = (
                f"Trade {t.tx_signature} on {t.mint_address} hit a Priority Fee Cliff: "
                f"jito_tip={t.jito_tip_sol:.4f} SOL and priority_fee={t.priority_fee_sol:.4f} SOL "
                f"were below the slot's 40th-80th congestion percentile, delaying Jito inclusion "
                f"to {t.latency_jito_ms:.1f}ms (total={t.total_latency_ms:.1f}ms, pnl={t.pnl_sol:+.4f} SOL)."
            )
            fix = (
                "Apply [RULE-EXEC-03]: dynamically pull priority fees and Jito tips from the "
                "current slot's 40th-80th percentile (capped at 1.5% of trade principal) instead "
                "of using static fee constants."
            )
            return ("Priority Fee Cliff", critique, fix, "RULE-EXEC-03")

        # 5. Check Jupiter Slippage Drift or >800ms total latency fill degradation
        if (
            t.total_latency_ms > 800.0
            or slippage_drift >= 150.0
            or t.realized_slippage_bps >= 500.0
            or t.failure_category == "Jupiter Slippage Drift"
        ) and t.pnl_sol <= 0.0:
            critique = (
                f"Trade {t.tx_signature} on {t.mint_address} suffered Jupiter Slippage Drift / "
                f"Latency Degradation: total_latency={t.total_latency_ms:.1f}ms (gRPC={t.latency_grpc_ms:.1f}ms, "
                f"parse={t.latency_parse_ms:.1f}ms, rug_gate={t.latency_rug_gate_ms:.1f}ms, "
                f"jito={t.latency_jito_ms:.1f}ms) caused quote drift from {t.expected_slippage_bps:.0f} bps "
                f"to {t.realized_slippage_bps:.0f} bps (pnl={t.pnl_sol:+.4f} SOL)."
            )
            fix = (
                "Apply [RULE-EXEC-01] & [RULE-EXEC-04]: abort pre-submission entries when cumulative "
                "pre-Jito latency exceeds 250ms, and build Jupiter swaps with swap_mode=ExactIn "
                "enforcing strict max slippage against t=0ms expected output."
            )
            return ("Jupiter Slippage Drift", critique, fix, "RULE-EXEC-01")

        # 6. Profitable trade
        if t.pnl_sol > 0.0 and t.failure_category in ("", "NONE"):
            critique = (
                f"Winning execution {t.tx_signature} on {t.mint_address} realized {t.pnl_sol:+.4f} SOL "
                f"within {t.total_latency_ms:.1f}ms total latency (slippage={t.realized_slippage_bps:.0f} bps)."
            )
            fix = "UPVOTE active execution and rug-gate rules that governed this trajectory."
            return ("NONE", critique, fix, "RULE-EXEC-01")

        # 7. Default: Thesis Error (clean sub-300ms execution & valid contract, but negative PnL)
        critique = (
            f"Trade {t.tx_signature} on {t.mint_address} executed cleanly in {t.total_latency_ms:.1f}ms "
            f"with low slippage ({t.realized_slippage_bps:.0f} bps), but lost {t.pnl_sol:+.4f} SOL due "
            f"to a Thesis Error (insufficient follow-on smart-money mindshare or spoofed narrative)."
        )
        fix = (
            "Require multi-wallet smart-money confluence and cross-verified social contract address "
            "validation ([RULE-RUG-05]) before entry."
        )
        return ("Thesis Error", critique, fix, "RULE-RUG-05")

    def _coerce_trajectory(
        self, trajectory: Union[TradeTrajectory, Mapping[str, Any]]
    ) -> TradeTrajectory:
        if isinstance(trajectory, TradeTrajectory):
            t = trajectory
        else:
            mode_val = str(trajectory.get("mode", "train")).lower()
            mode_lit: Literal["train", "test"] = "test" if mode_val == "test" else "train"
            grpc_ms = float(trajectory.get("latency_grpc_ms", 45.0))
            parse_ms = float(trajectory.get("latency_parse_ms", 4.0))
            rug_ms = float(trajectory.get("latency_rug_gate_ms", 28.0))
            jito_ms = float(trajectory.get("latency_jito_ms", 110.0))
            total_ms = float(
                trajectory.get(
                    "total_latency_ms",
                    grpc_ms + parse_ms + rug_ms + jito_ms + 15.0,
                )
            )
            t = TradeTrajectory(
                tx_signature=str(trajectory["tx_signature"]),
                mint_address=str(trajectory.get("mint_address", "PumpMint111111111111111111111111111")),
                mode=mode_lit,
                curve_progress_pct=float(trajectory.get("curve_progress_pct", 35.0)),
                latency_grpc_ms=grpc_ms,
                latency_parse_ms=parse_ms,
                latency_rug_gate_ms=rug_ms,
                latency_jito_ms=jito_ms,
                total_latency_ms=total_ms,
                jito_tip_sol=float(trajectory.get("jito_tip_sol", 0.008)),
                priority_fee_sol=float(trajectory.get("priority_fee_sol", 0.012)),
                expected_slippage_bps=float(trajectory.get("expected_slippage_bps", 80.0)),
                realized_slippage_bps=float(trajectory.get("realized_slippage_bps", 95.0)),
                pnl_sol=float(trajectory.get("pnl_sol", 0.0)),
                failure_category=str(trajectory.get("failure_category", "NONE")),
                embedding_json=str(trajectory.get("embedding_json", "[]")),
                metadata=dict(trajectory.get("metadata", {})),
            )

        if not t.embedding_json or t.embedding_json == "[]":
            emb = compute_trajectory_embedding(
                curve_progress_pct=t.curve_progress_pct,
                latency_grpc_ms=t.latency_grpc_ms,
                latency_parse_ms=t.latency_parse_ms,
                latency_rug_gate_ms=t.latency_rug_gate_ms,
                latency_jito_ms=t.latency_jito_ms,
                total_latency_ms=t.total_latency_ms,
                jito_tip_sol=t.jito_tip_sol,
                priority_fee_sol=t.priority_fee_sol,
                expected_slippage_bps=t.expected_slippage_bps,
                realized_slippage_bps=t.realized_slippage_bps,
                pnl_sol=t.pnl_sol,
            )
            t.embedding_json = json.dumps(emb)
        return t

    def record_trajectory(
        self,
        trajectory: Union[TradeTrajectory, Mapping[str, Any]],
        auto_reflect: bool = True,
    ) -> Tuple[TradeTrajectory, Optional[EpisodicReflection]]:
        """
        Records a trade trajectory in `trade_trajectories` and optionally generates
        an immediate Reflexion verbal self-critique in `episodic_reflections` and
        `memory/episodic_failures.jsonl` when `pnl_sol <= 0` or a failure mode is present.
        """
        t = self._coerce_trajectory(trajectory)
        failure_cat, critique, fix, rec_rule_id = self.classify_failure_mode(t)
        if t.failure_category in ("", "NONE") and failure_cat != "NONE":
            t.failure_category = failure_cat

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO trade_trajectories (
                    tx_signature, mint_address, mode, curve_progress_pct,
                    latency_grpc_ms, latency_parse_ms, latency_rug_gate_ms,
                    latency_jito_ms, total_latency_ms, jito_tip_sol,
                    priority_fee_sol, expected_slippage_bps, realized_slippage_bps,
                    pnl_sol, failure_category, embedding_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t.tx_signature,
                    t.mint_address,
                    t.mode,
                    t.curve_progress_pct,
                    t.latency_grpc_ms,
                    t.latency_parse_ms,
                    t.latency_rug_gate_ms,
                    t.latency_jito_ms,
                    t.total_latency_ms,
                    t.jito_tip_sol,
                    t.priority_fee_sol,
                    t.expected_slippage_bps,
                    t.realized_slippage_bps,
                    t.pnl_sol,
                    t.failure_category,
                    t.embedding_json,
                    json.dumps(t.metadata),
                ),
            )
            conn.commit()

        reflection: Optional[EpisodicReflection] = None
        if auto_reflect and (t.pnl_sol <= 0.0 or t.failure_category != "NONE"):
            reflection = self.record_episodic_reflection(
                tx_signature=t.tx_signature,
                verbal_critique=critique,
                counterfactual_fix=fix,
                failure_category=t.failure_category,
                recommended_rule_id=rec_rule_id,
            )

        return t, reflection

    def record_episodic_reflection(
        self,
        tx_signature: str,
        verbal_critique: str,
        counterfactual_fix: str,
        failure_category: str = "Thesis Error",
        recommended_rule_id: str = "RULE-EXEC-01",
    ) -> EpisodicReflection:
        """
        Stores a Reflexion verbal self-critique in `episodic_reflections` (`memory/telemetry.db`)
        and appends it to the short-term sliding buffer `memory/episodic_failures.jsonl`.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        already_existed = False
        with self._connect() as conn:
            existing_row = conn.execute(
                "SELECT id, created_at FROM episodic_reflections WHERE tx_signature = ? ORDER BY id ASC LIMIT 1",
                (tx_signature,),
            ).fetchone()
            if existing_row is not None:
                already_existed = True
                row_id = int(existing_row["id"])
                conn.execute(
                    """
                    UPDATE episodic_reflections
                    SET verbal_critique = ?, counterfactual_fix = ?, created_at = ?,
                        failure_category = ?, recommended_rule_id = ?
                    WHERE id = ?
                    """,
                    (
                        verbal_critique,
                        counterfactual_fix,
                        now_iso,
                        failure_category,
                        recommended_rule_id,
                        row_id,
                    ),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO episodic_reflections (
                        tx_signature, verbal_critique, counterfactual_fix,
                        created_at, failure_category, recommended_rule_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tx_signature,
                        verbal_critique,
                        counterfactual_fix,
                        now_iso,
                        failure_category,
                        recommended_rule_id,
                    ),
                )
                row_id = int(cur.lastrowid or 0)
            conn.commit()

        reflection = EpisodicReflection(
            id=row_id,
            tx_signature=tx_signature,
            verbal_critique=verbal_critique,
            counterfactual_fix=counterfactual_fix,
            created_at=now_iso,
            failure_category=failure_category,
            recommended_rule_id=recommended_rule_id,
        )

        if not already_existed:
            with self.episodic_jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(reflection.to_dict()) + "\n")

        return reflection

    def retrieve_knn_winning_trajectories(
        self,
        query_trajectory: Union[TradeTrajectory, Mapping[str, Any]],
        k: int = 3,
        mode_filter: Optional[Literal["train", "test"]] = None,
    ) -> List[Dict[str, Any]]:
        """
        ExpeL Trajectory Recall: Retrieves the k-nearest past winning executions (`pnl_sol > 0`)
        via cosine similarity over microstructure feature embeddings.
        """
        q = self._coerce_trajectory(query_trajectory)
        q_vec = orjson.loads(q.embedding_json)

        sql = "SELECT * FROM trade_trajectories WHERE pnl_sol > 0.0"
        params: List[Any] = []
        if mode_filter in ("train", "test"):
            sql += " AND mode = ?"
            params.append(mode_filter)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        scored: List[Dict[str, Any]] = []
        for row in rows:
            cand_vec = orjson.loads(row["embedding_json"] or "[]")
            sim = cosine_similarity(q_vec, cand_vec)
            item = dict(row)
            item["similarity"] = sim
            scored.append(item)

        scored.sort(key=lambda r: (-r["similarity"], -r["pnl_sol"]))
        return scored[: max(1, int(k))]

    def get_reflections(self, tx_signature: Optional[str] = None) -> List[EpisodicReflection]:
        """Returns recorded episodic reflections from `memory/telemetry.db`."""
        with self._connect() as conn:
            if tx_signature:
                rows = conn.execute(
                    "SELECT * FROM episodic_reflections WHERE tx_signature = ? ORDER BY id ASC",
                    (tx_signature,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM episodic_reflections ORDER BY id ASC"
                ).fetchall()
        return [
            EpisodicReflection(
                id=int(r["id"]),
                tx_signature=str(r["tx_signature"]),
                verbal_critique=str(r["verbal_critique"]),
                counterfactual_fix=str(r["counterfactual_fix"]),
                created_at=str(r["created_at"]),
                failure_category=str(r["failure_category"]),
                recommended_rule_id=str(r["recommended_rule_id"]),
            )
            for r in rows
        ]

    def get_heuristic_rule(self, rule_id: str) -> Optional[HeuristicRuleEntry]:
        """Fetches a single rule from `heuristic_ledger`."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM heuristic_ledger WHERE rule_id = ?",
                (rule_id,),
            ).fetchone()
        if row is None:
            return None
        return HeuristicRuleEntry(
            rule_id=str(row["rule_id"]),
            rule_text=str(row["rule_text"]),
            category=str(row["category"]),
            upvotes=int(row["upvotes"]),
            downvotes=int(row["downvotes"]),
            utility_score=int(row["utility_score"]),
            status=str(row["status"]),  # type: ignore[arg-type]
        )

    def list_heuristic_rules(
        self, status: Optional[str] = None
    ) -> List[HeuristicRuleEntry]:
        """Lists rules from `heuristic_ledger`, ordered by descending utility_score."""
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM heuristic_ledger WHERE status = ? ORDER BY utility_score DESC, rule_id ASC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM heuristic_ledger ORDER BY utility_score DESC, rule_id ASC"
                ).fetchall()
        return [
            HeuristicRuleEntry(
                rule_id=str(r["rule_id"]),
                rule_text=str(r["rule_text"]),
                category=str(r["category"]),
                upvotes=int(r["upvotes"]),
                downvotes=int(r["downvotes"]),
                utility_score=int(r["utility_score"]),
                status=str(r["status"]),  # type: ignore[arg-type]
            )
            for r in rows
        ]

    def apply_expel_operation(
        self,
        operation: Literal["ADD", "EDIT", "UPVOTE", "DOWNVOTE"],
        rule_id: str,
        rule_text: Optional[str] = None,
        category: str = "ONCHAIN_RUG_TOKEN2022",
        initial_status: Literal["shadow", "active", "archived"] = "shadow",
        weight: int = 1,
        sync_markdown: bool = True,
    ) -> HeuristicRuleEntry:
        """
        Executes a discrete ExpeL rule operation (`ADD`, `EDIT`, `UPVOTE`, `DOWNVOTE`)
        on `heuristic_ledger` and incrementally syncs active rules to
        `.agents/rules/solana-heuristics.md` without monolithic rewrites or YAML corruption.
        """
        op = operation.upper()
        step = max(1, int(weight))

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM heuristic_ledger WHERE rule_id = ?",
                (rule_id,),
            ).fetchone()

            if op == "ADD":
                if not rule_text:
                    raise ValueError("rule_text is required for ExpeL ADD operation")
                upvotes = step if initial_status == "active" else 1
                downvotes = 0
                utility = upvotes - downvotes
                conn.execute(
                    """
                    INSERT OR REPLACE INTO heuristic_ledger (
                        rule_id, rule_text, category, upvotes, downvotes, utility_score, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (rule_id, rule_text.strip(), category, upvotes, downvotes, utility, initial_status),
                )
            elif op == "EDIT":
                if existing is None:
                    raise KeyError(f"Cannot EDIT non-existent rule_id: {rule_id}")
                new_text = (rule_text or existing["rule_text"]).strip()
                new_cat = category or existing["category"]
                conn.execute(
                    "UPDATE heuristic_ledger SET rule_text = ?, category = ? WHERE rule_id = ?",
                    (new_text, new_cat, rule_id),
                )
            elif op == "UPVOTE":
                if existing is None:
                    raise KeyError(f"Cannot UPVOTE non-existent rule_id: {rule_id}")
                upvotes = int(existing["upvotes"]) + step
                downvotes = int(existing["downvotes"])
                utility = upvotes - downvotes
                conn.execute(
                    "UPDATE heuristic_ledger SET upvotes = ?, utility_score = ? WHERE rule_id = ?",
                    (upvotes, utility, rule_id),
                )
            elif op == "DOWNVOTE":
                if existing is None:
                    raise KeyError(f"Cannot DOWNVOTE non-existent rule_id: {rule_id}")
                upvotes = int(existing["upvotes"])
                downvotes = int(existing["downvotes"]) + step
                utility = upvotes - downvotes
                new_status = "archived" if utility <= 0 else str(existing["status"])
                conn.execute(
                    "UPDATE heuristic_ledger SET downvotes = ?, utility_score = ?, status = ? WHERE rule_id = ?",
                    (downvotes, utility, new_status, rule_id),
                )
            else:
                raise ValueError(f"Unsupported ExpeL operation: {operation}")

            conn.commit()

        entry = self.get_heuristic_rule(rule_id)
        assert entry is not None

        if sync_markdown:
            self.sync_heuristics_markdown_delta(target_entry=entry)

        return entry

    def sync_heuristics_markdown_delta(
        self,
        target_entry: Optional[HeuristicRuleEntry] = None,
    ) -> int:
        """
        Applies incremental delta updates to `.agents/rules/solana-heuristics.md`,
        preserving YAML frontmatter (`trigger` and `description`) and enforcing
        the <24,000 byte (24 KB) Antigravity rule cap by archiving `utility_score <= 0`
        or lowest-utility rules into `references/archived-heuristics.md`.
        """
        self.heuristics_rule_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.heuristics_rule_path.exists():
            default_header = (
                "---\n"
                "trigger: model_decision\n"
                "description: Evolving playbook of validated Solana memecoin execution heuristics, "
                "Pump.fun bonding curve thresholds, Jito tip rules, and Token-2022 anti-rug invariants "
                "maintained by the ACE Curator.\n"
                "---\n\n"
                "# Validated Solana Memecoin Trading & Anti-Rug Heuristics\n\n"
                "## 1. Execution & Latency Rules (ExpeL Scored)\n\n"
                "## 2. On-Chain Rug & Token-2022 Heuristics\n"
            )
            self.heuristics_rule_path.write_text(default_header, encoding="utf-8")

        content = self.heuristics_rule_path.read_text(encoding="utf-8")

        if target_entry is not None:
            pattern = re.compile(
                rf"^- `\[{re.escape(target_entry.rule_id)}\s*\|[^\]]+\]`.*$",
                re.MULTILINE,
            )
            formatted_line = (
                f"- `[{target_entry.rule_id} | Utility: {target_entry.utility_score:+d} | "
                f"Status: {target_entry.status.upper()}]` {target_entry.rule_text}"
            )

            if target_entry.status == "archived" or target_entry.utility_score <= 0:
                if pattern.search(content):
                    content = pattern.sub("", content)
                    content = re.sub(r"\n{3,}", "\n\n", content)
                self._append_to_archive(target_entry)
            elif target_entry.status == "active":
                if pattern.search(content):
                    content = pattern.sub(lambda _: formatted_line, content)
                else:
                    # Insert incrementally under the matching section header
                    if "EXEC" in target_entry.category.upper() or "LATENCY" in target_entry.category.upper():
                        sec_marker = "## 2. On-Chain Rug & Token-2022 Heuristics"
                        if sec_marker in content:
                            content = content.replace(
                                sec_marker,
                                f"{formatted_line}\n\n{sec_marker}",
                                1,
                            )
                        else:
                            content = content.rstrip() + f"\n{formatted_line}\n"
                    else:
                        content = content.rstrip() + f"\n{formatted_line}\n"

        # Enforce <24 KB hard limit (prune if >= 20 KB or > 24 KB)
        encoded = content.encode("utf-8")
        if len(encoded) >= RULE_FILE_PRUNE_THRESHOLD_BYTES:
            active_rules = self.list_heuristic_rules(status="active")
            # Sort ascending by utility_score so lowest utility rules are archived first
            active_rules.sort(key=lambda r: (r.utility_score, r.rule_id))
            for cand in active_rules:
                if len(content.encode("utf-8")) < RULE_FILE_PRUNE_THRESHOLD_BYTES and cand.utility_score > 0:
                    break
                pat = re.compile(
                    rf"^- `\[{re.escape(cand.rule_id)}\s*\|[^\]]+\]`.*$\n?",
                    re.MULTILINE,
                )
                if pat.search(content):
                    content = pat.sub("", content)
                    with self._connect() as conn:
                        conn.execute(
                            "UPDATE heuristic_ledger SET status = 'archived' WHERE rule_id = ?",
                            (cand.rule_id,),
                        )
                        conn.commit()
                    self._append_to_archive(cand)

        self.heuristics_rule_path.write_text(content, encoding="utf-8")
        return len(content.encode("utf-8"))

    def _append_to_archive(self, entry: HeuristicRuleEntry) -> None:
        self.archived_rules_path.parent.mkdir(parents=True, exist_ok=True)
        header = "# Archived Solana Heuristics Reference\n\n"
        existing = (
            self.archived_rules_path.read_text(encoding="utf-8")
            if self.archived_rules_path.exists()
            else header
        )
        line = (
            f"- `[{entry.rule_id} | Utility: {entry.utility_score:+d} | Status: ARCHIVED]` "
            f"{entry.rule_text}\n"
        )
        if entry.rule_id not in existing:
            updated = existing + line
            if len(updated) > REFERENCE_FILE_MAX_CHARS:
                body = updated[len(header) :] if updated.startswith(header) else updated
                body_lines = body.splitlines(keepends=True)
                budget = max(0, REFERENCE_FILE_MAX_CHARS - len(header))
                kept_lines: List[str] = []
                total_chars = 0
                for b_line in reversed(body_lines):
                    if total_chars + len(b_line) > budget:
                        break
                    kept_lines.append(b_line)
                    total_chars += len(b_line)
                kept_lines.reverse()
                updated = header + "".join(kept_lines)
            self.archived_rules_path.write_text(updated, encoding="utf-8")

    def validate_and_promote_shadow_rule(
        self,
        rule_id: str,
        rule_text: Optional[str] = None,
        category: str = "ONCHAIN_RUG_TOKEN2022",
        target_failure_category: str = "Token-2022/SPL Rug Vector",
        min_trajectories: int = 5,
    ) -> ShadowValidationResult:
        """
        FinMem Train-to-Test Promotion Gate:
          1. Ensures the candidate heuristic is registered in `heuristic_ledger` with `status='shadow'`.
          2. Evaluates the heuristic in `mode='train'` against historical/shadow trajectories in
             `memory/telemetry.db`.
          3. Computes counterfactual PnL improvement (`counterfactual_pnl_delta_sol`) when blocking
             losses matching `target_failure_category`.
          4. Promotes the rule to `status='active'` in `heuristic_ledger` and `.agents/rules/solana-heuristics.md`
             ONLY if `counterfactual_pnl_delta_sol > 0.0` and `evaluated_trajectories >= min_trajectories`.
        """
        existing = self.get_heuristic_rule(rule_id)
        if existing is None:
            if not rule_text:
                raise ValueError(f"Rule {rule_id} not found and no rule_text provided")
            existing = self.apply_expel_operation(
                operation="ADD",
                rule_id=rule_id,
                rule_text=rule_text,
                category=category,
                initial_status="shadow",
                sync_markdown=False,
            )

        with self._connect() as conn:
            train_rows = conn.execute(
                "SELECT * FROM trade_trajectories WHERE mode = 'train'"
            ).fetchall()

        evaluated_count = len(train_rows)
        baseline_pnl = sum(float(r["pnl_sol"]) for r in train_rows)
        baseline_wins = sum(1 for r in train_rows if float(r["pnl_sol"]) > 0.0)

        prevented_count = 0
        counterfactual_pnl = 0.0
        kept_trades = 0
        kept_wins = 0

        for r in train_rows:
            f_cat = str(r["failure_category"])
            pnl = float(r["pnl_sol"])
            meta = json.loads(r["metadata_json"] or "{}")
            matches_rule = (
                f_cat == target_failure_category
                or (
                    "transfer_hook" in existing.rule_text.lower()
                    and (bool(meta.get("transfer_hook")) or f_cat == "Token-2022/SPL Rug Vector")
                )
                or (
                    "graduation" in existing.rule_text.lower()
                    and (96.5 <= float(r["curve_progress_pct"]) <= 100.0 or f_cat == "Graduation Race Condition")
                )
            )
            if matches_rule and pnl < 0.0:
                prevented_count += 1
            else:
                counterfactual_pnl += pnl
                kept_trades += 1
                if pnl > 0.0:
                    kept_wins += 1

        pnl_delta = round(counterfactual_pnl - baseline_pnl, 6)
        base_wr = (baseline_wins / evaluated_count * 100.0) if evaluated_count > 0 else 0.0
        new_wr = (kept_wins / kept_trades * 100.0) if kept_trades > 0 else base_wr
        wr_delta = round(new_wr - base_wr, 2)

        promoted = bool(evaluated_count >= min_trajectories and pnl_delta > 0.0 and prevented_count > 0)
        if promoted:
            if existing.status != "active":
                with self._connect() as conn:
                    new_upvotes = int(existing.upvotes) + prevented_count
                    new_utility = new_upvotes - int(existing.downvotes)
                    conn.execute(
                        "UPDATE heuristic_ledger SET status = 'active', upvotes = ?, utility_score = ? WHERE rule_id = ?",
                        (new_upvotes, new_utility, rule_id),
                    )
                    conn.commit()
            updated_entry = self.get_heuristic_rule(rule_id)
            assert updated_entry is not None
            rule_bytes = self.sync_heuristics_markdown_delta(target_entry=updated_entry)
            return ShadowValidationResult(
                rule_id=rule_id,
                evaluated_trajectories=evaluated_count,
                matched_failures_prevented=prevented_count,
                counterfactual_pnl_delta_sol=pnl_delta,
                win_rate_delta_pct=wr_delta,
                promoted_to_active=True,
                new_status="active",
                utility_score=updated_entry.utility_score,
                rule_file_bytes=rule_bytes,
            )

        rule_bytes = (
            len(self.heuristics_rule_path.read_text(encoding="utf-8").encode("utf-8"))
            if self.heuristics_rule_path.exists()
            else 0
        )
        return ShadowValidationResult(
            rule_id=rule_id,
            evaluated_trajectories=evaluated_count,
            matched_failures_prevented=prevented_count,
            counterfactual_pnl_delta_sol=pnl_delta,
            win_rate_delta_pct=wr_delta,
            promoted_to_active=False,
            new_status=existing.status,
            utility_score=existing.utility_score,
            rule_file_bytes=rule_bytes,
        )
