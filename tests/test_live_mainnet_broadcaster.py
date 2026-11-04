"""Sovereign Titan OS — Comprehensive Test Suite for Live Mainnet Broadcaster,
Persistent Keystore, 36-Account ALT & 150-ATA Pre-Warmer, Go-Live Wizard, CLI & IPC Daemon
(`tests/test_live_mainnet_broadcaster.py`).
"""

from __future__ import annotations

import asyncio
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import struct
import threading
from typing import Any, Dict

import orjson
import pytest
from solders.pubkey import Pubkey

from scripts.go_live_mainnet_wizard import (
    build_mainnet_alt_and_ata_prewarm_plan,
    init_persistent_mainnet_wallets,
    inspect_api_streams_webhooks_and_mcp_status,
    main as wizard_main,
    read_live_broadcast_enabled,
    run_10point_mainnet_preflight_check,
    set_live_mainnet_broadcast_mode,
)
from src.cli.titan_cli import TitanCLIController, build_parser, main as cli_main
from src.config.settings import Settings, get_settings
from src.execution.alt_manager import ALTManager
from src.execution.live_mainnet_broadcaster import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    CANONICAL_MAINNET_ALT_ADDRESSES,
    OFFICIAL_JITO_TIP_PDAS,
    PREWARM_SHARD_TOKEN_MINTS,
    PROFIT_GUARD_PROGRAM_ID,
    SPL_TOKEN_PROGRAM_ID,
    USDC_MINT_PUBKEY,
    WSOL_MINT_PUBKEY,
    LiveMainnetBroadcaster,
    build_create_and_extend_alt_instructions,
    build_create_ata_idempotent_instruction,
    build_shard_prewarm_plan,
    derive_associated_token_address,
    derive_profit_guard_transient_pda,
)
from src.ipc.titan_ipc_daemon import TitanIPCDaemon
from src.security.stealth_sharding import SHARD_COUNT, StealthShardRingManager
from src.vault.withdrawal_manager import DeferredWithdrawalManager, LAMPORTS_PER_SOL


# ==============================================================================
# 1. PERSISTENT KEYSTORE & LIVE ON-CHAIN VAULT BALANCE SYNC TESTS
# ==============================================================================
def test_persistent_keystore_preserves_keys_across_reloads(tmp_path: Path) -> None:
    """Verifies that `load_or_initialize_keystore()` persists `.keystore.enc` on first run
    and preserves the exact same Master Vault, Reserve Lockbox, and 25 Stealth Shard
    public keys across subsequent instantiations without overwriting.
    """
    keystore_file = tmp_path / ".keystore.enc"
    cfg = get_settings()

    ring_first = StealthShardRingManager(config=cfg, keystore_path=keystore_file)
    returned_path = ring_first.load_or_initialize_keystore()
    assert returned_path == keystore_file
    assert keystore_file.exists()

    manifest_first = ring_first.export_public_addresses_manifest()
    assert manifest_first["shard_count"] == SHARD_COUNT == 25
    assert len(manifest_first["shards"]) == 25
    master_1 = manifest_first["master_treasury_pubkey"]
    lockbox_1 = manifest_first["reserve_lockbox_pubkey"]
    shards_1 = [s["pubkey"] for s in manifest_first["shards"]]

    # Instantiate a second manager pointing to the existing keystore file
    ring_second = StealthShardRingManager(config=cfg, keystore_path=keystore_file)
    loaded_existing = ring_second.load_existing_keystore()
    assert loaded_existing is True

    manifest_second = ring_second.export_public_addresses_manifest()
    assert manifest_second["master_treasury_pubkey"] == master_1
    assert manifest_second["reserve_lockbox_pubkey"] == lockbox_1
    assert [s["pubkey"] for s in manifest_second["shards"]] == shards_1

    # Also verify load_or_initialize_keystore() on second instance preserves keys
    ring_third = StealthShardRingManager(config=cfg, keystore_path=keystore_file)
    ring_third.load_or_initialize_keystore()
    assert str(ring_third.master_treasury_kp.pubkey()) == master_1
    assert str(ring_third.reserve_lockbox_kp.pubkey()) == lockbox_1
    assert [s.pubkey for s in ring_third.shards] == shards_1


