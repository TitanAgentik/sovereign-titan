---
name: sovereign-gui-command-center
description: "Tauri v2 (Rust Backend pinned to Threadripper Cores 32-35) + React 19 / TradingView Lightweight Charts v5 / WebGL 3D Cluster Graph Native Desktop GUI Command Center connected via 60-120Hz /mnt/ramdisk channels and <1ms /mnt/ramdisk/titan_ipc.sock."
version: 2.0.0
author: Sovereign Titan OS
license: MIT
metadata:
  hermes:
    tags: [tauri-v2, react-19, lightweight-charts-v5, webgl, solana-pay, command-center]
    related_skills: [alpha-wallet-shadow, solana-mev-titan, sovereign-orchestrator]
---

# Sovereign GUI Command Center (`sovereign-gui-command-center`)

## Hardware & IPC Architecture
- **CPU Pinning:** Pinned strictly to AMD Threadripper PRO 9995WX **Cores 32–35** (`libc::sched_setaffinity` in `src-tauri/src/lib.rs` and `taskset -c 32-35` in `/usr/local/bin/titan-gui`).
- **60–120 Hz Zero-Copy State Stream:** Streams `/mnt/ramdisk/execution_state/gui_telemetry_frame.json` and `libc::mmap` `/mnt/ramdisk/mev_pool_mirror/pools_2000.mmap` via `tauri::ipc::Channel` (`start_ramdisk_120hz_stream`).
- **Sub-1ms Command Socket:** Executes manual sniper actions, kill-switch flattening, mode switches, and vault withdrawals over `/mnt/ramdisk/titan_ipc.sock` (`execute_titan_ipc_command`).
- **100% Independent Backend Daemons:** Closing or restarting the GUI window never interrupts `swarm boot` or any active trading engine.

## Workspaces (`[Alt+1]` – `[Alt+7]`)
1. **Top Telemetry & Command Ribbon (`src/components/TopTelemetryBar.tsx`):** Alpenglow 200ms slot clock, Validator Geo City Flag, 25ms BAM tick pulse, E810 PTP `+38ns LOCKED` badge, Macro Regime Pill (`GREEN` / `AMBER` / `RED_MACRO_FLUSH`), Capital Mode Switcher (`PAPER` / `CANARY` / `LIVE`) + Graduation Ring, Live Equity Counter, and Guarded `[F12]` Master Kill-Switch.
2. **Workspace 1 `[Alt+1]` — Trading Cockpit (`src/views/TradingCockpit.tsx` & `src/components/ManualTradePanel.tsx`):** 1-Full / 2-Split / 4-Chart Quad Grid, tear-off multi-monitor window support, sub-second (`1 Tick`, `200ms`) & standard timeframes, Meteora DLMM Y-axis bin heatmap, drawing toolbar, on-chart `👑 Purple` / `⚡ Cyan` / `🐋 Orange` execution markers, draggable Master Cap & Asymmetric TP lines, and manual sniper dock.
3. **Workspace 2 `[Alt+2]` — Alpha Shadow & WebGL Cluster (`src/views/AlphaShadowView.tsx`):** 3D/2D WebGL cluster graph (`<=1-2 Fast Bot` Green Sharks, Cyan 3-Hop Burners, Red Crowded Whales) + Leaderboard & Port 8002 671B JSON profile editor.
4. **Workspace 3 `[Alt+3]` — MEV Titan Triad (`src/views/MevTriadView.tsx`):** Engine A (2,000-pool spread matrix, Kamino/Marginfi 100–5,000 SOL slider, 58% Jito EV bid, 1,000 SOL Live Flash-Sim Test), Engine B (Slot N+1..N+8 countdown + Manual Instant Unwind), and Engine C (`PAPER_SIM` locked until `+100 SOL` + high-fee DLMM scanner).
5. **Workspace 4 `[Alt+4]` — 4-Lane LLM Swarm & GEPA Arena (`src/views/LlmSwarmView.tsx`):** 96-Core Threadripper heatmap, Dual 96GB Blackwell GPU gauges, 512GB DDR5 bar, 100k `pHash` BK-Tree inspector, and 60-Trace GEPA Champion vs. Challenger arena.
6. **Workspace 5 `[Alt+5]` — Treasury Vault, Solana Pay QR & 25 Shards (`src/views/VaultAndShardsView.tsx`):** `[Ctrl+D]` Solana Pay QR generator + WebSocket audio chime, `[Ctrl+W]` Deferred Lockbox (`DEFERRED` -> HWM+20 SOL auto-sweep -> `profits` / `custom` / `ALL` withdrawals), and 25-Shard AES-256-GCM matrix.
7. **Workspaces 6 & 7 `[Alt+6/7]` — Parquet Tax Ledger & Deep Settings (`src/views/AuditAndSettingsView.tsx`):** Searchable `/var/lib/hermes/audit_ledger.parquet` with CSV/Parquet/Form 8949 export and Core 0 Root-Locked Risk Watchdog status.
