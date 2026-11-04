---
trigger: model_decision
description: "Apply these quantitative rules whenever implementing Solana wallet clustering, Pump.fun bonding curve math, Cabal-Hunter risk checks, or Jito bundle execution."
---

# Solana Cabal Forensics and Slot-Zero Execution Specification

## 1. Zero-Percent Dev & Shadow Cluster Detection
- Treat creator wallet (`w_c`) holding 0% supply as a potential deception indicator.
- Implement Algorithm 1 (Bundle Bot Detection): Flag any token where non-creator wallets execute buy transactions inside `b_launch` (Slot 0).
- Implement Algorithm 2 (Sniper Bot Detection): Flag non-creator buys within `b_launch < tx.block <= b_launch + 5`.
- Multi-Hop Graph Trace: For every new launch, trace `w_c` and the top 100 buyers backward 1 to 5 hops in Python NetworkX. Call Helius `POST /v1/wallet/batch-identity` (up to 100 addresses per batch) to whitelist and prune centralized exchange (CEX) hot wallets and public bridges from false-positive cluster merging.
- Apply Louvain community detection (`networkx.community.louvain_communities`) weighted by SOL transfer volume and temporal proximity to group shadow team wallets into a single `cluster_id`.

## 2. Serial Runner Qualification Filter
- Index historical Pump.fun migrations (85 SOL threshold to PumpSwap/Raydium).
- Classify a `cluster_id` as a `SERIAL_RUNNER_SYNDICATE` only if:
  1. Historical token graduation rate > 25% across >= 5 launches.
  2. Cluster member wallets exhibit average holding time > 10 minutes, historical win rate between 60% and 70%, and median realized return of 2x to 5x.
- Vet every target mint via Cabal-Hunter MCP (`check_cabal_risk`). If `cabal_score >= 65` AND the cluster is NOT a whitelisted `SERIAL_RUNNER_SYNDICATE`, abort the snipe immediately. If it IS a whitelisted runner syndicate, store `evidence_txs[]` and cluster member addresses as real-time sell-tripwires.

## 3. Slot-Zero Stack & Jito Bundle Rules
- Ingest live chain state exclusively via Yellowstone gRPC (Dragon's Mouth Protobuf stream) subscribing to the Pump.fun program and watched `SERIAL_RUNNER_SYNDICATE` shadow wallets.
- Compute PumpSwap and Raydium pool addresses deterministically via local PDA derivation from the token mint; do not make blocking RPC calls at fire-time.
- Jito Tipping & Fee Split:
  - For single-tx `sendTransaction`, enforce a 70% Solana Priority Fee / 30% Jito Tip split.
  - For multi-tx `sendBundle` (max 5 transactions), poll `https://bundles.jito.wtf/api/v1/bundles/tip_floor` and scale the tip dynamically (10x to 50x multiplier) based on trailing 50-block slot-leader acceptance data and bonding curve fill velocity.
- Forbidden Bundle Patterns: Never structure `[tip, tx_with_dont_front]`. Place the `jitodontfront` read-only account in Transaction 1 (the swap) and the random Jito tip account transfer instruction at the end of the final transaction without using Address Lookup Tables.
- Broadcast bundles in parallel across Jito Block Engine regions (NY, Frankfurt, Amsterdam, Tokyo, Salt Lake City) plus QuickNode Lil' JIT and Astralane relays.