def test_withdrawal_manager_sync_live_onchain_balances(tmp_path: Path) -> None:
    """Verifies `DeferredWithdrawalManager.sync_live_onchain_balances()` both in offline
    placeholder mode and against a live JSON-RPC `getMultipleAccounts` endpoint.
    """
    keystore_file = tmp_path / ".keystore.enc"
    cfg = get_settings()
    sharding = StealthShardRingManager(config=cfg, keystore_path=keystore_file)
    sharding.load_or_initialize_keystore()
    wm = DeferredWithdrawalManager(config=cfg, sharding=sharding)

    # 1. Placeholder / offline mode fallback
    offline_res = wm.sync_live_onchain_balances(
        rpc_url="https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_API_KEY"
    )
    assert offline_res["synced"] is False
    assert offline_res["mode"] == "OFFLINE_PLACEHOLDER_KEY"
    assert offline_res["queried_accounts"] == 27

    # 2. Spin up local mock Solana JSON-RPC server returning 27 account balances
    class _MockSolanaRPCHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = orjson.loads(self.rfile.read(length))
            assert body["method"] == "getMultipleAccounts"
            queried_pks = body["params"][0]
            assert len(queried_pks) == 27

            # Master = 2.5 SOL, Lockbox = 1.25 SOL, each of 25 Shards = 0.1 SOL (2.5 SOL total)
            values = [
                {"lamports": int(2.5 * LAMPORTS_PER_SOL), "owner": "11111111111111111111111111111111"},
                {"lamports": int(1.25 * LAMPORTS_PER_SOL), "owner": "11111111111111111111111111111111"},
            ] + [
                {"lamports": int(0.1 * LAMPORTS_PER_SOL), "owner": "11111111111111111111111111111111"}
                for _ in range(25)
            ]
            resp_bytes = orjson.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"context": {"slot": 342_815_000}, "value": values},
                }
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), _MockSolanaRPCHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        live_res = wm.sync_live_onchain_balances(rpc_url=f"http://127.0.0.1:{port}/")
        assert live_res["synced"] is True
        assert live_res["mode"] == "LIVE_MAINNET_RPC"
        assert live_res["queried_accounts"] == 27
        assert live_res["master_vault_sol"] == pytest.approx(2.5)
        assert live_res["reserve_lockbox_sol"] == pytest.approx(1.25)
        assert live_res["shards_total_sol"] == pytest.approx(2.5)
        assert live_res["hot_wallet_balance_sol"] == pytest.approx(5.0)
        assert wm.hot_wallet_balance_sol == pytest.approx(5.0)
        assert wm.pending_unclaimed_sweeps_sol == pytest.approx(1.25)
    finally:
        server.shutdown()
        server.server_close()


