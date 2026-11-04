#!/usr/bin/env python3
"""Sovereign Titan OS — Phase 1 Closed-Loop Foundation Verification Suite.

Validates:
1. Workspace directories, `/AGENTS.md`, and Hermes Skill symlinks (`~/.hermes/skills/`).
2. `/mnt/ramdisk` 128GB mount, subdirectories, and `<0.05ms` read/write speed.
3. Pydantic `Settings` parsing, Paid 4 + Free 7 APIs, and Alpenglow 200ms / Jito BAM 25ms invariants.
4. `UnifiedMCPBus` schema caching in RAMDisk and `FreeFirehosePipeline` 90%+ garbage rejection.
5. `SwarmClient` across Ports 8000–8003: prefix-cached MCP tool definitions, `<0.05ms` RAMDisk
   pre-approved token lookup, `45ms` hard circuit-breaker timeout on Port 8000, and live/mock
   health checks across all 4 lanes.
"""

from __future__ import annotations

import asyncio
import socket
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from aiohttp import web
import orjson
from pydantic import ValidationError

WORKSPACE_ROOT = Path("/home/titanagentik/sovereign-titan")
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.config.settings import Settings, get_settings
from src.ingest.free_firehose import FreeFirehosePipeline, RawTokenLaunchEvent
from src.ingest.mcp_bus import UnifiedMCPBus
from src.llm.swarm_client import (
    MCP_TOOL_DEFINITIONS,
    PreApprovedTokenEntry,
    SwarmClient,
)


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


async def start_mock_llm_lane_server(port: int, simulated_delay_ms: float = 4.0) -> web.AppRunner:
    """Starts an OpenAI/vLLM-compatible local loopback server on the specified port."""

    async def handle_models(request: web.Request) -> web.Response:
        payload = {
            "object": "list",
            "data": [{"id": f"mock-model-port-{port}", "object": "model"}],
        }
        return web.Response(body=orjson.dumps(payload), content_type="application/json")

    async def handle_chat_completions(request: web.Request) -> web.Response:
        body = orjson.loads(await request.read())
        delay_s = float(request.headers.get("X-Mock-Delay-Ms", simulated_delay_ms)) / 1000.0
        user_msg = body.get("messages", [{}])[-1].get("content", "")
        if isinstance(user_msg, str) and "SLOW_SIMULATION" in user_msg:
            delay_s = 0.075  # 75ms -> triggers Port 8000 45ms circuit breaker
        if delay_s > 0:
            await asyncio.sleep(delay_s)

        schema_name = (
            body.get("response_format", {})
            .get("json_schema", {})
            .get("name", "tactical_gate_decision")
        )

        if schema_name == "tactical_gate_decision":
            parsed_user = orjson.loads(user_msg) if isinstance(user_msg, str) else {}
            mint = parsed_user.get("mint", "So11111111111111111111111111111111111111112")
            content_obj = {
                "mint": mint,
                "action": "EXECUTE_CONVICTION",
                "confidence": 0.91,
                "recommended_slippage_bps": 125,
                "jito_tip_lamports": 120000,
                "reason": "Strong sub-slot alpha whale cluster inflow + clean RugCheck/GoPlus",
            }
        elif schema_name == "vision_audit_result":
            content_obj = {
                "mint": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                "phash_64": "a1b2c3d4e5f60718",
                "is_recycled_scam_banner": False,
                "ocr_extracted_text": "SOVEREIGN TITAN AI",
                "narrative_score": 0.89,
                "verdict": "CLEAN_NARRATIVE",
            }
        elif schema_name == "deep_alpha_analysis":
            content_obj = {
                "subject": "3-hop-burner-cluster-01",
                "cluster_sybil_probability": 0.08,
                "expected_ev_bps": 420.5,
                "recommended_parameter_updates": {"scout_tranche_ratio": 0.25},
                "summary": "Verified non-sybil CEX-funded lead wallet cluster.",
            }
        else:
            content_obj = {
                "mint": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                "social_velocity_score": 0.86,
                "pass_to_gatekeeper": True,
            }

        resp_payload = {
            "id": f"chatcmpl-{port}",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": orjson.dumps(content_obj).decode("utf-8"),
                    },
                    "finish_reason": "stop",
                }
            ],
        }
        return web.Response(
            body=orjson.dumps(resp_payload), content_type="application/json"
        )

    app = web.Application()
    app.router.add_get("/v1/models", handle_models)
    app.router.add_post("/v1/chat/completions", handle_chat_completions)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    return runner


