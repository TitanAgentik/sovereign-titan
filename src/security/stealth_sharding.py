"""Sovereign Titan OS — 25-Wallet Stealth Ring-Buffer & Hourly Counter-Copy Self-Audit (`src/security/stealth_sharding.py`).

Implements:
1. AES-256-GCM encrypted keyring at `~/.hermes/skills/solana-mev-titan/.keystore.enc`
   loaded into `mlock`-pinned RAM containing:
   - `MASTER_TREASURY_KEYPAIR`
   - `RESERVE_LOCKBOX_KEYPAIR`
   - `25 Ephemeral Stealth Execution Shards` (`shard_00` .. `shard_24`)
2. Shard rotation every `8–10` profitable directional trades using randomized multi-hop funding splits.
3. Hourly Counter-Copy Self-Audit (`run_hourly_counter_copy_self_audit`):
   Passes all 25 of our own shards through `LeadLagDiscoveryEngine` (`discovery_lead_lag.py`).
   If any shard picks up `>= 2` external copy-bots, marks it `COMPROMISED`, sweeps its SOL to
   a freshly generated keypair, and optionally flags the old address as a `COUNTER_BAIT_WALLET`
   for Engine B.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import random
import time
from typing import Any, Dict, List, Literal, Optional, Sequence

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import orjson
from solders.keypair import Keypair

from src.config.settings import Settings, get_settings
from src.discovery.discovery_lead_lag import (
    CandidateWalletMetrics,
    LeadLagDiscoveryEngine,
    SwapObservationRecord,
)


SHARD_COUNT = 25
ShardStatus = Literal[
    "ACTIVE",
    "ACTIVE_HOT",
    "STANDBY_RENT_SAVER",
    "COMPROMISED",
    "COUNTER_BAIT_WALLET",
]


def compute_optimal_active_shard_count(total_equity_sol: float) -> int:
    """Capital-Aware Shard Scaling:
    - `< 25.0 SOL`: `3` active hot shards (`22` standby) -> saves ~`0.269 SOL` in idle ATA rent
    - `25.0–99.9 SOL`: `8` active hot shards (`17` standby)
    - `>= 100.0 SOL`: full `25` active hot shards (`0` standby)
    """
    eq = max(0.0, float(total_equity_sol))
    if eq < 25.0:
        return 3
    if eq < 100.0:
        return 8
    return 25


@dataclass
class StealthShardEntry:
    shard_index: int
    pubkey: str
    secret_bytes: bytes
    status: ShardStatus = "ACTIVE"
    profitable_trades_count: int = 0
    rotation_threshold_trades: int = 9  # Randomized within [8, 10]
    sol_balance: float = 1.0
    detected_external_copy_bots: int = 0

    @property
    def shard_id(self) -> int:
        return self.shard_index

    def to_keypair(self) -> Keypair:
        return Keypair.from_bytes(self.secret_bytes)


@dataclass
class ShardRotationEvent:
    old_shard_index: int
    old_pubkey: str
    new_shard_index: int
    new_pubkey: str
    reason: Literal["TRADE_COUNT_ROTATION_8_TO_10", "COMPROMISED_BY_COPY_BOTS"]
    hop_splits_sol: List[float]
    intermediate_hops: int


@dataclass
class CounterCopySelfAuditReport:
    audited_shards: int
    compromised_shards: List[str] = field(default_factory=list)
    counter_bait_wallets: List[str] = field(default_factory=list)
    replacement_pubkeys: List[str] = field(default_factory=list)
    rotations: List[ShardRotationEvent] = field(default_factory=list)


class StealthShardRingManager:
    """Manages the AES-256-GCM encrypted 25-wallet stealth ring buffer in `mlock` RAM."""

    DEFAULT_KEYSTORE_PATH = (
        Path.home() / ".hermes" / "skills" / "solana-mev-titan" / ".keystore.enc"
    )
    DEFAULT_PASSPHRASE = "SOVEREIGN_TITAN_BLACKWELL_9995WX_KEYRING"

    def __init__(
        self,
        config: Optional[Settings] = None,
        keystore_path: Optional[Path] = None,
        passphrase: str = "SOVEREIGN_TITAN_BLACKWELL_9995WX_KEYRING",
        use_os_entropy: bool = False,
    ) -> None:
        self.settings = config or get_settings()
        self.keystore_path: Path = keystore_path or self.DEFAULT_KEYSTORE_PATH
        if passphrase == self.DEFAULT_PASSPHRASE:
            resolved_passphrase = os.environ.get(
                "TITAN_KEYSTORE_PASSPHRASE", self.settings.TITAN_KEYSTORE_PASSPHRASE
            )
        else:
            resolved_passphrase = passphrase
        self.passphrase: str = resolved_passphrase
        self._aes_key: bytes = hashlib.sha256(
            resolved_passphrase.encode("utf-8")
        ).digest()  # 256-bit key

        self.use_os_entropy: bool = bool(
            use_os_entropy or self.settings.LIVE_MAINNET_BROADCAST_ENABLED
        )
        self._rng: random.Random = (
            random.SystemRandom() if self.use_os_entropy else random.Random(20261026)
        )

        self.master_treasury_kp: Keypair = Keypair()
        self.reserve_lockbox_kp: Keypair = Keypair()
        self.shards: List[StealthShardEntry] = []
        self.active_cursor: int = 0
        self.active_scaled_shard_count: int = SHARD_COUNT
        self.counter_bait_wallets: Dict[str, StealthShardEntry] = {}

        self._mlock_buffer: Optional[ctypes.Array[ctypes.c_char]] = None
        self.mlock_active: bool = False

    def initialize_and_encrypt_keystore(self, force_regenerate: bool = False) -> Path:
        """Generates `MASTER_TREASURY_KEYPAIR`, `RESERVE_LOCKBOX_KEYPAIR`, and 25 Ephemeral Stealth
        Execution Shards, encrypts with AES-256-GCM to `~/.hermes/skills/solana-mev-titan/.keystore.enc`,
        and pins decrypted secret bytes into RAM using `mlock`.
        If `.keystore.enc` already exists on disk and `force_regenerate` is False, loads and preserves
        the existing keys so live Mainnet wallets are never overwritten.
        """
        if not force_regenerate and self.keystore_path.exists():
            if self.load_existing_keystore():
                return self.keystore_path

        self.master_treasury_kp = Keypair()
        self.reserve_lockbox_kp = Keypair()
        self.shards = []

        for idx in range(SHARD_COUNT):
            kp = Keypair()
            self.shards.append(
                StealthShardEntry(
                    shard_index=idx,
                    pubkey=str(kp.pubkey()),
                    secret_bytes=bytes(kp),
                    status="ACTIVE",
                    profitable_trades_count=0,
                    rotation_threshold_trades=self._rng.randint(8, 10),
                    sol_balance=round(
                        self.settings.INITIAL_PAPER_SOL / float(SHARD_COUNT), 4
                    ),
                )
            )

        self._save_encrypted_keystore()
        self._pin_memory_mlock()
        return self.keystore_path

    def _save_encrypted_keystore(self) -> None:
        self.keystore_path.parent.mkdir(parents=True, exist_ok=True)
        shard_records = [
            {
                "shard_index": s.shard_index,
                "pubkey": s.pubkey,
                "secret_hex": s.secret_bytes.hex(),
                "secret_bytes": list(s.secret_bytes),
                "status": s.status,
                "profitable_trades_count": s.profitable_trades_count,
                "rotation_threshold_trades": s.rotation_threshold_trades,
                "sol_balance": s.sol_balance,
                "detected_external_copy_bots": s.detected_external_copy_bots,
            }
            for s in self.shards
        ]
        plaintext_obj = {
            "version": 1,
            "created_at_epoch_s": time.time(),
            "master_treasury_pubkey": str(self.master_treasury_kp.pubkey()),
            "master_treasury_secret_hex": bytes(self.master_treasury_kp).hex(),
            "reserve_lockbox_pubkey": str(self.reserve_lockbox_kp.pubkey()),
            "reserve_lockbox_secret_hex": bytes(self.reserve_lockbox_kp).hex(),
            "MASTER_TREASURY_KEYPAIR": list(bytes(self.master_treasury_kp)),
            "RESERVE_LOCKBOX_KEYPAIR": list(bytes(self.reserve_lockbox_kp)),
            "shards": shard_records,
            "STEALTH_SHARDS": shard_records,
        }
        plaintext_bytes = orjson.dumps(plaintext_obj)
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._aes_key)
        ciphertext = aesgcm.encrypt(
            nonce, plaintext_bytes, b"SOVEREIGN_TITAN_KEYSTORE_V1"
        )
        envelope = orjson.dumps(
            {
                "cipher": "AES-256-GCM",
                "nonce_hex": nonce.hex(),
                "ciphertext_hex": ciphertext.hex(),
            }
        )
        self.keystore_path.write_bytes(envelope)
        os.chmod(self.keystore_path, 0o600)

    def decrypt_and_verify_keystore(self) -> Dict[str, Any]:
        """Decrypts and verifies `.keystore.enc` via AES-256-GCM and normalizes the payload schema."""
        envelope = orjson.loads(self.keystore_path.read_bytes())
        nonce = bytes.fromhex(envelope["nonce_hex"])
        ciphertext = bytes.fromhex(envelope["ciphertext_hex"])
        aesgcm = AESGCM(self._aes_key)
        plaintext_bytes = aesgcm.decrypt(
            nonce, ciphertext, b"SOVEREIGN_TITAN_KEYSTORE_V1"
        )
        payload: Dict[str, Any] = orjson.loads(plaintext_bytes)

        if (
            "master_treasury_secret_hex" not in payload
            and "MASTER_TREASURY_KEYPAIR" in payload
        ):
            payload["master_treasury_secret_hex"] = bytes(
                payload["MASTER_TREASURY_KEYPAIR"]
            ).hex()
        if (
            "reserve_lockbox_secret_hex" not in payload
            and "RESERVE_LOCKBOX_KEYPAIR" in payload
        ):
            payload["reserve_lockbox_secret_hex"] = bytes(
                payload["RESERVE_LOCKBOX_KEYPAIR"]
            ).hex()
        if "shards" not in payload and "STEALTH_SHARDS" in payload:
            payload["shards"] = payload["STEALTH_SHARDS"]

        return payload

    def load_existing_keystore(self) -> bool:
        """Loads and decrypts an existing `.keystore.enc` without overwriting keys. Returns `True` on success."""
        if not self.keystore_path.exists():
            return False

        try:
            payload = self.decrypt_and_verify_keystore()
            self.master_treasury_kp = Keypair.from_bytes(
                bytes.fromhex(payload["master_treasury_secret_hex"])
            )
            self.reserve_lockbox_kp = Keypair.from_bytes(
                bytes.fromhex(payload["reserve_lockbox_secret_hex"])
            )
            reconstructed: List[StealthShardEntry] = []
            for item in payload["shards"]:
                if "secret_bytes" in item and isinstance(item["secret_bytes"], list):
                    raw_secret = bytes(item["secret_bytes"])
                elif "secret_hex" in item:
                    raw_secret = bytes.fromhex(item["secret_hex"])
                else:
                    raw_secret = bytes(item["secret_bytes"])

                reconstructed.append(
                    StealthShardEntry(
                        shard_index=int(item["shard_index"]),
                        pubkey=str(item["pubkey"]),
                        secret_bytes=raw_secret,
                        status=item.get("status", "ACTIVE"),
                        profitable_trades_count=int(
                            item.get("profitable_trades_count", 0)
                        ),
                        rotation_threshold_trades=int(
                            item.get(
                                "rotation_threshold_trades",
                                self._rng.randint(8, 10),
                            )
                        ),
                        sol_balance=float(
                            item.get(
                                "sol_balance",
                                round(
                                    self.settings.INITIAL_PAPER_SOL / float(SHARD_COUNT),
                                    4,
                                ),
                            )
                        ),
                        detected_external_copy_bots=int(
                            item.get("detected_external_copy_bots", 0)
                        ),
                    )
                )
            self.shards = reconstructed
            self._pin_memory_mlock()
            return True
        except Exception:
            return False

    def load_or_initialize_keystore(self) -> Path:
        """Loads existing `.keystore.enc` if present; otherwise generates and encrypts a new keystore."""
        if self.load_existing_keystore():
            return self.keystore_path
        return self.initialize_and_encrypt_keystore()

    def load_and_decrypt_keystore(self) -> None:
        """Loads and decrypts `~/.hermes/skills/solana-mev-titan/.keystore.enc` and pins into `mlock` RAM."""
        self.load_or_initialize_keystore()

    def _pin_memory_mlock(self, raw_bytes: Optional[bytes] = None) -> bool:
        """Pins all 27 keypairs (Treasury + Lockbox + 25 Shards = 1,728 bytes) in physical RAM via `libc.mlock`."""
        if raw_bytes is None:
            concatenated = bytearray()
            concatenated.extend(bytes(self.master_treasury_kp))
            concatenated.extend(bytes(self.reserve_lockbox_kp))
            for s in self.shards:
                concatenated.extend(s.secret_bytes)
            raw_bytes = bytes(concatenated)

        buf = ctypes.create_string_buffer(raw_bytes, len(raw_bytes))
        self._mlock_buffer = buf
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            res = libc.mlock(ctypes.byref(buf), ctypes.c_size_t(len(raw_bytes)))
            self.mlock_active = (res == 0)
        except Exception:
            self.mlock_active = False
        return self.mlock_active

    def _pin_secrets_in_mlock_ram(self) -> None:
        self._pin_memory_mlock()

    def export_public_addresses_manifest(self) -> Dict[str, Any]:
        """Exports the public address manifest for Master Treasury, Reserve Lockbox, and all 25 Shards."""
        if not self.shards:
            self.load_or_initialize_keystore()
        return {
            "master_treasury_pubkey": str(self.master_treasury_kp.pubkey()),
            "reserve_lockbox_pubkey": str(self.reserve_lockbox_kp.pubkey()),
            "shard_count": len(self.shards),
            "shards": [
                {
                    "shard_index": s.shard_index,
                    "pubkey": s.pubkey,
                    "status": s.status,
                    "sol_balance": s.sol_balance,
                }
                for s in self.shards
            ],
            "keystore_path": str(self.keystore_path),
            "mlock_active": self.mlock_active,
        }

    def apply_capital_aware_shard_scaling(
        self, total_equity_sol: float
    ) -> Dict[str, Any]:
        """Scales active hot shards by live equity (`<25 SOL -> 3`, `25–99.9 SOL -> 8`,
        `>=100 SOL -> 25`) while preserving all 25 keypairs in `.keystore.enc`.
        """
        if not self.shards:
            self.load_or_initialize_keystore()
        target_active = compute_optimal_active_shard_count(total_equity_sol)
        self.active_scaled_shard_count = target_active
        for idx, shard in enumerate(self.shards):
            if shard.status in ("COMPROMISED", "COUNTER_BAIT_WALLET"):
                continue
            shard.status = "ACTIVE_HOT" if idx < target_active else "STANDBY_RENT_SAVER"
        standby_count = max(0, len(self.shards) - target_active)
        ata_rent_saved_sol = round(standby_count * 6 * 0.00203928, 4)
        return {
            "total_shards": len(self.shards),
            "active_hot_shards": target_active,
            "active_hot_shards_count": target_active,
            "standby_rent_saver_shards": standby_count,
            "standby_rent_saver_shards_count": standby_count,
            "ata_rent_saved_sol": ata_rent_saved_sol,
        }

    def get_current_active_shard(self) -> StealthShardEntry:
        if not self.shards:
            self.load_or_initialize_keystore()
        active_hot_pool = [s for s in self.shards if s.status == "ACTIVE_HOT"]
        if active_hot_pool:
            return active_hot_pool[self.active_cursor % len(active_hot_pool)]
        return self.shards[self.active_cursor % len(self.shards)]

    def select_Random_Execution_Shard(
        self, total_equity_sol: Optional[float] = None
    ) -> StealthShardEntry:
        """Selects a random execution shard strictly from active hot shards (`ACTIVE_HOT`),
        falling back to `ACTIVE` shards if capital scaling has not been applied.
        """
        if not self.shards:
            self.load_or_initialize_keystore()
        if total_equity_sol is not None:
            self.apply_capital_aware_shard_scaling(total_equity_sol)
        active_hot_pool = [s for s in self.shards if s.status == "ACTIVE_HOT"]
        if active_hot_pool:
            return self._rng.choice(active_hot_pool)
        active_pool = [s for s in self.shards if s.status in ("ACTIVE", "ACTIVE_HOT")]
        if active_pool:
            return self._rng.choice(active_pool)
        return self._rng.choice(self.shards)

    select_random_execution_shard = select_Random_Execution_Shard

    def plan_three_hop_sweep(self, total_sweep: float) -> List[float]:
        """Computes a randomized 3-part multi-hop funding split whose sum equals `round(total_sweep, 6)`."""
        w1 = self._rng.uniform(0.25, 0.45)
        w2 = self._rng.uniform(0.25, 0.40)
        split1 = round(total_sweep * w1, 6)
        split2 = round(total_sweep * w2, 6)
        split3 = round(total_sweep - split1 - split2, 6)
        return [split1, split2, split3]

    def record_profitable_directional_trade(
        self, profit_sol: float = 0.25
    ) -> Optional[ShardRotationEvent]:
        """Increments trade count on the active shard and rotates to the next shard every 8–10
        profitable directional trades using randomized multi-hop funding splits.
        """
        shard = self.get_current_active_shard()
        shard.profitable_trades_count += 1
        shard.sol_balance = round(shard.sol_balance + profit_sol, 6)

        if shard.profitable_trades_count >= shard.rotation_threshold_trades:
            old_idx = shard.shard_index
            old_pk = shard.pubkey
            shard.profitable_trades_count = 0
            shard.rotation_threshold_trades = self._rng.randint(8, 10)

            self.active_cursor = (self.active_cursor + 1) % len(self.shards)
            next_shard = self.shards[self.active_cursor]

            total_sweep = shard.sol_balance
            splits = self.plan_three_hop_sweep(total_sweep)
            next_shard.sol_balance = round(next_shard.sol_balance + total_sweep, 6)
            shard.sol_balance = 0.0
            self._save_encrypted_keystore()

            return ShardRotationEvent(
                old_shard_index=old_idx,
                old_pubkey=old_pk,
                new_shard_index=next_shard.shard_index,
                new_pubkey=next_shard.pubkey,
                reason="TRADE_COUNT_ROTATION_8_TO_10",
                hop_splits_sol=splits,
                intermediate_hops=2,
            )
        return None

    # --------------------------------------------------------------------------
    # Hourly Counter-Copy Self-Audit via `discovery_lead_lag.py`
    # --------------------------------------------------------------------------
    def run_hourly_counter_copy_self_audit(
        self,
        swap_observations: Sequence[SwapObservationRecord],
        flag_as_counter_bait: bool = True,
    ) -> CounterCopySelfAuditReport:
        """Passes all 25 of our own stealth shards through `LeadLagDiscoveryEngine`:
        If any shard picks up `>= 2` external copy-bots (`fast_bot_followers + slow_retail_followers >= 2`),
        marks it `COMPROMISED`, sweeps its SOL to a freshly generated keypair, and optionally flags
        the old wallet as a `COUNTER_BAIT_WALLET` for Engine B.
        """
        if not self.shards:
            self.load_and_decrypt_keystore()

        candidates = [
            CandidateWalletMetrics(
                wallet=s.pubkey,
                win_rate_30d=0.62,
                profit_factor_30d=3.2,
                realized_pnl_30d_usd=35_000.0,
                trades_30d=25,
                zero_to_two_slot_entry_ratio=0.10,
                median_entry_mc_usd=85_000.0,
            )
            for s in self.shards
        ]

        engine = LeadLagDiscoveryEngine(self.settings)
        try:
            engine.ingest_candidates_and_swaps(candidates, swap_observations)
            audit_results = engine.run_latency_split_audit(candidates)
        finally:
            engine.close()

        audit_by_wallet = {r.wallet: r for r in audit_results}
        report = CounterCopySelfAuditReport(audited_shards=len(self.shards))

        for idx, shard in enumerate(self.shards):
            res = audit_by_wallet.get(shard.pubkey)
            if res is None:
                continue
            total_followers = res.fast_bot_followers + res.slow_retail_followers
            shard.detected_external_copy_bots = total_followers

            if total_followers >= 2:
                old_pubkey = shard.pubkey
                swept_sol = shard.sol_balance
                shard.status = (
                    "COUNTER_BAIT_WALLET" if flag_as_counter_bait else "COMPROMISED"
                )
                report.compromised_shards.append(old_pubkey)
                if flag_as_counter_bait:
                    report.counter_bait_wallets.append(old_pubkey)
                    self.counter_bait_wallets[old_pubkey] = shard

                # Generate a brand-new replacement stealth shard keypair and sweep SOL via multi-hop split
                fresh_kp = Keypair()
                fresh_pk = str(fresh_kp.pubkey())
                replacement = StealthShardEntry(
                    shard_index=idx,
                    pubkey=fresh_pk,
                    secret_bytes=bytes(fresh_kp),
                    status="ACTIVE",
                    profitable_trades_count=0,
                    rotation_threshold_trades=self._rng.randint(8, 10),
                    sol_balance=swept_sol,
                    detected_external_copy_bots=0,
                )
                self.shards[idx] = replacement
                report.replacement_pubkeys.append(fresh_pk)
                report.rotations.append(
                    ShardRotationEvent(
                        old_shard_index=idx,
                        old_pubkey=old_pubkey,
                        new_shard_index=idx,
                        new_pubkey=fresh_pk,
                        reason="COMPROMISED_BY_COPY_BOTS",
                        hop_splits_sol=[
                            round(swept_sol * 0.45, 6),
                            round(swept_sol * 0.55, 6),
                        ],
                        intermediate_hops=2,
                    )
                )

        if report.compromised_shards:
            self._save_encrypted_keystore()
            self._pin_secrets_in_mlock_ram()

        return report


StealthWalletSharding = StealthShardRingManager
NUM_STEALTH_SHARDS = SHARD_COUNT