# ==============================================================================
# 2. DETERMINISTIC SPL ATA & PROFIT_GUARD TRANSIENT STATE PDA DERIVATION TESTS
# ==============================================================================
def test_deterministic_ata_and_profit_guard_pda_derivation(tmp_path: Path) -> None:
    """Verifies `derive_associated_token_address`, `derive_profit_guard_transient_pda`,
    `build_create_ata_idempotent_instruction`, and `build_shard_prewarm_plan` for 25 shards x 6 mints = 150 ATAs.
    """
    keystore_file = tmp_path / ".keystore.enc"
    sharding = StealthShardRingManager(keystore_path=keystore_file)
    sharding.load_or_initialize_keystore()
    shard_pubkeys = [s.pubkey for s in sharding.shards]
    assert len(shard_pubkeys) == 25

    owner_pk = Pubkey.from_string(shard_pubkeys[0])
    wsol_mint_pk = Pubkey.from_string(WSOL_MINT_PUBKEY)
    token_prog_pk = Pubkey.from_string(SPL_TOKEN_PROGRAM_ID)
    ata_prog_pk = Pubkey.from_string(ASSOCIATED_TOKEN_PROGRAM_ID)

    expected_ata, _ = Pubkey.find_program_address(
        [bytes(owner_pk), bytes(token_prog_pk), bytes(wsol_mint_pk)],
        ata_prog_pk,
    )
    derived_ata = derive_associated_token_address(
        owner_pubkey=shard_pubkeys[0],
        mint_pubkey=WSOL_MINT_PUBKEY,
        token_program_id=SPL_TOKEN_PROGRAM_ID,
    )
    assert derived_ata == str(expected_ata)

    # Verify CreateIdempotent instruction structure (opcode 0x01, 6 accounts)
    ix = build_create_ata_idempotent_instruction(
        payer=owner_pk,
        owner=owner_pk,
        mint=wsol_mint_pk,
        token_program=token_prog_pk,
    )
    assert ix.program_id == ata_prog_pk
    assert bytes(ix.data) == b"\x01"
    assert len(ix.accounts) == 6
    assert ix.accounts[0].pubkey == owner_pk
    assert ix.accounts[0].is_signer is True
    assert ix.accounts[0].is_writable is True
    assert str(ix.accounts[1].pubkey) == derived_ata
    assert ix.accounts[1].is_writable is True

    # Verify profit_guard transient state PDA derivation
    pg_pda, pg_bump = derive_profit_guard_transient_pda(
        payer_pubkey=shard_pubkeys[0],
        program_id=PROFIT_GUARD_PROGRAM_ID,
    )
    expected_pg_pda, expected_pg_bump = Pubkey.find_program_address(
        [b"profit_guard_state", bytes(owner_pk)],
        Pubkey.from_string(PROFIT_GUARD_PROGRAM_ID),
    )
    assert pg_pda == str(expected_pg_pda)
    assert pg_bump == int(expected_pg_bump)

    # Verify 25-shard x 6-mint = 150 ATAs prewarm plan
    plan = build_shard_prewarm_plan(
        shard_pubkeys=shard_pubkeys,
        profit_guard_program_id=PROFIT_GUARD_PROGRAM_ID,
    )
    assert plan["shard_count"] == 25
    assert plan["tokens_per_shard"] == list(PREWARM_SHARD_TOKEN_MINTS.keys())
    assert len(plan["tokens_per_shard"]) == 6
    assert plan["total_ata_count"] == 150
    assert plan["prewarmed_shard_atas_count"] == 150
    assert plan["total_create_idempotent_instructions"] == 150
    assert len(plan["shards"]) == 25
    assert len(plan["instructions"]) == 150

    # Ensure the entire plan serializes cleanly via orjson
    serialized = orjson.dumps(plan)
    decoded = orjson.loads(serialized)
    assert decoded["total_ata_count"] == 150


# ==============================================================================
# 3. 36-ACCOUNT MAINNET ALT BUILDER & JITO TIP PDA EXCLUSION INVARIANT TESTS
# ==============================================================================
def test_36_account_mainnet_alt_builder_excludes_jito_tip_pdas() -> None:
    """Verifies `CANONICAL_MAINNET_ALT_ADDRESSES` has exactly 36 accounts, strictly excludes
    all 8 Jito Tip PDAs, and builds valid `CreateLookupTable` and `ExtendLookupTable` instructions.
    """
    assert len(CANONICAL_MAINNET_ALT_ADDRESSES) == 36
    assert len(OFFICIAL_JITO_TIP_PDAS) == 8

    for tip_pda in OFFICIAL_JITO_TIP_PDAS:
        assert tip_pda not in CANONICAL_MAINNET_ALT_ADDRESSES

    authority = Pubkey.from_string("7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF")
    recent_slot = 342_814_920

    # Pass canonical 36 addresses + injected Jito Tip PDAs to verify strict filtering
    polluted_input = [*CANONICAL_MAINNET_ALT_ADDRESSES, *OFFICIAL_JITO_TIP_PDAS]
    alt_plan = build_create_and_extend_alt_instructions(
        authority=authority,
        payer=authority,
        recent_slot=recent_slot,
        addresses=polluted_input,
    )

    assert alt_plan["address_count"] == 36
    assert len(alt_plan["addresses"]) == 36
    assert alt_plan["jito_tip_pdas_excluded"] is True
    for tip_pda in OFFICIAL_JITO_TIP_PDAS:
        assert tip_pda not in alt_plan["addresses"]

    # Check CreateLookupTable binary layout: u32(0) LE + u64(recent_slot) LE + u8(bump) = 13 bytes
    create_ix = alt_plan["create_instruction"]
    create_bytes = bytes(create_ix.data)
    assert len(create_bytes) == 13
    disc, unpacked_slot, unpacked_bump = struct.unpack("<IQB", create_bytes)
    assert disc == 0
    assert unpacked_slot == recent_slot
    assert unpacked_bump == alt_plan["bump"]

    # Check ExtendLookupTable binary layout: u32(2) LE + u64(36) LE + 36 * 32 bytes = 1,164 bytes
    extend_ix = alt_plan["extend_instruction"]
    extend_bytes = bytes(extend_ix.data)
    assert len(extend_bytes) == 4 + 8 + (36 * 32) == 1164
    ext_disc, num_addrs = struct.unpack("<IQ", extend_bytes[:12])
    assert ext_disc == 2
    assert num_addrs == 36

    # Also verify ALTManager warm ALTs initialization
    alt_mgr = ALTManager()
    state = alt_mgr.initialize_warm_alts(top_pool_count=500)
    assert state.top_pool_vault_count == 500
    assert len(alt_mgr.get_lookup_table_accounts()) >= 3