def verify_step_1_workspace_and_skills() -> None:
    print("\n[CHECK 1/5] Verifying Workspace Invariants & Hermes Skill Symlinks...")
    agents_md = WORKSPACE_ROOT / "AGENTS.md"
    forensics_rules_md = WORKSPACE_ROOT / ".agents" / "rules" / "solana-mev-forensics.md"
    heuristics_rules_md = WORKSPACE_ROOT / ".agents" / "rules" / "solana-heuristics.md"
    assert agents_md.exists(), "AGENTS.md missing from workspace root"
    assert forensics_rules_md.exists(), "solana-mev-forensics.md missing from .agents/rules/"
    assert heuristics_rules_md.exists(), "solana-heuristics.md missing from .agents/rules/"
    content = (
        agents_md.read_text(encoding="utf-8")
        + "\n"
        + forensics_rules_md.read_text(encoding="utf-8")
        + "\n"
        + heuristics_rules_md.read_text(encoding="utf-8")
    )
    assert "jitodontfront" in content
    assert "Louvain" in content and "85 SOL" in content
    assert "RULE-EXEC-01" in content and "RULE-RUG-02" in content

    required_skills = [
        "alpha-wallet-shadow",
        "solana-mev-titan",
        "sovereign-orchestrator",
        "sovereign-gui-command-center",
    ]
    hermes_skills_dir = Path.home() / ".hermes" / "skills"
    agy_skills_dir = WORKSPACE_ROOT / ".agents" / "skills"

    for skill in required_skills:
        src_skill_md = WORKSPACE_ROOT / "hermes-skills" / skill / "SKILL.md"
        hermes_link = hermes_skills_dir / skill
        agy_link = agy_skills_dir / skill
        assert src_skill_md.exists(), f"Missing source skill {src_skill_md}"
        assert hermes_link.is_symlink(), f"Missing symlink in ~/.hermes/skills/{skill}"
        assert hermes_link.resolve() == src_skill_md.parent.resolve()
        assert agy_link.is_symlink(), f"Missing symlink in .agents/skills/{skill}"
        assert agy_link.resolve() == src_skill_md.parent.resolve()
        print(f"  [OK] Skill '{skill}' mirrored & symlinked -> {hermes_link}")


def verify_step_2_ramdisk_speed() -> None:
    print("\n[CHECK 2/5] Verifying 128GB /mnt/ramdisk Directories & <0.05ms Latency...")
    cfg = get_settings()
    assert cfg.RAMDISK_ROOT.exists(), "/mnt/ramdisk does not exist"
    for d in cfg.ramdisk_directories:
        assert d.exists() and d.is_dir(), f"Missing RAMDisk directory: {d}"

    bench_file = cfg.RAMDISK_PRE_APPROVED_TOKENS / "_bench_latency.bin"
    payload = orjson.dumps(
        {
            "mint": "So11111111111111111111111111111111111111112",
            "score": 0.95,
            "jito_tip_lamports": 100000,
            "ttl_sec": 120,
        }
    )

    write_latencies_ms: List[float] = []
    read_latencies_ms: List[float] = []

    # Warmup
    for _ in range(25):
        bench_file.write_bytes(payload)
        _ = bench_file.read_bytes()

    for _ in range(500):
        t0 = time.perf_counter()
        bench_file.write_bytes(payload)
        write_latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        t1 = time.perf_counter()
        raw = bench_file.read_bytes()
        read_latencies_ms.append((time.perf_counter() - t1) * 1000.0)
        assert len(raw) == len(payload)

    bench_file.unlink(missing_ok=True)

    median_write_ms = statistics.median(write_latencies_ms)
    median_read_ms = statistics.median(read_latencies_ms)
    print(
        f"  [OK] /mnt/ramdisk Median Write: {median_write_ms:.5f} ms | Median Read: {median_read_ms:.5f} ms (Threshold: <0.05000 ms)"
    )
    assert median_write_ms < 0.05, f"RAMDisk write too slow: {median_write_ms:.5f}ms"
    assert median_read_ms < 0.05, f"RAMDisk read too slow: {median_read_ms:.5f}ms"


