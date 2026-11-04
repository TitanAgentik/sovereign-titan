---
name: sovereign-orchestrator
description: "4-Lane Local LLM Swarm Orchestrator, Counterfactual 60-Trace GEPA Self-Improvement Arena, Core 0 Immutable Risk Watchdog, 3-Stage Paper-to-Live Graduation Engine, Solana Pay QR Deposit, and Deferred Withdrawal Vault."
version: 2.0.0
author: Sovereign Titan OS
license: MIT
metadata:
  hermes:
    tags: [llm-swarm, vllm, sglang, ktransformers, llama-cpp, mcp, dspy, gepa, risk-watchdog, solana-pay, vault]
    related_skills: [alpha-wallet-shadow, solana-mev-titan, sovereign-gui-command-center]
---

# Sovereign Orchestrator (`sovereign-orchestrator`)

## 1. 4-Lane Local LLM Swarm Architecture
1. **Lane 1 — Port 8000 (GPU 0, 88% VRAM):**
   - Model: `Qwen/Qwen3-Coder-Next-80B-A3B-FP8` (vLLM, `--enable-prefix-caching`, `--guided-decoding-backend xgrammar`, `--tool-call-parser hermes`).
   - Role: Sub-45ms Tactical Gatekeeper & MCP Router (`45ms` hard circuit-breaker timeout).
2. **Lane 2 — Port 8001 (GPU 1, Slice 1 — 31% VRAM):**
   - Model: `huihui-ai/Qwen3-VL-30B-A3B-Instruct-abliterated-FP8` (vLLM Multimodal).
   - Role: Multimodal Vision Banner/OCR Auditor + Uncensored Trench Narrative Scorer, integrated with `/mnt/ramdisk/image_phash_index` (64-bit Perceptual Hash BK-Tree of last 100,000 token banners).
3. **Lane 3 — Port 8002 (GPU 1, Slice 2 — 60% VRAM + Cores 48–95 + 340GB DDR5):**
   - Model: `DeepSeek-V3.2-671B` / `Kimi-K2.5-1T` via `SGLang + KTransformers` (`--kt-cpuinfer 48 --kt-num-gpu-experts 48`).
   - Role: Deep Asynchronous Alpha Synthesis, Post-Mortem Forensics, and 12-Hour 60-Trace DSPy/GEPA Evolution.
4. **Lane 4 — Port 8003 (Cores 36–47 L3 Cache):**
   - Model: `Qwen3.5-4B-Instruct-Q8_0.gguf` via `llama-server` (`-t 12 -cb -fa --cache-reuse 256`).
   - Role: High-frequency CPU L3-resident Micro-Classifier & Social Velocity Filter.

## 2. Phase 5 Orchestration, GEPA Evolution, Risk & Vault Modules
- **Counterfactual "Missed Runner" Logger (`src/evolution/counterfactual_logger.py`):**
  Logs every `SKIP` decision to `/mnt/ramdisk/counterfactual_log.duckdb`, tracks `+60s`, `+300s`, and `+900s` prices, and flags skipped tokens reaching `>= 3.0x` (`LP > $25k`) as `FALSE_NEGATIVE_OMISSION`.
- **60-Trace GEPA Self-Improvement Arena (`src/evolution/gepa_arena.py`):**
  Optimizes Gatekeeper instructions (`<= 900 tokens`) over 15 top winners, 15 worst losses, 15 missed runners, and 15 true rug blocks. Evaluates `SHADOW_CHALLENGER` over 50 `simulateBundle` triggers and promotes only at `>= +10%` net SOL EV with `0` honeypots; auto-rollbacks at `-4.0%` drawdown. Enforces the Immutable Safety Lock on `risk_watchdog.py` and `anchor_profit_guard/programs/profit_guard/src/lib.rs`.
- **Core 0 Root-Locked Risk Watchdog & Parquet Tax Ledger (`src/risk/risk_watchdog.py`, `src/risk/audit_ledger.py`):**
  100ms polling on Core 0 (`>= 6.0%` 15m drawdown, `4` consecutive `>5%` slippage trades, `>5ms` PTP offset, or `>1,500ms` Helius lag triggers `EMERGENCY_DEMOTE_TO_PAPER`), Pyth/Binance 1s Macro Crash Filter (`GREEN`, `AMBER`, `RED_MACRO_FLUSH`), and `/var/lib/hermes/audit_ledger.parquet`.
- **3-Stage Paper-to-Live Graduation Engine (`src/vault/paper_to_live_engine.py`):**
  Boots in `PAPER` (`25.00 vSOL`) and unlocks `CANARY` (`15%` Shard #1) and `LIVE` (`100%` 25 Shards) at `>= 40` trades, `PF >= 1.80`, `PnL >= +3.5 SOL`, `max_dd <= 5.0%`, and `0` unhandled honeypots.
- **Solana Pay QR Deposit & Deferred Withdrawal Vault (`src/vault/qr_deposit.py`, `src/vault/withdrawal_manager.py`):**
  Generates `solana:` URIs, UTF-8 half-block QR panels, `600x600` `~/sovereign-titan/latest_deposit_qr.png`, automatic `+20 SOL` HWM -> `10 SOL` `RESERVE_LOCKBOX_KEYPAIR` sweeps while `WITHDRAW_ADDRESS = "DEFERRED"`, and full 25-shard ATA rent-reclaiming withdrawals.

## 3. Unified CLI Commands (`src/cli/titan_cli.py`)
```bash
python -m src.cli.titan_cli swarm boot
python -m src.cli.titan_cli swarm status
python -m src.cli.titan_cli swarm benchmark
python -m src.cli.titan_cli swarm evolve
python -m src.cli.titan_cli vault status
python -m src.cli.titan_cli vault mode [paper|canary|live]
python -m src.cli.titan_cli vault deposit [amount] [--auto-shard]
python -m src.cli.titan_cli vault set-withdraw <address>
python -m src.cli.titan_cli vault withdraw <amount|profits|ALL> [--to <address>]
python -m src.cli.titan_cli shadow scan
python -m src.cli.titan_cli shadow inspect <wallet>
python -m src.cli.titan_cli mev flash-test
```
