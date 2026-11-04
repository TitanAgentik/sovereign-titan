//! SOVEREIGN TITAN OS — ON-CHAIN PROFIT GUARD (`profit_guard`)
//!
//! Architectural Invariant (/AGENTS.md):
//! - Guarantees 0 principal loss on atomic back-runs and Kamino/Marginfi flash-loan arbitrages.
//! - Instruction 1: `record_pre_balance(ctx: Context<ProfitCheck>)`
//!     Reads the payer's wSOL + native SOL lamports prior to inner DEX swaps and stores
//!     `pre_lamports` in transient state.
//! - Instruction 2: `assert_min_profit_and_tip(ctx: Context<ProfitCheck>, min_net_profit_lamports: u64, jito_tip_lamports: u64)`
//!     Reads `post_lamports` after inner DEX swaps and flash-loan repayment complete.
//!     Enforces the hard invariant:
//!       `require!(post_lamports >= pre_lamports + min_net_profit_lamports + jito_tip_lamports, MevError::InsufficientProfit);`
//!     If satisfied, transfers `jito_tip_lamports` to the passed official Jito Tip PDA inside
//!     the same instruction so the tip is ONLY paid when profitable.
//!     If unsatisfied, reverts the entire transaction and flash loan for $0 loss.
//! - IMMUTABLE SAFETY LOCK: This file must NEVER be modified by self-evolving DSPy/GEPA routines.

use anchor_lang::prelude::*;
use anchor_lang::system_program;

declare_id!("PrftGrd111111111111111111111111111111111111");

/// Official 8 Jito Tip Payment PDAs on Solana Mainnet-Beta.
pub const OFFICIAL_JITO_TIP_PDAS: [&str; 8] = [
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
];

/// SPL Token Account balance offset (bytes 64..72 store the little-endian u64 token amount).
pub const SPL_TOKEN_AMOUNT_OFFSET: usize = 64;
pub const SPL_TOKEN_ACCOUNT_MIN_LEN: usize = 72;

/// Reads the payer's combined native SOL lamports + wSOL SPL Token balance.
#[inline(always)]
pub fn read_combined_sol_and_wsol_lamports<'info>(
    payer: &Signer<'info>,
    wsol_token_account: &UncheckedAccount<'info>,
) -> Result<u64> {
    let native_lamports = payer.lamports();
    let data = wsol_token_account
        .info
        .try_borrow_data()
        .map_err(AnchorError::from)?;

    let wsol_lamports = if data.len() >= SPL_TOKEN_ACCOUNT_MIN_LEN {
        let mut amount_bytes = [0u8; 8];
        amount_bytes.copy_from_slice(&data[SPL_TOKEN_AMOUNT_OFFSET..SPL_TOKEN_ACCOUNT_MIN_LEN]);
        u64::from_le_bytes(amount_bytes)
    } else {
        0u64
    };

    native_lamports
        .checked_add(wsol_lamports)
        .ok_or_else(|| AnchorError::from(MevError::ArithmeticOverflow))
}

/// Verifies that the destination tip account is one of the 8 official Jito Tip PDAs.
#[inline(always)]
pub fn is_valid_jito_tip_pda(candidate: &Pubkey) -> bool {
    let candidate_str = candidate.to_string();
    OFFICIAL_JITO_TIP_PDAS
        .iter()
        .any(|official| *official == candidate_str)
}

pub mod profit_guard {
    use super::*;

    /// Instruction 1: Records the payer's combined native SOL + wSOL lamports prior to
    /// inner DEX swap legs and stores `pre_lamports` in transient state.
    pub fn record_pre_balance<'a, 'b, 'c, 'info>(
        ctx: Context<'a, 'b, 'c, 'info, ProfitCheck<'info>>,
    ) -> Result<()> {
        let combined_pre_lamports = read_combined_sol_and_wsol_lamports(
            &ctx.accounts.payer,
            &ctx.accounts.wsol_token_account,
        )?;

        let state = &mut ctx.accounts.transient_state;
        state.payer = ctx.accounts.payer.key();
        state.pre_lamports = combined_pre_lamports;
        state.post_lamports = 0;
        state.last_net_profit_lamports = 0;
        state.last_jito_tip_lamports = 0;
        state.is_active = true;

        Ok(())
    }