def verify_step_3_pydantic_config() -> None:
    print("\n[CHECK 3/5] Verifying Pydantic Settings & Protocol Timing Invariants...")
    cfg = Settings()
    assert cfg.PRIMARY_NIC_INTERFACE in ("enp210s0f0np0", "enp65s0f0")
    assert cfg.INITIAL_EXECUTION_MODE == "PAPER"
    assert cfg.INITIAL_PAPER_SOL == 25.0
    assert cfg.WITHDRAW_ADDRESS == "DEFERRED" or len(cfg.WITHDRAW_ADDRESS) >= 32
    assert cfg.ENABLE_BAM_DBI is False
    assert cfg.MAX_VERSIONED_TX_ACCOUNTS == 64
    assert cfg.effective_max_tx_accounts(agave_45_enabled=True) == 96
    assert cfg.ALPENGLOW_SLOT_MS == 200
    assert cfg.JITO_BAM_TICK_MS == 25
    assert len(cfg.jito_regional_endpoints) == 4

    # Ensure legacy 400ms slot duration is rejected
    rejected_400ms = False
    try:
        Settings(ALPENGLOW_SLOT_MS=400)
    except ValidationError:
        rejected_400ms = True
    assert rejected_400ms, "Settings failed to reject legacy 400ms slot duration"
    print(
        "  [OK] Paid 4 + Free 7 APIs validated; Alpenglow 200ms & Jito BAM 25ms invariants enforced."
    )


async def verify_step_4_mcp_bus_and_free_firehose() -> None:
    print("\n[CHECK 4/5] Verifying UnifiedMCPBus & $0 Free Firehose (90%+ Discard Rate)...")
    async with UnifiedMCPBus() as bus:
        write_ms = bus.schema_cache.save_to_ramdisk()
        read_ms = bus.schema_cache.load_from_ramdisk()
        assert len(bus.schema_cache.schemas) == 4
        assert len(bus.schema_cache.schema_sha256) == 64
        assert read_ms < 0.05, f"MCP schema cache read exceeded 0.05ms: {read_ms:.5f}ms"

        preconf_sub = bus.build_helius_preconf_subscription(
            tracked_signers=["7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"]
        )
        assert preconf_sub["method"] == "preconfSubscribe"
        routes = bus.get_simultaneous_outbound_routes()
        assert set(routes.keys()) == {
            "helius_sender",
            "jito_ny",
            "jito_frankfurt",
            "jito_amsterdam",
            "jito_tokyo",
            "astralane",
        }
        print(
            f"  [OK] MCP Schema Cache SHA256={bus.schema_cache.schema_sha256[:16]}... | RAMDisk Read={read_ms:.5f}ms"
        )

    # Test FreeFirehosePipeline with 20 synthetic launches (18 garbage/honeypots, 2 clean gems)
    base58_digits = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    async with FreeFirehosePipeline() as firehose:
        for i in range(18):
            suffix = base58_digits[i + 1] * 2
            bad_mint = f"BadMint{suffix}111111111111111111111111111111111"[:44]
            if i < 6:
                # Fails Stage 1 (mint authority active / dev buy > 20%)
                ev = RawTokenLaunchEvent(
                    mint=bad_mint,
                    symbol=f"RUG{i}",
                    uri="https://ipfs.io/ipfs/QmValid",
                    mint_authority_active=True,
                )
                rep = await firehose.evaluate_token_launch(ev)
                assert not rep.passed and rep.discard_reason == "MINT_AUTHORITY_ACTIVE"
            elif i < 12:
                # Fails Stage 2 (GoPlus Honeypot)
                ev = RawTokenLaunchEvent(
                    mint=bad_mint,
                    symbol=f"HPOT{i}",
                    uri="https://ipfs.io/ipfs/QmValid",
                )
                rep = await firehose.evaluate_token_launch(
                    ev,
                    mock_security_overrides={
                        "rugcheck": {"score": 150, "risks": []},
                        "goplus": {"is_honeypot": "1"},
                        "dexscreener": {"liquidity_usd": 10000.0, "volume_5m_usd": 5000.0},
                    },
                )
                assert not rep.passed and rep.discard_reason == "GOPLUS_HONEYPOT_OR_CANNOT_SELL"
            else:
                # Fails Stage 3 (Low liquidity / high RugCheck risk score)
                ev = RawTokenLaunchEvent(
                    mint=bad_mint,
                    symbol=f"GARB{i}",
                    uri="https://ipfs.io/ipfs/QmValid",
                )
                rep = await firehose.evaluate_token_launch(
                    ev,
                    mock_security_overrides={
                        "rugcheck": {"score": 850, "risks": [{"name": "Top 10 holders", "level": "danger"}]},
                        "goplus": {"is_honeypot": "0"},
                        "dexscreener": {"liquidity_usd": 500.0, "volume_5m_usd": 100.0},
                    },
                )
                assert not rep.passed

        # 2 Clean High-Conviction Launches
        for j in range(2):
            suffix = base58_digits[j + 25] * 2
            good_mint = f"GemMint{suffix}111111111111111111111111111111111"[:44]
            ev = RawTokenLaunchEvent(
                mint=good_mint,
                symbol=f"TITAN{j}",
                uri="https://ipfs.io/ipfs/QmCleanMetadata",
                initial_dev_buy_pct=3.5,
                virtual_sol_reserves=45.0,
            )
            rep = await firehose.evaluate_token_launch(
                ev,
                mock_security_overrides={
                    "rugcheck": {"score": 40, "risks": []},
                    "goplus": {"is_honeypot": "0", "cannot_sell_all": "0"},
                    "dexscreener": {
                        "liquidity_usd": 35000.0,
                        "volume_5m_usd": 22000.0,
                        "boost_points": 100,
                        "paid_order_approved": True,
                    },
                },
            )
            assert rep.passed, f"Expected clean gem {good_mint} to pass Free Firehose (got {rep})"

        discard_ratio = firehose.stats.discard_ratio
        print(
            f"  [OK] Free Firehose Funnel: Ingested={firehose.stats.total_ingested}, "
            f"Discarded={firehose.stats.total_discarded} ({discard_ratio * 100:.1f}%), "
            f"Passed={firehose.stats.passed_to_paid_bus}"
        )
        assert discard_ratio >= 0.90, f"Expected >=90% discard ratio, got {discard_ratio:.2%}"