# ==============================================================================
# 4. LIVE MAINNET BROADCASTER (BLOCKHASH, JUPITER V2 QUOTE, 5-REGION JITO) TESTS
# ==============================================================================
def test_live_mainnet_broadcaster_blockhash_quote_and_5region_jito() -> None:
    """Verifies `LiveMainnetBroadcaster`:
    - `fetch_latest_blockhash_sync()`
    - `fetch_jupiter_v2_quote_sync()`
    - `broadcast_jito_bundle_5region_sync()` (both DRY_RUN_SIMULATION_MODE and live wire dispatch)
    - `run_live_connectivity_probe()`
    """
    cfg = get_settings()
    broadcaster = LiveMainnetBroadcaster(config=cfg, http_timeout_s=1.0)

    # 1. Blockhash sync & RAMDisk cache
    bh_res = broadcaster.fetch_latest_blockhash_sync()
    assert len(bh_res["blockhash"]) >= 32
    assert bh_res["last_valid_block_height"] > 0
    assert Path(bh_res["cache_path"]).exists()

    # 2. Jupiter V2 quote fallback & validation
    with pytest.raises(ValueError):
        broadcaster.fetch_jupiter_v2_quote_sync(WSOL_MINT_PUBKEY, USDC_MINT_PUBKEY, 0)

    quote = broadcaster.fetch_jupiter_v2_quote_sync(
        input_mint=WSOL_MINT_PUBKEY,
        output_mint=USDC_MINT_PUBKEY,
        amount_lamports=1_000_000_000,
        slippage_bps=50,
    )
    assert quote["inputMint"] == WSOL_MINT_PUBKEY
    assert quote["outputMint"] == USDC_MINT_PUBKEY
    assert int(quote["outAmount"]) > 0
    assert int(quote["otherAmountThreshold"]) > 0

    # 3. 5-Region Jito bundle broadcast in DRY_RUN_SIMULATION_MODE
    tx_b64 = base64.b64encode(b"\x01" * 240).decode("ascii")
    dry_receipt = broadcaster.broadcast_jito_bundle_5region_sync(
        signed_txs_b64=[tx_b64],
        tip_lamports=125_000,
    )
    assert dry_receipt["mode"] == "DRY_RUN_SIMULATION_MODE"
    assert dry_receipt["bundle_size_valid"] is True
    assert set(dry_receipt["jito_regions_targeted"]) == {
        "ny",
        "frankfurt",
        "amsterdam",
        "tokyo",
        "slc",
    }
    assert "astralane" in dry_receipt["relay_receipts"]
    assert "helius_sender" in dry_receipt["relay_receipts"]

    # Validate bundle count and MTU guards
    with pytest.raises(ValueError):
        broadcaster.broadcast_jito_bundle_5region_sync([])
    with pytest.raises(ValueError):
        broadcaster.broadcast_jito_bundle_5region_sync([tx_b64] * 6)
    oversized_tx = base64.b64encode(b"\xff" * 1300).decode("ascii")
    with pytest.raises(ValueError):
        broadcaster.broadcast_jito_bundle_5region_sync([oversized_tx])

    # 4. Test live wire dispatch against a local mock Jito/Relay server
    class _MockRelayHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            payload = orjson.loads(self.rfile.read(length))
            assert payload["method"] == "sendBundle"
            resp_bytes = orjson.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": "mock_bundle_id_999"}
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

        def log_message(self, format: str, *args: Any) -> None:
            return

    relay_srv = HTTPServer(("127.0.0.1", 0), _MockRelayHandler)
    relay_url = f"http://127.0.0.1:{relay_srv.server_port}/api/v1/bundles"
    relay_thread = threading.Thread(target=relay_srv.serve_forever, daemon=True)
    relay_thread.start()
    try:
        live_cfg = Settings(
            HELIUS_API_KEY="live_test_helius_key_123456",
            LIVE_MAINNET_BROADCAST_ENABLED=True,
            JITO_NY_BLOCK_ENGINE_URL=relay_url,
            JITO_FRANKFURT_BLOCK_ENGINE_URL=relay_url,
            JITO_AMSTERDAM_BLOCK_ENGINE_URL=relay_url,
            JITO_TOKYO_BLOCK_ENGINE_URL=relay_url,
            JITO_SLC_BLOCK_ENGINE_URL=relay_url,
            ASTRALANE_DISPATCH_URL=relay_url,
            HELIUS_SENDER_URL=relay_url,
        )
        live_broadcaster = LiveMainnetBroadcaster(config=live_cfg, http_timeout_s=1.0)
        live_receipt = live_broadcaster.broadcast_jito_bundle_5region_sync(
            signed_txs_b64=[tx_b64],
            tip_lamports=150_000,
        )
        assert live_receipt["mode"] == "LIVE_MAINNET_WIRE_BROADCAST"
        assert live_receipt["status"] == "SUBMITTED"
        for r_name, r_info in live_receipt["relay_receipts"].items():
            assert r_info["status"] == "SUBMITTED", f"Relay {r_name} failed"
            assert r_info["bundle_id"] == "mock_bundle_id_999"
    finally:
        relay_srv.shutdown()
        relay_srv.server_close()

    # 5. Connectivity probe
    probe = broadcaster.run_live_connectivity_probe()
    assert "helius_rpc" in probe
    assert "jupiter_v2" in probe
    assert "jito_block_engine" in probe
    assert "dexscreener" in probe


