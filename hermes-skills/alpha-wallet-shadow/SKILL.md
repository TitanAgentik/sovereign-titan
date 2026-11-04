---
name: alpha-wallet-shadow
description: "Sub-slot (<1-2 Fast Bot) Alpha Wallet Shadow Executor, DuckDB Lead-Lag Matrix, and rustworkx 3-Hop Burner Graph pinned to Cores 24-31 & 36-47."
version: 1.0.0
author: Sovereign Titan OS
license: MIT
metadata:
  hermes:
    tags: [solana, copy-trading, lead-lag, burner-graph, alpenglow, bam]
    related_skills: [solana-mev-titan, sovereign-orchestrator, sovereign-gui-command-center]
---

# Alpha Wallet Shadow Executor (`alpha-wallet-shadow`)

## Overview & Hardware Pinning
- **Execution Cores:** Cores 24–31 (`<1-2 Fast Bot` Sub-Slot Copy Engine).
- **Discovery & Graph Cores:** Cores 36–47 (DuckDB Lead-Lag Matrix + `rustworkx` 3-Hop Burner Graph Workers).
- **RAMDisk State:**
  - `/mnt/ramdisk/alpha_graph`: DuckDB Lead-Lag Matrix + `rustworkx` 3-Hop Burner Graph.
  - `/mnt/ramdisk/pre_approved_tokens`: 0ms pre-computed LLM/Vision token scores (`TTL=120s`, `<0.05ms` lookup).
  - `/mnt/ramdisk/execution_state`: 25-Wallet Stealth Shards & live position state.

## Protocol Timing & Execution Rules
1. **Alpenglow & Jito BAM Cadence:**
   - Slot duration is strictly `200ms` (Alpenglow consensus).
   - Jito BAM tick interval is `25ms` (8 ticks per 200ms slot).
2. **Primary Ingestion:**
   - Helius `preconfSubscribe` filtered by tracked alpha `signer`, funding `source`, and swap `instruction`.
   - Helius LaserStream gRPC at `processed` commitment.
3. **Two-Tranche Hot-Path Execution:**
   - If `/mnt/ramdisk/pre_approved_tokens/{mint}.json` holds a valid score (`TTL <= 120s`), execute full size immediately (`<0.05ms` lookup, zero synchronous LLM calls).
   - For uncached 0-second tokens, fire a **25% deterministic Scout Tranche in `<2ms`** and evaluate the **75% Conviction Tranche** asynchronously via Port 8000 (`Qwen3-Coder-Next-80B-A3B-FP8`) within a hard `45ms` circuit-breaker timeout.
4. **Anti-Frontrun & Rent Reclaim:**
   - Inject read-only `jitodontfront111111111111111111111111111111` pubkey into Instruction 0 on every directional buy.
   - Append `spl_token::instruction::close_account` on every 100% token exit to reclaim `0.00203928 SOL` ATA rent.
