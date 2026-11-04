# Sovereign Titan v2.0 — Whole-Solana Ecosystem & Multi-Protocol Mega-Flash Syndicate Command Center

**Sovereign Titan v2.0** is an institutional-grade, bare-metal Solana MEV, Cross-DEX Atomic Flash Arbitrage (`$100K → $1M → $10M → $50M+`), Whole-Solana-Ecosystem Alpha, and CEX-to-Polymarket L2 Binary Strike Latency Arbitrage system engineered for a **96-Core AMD Threadripper PRO 9995WX**, **Dual NVIDIA RTX PRO 6000 Blackwell GPUs (192GB VRAM)**, and a **128GB tmpfs RAMDisk (`/mnt/ramdisk`)**.

---

## 📚 Definitive Documentation & Runbooks (`docs/`)

- **[20-Page Definitive System Bible (Markdown)](docs/SOVEREIGN_TITAN_20_PAGE_DEFINITIVE_SYSTEM_BIBLE.md)** | **[PDF Edition](docs/SOVEREIGN_TITAN_20_PAGE_DEFINITIVE_SYSTEM_BIBLE.pdf)**
- **[15-Page Master Quantitative Whitepaper (Markdown)](docs/SOVEREIGN_TITAN_15_PAGE_MASTER_WHITEPAPER.md)** | **[PDF Edition](docs/SOVEREIGN_TITAN_15_PAGE_MASTER_WHITEPAPER.pdf)**
- **[Operator Action Manual (Markdown)](docs/SOVEREIGN_TITAN_OPERATOR_ACTION_MANUAL.md)** | **[PDF Edition](docs/SOVEREIGN_TITAN_OPERATOR_ACTION_MANUAL.pdf)**
- **[Live Capital 24/7 Runbook (Markdown)](docs/SOVEREIGN_TITAN_LIVE_CAPITAL_24X7_RUNBOOK.md)** | **[PDF Edition](docs/SOVEREIGN_TITAN_LIVE_CAPITAL_24X7_RUNBOOK.pdf)**

---

## ⚡ Core Architectural Highlights

1. **Institutional Multi-Protocol Mega-Flash Loan Syndicate (`$100K → $1M → $10M → $50M+`)**:
   - Stacks **MarginFi V2 (`0.0 bps` fee)** + **Kamino KLend (`0.1 bps` fee)** + **Sanctum S-Controller / Jupiter JLP (`0.1 bps` fee)** + **Save / Solend (`0.3 bps` fee)** in a single atomic execution plan (`packages/sniper-rs/src/mega_flash.rs`, `src/execution/kamino_flash_integrator.py`).
   - Uses **KKT Lagrange Water-Filling** across **Raydium CLMM**, **Orca Whirlpools**, **Meteora DLMM**, **Phoenix CLOB**, **Lifinity V2**, and **Sanctum S-Controller** to eliminate quadratic single-pool price impact.
   - Enforces **`0.00 SOL` Principal Risk** via on-chain `profit_guard` (`anchor_profit_guard/programs/profit_guard/src/lib.rs`) and Zero-Rent Native Slippage Guard (`otherAmountThreshold`).

2. **Whole-Solana-Ecosystem Proprietary Alpha Engines (`src/execution/phase13_8profit_engines.py`)**:
   - **Engine 1**: Pyth Lazer (`1ms`) & Switchboard Surge Oracle-Lag AMM Arbitrage (`Lifinity V2`, `Obric V2`, `Jupiter JLP`).
   - **Engine 2**: Cross-DEX CLMM/Whirlpool Tick-Boundary Liquidation Cascades (`Kamino KLend`, `MarginFi V2`, `Drift v2` `5%–10%` liquidation bonus).
   - **Engine 3**: `JLP` (Jupiter Perps LP) Mint/Burn vs. Orca/Meteora Secondary DEX Atomic Basis Sweep (`$500K–$15M`).
   - **Engine 4**: Sanctum Infinity (`INF`) 20-LST Basket NAV Triangle & 48h Epoch-Boundary Stake-Pool Crank (`UpdateStakePoolBalance`).
   - **Engine 5**: Single-Bin Constant-Sum (`P*x + y = L`) DLMM Flash JIT Fee-Surge Harvester (`2.5%–10.0%` dynamic fees) + PumpSwap Unwind.
   - **Engine 6**: Lookahead Creator-Vault Buyback Crank (`96%–99.9%` threshold crossing), Token-2022 Withheld-Tax Crank, & Cross-Chain Whale Bridge Lookahead (`Mayan Swift`, `deBridge DLN`).

3. **Anti-Loss Iron Dome & 6-Stage Trail-Win Engine (`src/execution/trail_win_engine.py`)**:
   - `<= 1.8%` Pre-Trade Same-Slot Round-Trip Simulation Gate (`SOL -> Token -> SOL`).
   - `VPIN <= 0.78` Order-Flow Toxicity Ceiling.
   - `3.5s` Zero-Velocity Scratch (`<= 0.0001 SOL` capped scratch tip) + Automatic `CloseAccount` (`0x09`) ATA Rent Reclaim (`+0.00203928 SOL/ATA`).
   - `+2.2% -> +0.85%` Fee-Adjusted Break-Even Floor Ratchet.

4. **32 Primary Agents & 96 Specialized Subagents + 7-Workspace Tauri Desktop GUI**:
   - Native Rust + React/TypeScript Desktop Command Center (`hermes-skills/sovereign-gui-command-center/`) communicating over a `<0.3ms` UNIX domain socket (`/mnt/ramdisk/titan_ipc.sock`) with `src/ipc/titan_ipc_daemon.py`.

---

## 🚀 Quickstart

```bash
# 1. Copy environment template and configure private keys in .env (gitignored)
cp .env.example .env

# 2. Launch the IPC Daemon & Native Tauri Desktop Command Center
./scripts/launch_titan_gui.sh

# 3. Run the verification test suite
PYTHONPATH=. ./.venv/bin/pytest -q tests/verify_phase2_onchain.py tests/test_live_mainnet_broadcaster.py tests/test_golden5_phased_rollout_governor.py
cargo test --manifest-path packages/sniper-rs/Cargo.toml
```