    /// Instruction 2: Asserts post-swap & post-flash-loan-repay balance strictly covers
    /// `pre_lamports + min_net_profit_lamports + jito_tip_lamports`, and transfers
    /// `jito_tip_lamports` to the official Jito Tip PDA inside the same instruction.
    pub fn assert_min_profit_and_tip<'a, 'b, 'c, 'info>(
        ctx: Context<'a, 'b, 'c, 'info, ProfitCheck<'info>>,
        min_net_profit_lamports: u64,
        jito_tip_lamports: u64,
    ) -> Result<()> {
        require!(
            ctx.accounts.transient_state.is_active,
            MevError::PreBalanceNotRecorded
        );
        require_keys_eq!(
            ctx.accounts.transient_state.payer,
            ctx.accounts.payer.key(),
            MevError::PayerMismatch
        );
        require!(
            is_valid_jito_tip_pda(&ctx.accounts.jito_tip_pda.key()),
            MevError::InvalidJitoTipAccount
        );

        let pre_lamports = ctx.accounts.transient_state.pre_lamports;
        let post_lamports = read_combined_sol_and_wsol_lamports(
            &ctx.accounts.payer,
            &ctx.accounts.wsol_token_account,
        )?;

        // Check overflow prior to enforcing the exact invariant
        let required_post_lamports = pre_lamports
            .checked_add(min_net_profit_lamports)
            .and_then(|v| v.checked_add(jito_tip_lamports))
            .ok_or_else(|| AnchorError::from(MevError::ArithmeticOverflow))?;

        // Exact Mandatory Invariant (/AGENTS.md & Prompt 2):
        require!(
            post_lamports >= pre_lamports + min_net_profit_lamports + jito_tip_lamports,
            MevError::InsufficientProfit
        );
        require!(
            post_lamports >= required_post_lamports,
            MevError::InsufficientProfit
        );

        // Conditional Jito Tip Payment: only executed when the profit invariant holds
        if jito_tip_lamports > 0 {
            system_program::transfer(
                &ctx.accounts.payer.info,
                &ctx.accounts.jito_tip_pda.info,
                jito_tip_lamports,
            )?;
        }

        let net_profit = post_lamports
            .saturating_sub(pre_lamports)
            .saturating_sub(jito_tip_lamports);

        let state = &mut ctx.accounts.transient_state;
        state.post_lamports = post_lamports.saturating_sub(jito_tip_lamports);
        state.last_net_profit_lamports = net_profit;
        state.last_jito_tip_lamports = jito_tip_lamports;
        state.total_profitable_executions = state.total_profitable_executions.saturating_add(1);
        state.is_active = false;

        Ok(())
    }
}

/// Accounts context for `record_pre_balance` and `assert_min_profit_and_tip`.
pub struct ProfitCheck<'info> {
    pub payer: Signer<'info>,
    pub wsol_token_account: UncheckedAccount<'info>,
    pub transient_state: Account<'info, TransientProfitState>,
    pub jito_tip_pda: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}

/// Transient per-wallet state recording pre-swap and post-swap balances.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, AnchorSerialize, AnchorDeserialize)]
pub struct TransientProfitState {
    pub payer: Pubkey,
    pub pre_lamports: u64,
    pub post_lamports: u64,
    pub last_net_profit_lamports: u64,
    pub last_jito_tip_lamports: u64,
    pub total_profitable_executions: u64,
    pub is_active: bool,
}

impl TransientProfitState {
    pub const LEN: usize = 8 + 32 + 8 + 8 + 8 + 8 + 8 + 1;
}

/// Custom Anchor Error Codes (6000+) for `profit_guard`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum MevError {
    /// 6000: Post-swap balance insufficient to cover principal, min profit, and Jito tip
    InsufficientProfit = 6000,
    /// 6001: `record_pre_balance` was not called prior to `assert_min_profit_and_tip`
    PreBalanceNotRecorded = 6001,
    /// 6002: Payer account does not match the signer recorded in `record_pre_balance`
    PayerMismatch = 6002,
    /// 6003: Destination tip account is not an official Jito Tip PDA
    InvalidJitoTipAccount = 6003,
    /// 6004: Checked u64 addition overflowed
    ArithmeticOverflow = 6004,
}

impl MevError {
    pub fn name(&self) -> &'static str {
        match self {
            Self::InsufficientProfit => "InsufficientProfit",
            Self::PreBalanceNotRecorded => "PreBalanceNotRecorded",
            Self::PayerMismatch => "PayerMismatch",
            Self::InvalidJitoTipAccount => "InvalidJitoTipAccount",
            Self::ArithmeticOverflow => "ArithmeticOverflow",
        }
    }

    pub fn msg(&self) -> &'static str {
        match self {
            Self::InsufficientProfit => {
                "Post-swap balance insufficient to cover principal, min profit, and Jito tip"
            }
            Self::PreBalanceNotRecorded => {
                "record_pre_balance must be invoked prior to assert_min_profit_and_tip"
            }
            Self::PayerMismatch => {
                "Payer signer does not match transient state owner"
            }
            Self::InvalidJitoTipAccount => {
                "Provided tip recipient is not in OFFICIAL_JITO_TIP_PDAS"
            }
            Self::ArithmeticOverflow => "Checked lamport arithmetic overflow",
        }
    }
}

