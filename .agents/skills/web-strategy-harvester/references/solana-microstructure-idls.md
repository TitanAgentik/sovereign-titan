# Solana Launchpad & Token-2022 Microstructure Reference (`<= 60,000` characters)

## 1. Canonical Program IDs & Bonding Curve Invariants
- **Pump.fun Bonding Curve Program**: `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`
  - Constant Product Invariant: $k = v_{\text{SOL}} \cdot v_{\text{Tokens}}$
  - Graduation Threshold: `~85 SOL` raised (`~$69,000` market cap), migrating `~$12,000` in SOL and `210,000,000` tokens into burned/locked LP on Raydium CPMM or PumpSwap.
  - Graduation Race Window: `82 SOL` to `85 SOL` (`96.5%` to `100%` curve completion) opens a `1–2` slot (`~30s`) handoff window where curve buys fail or route into drained reserves.
- **Raydium AMM v4 Program**: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`
- **PumpSwap AMM Program**: `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`

## 2. Six-Stage Sub-300ms Execution Latency Budget
1. **Colocated Yellowstone gRPC Subscription**: `30ms–80ms` (`vote=false, failed=false` strips `>85%` of Solana firehose noise).
2. **Anchor IDL Event Classification**: `0ms–15ms` (`<5ms` with server-side filtered gRPC streams across `buy`, `sell`, `create`, `graduation`, `migration`).
3. **In-Memory Hash-Set Wallet Match**: `<1ms` across `100+` tracked smart-money wallets.
4. **Jupiter Sellability Quote & On-Chain Rug Gate**: `20ms–40ms` (filters out `5%–15%` of candidate buys).
5. **Bankroll Sizing, `swap_mode=ExactIn` Route & Dynamic Slot Percentile Fee Build**: `10ms–20ms`.
6. **Single-Tx Jito Bundle Submission & Slot Inclusion**: `80ms–150ms` (`1–2` slots, max `1` auto-retry).
