---
trigger: always_on
description: Immutable on-chain SPL authority, Token-2022 extension, and capital preservation risk invariants enforced across all execution and learning loops.
---

# Hard On-Chain Risk & Authority Invariants

1. **SPL Mint & Freeze Authority Invariant**: Both `mint_authority` and `freeze_authority` must be strictly `null` (revoked). Live `mint_authority` enables infinite supply printing; live `freeze_authority` traps holder Associated Token Accounts (ATAs).
2. **Token-2022 Safe Invariants**: Require `transfer_hook: []`, `fee_rate: 0`, and `non_transferable: "0"`. Any unverified `transfer_hook` program or mutable `transfer_fee` configuration is hard-blocked.
3. **Liquidity & Bonding Curve Invariant**: Enforce constant-product invariant $k = v_{\text{SOL}} \cdot v_{\text{Tokens}}$, verify `100%` LP burned/locked post-graduation directly on-chain, and block bonding-curve entries in the `96.5%–100%` (`82–85 SOL`) graduation race zone.
4. **FinMem Train-Before-Test Gate**: No newly synthesized heuristic or web-harvested script may execute with live capital (`mode='test'`) until it achieves positive counterfactual PnL across at least 5 trajectories in `mode='train'` (`status='shadow'` -> `status='active'`).