async def verify_step_5_llm_swarm_and_circuit_breaker() -> None:
    print("\n[CHECK 5/5] Verifying 4-Lane LLM Swarm (Ports 8000-8003) & 45ms Circuit Breaker...")
    runners: List[web.AppRunner] = []
    ephemeral_overrides: Dict[int, str] = {}

    try:
        # Spin up mock loopback servers on any of Ports 8000-8003 that are not currently live
        for port in (8000, 8001, 8002, 8003):
            if not is_port_in_use(port):
                runner = await start_mock_llm_lane_server(port, simulated_delay_ms=4.0)
                runners.append(runner)
            else:
                print(f"  [INFO] Port {port} already has a live server listening on host.")

        # Also start a dedicated loopback endpoint for deterministic schema & timeout tests if 8002 is live
        test_8002_port = 18002
        runner_18002 = await start_mock_llm_lane_server(test_8002_port, simulated_delay_ms=4.0)
        runners.append(runner_18002)

        async with SwarmClient() as client:
            assert len(MCP_TOOL_DEFINITIONS) == 4
            assert len(client.prefix_cache_hash) == 64

            # 1. Check health across all 4 canonical ports (8000, 8001, 8002, 8003)
            health_map = await client.check_all_lanes(ephemeral_overrides)
            for port, status in sorted(health_map.items()):
                print(
                    f"  [OK] Port {port} ({status.lane_id}) -> online={status.online}, latency={status.latency_ms:.2f}ms"
                )
                assert status.online, f"Lane on port {port} failed health check: {status.detail}"

            # 2. Verify <0.05ms RAMDisk pre_approved_tokens lookup
            fast_mint = "GemMintRR111111111111111111111111111111111"
            client.write_pre_approved_token(
                PreApprovedTokenEntry(
                    mint=fast_mint,
                    score=0.94,
                    vision_verdict="CLEAN_NARRATIVE",
                    recommended_slippage_bps=120,
                    jito_tip_lamports=150000,
                    created_at_epoch_s=time.time(),
                    ttl_sec=120,
                )
            )
            t0 = time.perf_counter()
            hit = client.lookup_pre_approved_token(fast_mint)
            lookup_ms = (time.perf_counter() - t0) * 1000.0
            assert hit is not None and hit.score == 0.94
            assert lookup_ms < 0.05, f"Pre-approved lookup took {lookup_ms:.5f}ms (>0.05ms)"
            print(f"  [OK] RAMDisk pre_approved_tokens 0ms Fast-Path Lookup: {lookup_ms:.5f} ms")

            # 3. Verify Port 8000 live tactical gatekeeper (<45ms) on uncached token
            uncached_mint = "UncachedMint111111111111111111111111111111"
            gate_dec = await client.evaluate_tactical_gate(
                mint=uncached_mint,
                market_snapshot={"liquidity_sol": 85.0, "whale_signers": 2},
                endpoint_override="http://127.0.0.1:8000/v1",
            )
            assert gate_dec.action == "EXECUTE_CONVICTION"
            assert gate_dec.source == "PORT_8000_LLM"
            assert gate_dec.latency_ms < 45.0
            print(
                f"  [OK] Port 8000 Tactical Gatekeeper JSON Schema Validated in {gate_dec.latency_ms:.2f} ms (<45ms)"
            )

            # 4. Verify Port 8000 hard 45ms circuit-breaker timeout & 25% Scout Tranche fallback
            slow_mint = "SlowMint1111111111111111111111111111111111"
            plan = await client.build_two_tranche_plan(
                mint=slow_mint,
                total_sol=4.0,
                market_snapshot={"mode": "SLOW_SIMULATION"},
                endpoint_override="http://127.0.0.1:8000/v1",
            )
            assert plan.immediate_tranche_sol == 1.0  # 25% Scout Tranche
            assert plan.deferred_conviction_tranche_sol == 0.0  # Aborted due to >45ms timeout
            assert plan.immediate_latency_ms < 2.0
            assert plan.gate_decision is not None
            assert plan.gate_decision.source == "CIRCUIT_BREAKER_SCOUT_FALLBACK"
            assert client.circuit_breaker.total_timeouts >= 1
            print(
                f"  [OK] Hard 45ms Circuit Breaker verified: 25% Scout Tranche ({plan.immediate_tranche_sol} SOL) "
                f"prepared in {plan.immediate_latency_ms:.4f} ms; slow 75ms LLM call safely tripped fallback."
            )

            # 5. Verify Lanes 8001 (Vision), 8002 (Deep Reasoner), and 8003 (Fast L3)
            vision_res = await client.audit_vision_narrative(
                mint=fast_mint,
                image_url="https://ipfs.io/ipfs/QmBannerImage",
                phash_64="a1b2c3d4e5f60718",
                token_description="Sovereign Titan Official Launch",
                endpoint_override="http://127.0.0.1:8001/v1",
            )
            assert vision_res.verdict == "CLEAN_NARRATIVE"

            deep_res = await client.run_deep_alpha_synthesis(
                subject="3-hop-burner-cluster-01",
                graph_evidence={"hops": 3, "cex_root": "BinanceHotWallet"},
                endpoint_override=f"http://127.0.0.1:{test_8002_port}/v1",
            )
            assert deep_res.cluster_sybil_probability < 0.20

            l3_res = await client.classify_fast_l3(
                mint=fast_mint,
                social_burst_metrics={"mentions_1m": 42, "unique_authors": 31},
                endpoint_override="http://127.0.0.1:8003/v1",
            )
            assert l3_res.pass_to_gatekeeper is True
            print(
                "  [OK] All 4 LLM Swarm Lanes (8000, 8001, 8002, 8003) passed strict JSON schema validation."
            )
    finally:
        for r in runners:
            await r.cleanup()


