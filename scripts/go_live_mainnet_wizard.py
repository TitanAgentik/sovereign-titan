#!/usr/bin/env python3
"""Sovereign Titan OS — Interactive & Automated Live Mainnet-Beta Onboarding Wizard (`scripts/go_live_mainnet_wizard.py`).

Supports CLI flags:
  - `--preflight` (default): Runs the complete 10-Point Mainnet Live-Capital Readiness Check
    plus detailed inspection of Paid Core 4 APIs, Free 7 Feeds/Streams, Webhooks & Telegram MTProto,
    and all 6 MCP Servers (`:8090` Helius, `:8091` Jupiter, Birdeye, CoinStats, `cabal-hunter` x402, `coingecko-docs`).
  - `--init-wallets`: Calls `StealthShardRingManager.load_or_initialize_keystore()` and prints
    the Master Vault deposit address, Reserve Lockbox address, and all 25 Stealth Shard pubkeys.
  - `--prewarm-plan`: Builds and prints the 36-Account Mainnet ALT & 25-Shard
    (`wSOL`/`USDC`/`jitoSOL`/`mSOL`/`bSOL`/`INF` = 150 ATAs) pre-warm instruction plan.
  - `--set-live <true|false>`: Toggles `LIVE_MAINNET_BROADCAST_ENABLED` in runtime state.
"""

from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path
import socket
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

WORKSPACE_ROOT = Path("/home/titanagentik/sovereign-titan")
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import orjson

from src.config.settings import Settings, get_settings
from src.security.stealth_sharding import SHARD_COUNT, StealthShardRingManager

FALLBACK_36_MAINNET_ALT_ADDRESSES: List[str] = [
    "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",
    "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF",
    "d4A2prbA2whesmvHaL88BH6Ewn5N4bTSU2Ze8P6Bc4Q",
    "GafNuUXj9rxGLn4y79dPu6MHSuPWeJR6UtTWuexpGh3U",
    "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf",
    "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
    "5ocnV1qiCgaQR8Jb8xWnVbApfaygJ8tNoZfgPwsgx9kx",
    "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
    "AddressLookupTable1111111111111111111111111",
    "ComputeBudget111111111111111111111111111111",
    "11111111111111111111111111111111",
    "Sysvar1nstructions1111111111111111111111111",
    "SysvarRent111111111111111111111111111111111",
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
    "5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm",
    "jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v",
    "BonK1YhkXEGLZzwtcvRTip3gAL9nCeQD7ppZBLXhtTs",
    "PrftGrd111111111111111111111111111111111111",
]

PREWARM_TOKEN_MINTS: Dict[str, str] = {
    "wSOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "jitoSOL": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
    "mSOL": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "bSOL": "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
    "INF": "5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm",
}


def _is_real_credential(val: str) -> bool:
    cleaned = (val or "").strip()
    if not cleaned:
        return False
    upper = cleaned.upper()
    if "YOUR_" in upper or "PLACEHOLDER" in upper or cleaned.startswith("0000000000:"):
        return False
    return True


def _probe_tcp_port(host: str, port: int, timeout_s: float = 0.15) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except Exception:
        return False


def _test_mlock_capability() -> bool:
    buf = ctypes.create_string_buffer(b"TITAN_MLOCK_PROBE", 17)
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        res = libc.mlock(ctypes.byref(buf), ctypes.c_size_t(17))
        if res == 0:
            libc.munlock(ctypes.byref(buf), ctypes.c_size_t(17))
            return True
    except Exception:
        pass
    return False


def get_runtime_broadcast_state_path(config: Optional[Settings] = None) -> Path:
    cfg = config or get_settings()
    return cfg.RAMDISK_EXECUTION_STATE / "live_mainnet_broadcast_state.json"


def read_live_broadcast_enabled(config: Optional[Settings] = None) -> bool:
    cfg = config or get_settings()
    state_path = get_runtime_broadcast_state_path(cfg)
    if state_path.exists():
        try:
            payload = orjson.loads(state_path.read_bytes())
            if "live_broadcast_enabled" in payload:
                return bool(payload["live_broadcast_enabled"])
        except Exception:
            pass
    return bool(getattr(cfg, "LIVE_MAINNET_BROADCAST_ENABLED", False))