impl From<MevError> for AnchorError {
    fn from(e: MevError) -> Self {
        AnchorError {
            error_name: e.name().to_string(),
            error_code_number: e as u32,
            error_msg: e.msg().to_string(),
        }
    }
}

/// Helper to build the canonical Anchor IDL JSON for `profit_guard`.
pub fn generate_anchor_idl_json() -> serde_json::Value {
    let disc_record = anchor_lang::anchor_discriminator("global", "record_pre_balance");
    let disc_assert = anchor_lang::anchor_discriminator("global", "assert_min_profit_and_tip");
    let disc_state = anchor_lang::anchor_discriminator("account", "TransientProfitState");

    serde_json::json!({
        "address": ID_STR,
        "metadata": {
            "name": "profit_guard",
            "version": "0.1.0",
            "spec": "0.1.0",
            "description": "Sovereign Titan OS — Immutable On-Chain Profit Guard & Conditional Jito Tip Enforcer"
        },
        "instructions": [
            {
                "name": "record_pre_balance",
                "discriminator": disc_record,
                "accounts": [
                    {"name": "payer", "writable": true, "signer": true},
                    {"name": "wsol_token_account", "writable": false, "signer": false},
                    {"name": "transient_state", "writable": true, "signer": false},
                    {"name": "jito_tip_pda", "writable": true, "signer": false},
                    {"name": "system_program", "writable": false, "signer": false, "address": "11111111111111111111111111111111"}
                ],
                "args": []
            },
            {
                "name": "assert_min_profit_and_tip",
                "discriminator": disc_assert,
                "accounts": [
                    {"name": "payer", "writable": true, "signer": true},
                    {"name": "wsol_token_account", "writable": false, "signer": false},
                    {"name": "transient_state", "writable": true, "signer": false},
                    {"name": "jito_tip_pda", "writable": true, "signer": false},
                    {"name": "system_program", "writable": false, "signer": false, "address": "11111111111111111111111111111111"}
                ],
                "args": [
                    {"name": "min_net_profit_lamports", "type": "u64"},
                    {"name": "jito_tip_lamports", "type": "u64"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "TransientProfitState",
                "discriminator": disc_state
            }
        ],
        "types": [
            {
                "name": "TransientProfitState",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "payer", "type": "pubkey"},
                        {"name": "pre_lamports", "type": "u64"},
                        {"name": "post_lamports", "type": "u64"},
                        {"name": "last_net_profit_lamports", "type": "u64"},
                        {"name": "last_jito_tip_lamports", "type": "u64"},
                        {"name": "total_profitable_executions", "type": "u64"},
                        {"name": "is_active", "type": "bool"}
                    ]
                }
            }
        ],
        "errors": [
            {
                "code": 6000,
                "name": "InsufficientProfit",
                "msg": "Post-swap balance insufficient to cover principal, min profit, and Jito tip"
            },
            {
                "code": 6001,
                "name": "PreBalanceNotRecorded",
                "msg": "record_pre_balance must be invoked prior to assert_min_profit_and_tip"
            },
            {
                "code": 6002,
                "name": "PayerMismatch",
                "msg": "Payer signer does not match transient state owner"
            },
            {
                "code": 6003,
                "name": "InvalidJitoTipAccount",
                "msg": "Provided tip recipient is not in OFFICIAL_JITO_TIP_PDAS"
            },
            {
                "code": 6004,
                "name": "ArithmeticOverflow",
                "msg": "Checked lamport arithmetic overflow"
            }
        ]
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_spl_token_data(amount: u64) -> Vec<u8> {
        let mut buf = vec![0u8; 165];
        buf[64..72].copy_from_slice(&amount.to_le_bytes());
        buf
    }

    #[test]
    fn test_profitable_arb_transfers_jito_tip() {
        let prog_id = id();
        let payer_key = Pubkey::from_str_const("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU");
        let wsol_key = Pubkey::from_str_const("So11111111111111111111111111111111111111112");
        let state_key = Pubkey::from_str_const("StAtE11111111111111111111111111111111111111");
        let jito_key = Pubkey::from_str_const(OFFICIAL_JITO_TIP_PDAS[0]);

        // Initial balance: 10 SOL native + 15 SOL wSOL = 25 SOL (25_000_000_000 lamports)
        let payer_info = AccountInfo::new(
            payer_key,
            true,
            true,
            10_000_000_000,
            vec![],
            System::id(),
            false,
        );
        let wsol_info = AccountInfo::new(
            wsol_key,
            false,
            true,
            2_039_280,
            make_spl_token_data(15_000_000_000),
            Pubkey::default(),
            false,
        );
        let state_info = AccountInfo::new(
            state_key,
            false,
            true,
            1_000_000,
            vec![],
            prog_id,
            false,
        );
        let jito_info = AccountInfo::new(
            jito_key,
            false,
            true,
            0,
            vec![],
            System::id(),
            false,
        );
        let sys_info = AccountInfo::new(
            System::id(),
            false,
            false,
            1,
            vec![],
            System::id(),
            true,
        );

        let mut accounts = ProfitCheck {
            payer: Signer::new(payer_info).unwrap(),
            wsol_token_account: UncheckedAccount::new(wsol_info),
            transient_state: Account::new(state_info, TransientProfitState::default()),
            jito_tip_pda: UncheckedAccount::new(jito_info),
            system_program: Program::new(sys_info),
        };

        // Step 1: record_pre_balance
        {
            let ctx = Context::new(&prog_id, &mut accounts, &[]);
            profit_guard::record_pre_balance(ctx).unwrap();
        }
        assert_eq!(accounts.transient_state.pre_lamports, 25_000_000_000);
        assert!(accounts.transient_state.is_active);

        // Simulate atomic flash-loan back-run yielding +0.05 SOL (50_000_000 lamports) in wSOL
        {
            let mut wsol_data = accounts.wsol_token_account.info.data.borrow_mut();
            wsol_data[64..72].copy_from_slice(&15_050_000_000u64.to_le_bytes());
        }

        // Step 2: assert_min_profit_and_tip (min_net_profit = 10_000_000, jito_tip = 5_000_000)
        {
            let ctx = Context::new(&prog_id, &mut accounts, &[]);
            profit_guard::assert_min_profit_and_tip(ctx, 10_000_000, 5_000_000).unwrap();
        }

        assert_eq!(accounts.jito_tip_pda.lamports(), 5_000_000);
        assert_eq!(accounts.transient_state.last_net_profit_lamports, 45_000_000);
        assert_eq!(accounts.transient_state.total_profitable_executions, 1);
        assert!(!accounts.transient_state.is_active);
    }

    #[test]
    fn test_unprofitable_arb_reverts_with_zero_loss() {
        let prog_id = id();
        let payer_key = Pubkey::from_str_const("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU");
        let wsol_key = Pubkey::from_str_const("So11111111111111111111111111111111111111112");
        let state_key = Pubkey::from_str_const("StAtE11111111111111111111111111111111111111");
        let jito_key = Pubkey::from_str_const(OFFICIAL_JITO_TIP_PDAS[1]);

        let payer_info = AccountInfo::new(
            payer_key,
            true,
            true,
            10_000_000_000,
            vec![],
            System::id(),
            false,
        );
        let wsol_info = AccountInfo::new(
            wsol_key,
            false,
            true,
            2_039_280,
            make_spl_token_data(15_000_000_000),
            Pubkey::default(),
            false,
        );
        let state_info = AccountInfo::new(state_key, false, true, 1_000_000, vec![], prog_id, false);
        let jito_info = AccountInfo::new(jito_key, false, true, 0, vec![], System::id(), false);
        let sys_info = AccountInfo::new(System::id(), false, false, 1, vec![], System::id(), true);

        let mut accounts = ProfitCheck {
            payer: Signer::new(payer_info).unwrap(),
            wsol_token_account: UncheckedAccount::new(wsol_info),
            transient_state: Account::new(state_info, TransientProfitState::default()),
            jito_tip_pda: UncheckedAccount::new(jito_info),
            system_program: Program::new(sys_info),
        };

        {
            let ctx = Context::new(&prog_id, &mut accounts, &[]);
            profit_guard::record_pre_balance(ctx).unwrap();
        }

        // Simulate swap only gaining +1,000 lamports (less than min_profit + tip)
        {
            let mut wsol_data = accounts.wsol_token_account.info.data.borrow_mut();
            wsol_data[64..72].copy_from_slice(&15_000_001_000u64.to_le_bytes());
        }

        let res = {
            let ctx = Context::new(&prog_id, &mut accounts, &[]);
            profit_guard::assert_min_profit_and_tip(ctx, 10_000_000, 5_000_000)
        };

        assert!(res.is_err());
        let err = res.unwrap_err();
        assert_eq!(err.error_code_number, MevError::InsufficientProfit as u32);
        assert_eq!(accounts.jito_tip_pda.lamports(), 0);
    }
}