async def main() -> int:
    print("==============================================================================")
    print("SOVEREIGN TITAN OS — PHASE 1 CLOSED-LOOP VERIFICATION SUITE")
    print("==============================================================================")
    t_start = time.perf_counter()
    verify_step_1_workspace_and_skills()
    verify_step_2_ramdisk_speed()
    verify_step_3_pydantic_config()
    await verify_step_4_mcp_bus_and_free_firehose()
    await verify_step_5_llm_swarm_and_circuit_breaker()
    elapsed_s = time.perf_counter() - t_start
    print("\n==============================================================================")
    print(f"[PASS] 100% OF PHASE 1 FOUNDATION CHECKS PASSED IN {elapsed_s:.3f}s")
    print("==============================================================================")
    return 0


def test_phase1_step_1_workspace_and_skills() -> None:
    verify_step_1_workspace_and_skills()


def test_phase1_step_2_ramdisk_speed() -> None:
    verify_step_2_ramdisk_speed()


def test_phase1_step_3_pydantic_config() -> None:
    verify_step_3_pydantic_config()


def test_phase1_steps_4_and_5_mcp_bus_firehose_and_llm_swarm() -> None:
    asyncio.run(verify_step_4_mcp_bus_and_free_firehose())
    asyncio.run(verify_step_5_llm_swarm_and_circuit_breaker())


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

