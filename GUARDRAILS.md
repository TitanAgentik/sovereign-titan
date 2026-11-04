# Loop & Safety Guardrails (`GUARDRAILS.md`)

## 1. Zero Browser-Looping Token Protection
- **Skip browser verification entirely.** Do not invoke Chrome DevTools or browser automation loops for UI testing; validate all modules exclusively via headless CLI (`pytest` and `cargo test`) to prevent multi-million-token validation loops.

## 2. Compilation & Test Loop Circuit Breaker
- Maximum 3 consecutive compilation or test retry cycles per subagent before escalating with exact traceback diagnostics.
- Always run `pytest -x --tb=short` and `cargo test --manifest-path packages/sniper-rs/Cargo.toml` deterministically offline.

## 3. Cryptographic & Mainnet Isolation Guardrails
- Never expose private keys, seed phrases, or `.env` secrets in logs, test fixtures, or MCP tool calls.
- Cap HTTP 402 (`x402`) Solana USDC micropayments at `0.01 USDC` per cached/live `cabal-hunter` scan and require human confirmation above `$1.00 USDC` cumulative spend.
- Enforce `jitodontfront` at Transaction 1 Index 0, exclude Jito tip accounts from Address Lookup Tables (ALTs), and require `simulateBundle` pre-flight success before any relay broadcast.