# ==============================================================================
# 5. GO-LIVE MAINNET WIZARD & TITAN CLI (`mainnet`) SUBCOMMAND TESTS
# ==============================================================================
def test_go_live_mainnet_wizard_and_cli_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verifies `scripts/go_live_mainnet_wizard.py` and `src/cli/titan_cli.py`
    subcommands (`preflight`, `init-wallets`, `prewarm-alt`, `sync-balances`,
    `enable-live`, `disable-live`).
    """
    try:
        # 1. 10-Point Preflight Check & Full API/Stream/Webhook/MCP Inventory
        report = run_10point_mainnet_preflight_check()
        assert report["total_checks"] == 10
        assert len(report["checklist"]) == 10
        assert report["alt_address_count"] == 36
        assert report["prewarmed_shard_atas_count"] == 150
        assert len(report["master_vault_pubkey"]) >= 32
        assert len(report["reserve_lockbox_pubkey"]) >= 32

        # Verify Paid Core 4, Free 7 Streams, Webhooks/Telegram, and 6 MCP Servers
        assert "paid_core_4" in report
        for key_name in (
            "HELIUS_API_KEY",
            "BIRDEYE_API_KEY",
            "JUPITER_API_KEY",
            "SOCIALDATA_API_KEY",
        ):
            assert key_name in report["paid_core_4"]
        assert "free_7_apis_and_streams" in report
        assert "webhooks_and_telegram" in report
        assert "mcp_servers" in report
        assert "cabal_hunter_mcp" in report["mcp_servers"]
        assert "coingecko_docs_mcp" in report["mcp_servers"]

        # 2. Wizard CLI flags
        assert wizard_main(["--preflight"]) == 0
        out_preflight = orjson.loads(capsys.readouterr().out)
        assert out_preflight["total_checks"] == 10

        assert wizard_main(["--init-wallets"]) == 0
        out_wallets = orjson.loads(capsys.readouterr().out)
        assert out_wallets["shard_count"] == 25

        assert wizard_main(["--prewarm-plan"]) == 0
        out_prewarm = orjson.loads(capsys.readouterr().out)
        assert out_prewarm["alt_address_count"] == 36
        assert out_prewarm["prewarmed_shard_atas_count"] == 150

        # 3. TitanCLIController & CLI `mainnet` subcommands
        parser = build_parser()
        parsed = parser.parse_args(["mainnet", "preflight"])
        assert parsed.group == "mainnet"
        assert parsed.subcommand == "preflight"

        assert cli_main(["mainnet", "init-wallets"]) == 0
        cli_wallets = orjson.loads(capsys.readouterr().out)
        assert cli_wallets["action"] == "init-wallets"
        assert cli_wallets["shard_count"] == 25

        assert cli_main(["mainnet", "prewarm-alt"]) == 0
        cli_prewarm = orjson.loads(capsys.readouterr().out)
        assert cli_prewarm["action"] == "prewarm-alt"
        assert cli_prewarm["alt_address_count"] == 36
        assert cli_prewarm["prewarmed_shard_atas_count"] == 150

        assert cli_main(["mainnet", "sync-balances"]) == 0
        cli_sync = orjson.loads(capsys.readouterr().out)
        assert cli_sync["action"] == "sync-balances"
        assert cli_sync["queried_accounts"] == 27

        assert cli_main(["mainnet", "enable-live"]) == 0
        cli_enable = orjson.loads(capsys.readouterr().out)
        assert cli_enable["live_broadcast_enabled"] is True
        assert read_live_broadcast_enabled() is True

        assert cli_main(["mainnet", "disable-live"]) == 0
        cli_disable = orjson.loads(capsys.readouterr().out)
        assert cli_disable["live_broadcast_enabled"] is False
        assert read_live_broadcast_enabled() is False
    finally:
        set_live_mainnet_broadcast_mode(False)


# ==============================================================================
# 6. TITAN IPC DAEMON TELEMETRY & MAINNET GO-LIVE IPC HANDLERS TESTS
# ==============================================================================
def test_titan_ipc_daemon_mainnet_readiness_and_commands() -> None:
    """Verifies `TitanIPCDaemon.build_telemetry_frame()["mainnet_readiness"]` and all
    4 live Mainnet IPC command handlers (`RUN_LIVE_MAINNET_PREFLIGHT_CHECK`,
    `SYNC_LIVE_ONCHAIN_VAULT_BALANCES`, `PREWARM_SHARD_ATAS_AND_ALT`,
    `SET_LIVE_MAINNET_BROADCAST_MODE`).
    """

    async def _run_ipc_checks() -> None:
        daemon = TitanIPCDaemon()
        try:
            frame = daemon.build_telemetry_frame()
            assert "mainnet_readiness" in frame
            mr: Dict[str, Any] = frame["mainnet_readiness"]

            assert len(mr["master_vault_pubkey"]) >= 32
            assert len(mr["reserve_lockbox_pubkey"]) >= 32
            assert mr["alt_address_count"] == 36
            assert mr["prewarmed_shard_atas_count"] == 150
            assert mr["total_checks"] == 10
            assert len(mr["checklist"]) == 10
            assert "paid_core_4" in mr
            assert "free_7_apis_and_streams" in mr
            assert "webhooks_and_telegram" in mr
            assert "mcp_servers" in mr

            # 1. RUN_LIVE_MAINNET_PREFLIGHT_CHECK
            res_pre = await daemon.handle_ipc_payload(
                {"action": "RUN_LIVE_MAINNET_PREFLIGHT_CHECK"}
            )
            assert res_pre["status"] == "OK"
            assert res_pre["mainnet_readiness"]["alt_address_count"] == 36

            # 2. SYNC_LIVE_ONCHAIN_VAULT_BALANCES
            res_sync = await daemon.handle_ipc_payload(
                {"action": "SYNC_LIVE_ONCHAIN_VAULT_BALANCES"}
            )
            assert res_sync["status"] == "OK"
            assert res_sync["sync_report"]["queried_accounts"] == 27

            # 3. PREWARM_SHARD_ATAS_AND_ALT
            res_prewarm = await daemon.handle_ipc_payload(
                {"action": "PREWARM_SHARD_ATAS_AND_ALT"}
            )
            assert res_prewarm["status"] == "OK"
            assert res_prewarm["alt_address_count"] == 36
            assert res_prewarm["prewarmed_shard_atas_count"] == 150

            # 4. SET_LIVE_MAINNET_BROADCAST_MODE (toggle on then back off)
            res_on = await daemon.handle_ipc_payload(
                {"action": "SET_LIVE_MAINNET_BROADCAST_MODE", "enabled": True}
            )
            assert res_on["status"] == "OK"
            assert res_on["live_broadcast_enabled"] is True

            res_off = await daemon.handle_ipc_payload(
                {"action": "SET_LIVE_MAINNET_BROADCAST_MODE", "enabled": False}
            )
            assert res_off["status"] == "OK"
            assert res_off["live_broadcast_enabled"] is False
        finally:
            set_live_mainnet_broadcast_mode(False)

    asyncio.run(_run_ipc_checks())