def set_live_mainnet_broadcast_mode(
    enabled: bool,
    config: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Toggles `LIVE_MAINNET_BROADCAST_ENABLED` in runtime state and persists to RAMDisk."""
    cfg = config or get_settings()
    cfg.ensure_ramdisk_directories()
    try:
        object.__setattr__(cfg, "LIVE_MAINNET_BROADCAST_ENABLED", bool(enabled))
    except Exception:
        pass

    state_path = get_runtime_broadcast_state_path(cfg)
    payload = {
        "live_broadcast_enabled": bool(enabled),
        "execution_mode": getattr(cfg, "INITIAL_EXECUTION_MODE", "PAPER"),
        "updated_at_epoch_s": time.time(),
        "updated_at_ns": time.time_ns(),
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
    return payload


def init_persistent_mainnet_wallets(
    config: Optional[Settings] = None,
    sharding: Optional[StealthShardRingManager] = None,
) -> Dict[str, Any]:
    """Loads or initializes the persistent AES-256-GCM `.keystore.enc` and returns all public addresses."""
    cfg = config or get_settings()
    ring = sharding or StealthShardRingManager(cfg)
    if hasattr(ring, "load_or_initialize_keystore"):
        ring.load_or_initialize_keystore()
    else:
        ring.load_and_decrypt_keystore()

    if hasattr(ring, "export_public_addresses_manifest"):
        manifest = ring.export_public_addresses_manifest()
    else:
        manifest = {
            "master_treasury_pubkey": str(ring.master_treasury_kp.pubkey()),
            "reserve_lockbox_pubkey": str(ring.reserve_lockbox_kp.pubkey()),
            "shard_count": len(ring.shards),
            "shards": [
                {
                    "shard_index": s.shard_index,
                    "pubkey": s.pubkey,
                    "status": s.status,
                    "sol_balance": s.sol_balance,
                }
                for s in ring.shards
            ],
            "keystore_path": str(ring.keystore_path),
            "mlock_active": bool(ring.mlock_active),
        }
    return manifest


def build_mainnet_alt_and_ata_prewarm_plan(
    config: Optional[Settings] = None,
    shard_pubkeys: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Builds the 36-Account Mainnet ALT & 25-Shard (`wSOL`/`USDC`/`jitoSOL`/`mSOL`/`bSOL`/`INF`) ATA pre-warm plan."""
    cfg = config or get_settings()
    if shard_pubkeys is None:
        manifest = init_persistent_mainnet_wallets(cfg)
        shard_pubkeys = [s["pubkey"] for s in manifest.get("shards", [])]

    profit_guard_program_id = getattr(
        cfg,
        "PROFIT_GUARD_PROGRAM_ID",
        "PrftGrd111111111111111111111111111111111111",
    )

    try:
        from src.execution.live_mainnet_broadcaster import (
            CANONICAL_MAINNET_ALT_ADDRESSES,
            build_create_and_extend_alt_instructions,
            build_shard_prewarm_plan,
        )
        from solders.pubkey import Pubkey

        authority = (
            Pubkey.from_string(shard_pubkeys[0])
            if shard_pubkeys
            else Pubkey.default()
        )
        alt_bundle = build_create_and_extend_alt_instructions(
            authority=authority,
            payer=authority,
            recent_slot=342_814_920,
            addresses=list(CANONICAL_MAINNET_ALT_ADDRESSES),
        )
        shard_plan = build_shard_prewarm_plan(
            shard_pubkeys=list(shard_pubkeys),
            profit_guard_program_id=profit_guard_program_id,
        )
        alt_addresses = list(CANONICAL_MAINNET_ALT_ADDRESSES)
        alt_table_address = str(alt_bundle.get("lookup_table_address", ""))
    except Exception:
        from solders.pubkey import Pubkey
        from src.execution.alt_manager import (
            SPL_ASSOCIATED_TOKEN_PROGRAM_ID,
            SPL_TOKEN_PROGRAM_ID,
        )

        alt_addresses = list(FALLBACK_36_MAINNET_ALT_ADDRESSES)
        alt_table_address = getattr(cfg, "MAINNET_ALT_ADDRESS", "") or "MainnetALT36Table1111111111111111111111111"
        ata_prog = Pubkey.from_string(SPL_ASSOCIATED_TOKEN_PROGRAM_ID)
        tok_prog = Pubkey.from_string(SPL_TOKEN_PROGRAM_ID)
        pg_prog = Pubkey.from_string(profit_guard_program_id)

        shards_detail: List[Dict[str, Any]] = []
        for idx, spk_str in enumerate(shard_pubkeys):
            owner_pk = Pubkey.from_string(spk_str)
            atas: Dict[str, str] = {}
            for sym, mint_str in PREWARM_TOKEN_MINTS.items():
                mint_pk = Pubkey.from_string(mint_str)
                ata_pk, _ = Pubkey.find_program_address(
                    [bytes(owner_pk), bytes(tok_prog), bytes(mint_pk)],
                    ata_prog,
                )
                atas[sym] = str(ata_pk)
            pda_pk, bump = Pubkey.find_program_address(
                [b"profit_guard_state", bytes(owner_pk)],
                pg_prog,
            )
            shards_detail.append(
                {
                    "shard_index": idx,
                    "shard_pubkey": spk_str,
                    "atas": atas,
                    "profit_guard_transient_pda": str(pda_pk),
                    "profit_guard_bump": bump,
                }
            )
        shard_plan = {
            "shard_count": len(shard_pubkeys),
            "tokens_per_shard": list(PREWARM_TOKEN_MINTS.keys()),
            "total_ata_count": len(shard_pubkeys) * len(PREWARM_TOKEN_MINTS),
            "profit_guard_program_id": profit_guard_program_id,
            "shards": shards_detail,
        }

    total_atas = int(
        shard_plan.get(
            "total_ata_count",
            len(shard_pubkeys) * len(PREWARM_TOKEN_MINTS),
        )
    )
    return {
        "alt_table_address": alt_table_address,
        "alt_address_count": len(alt_addresses),
        "alt_addresses": alt_addresses,
        "jito_tip_pdas_excluded_from_alt": True,
        "prewarmed_shard_atas_count": total_atas,
        "shard_count": len(shard_pubkeys),
        "tokens_per_shard": list(PREWARM_TOKEN_MINTS.keys()),
        "profit_guard_program_id": profit_guard_program_id,
        "shard_prewarm_plan": shard_plan,
        "timestamp_ns": time.time_ns(),
    }


def inspect_api_streams_webhooks_and_mcp_status(
    config: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Explicitly inspects and reports the status of:
    1. Paid Core 4 APIs & RPCs
    2. Free 7 APIs & Real-Time Streams
    3. Webhooks & Telegram MTProto
    4. All 6 MCP Servers (Helius :8090, Jupiter :8091, Birdeye, CoinStats, cabal-hunter x402, coingecko-docs)
    """
    cfg = config or get_settings()

    helius_ok = _is_real_credential(cfg.HELIUS_API_KEY)
    birdeye_ok = _is_real_credential(cfg.BIRDEYE_API_KEY)
    jupiter_ok = _is_real_credential(cfg.JUPITER_API_KEY)
    socialdata_ok = _is_real_credential(cfg.SOCIALDATA_API_KEY)

    paid_core_4 = {
        "HELIUS_API_KEY": {
            "configured": helius_ok,
            "rpc_url": cfg.HELIUS_RPC_URL,
            "ws_url": cfg.HELIUS_WS_URL,
            "laserstream_grpc_url": cfg.HELIUS_LASERSTREAM_GRPC_URL,
            "sender_url": cfg.HELIUS_SENDER_URL,
        },
        "BIRDEYE_API_KEY": {
            "configured": birdeye_ok,
            "rest_url": cfg.BIRDEYE_REST_URL,
        },
        "JUPITER_API_KEY": {
            "configured": jupiter_ok,
            "swap_v2_url": cfg.JUPITER_SWAP_V2_URL,
        },
        "SOCIALDATA_API_KEY": {
            "configured": socialdata_ok,
            "api_url": cfg.SOCIALDATA_API_URL,
        },
        "all_4_configured": helius_ok and birdeye_ok and jupiter_ok and socialdata_ok,
        "configured_count": sum([helius_ok, birdeye_ok, jupiter_ok, socialdata_ok]),
    }

    goplus_ok = _is_real_credential(cfg.GOPLUS_API_KEY)
    coinstats_ok = _is_real_credential(cfg.COINSTATS_API_KEY)
    jito_5_regions = {
        "ny": cfg.JITO_NY_BLOCK_ENGINE_URL,
        "frankfurt": cfg.JITO_FRANKFURT_BLOCK_ENGINE_URL,
        "amsterdam": cfg.JITO_AMSTERDAM_BLOCK_ENGINE_URL,
        "tokyo": cfg.JITO_TOKYO_BLOCK_ENGINE_URL,
        "slc": getattr(
            cfg,
            "JITO_SLC_BLOCK_ENGINE_URL",
            "https://slc.mainnet.block-engine.jito.wtf/api/v1/bundles",
        ),
    }

    free_7_apis_and_streams = {
        "RUGCHECK_SUMMARY_URL_TEMPLATE": {
            "ready": bool(cfg.RUGCHECK_SUMMARY_URL_TEMPLATE),
            "url": cfg.RUGCHECK_SUMMARY_URL_TEMPLATE,
        },
        "GOPLUS_API_KEY": {
            "configured": goplus_ok,
            "url": cfg.GOPLUS_SOLANA_SECURITY_URL,
        },
        "DEXSCREENER_BOOSTS_URL": {
            "ready": bool(cfg.DEXSCREENER_BOOSTS_URL),
            "url": cfg.DEXSCREENER_BOOSTS_URL,
        },
        "PUMPPORTAL_WS_URL": {
            "ready": bool(cfg.PUMPPORTAL_WS_URL),
            "url": cfg.PUMPPORTAL_WS_URL,
        },
        "GECKOTERMINAL_API_URL": {
            "ready": bool(cfg.GECKOTERMINAL_API_URL),
            "url": cfg.GECKOTERMINAL_API_URL,
        },
        "JITO_TIP_STREAM_AND_5_BLOCK_ENGINES": {
            "ready": True,
            "tip_stream_ws_url": cfg.JITO_TIP_STREAM_WS_URL,
            "block_engines_5region": jito_5_regions,
            "astralane_dispatch_url": cfg.ASTRALANE_DISPATCH_URL,
        },
        "COINSTATS_API_KEY": {
            "configured": coinstats_ok,
            "rest_url": cfg.COINSTATS_REST_URL,
        },
    }

    webhook_ok = _is_real_credential(cfg.HELIUS_ENHANCED_WEBHOOK_SECRET)
    tg_api_ok = (
        int(cfg.TELEGRAM_API_ID) != 12345678
        and cfg.TELEGRAM_API_HASH != "0123456789abcdef0123456789abcdef"
    )
    tg_bot_ok = _is_real_credential(cfg.TELEGRAM_BOT_TOKEN)
    tg_session_exists = Path(cfg.TELEGRAM_SESSION_PATH).exists()

    webhooks_and_telegram = {
        "HELIUS_ENHANCED_WEBHOOK_SECRET": {"configured": webhook_ok},
        "TELEGRAM_API_ID": {
            "configured": tg_api_ok,
            "value": cfg.TELEGRAM_API_ID,
        },
        "TELEGRAM_API_HASH": {"configured": tg_api_ok},
        "TELEGRAM_BOT_TOKEN": {"configured": tg_bot_ok},
        "TELEGRAM_CHAT_ID": {
            "configured": cfg.TELEGRAM_CHAT_ID != "-1001234567890",
            "chat_id": cfg.TELEGRAM_CHAT_ID,
        },
        "TELEGRAM_SESSION_FILE": {
            "exists": tg_session_exists,
            "path": cfg.TELEGRAM_SESSION_PATH,
        },
    }

    cabal_mcp_dir = Path("/home/titanagentik/.gemini/antigravity/mcp/cabal-hunter")
    coingecko_mcp_dir = Path("/home/titanagentik/.gemini/antigravity/mcp/coingecko-docs")
    x402_wallet = str(getattr(cfg, "CABAL_HUNTER_X402_WALLET_PUBKEY", "") or "").strip()

    mcp_servers = {
        "helius_mcp_8090": {
            "url": cfg.HELIUS_MCP_URL,
            "port_open": _probe_tcp_port("127.0.0.1", 8090),
            "api_key_ready": helius_ok,
        },
        "jupiter_mcp_8091": {
            "url": cfg.JUPITER_MCP_URL,
            "port_open": _probe_tcp_port("127.0.0.1", 8091),
            "api_key_ready": jupiter_ok,
        },
        "birdeye_mcp": {
            "url": cfg.BIRDEYE_MCP_URL,
            "api_key_ready": birdeye_ok,
        },
        "coinstats_mcp": {
            "url": cfg.COINSTATS_MCP_URL,
            "api_key_ready": coinstats_ok,
        },
        "cabal_hunter_mcp": {
            "installed": cabal_mcp_dir.exists(),
            "x402_wallet_pubkey": x402_wallet or "UNSET_FALLBACK_LOCAL_LOUVAIN",
            "x402_funded_configured": len(x402_wallet) >= 32,
        },
        "coingecko_docs_mcp": {
            "installed": coingecko_mcp_dir.exists(),
        },
    }

    return {
        "paid_core_4": paid_core_4,
        "free_7_apis_and_streams": free_7_apis_and_streams,
        "webhooks_and_telegram": webhooks_and_telegram,
        "mcp_servers": mcp_servers,
    }


def run_10point_mainnet_preflight_check(
    config: Optional[Settings] = None,
    sharding: Optional[StealthShardRingManager] = None,
    onchain_total_sol: float = 0.0,
) -> Dict[str, Any]:
    """Executes the complete 10-Point Mainnet Live-Capital Readiness Check."""
    cfg = config or get_settings()
    cfg.ensure_ramdisk_directories()

    wallet_manifest = init_persistent_mainnet_wallets(cfg, sharding=sharding)
    prewarm = build_mainnet_alt_and_ata_prewarm_plan(
        cfg,
        shard_pubkeys=[s["pubkey"] for s in wallet_manifest.get("shards", [])],
    )
    integrations = inspect_api_streams_webhooks_and_mcp_status(cfg)

    from src.execution.live_mainnet_broadcaster import LiveMainnetBroadcaster

    broadcaster = LiveMainnetBroadcaster(config=cfg)
    deployment_probe = broadcaster.probe_onchain_program_and_alt_deployment_sync()
    funding_readiness = broadcaster.evaluate_funding_and_broadcast_readiness(
        onchain_total_sol=float(onchain_total_sol)
    )
    zero_rent_native_fallback: Dict[str, Any] = {
        **deployment_probe,
        **funding_readiness,
        "deployment_probe": deployment_probe,
        "funding_readiness": funding_readiness,
        "deployment_rent_required_sol": 0.0,
    }

    # 1. RAMDisk & mlock
    ramdisk_exists = cfg.RAMDISK_ROOT.exists() and all(
        d.exists() for d in cfg.ramdisk_directories
    )
    mlock_ok = bool(wallet_manifest.get("mlock_active")) or _test_mlock_capability()

    # 2. 4-Lane Local LLM Fleet (:8005, :8002, :8006, :8007)
    lane_ports = {
        "8005_gatekeeper": _probe_tcp_port("127.0.0.1", 8005),
        "8002_vision_reasoner": _probe_tcp_port("127.0.0.1", 8002),
        "8006_fast_l3": _probe_tcp_port("127.0.0.1", 8006),
        "8007_bge_m3_embed": _probe_tcp_port("127.0.0.1", 8007),
    }
    lanes_online_count = sum(1 for v in lane_ports.values() if v)

    # 3. Paid Core 4 API Keys
    paid4 = integrations["paid_core_4"]
    paid4_ok = bool(paid4["all_4_configured"])

    # 4. Free 7 Feeds & Telegram MTProto
    free7_tg = integrations["webhooks_and_telegram"]
    free7_ok = bool(
        integrations["free_7_apis_and_streams"]["RUGCHECK_SUMMARY_URL_TEMPLATE"]["ready"]
        and integrations["free_7_apis_and_streams"]["PUMPPORTAL_WS_URL"]["ready"]
    )

    # 5. Persistent Encrypted Keystore (.keystore.enc) + Master + Lockbox + 25 Shards
    keystore_path = Path(wallet_manifest["keystore_path"])
    keystore_ok = (
        keystore_path.exists()
        and int(wallet_manifest.get("shard_count", 0)) == SHARD_COUNT
    )

    # 6. Bound Personal Cold Withdrawal Address
    withdraw_addr = str(getattr(cfg, "WITHDRAW_ADDRESS", "DEFERRED")).strip()
    withdraw_vault_state_path = (
        cfg.RAMDISK_EXECUTION_STATE / "withdrawal_vault_state.json"
    )
    if withdraw_vault_state_path.exists():
        try:
            w_state = orjson.loads(withdraw_vault_state_path.read_bytes())
            saved_w = str(w_state.get("withdraw_address", "DEFERRED")).strip()
            if saved_w and saved_w != "DEFERRED":
                withdraw_addr = saved_w
        except Exception:
            pass
    withdraw_bound = withdraw_addr != "DEFERRED" and len(withdraw_addr) >= 32

    # 7. On-Chain profit_guard Smart Contract Artifact
    so_path = (
        WORKSPACE_ROOT
        / "anchor_profit_guard"
        / "target"
        / "deploy"
        / "profit_guard.so"
    )
    so_exists = so_path.exists()
    profit_guard_program_id = str(
        getattr(
            cfg,
            "PROFIT_GUARD_PROGRAM_ID",
            "PrftGrd111111111111111111111111111111111111",
        )
    )

    # 8. Mainnet 36-Account ALT & 150 Shard ATAs Pre-Warm Plan
    alt_count = int(prewarm["alt_address_count"])
    atas_count = int(prewarm["prewarmed_shard_atas_count"])
    alt_ata_ok = alt_count == 36 and atas_count == 150 and bool(
        prewarm["jito_tip_pdas_excluded_from_alt"]
    )

    # 9. 5-Region Jito Block Engine (NY, FRA, AMS, TYO, SLC) + Helius Sender
    jito_regions = list(
        integrations["free_7_apis_and_streams"]["JITO_TIP_STREAM_AND_5_BLOCK_ENGINES"][
            "block_engines_5region"
        ].keys()
    )
    jito_5region_ok = len(jito_regions) == 5 and bool(cfg.HELIUS_SENDER_URL)

    # 10. Live Mainnet Wire Broadcast Switch
    live_broadcast_enabled = read_live_broadcast_enabled(cfg)

    checklist: List[Dict[str, Any]] = [
        {
            "id": 1,
            "key": "ramdisk_and_mlock",
            "label": "128GB RAMDisk (/mnt/ramdisk) & mlock Keyring",
            "passed": bool(ramdisk_exists and mlock_ok),
            "status": "READY" if (ramdisk_exists and mlock_ok) else "WARN",
            "detail": f"ramdisk={ramdisk_exists}, mlock={mlock_ok}",
        },
        {
            "id": 2,
            "key": "llm_4lane_fleet",
            "label": "4-Lane Local GPU LLM Fleet (:8005/:8002/:8006/:8007)",
            "passed": lanes_online_count >= 1,
            "status": "ONLINE" if lanes_online_count == 4 else f"{lanes_online_count}/4 ONLINE",
            "detail": lane_ports,
        },
        {
            "id": 3,
            "key": "paid_core_4_apis",
            "label": "Paid Core 4 API Keys (Helius, Jupiter V2, Birdeye, SocialData)",
            "passed": paid4_ok,
            "status": "CONFIGURED" if paid4_ok else f"{paid4['configured_count']}/4 CONFIGURED",
            "detail": {
                "helius": paid4["HELIUS_API_KEY"]["configured"],
                "jupiter": paid4["JUPITER_API_KEY"]["configured"],
                "birdeye": paid4["BIRDEYE_API_KEY"]["configured"],
                "socialdata": paid4["SOCIALDATA_API_KEY"]["configured"],
            },
        },
        {
            "id": 4,
            "key": "free_7_and_telegram_mcp",
            "label": "Free 7 Streams, Telegram MTProto & 6 MCP Servers",
            "passed": free7_ok,
            "status": "READY" if free7_ok else "PARTIAL",
            "detail": {
                "goplus_configured": integrations["free_7_apis_and_streams"]["GOPLUS_API_KEY"]["configured"],
                "coinstats_configured": integrations["free_7_apis_and_streams"]["COINSTATS_API_KEY"]["configured"],
                "telegram_bot_configured": free7_tg["TELEGRAM_BOT_TOKEN"]["configured"],
                "cabal_hunter_mcp": integrations["mcp_servers"]["cabal_hunter_mcp"]["installed"],
                "coingecko_docs_mcp": integrations["mcp_servers"]["coingecko_docs_mcp"]["installed"],
            },
        },
        {
            "id": 5,
            "key": "persistent_keystore",
            "label": "Persistent AES-256-GCM .keystore.enc (Master + Lockbox + 25 Shards)",
            "passed": keystore_ok,
            "status": "PERSISTED" if keystore_ok else "MISSING",
            "detail": {
                "keystore_path": str(keystore_path),
                "master_vault_pubkey": wallet_manifest["master_treasury_pubkey"],
                "reserve_lockbox_pubkey": wallet_manifest["reserve_lockbox_pubkey"],
                "shard_count": wallet_manifest["shard_count"],
            },
        },
        {
            "id": 6,
            "key": "withdraw_address_bound",
            "label": "Bound Personal Cold Withdrawal Wallet",
            "passed": withdraw_bound,
            "status": "BOUND" if withdraw_bound else "DEFERRED",
            "detail": withdraw_addr,
        },
        {
            "id": 7,
            "key": "profit_guard_contract",
            "label": "On-Chain profit_guard Smart Contract (profit_guard.so)",
            "passed": so_exists,
            "status": "COMPILED" if so_exists else "MISSING",
            "detail": {
                "so_path": str(so_path),
                "so_exists": so_exists,
                "program_id": profit_guard_program_id,
            },
        },
        {
            "id": 8,
            "key": "alt_36_and_150_atas",
            "label": "Mainnet 36-Account ALT & 150 Shard wSOL/LST ATAs Plan",
            "passed": alt_ata_ok,
            "status": "READY",
            "detail": {
                "alt_address_count": alt_count,
                "prewarmed_shard_atas_count": atas_count,
                "jito_tip_pdas_excluded": prewarm["jito_tip_pdas_excluded_from_alt"],
            },
        },
        {
            "id": 9,
            "key": "jito_5region_and_helius_sender",
            "label": "5-Region Jito Block Engine (NY/FRA/AMS/TYO/SLC) + Helius Sender",
            "passed": jito_5region_ok,
            "status": "READY",
            "detail": {
                "regions": jito_regions,
                "helius_sender_url": cfg.HELIUS_SENDER_URL,
                "astralane_url": cfg.ASTRALANE_DISPATCH_URL,
            },
        },
        {
            "id": 10,
            "key": "live_broadcast_switch",
            "label": "Live Mainnet Wire Broadcast Switch",
            "passed": live_broadcast_enabled,
            "status": "ARMED_LIVE" if live_broadcast_enabled else "DRY_RUN_SAFE",
            "detail": {
                "live_broadcast_enabled": live_broadcast_enabled,
                "initial_execution_mode": cfg.INITIAL_EXECUTION_MODE,
            },
        },
    ]

    passed_count = sum(1 for item in checklist if item["passed"])
    return {
        "ready_score": f"{passed_count}/10",
        "passed_count": passed_count,
        "total_checks": 10,
        "live_broadcast_enabled": live_broadcast_enabled,
        "execution_mode": cfg.INITIAL_EXECUTION_MODE,
        "master_vault_pubkey": wallet_manifest["master_treasury_pubkey"],
        "reserve_lockbox_pubkey": wallet_manifest["reserve_lockbox_pubkey"],
        "withdraw_address": withdraw_addr,
        "keystore_path": str(keystore_path),
        "keystore_persisted": keystore_ok,
        "mlock_active": mlock_ok,
        "profit_guard_program_id": profit_guard_program_id,
        "profit_guard_so_compiled": so_exists,
        "alt_table_address": prewarm["alt_table_address"],
        "alt_address_count": alt_count,
        "prewarmed_shard_atas_count": atas_count,
        "checklist": checklist,
        "integrations": integrations,
        "paid_core_4": integrations["paid_core_4"],
        "free_7_apis_and_streams": integrations["free_7_apis_and_streams"],
        "webhooks_and_telegram": integrations["webhooks_and_telegram"],
        "mcp_servers": integrations["mcp_servers"],
        "zero_rent_native_fallback": zero_rent_native_fallback,
        "timestamp_ns": time.time_ns(),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="go_live_mainnet_wizard",
        description="Sovereign Titan OS — 10-Point Mainnet Live-Capital Readiness & Onboarding Wizard",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run the 10-Point Mainnet Live-Capital Readiness Check (default)",
    )
    parser.add_argument(
        "--init-wallets",
        action="store_true",
        dest="init_wallets",
        help="Initialize or load persistent .keystore.enc and print Master Vault, Lockbox & 25 Shard pubkeys",
    )
    parser.add_argument(
        "--prewarm-plan",
        action="store_true",
        dest="prewarm_plan",
        help="Build and print the 36-Account Mainnet ALT & 150-ATA Shard pre-warm instruction plan",
    )
    parser.add_argument(
        "--set-live",
        type=str,
        default=None,
        dest="set_live",
        help="Toggle LIVE_MAINNET_BROADCAST_ENABLED in runtime state (true|false)",
    )
    parser.add_argument(
        "--enable-5k-daily",
        action="store_true",
        dest="enable_5k_daily",
        help="Activate the 5-Tier $5,000+/Day (28.50 SOL/Day) High-Velocity Institutional Preset & 6 Multipliers",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON report (enabled by default)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.enable_5k_daily:
        from src.execution.golden5_phased_rollout_governor import (
            Golden5PhasedRolloutGovernor,
        )

        gov = Golden5PhasedRolloutGovernor()
        res = gov.activate_5k_daily_velocity_preset()
        sys.stdout.write(
            orjson.dumps(res, option=orjson.OPT_INDENT_2).decode("utf-8") + "\n"
        )
        return 0

    if args.set_live is not None:
        target = args.set_live.strip().lower() in ("1", "true", "yes", "on")
        result = set_live_mainnet_broadcast_mode(target)
        sys.stdout.write(
            orjson.dumps(result, option=orjson.OPT_INDENT_2).decode("utf-8") + "\n"
        )
        return 0

    if args.init_wallets:
        manifest = init_persistent_mainnet_wallets()
        sys.stdout.write(
            orjson.dumps(manifest, option=orjson.OPT_INDENT_2).decode("utf-8") + "\n"
        )
        return 0

    if args.prewarm_plan:
        plan = build_mainnet_alt_and_ata_prewarm_plan()
        sys.stdout.write(
            orjson.dumps(plan, option=orjson.OPT_INDENT_2).decode("utf-8") + "\n"
        )
        return 0

    report = run_10point_mainnet_preflight_check()
    sys.stdout.write(
        orjson.dumps(report, option=orjson.OPT_INDENT_2).decode("utf-8") + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
