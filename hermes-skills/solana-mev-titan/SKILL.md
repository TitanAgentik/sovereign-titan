---
name: solana-mev-titan
description: "Tri-Engine Solana MEV Suite: Engine A (2,000-Pool Mirror + Kamino/Marginfi Flash-Loan Atomic Back-Runner), Engine B (Crowded-Whale Copy-Herd & Multi-Clip TWAP Wide-Sandwich), and Engine C (Meteora DLMM 3-Bin JIT Fee Harvester)."
version: 1.0.0
author: Sovereign Titan OS
license: MIT
metadata:
  hermes:
    tags: [solana, mev, arbitrage, kamino, marginfi, meteora-dlmm, jito-bam]
    related_skills: [alpha-wallet-shadow, sovereign-orchestrator, sovereign-gui-command-center]
---

# Solana MEV Titan (`solana-mev-titan`)

## Tri-Engine Core Allocation
- **Cores 0–3:** Intel E810 NIC RX/TX hardware timestamping IRQs & GPSDO PTP clock sync (`ptp4l` / `phc2sys`) + Core 0 Isolated Risk Watchdog.
- **Cores 4–15 (Engine A):** In-Memory 2,000-Pool Mirror (`/mnt/ramdisk/mev_pool_mirror` zero-copy mmap) + Kamino/Marginfi 0-Fee Flash-Loan Atomic Back-Runner.
- **Cores 16–23 (Engine B):** Crowded-Whale Copy-Herd & Multi-Clip TWAP Wide-Sandwich Engine.
- **Cores 24–31 (Engine C):** Meteora DLMM 3-Bin JIT Fee Harvester (strictly locked to `PAPER_SIM` until `+100 SOL` realized profit).

## Transaction & Dispatch Invariants
- **Account Limits & ALTs:** `MAX_VERSIONED_TX_ACCOUNTS = 64` (with auto-upgrade support to `96` under Agave 4.5 for 3-hop triangular arbitrage). All multi-hop transactions use pre-warmed Address Lookup Tables (ALTs) to remain `< 1,150 bytes` (below the 1,232-byte MTU limit).
- **Simultaneous Multi-Path Dispatch:** Broadcast simultaneously to Helius Sender + Regional Jito Block Engines (`ny`, `frankfurt`, `amsterdam`, `tokyo`) + Astralane (`ENABLE_BAM_DBI=false` configurable toggle until keypair is whitelisted).
- **Immutable On-Chain & Host Safety:** `anchor_profit_guard/programs/profit_guard/src/lib.rs` and `risk_watchdog.py` are immutable and must never be modified by self-evolving DSPy/GEPA routines.
