---
name: web-strategy-harvester
description: Autonomous web intelligence and strategy harvesting skill instructing @web-alpha-researcher how to search, extract, sandbox-test in FinMem train mode, and register new Solana trading heuristics.
---

# Web Strategy Harvester (`web-strategy-harvester`)

## Overview
Equips `@web-alpha-researcher` to operate across two timescales:
1. **Intraday Narrative & Contract Address Verification**:
   - Cross-checks Pump.fun and Raydium mint addresses against social announcements, Metaplex `metadata_mutable: false` and unique URI invariants, and `pump-fun-chat-mcp` comment velocity.
   - Treats founder DOX signals strictly as a secondary signal subordinated to hard on-chain SPL/Token-2022 authority checks.
2. **Scheduled 6-Hour Meta-Learning (`0 */6 * * *`)**:
   - Monitors `solana-foundation/awesome-solana-ai`, `sendaifun/solana-agent-kit`, Jito Block Engine tip percentile APIs, Anchor IDL updates, and quantitative finance preprints.
   - Translates newly discovered Token-2022 exploit signatures (`transfer_hook`, `transfer_fee`), sybil clustering heuristics, and gRPC filters into executable CLI scripts.
   - Sandbox-tests candidate heuristics against historical losing trajectories in `memory/telemetry.db` (`mode='train'`) before recommending promotion to `@ace-curator`.

## Black-Box CLI Scripts
- **Validate & Register Web-Harvested Heuristic in FinMem `train` Mode**:
  ```bash
  python3 .agents/skills/web-strategy-harvester/scripts/validate_web_alpha.py --help
  ```
- **Inspect Top-10 Holder Concentration & Bundled Jito Sybil Clusters**:
  ```bash
  python3 .agents/skills/web-strategy-harvester/scripts/sybil_check.py --help
  ```

## Reference Documentation
- Canonical Pump.fun (`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`), PumpSwap, Raydium AMM v4, and Token-2022 instruction discriminators are documented in [`references/solana-microstructure-idls.md`](references/solana-microstructure-idls.md).
