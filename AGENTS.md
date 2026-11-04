# AGENTS.md

## System Overview
High-frequency Solana memecoin cabal forensics, Slot-Zero Jito sniping, and closed-loop experiential learning platform powered by local LLMs (`LocalOpenAIAgentConfig(...).lightweight()` & `LiteRTAgentConfig`).
- `packages/forensics-py/`: Python 3.12 graph engine (NetworkX, Louvain clustering, Helius API, Cabal-Hunter MCP client).
- `packages/sniper-rs/`: Rust 1.82 ultra-low-latency execution engine (Yellowstone gRPC Dragon's Mouth client, Jito multi-relay bundle builder, deterministic Pump.fun / PumpSwap PDA calculator).
- `packages/calibration/`: Offline backtesting, wallet cluster scoring, and SQLite/PostgreSQL storage.
- `src/memory/experience_pool.py`: Embedded SQLite + vector trajectory pool (`memory/telemetry.db` & `memory/episodic_failures.jsonl`) storing `trade_trajectories`, `episodic_reflections`, and `heuristic_ledger` with ExpeL $k$-NN recall and FinMem `train`/`test` promotion gating.
- `src/orchestrator/local_harness.py`: Local LLM Antigravity SDK harness (`LocalOpenAIAgentConfig.lightweight()` / `LiteRTAgentConfig`) and 6-hour scheduled web-evolution trigger (`0 */6 * * *`).
- `.agents/agents/`: Custom subagent definitions (`post-trade-reflector.md`, `web-alpha-researcher.md`, `ace-curator.md`).
- `.agents/rules/`: Modular evolving rule files (`solana-heuristics.md`, `risk-invariants.md`, `solana-mev-forensics.md`).
- `.agents/skills/`: Open `agentskills.io` progressive-disclosure skill bundles (`experiential-learning-loop/`, `web-strategy-harvester/`).
- `artifacts/`: Standalone zero-dependency HTML/JS visualizations generated via `/generative_ui`.

## Setup, Build, and Test Commands
- Install Python deps: `uv pip install -r packages/forensics-py/requirements.txt`
- Run Self-Improvement Loop tests: `PYTHONPATH=. /home/titanagentik/sovereign-titan/.venv/bin/pytest -v tests/test_self_improvement_loop.py`
- Run Forensics unit tests: `PYTHONPATH=. /home/titanagentik/sovereign-titan/.venv/bin/pytest -x --tb=short packages/forensics-py/tests`
- Evaluate trajectory CLI: `PYTHONPATH=. /home/titanagentik/sovereign-titan/.venv/bin/python3 .agents/skills/experiential-learning-loop/scripts/evaluate_trajectory.py --help`
- Curate ExpeL rules CLI: `PYTHONPATH=. /home/titanagentik/sovereign-titan/.venv/bin/python3 .agents/skills/experiential-learning-loop/scripts/curate_rules.py --help`
- Validate web alpha CLI: `PYTHONPATH=. /home/titanagentik/sovereign-titan/.venv/bin/python3 .agents/skills/web-strategy-harvester/scripts/validate_web_alpha.py --help`
- Build Rust sniper engine: `cargo build --release --manifest-path packages/sniper-rs/Cargo.toml`
- Run Rust execution tests: `cargo test --manifest-path packages/sniper-rs/Cargo.toml -- --nocapture`

## Self-Improvement Paradigm (ACE + ExpeL + Voyager + FinMem)
- **No Monolithic Rewrites**: Never overwrite `AGENTS.md` or full rule files in place. Evolve context strictly via incremental ExpeL delta operations (`ADD`, `EDIT`, `UPVOTE`, `DOWNVOTE`) inside `.agents/rules/solana-heuristics.md` (`< 24 KB` per file, `< 20,000` tokens cumulative).
- **FinMem Two-Mode Gate**: All newly discovered heuristics or web-harvested scripts enter `heuristic_ledger` with `status='shadow'` (`mode='train'`). Promote to `status='active'` (`mode='test'`) only after positive counterfactual PnL validation across historical/shadow trajectories.
- **Strict No-Polling Rule**: When dispatching subagents via `invoke_subagent`, never use bash `sleep` loops or status polling; rely exclusively on Antigravity's Reactive Wakeup and `send_message`.

## Domain Isolation Scopes
- Subagent Forensics: Modify files ONLY in `packages/forensics-py/` and `packages/calibration/`.
- Subagent Execution: Modify files ONLY in `packages/sniper-rs/`.
- Subagent Self-Improvement (`@post-trade-reflector`, `@web-alpha-researcher`, `@ace-curator`): Modify files ONLY in `memory/`, `.agents/rules/solana-heuristics.md`, and `.agents/skills/`.
- Never modify `src/risk/risk_watchdog.py` or `anchor_profit_guard/programs/profit_guard/src/lib.rs`.

## Boundaries (Three-Tier Classification)
- **ALWAYS**: Run `pytest -x --tb=short` and `cargo check` before marking any task complete. Use `simulateBundle` before any Jito bundle submission logic. Include a `jitodontfront` prefixed pubkey in the first transaction of every Jito bundle. Keep `AGENTS.md` under 3,000 tokens.
- **ASK FIRST**: Before changing cluster score cutoffs, switching RPC endpoints, or invoking paid `x402` API calls exceeding `$1.00 USDC`.
- **NEVER**: Never launch automated browser testing loops (skip browser verification to prevent token burn). Never log or commit private keys, seed phrases, or `.env` files. Never include Jito tip accounts inside Address Lookup Tables (ALTs).

## Modular Rule Includes
@/packages/sniper-rs/src/jito_bundle.rs
@[Solana Heuristics Playbook](.agents/rules/solana-heuristics.md)
@[Hard Risk Invariants](.agents/rules/risk-invariants.md)
@[Solana MEV & Forensics Rules](.agents/rules/solana-mev-forensics.md)
@[Loop & Safety Guardrails](GUARDRAILS.md)
