---
trigger: model_decision
description: Evolving playbook of validated Solana memecoin execution heuristics, Pump.fun bonding curve thresholds, Jito tip rules, and Token-2022 anti-rug invariants maintained by the ACE Curator.
---

# Validated Solana Memecoin Trading & Anti-Rug Heuristics

## 1. Execution & Latency Rules (ExpeL Scored)
- `[RULE-EXEC-01 | Utility: +14 | Status: ACTIVE]` Maintain Yellowstone gRPC subscription filters `vote=false, failed=false` on program `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` and abort any copy-trade entry if cumulative pre-submission latency exceeds `250ms`, preventing `>800ms` fill degradation (`15%–40%` worse entry fills).
- `[RULE-EXEC-02 | Utility: +25 | Status: ACTIVE]` Graduation Race Gate: When bonding curve invariant k = vSOL * vTokens indicates reserve accumulation between 82 SOL and 85 SOL (96.5% to 100% completion), halt direct bonding-curve buys and wait for the on-chain Raydium CPMM / PumpSwap migration instruction discriminator before routing via Jupiter.
- `[RULE-EXEC-03 | Utility: +11 | Status: ACTIVE]` Dynamic Priority Fee & Jito Tip Scaling: Never use static SOL tips. Query current-slot priority fee percentiles; during quiet slots use the `50th` percentile, and when target wallet competition or slot congestion spikes, scale dynamically across the `40th` to `80th` percentile or cap tips at `1.5%` of trade principal, whichever is lower.
- `[RULE-EXEC-04 | Utility: +13 | Status: ACTIVE]` Jupiter Slippage Drift & ExactIn Protection: Build swap instructions with `swap_mode=ExactIn` and enforce the trader's true maximum slippage tolerance (`<= 250 bps`) against expected quote output at `t=0ms` so Jupiter deterministically aborts swaps that drift by `t=150ms` rather than executing `10%+` bad fills.
- `[RULE-EXEC-05 | Utility: +17 | Status: ACTIVE]` Sell-Side Execution Parity: Mirror target wallet sells and stop-loss triggers through the same sub-300ms colocated gRPC + Jito single-transaction bundle pipeline (80-150ms slot inclusion, max 1 auto-retry) to eliminate sell-side execution amnesia.

- `[RULE-GH-SIMD0216-01 | Utility: +4 | Status: ACTIVE]` GitHub Anza/Agave SIMD-0216 Compute-Budget Gate: Prepend SetLoadedAccountsDataSizeLimit(512_000) alongside SetComputeUnitLimit on all v0 Jito bundles to shrink default 64MB account-data allocation weight and boost scheduler priority fee efficiency by 35%-60% during Graduation Race slots.

- `[RULE-GH-JITOBAM-02 | Utility: +2 | Status: ACTIVE]` GitHub Jito BAM Knapsack Rule: Place jitodontfront111111111111111111111111111111 at read-only account index 0 on lead bundle legs and combine up to 5 independent positive-EV transactions to maximize tip-per-CU density in Stage-2 Block Engine auctions.

- `[RULE-GH-YELLOWSTONE-03 | Utility: +3 | Status: ACTIVE]` GitHub Yellowstone-gRPC Zero-Copy Ingest Rule: Enforce commitment=PROCESSED with vote=false, failed=false and stack-allocated O(1) Base58 LUT decoding to sustain >18,000 msg/s shred ingestion and <385us PDA derivation on Threadripper 9995WX Core Group A.

- `[RULE-ARXIV-DLMM-02 | Utility: +2 | Status: ACTIVE]` arXiv Avellaneda-Stoikov DLMM Rule: Concentrate Meteora DLMM liquidity in the 3 active bins only when volatility accumulator v_a triggers dynamic swap fees >= 250 bps (2.5%-10%), while maintaining a 100% delta-neutral short hedge on Drift V2 / PumpSwap.

## 2. On-Chain Rug & Token-2022 Heuristics
- `[RULE-RUG-01 | Utility: +27 | Status: ACTIVE]` Authority Invariant: Immediately reject any SPL mint where mint_authority != null or freeze_authority != null.
- `[RULE-RUG-02 | Utility: +20 | Status: ACTIVE]` Token-2022 Extension Gate: Inspect all Token-2022 mint accounts for transfer_hook and transfer_fee. Reject any token with a non-empty transfer_hook program address or a mutable transfer_fee configuration unless the hook program is on the verified protocol allowlist.
- `[RULE-RUG-03 | Utility: +18 | Status: ACTIVE]` Direct Vault LP Burn Check: Because DexScreener indexing lags fresh LP burns by 15-30 minutes, verify lpBurnedOrLocked directly via RPC account balance inspection on the Raydium/PumpSwap LP mint immediately upon graduation.
- `[RULE-RUG-04 | Utility: +15 | Status: ACTIVE]` Holder Concentration & Sybil Deployer Gate: Require Top-10 non-pool holders `<= 15%` of total supply and zero prior deployer rugs, running `scripts/sybil_check.py` to unmask bundled Jito multi-wallet distributions.
- `[RULE-RUG-05 | Utility: +12 | Status: ACTIVE]` Metaplex Metadata Mutability & Anti-Vampire Gate: Require `metadata_mutable: false` and unique metadata URI cross-verified against official social contract-address announcements before execution.
- `[RULE-ARXIV-HAWKES-01 | Utility: +2 | Status: ACTIVE]` arXiv Hawkes-VPIN Confluence Gate: Require Bayesian posterior win probability P(Win|E) >= 92.5% combining positive Hawkes order-arrival intensity, VPIN toxicity < 0.72, and >=3 independent smart-money cluster wallets before authorizing any Step-2 late-curve squeeze.
- `[RULE-HF-VISION-01 | Utility: +3 | Status: ACTIVE]` Hugging Face Multimodal Vision CA Gate: Extract Base58 contract addresses from KOL social screenshots via Port :8002 Qwen3.8-27B in <200ms, but hard-veto any image-extracted mint that fails Token-2022 transfer_hook/mint_authority verification or mimics an existing ticker.
- `[RULE-HF-BGEM3-02 | Utility: +2 | Status: ACTIVE]` Hugging Face BGE-M3 & FinMem Promotion Gate: Retrieve top-k winning historical trajectories via Port :8007 embeddings before tactical gate evaluation and require positive counterfactual PnL delta in train mode before promoting any shadow rule to active.
- `[RULE-INST-T22-SHIELD-01 | Utility: +3 | Status: ACTIVE]` Institutional Security Advisory Gate: Reject any Token-2022 mint carrying PermanentDelegate, unverified TransferHook CPI, or mutable TransferFeeConfig, and lock an instant +0.85% fee-covered break-even ratchet the moment any directional position reaches +3.0% unrealized gain.
