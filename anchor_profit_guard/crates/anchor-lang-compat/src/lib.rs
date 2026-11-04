//! Sovereign Titan OS — High-Performance Anchor Prelude & Runtime Compatibility Layer.
//! Provides zero-overhead Anchor types, `Context<T>`, `Pubkey`, `AccountInfo`, `Account`,
//! `Signer`, `System`, `Result<T>`, `require!`, `declare_id!`, and SHA-256 8-byte
//! instruction/account discriminators compatible with `rustc 1.99+` and Solana Agave 4.5.

pub mod prelude {
    pub use crate::{
        declare_id, err, error, program, require, require_eq, require_gte, require_keys_eq,
        Account, AccountInfo, AnchorDeserialize, AnchorError, AnchorSerialize, Context, Key,
        Program, ProgramError, Pubkey, Result, Signer, System, UncheckedAccount,
    };
    pub use borsh::{BorshDeserialize, BorshSerialize};
    pub use serde::{Deserialize, Serialize};
}

pub use borsh::{BorshDeserialize as AnchorDeserialize, BorshSerialize as AnchorSerialize};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::cell::RefCell;
use std::fmt;
use std::rc::Rc;

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default, Serialize, Deserialize, AnchorSerialize, AnchorDeserialize)]
pub struct Pubkey(pub [u8; 32]);

impl Pubkey {
    pub const fn new_from_array(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    pub fn from_str_const(base58_str: &str) -> Self {
        let decoded = bs58::decode(base58_str)
            .into_vec()
            .unwrap_or_else(|_| vec![0u8; 32]);
        let mut arr = [0u8; 32];
        let copy_len = decoded.len().min(32);
        arr[..copy_len].copy_from_slice(&decoded[..copy_len]);
        Self(arr)
    }

    pub fn to_bytes(&self) -> [u8; 32] {
        self.0
    }
}

impl fmt::Display for Pubkey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", bs58::encode(self.0).into_string())
    }
}

impl fmt::Debug for Pubkey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Pubkey({})", bs58::encode(self.0).into_string())
    }
}

pub trait Key {
    fn key(&self) -> Pubkey;
}

impl Key for Pubkey {
    fn key(&self) -> Pubkey {
        *self
    }
}

#[derive(Clone, Debug)]
pub struct AccountInfo<'info> {
    pub key: Pubkey,
    pub is_signer: bool,
    pub is_writable: bool,
    pub lamports: Rc<RefCell<u64>>,
    pub data: Rc<RefCell<Vec<u8>>>,
    pub owner: Pubkey,
    pub executable: bool,
    pub _phantom: std::marker::PhantomData<&'info ()>,
}

impl<'info> AccountInfo<'info> {
    pub fn new(
        key: Pubkey,
        is_signer: bool,
        is_writable: bool,
        lamports: u64,
        data: Vec<u8>,
        owner: Pubkey,
        executable: bool,
    ) -> Self {
        Self {
            key,
            is_signer,
            is_writable,
            lamports: Rc::new(RefCell::new(lamports)),
            data: Rc::new(RefCell::new(data)),
            owner,
            executable,
            _phantom: std::marker::PhantomData,
        }
    }

    pub fn lamports(&self) -> u64 {
        *self.lamports.borrow()
    }

    pub fn try_borrow_lamports(&self) -> std::result::Result<std::cell::Ref<'_, u64>, ProgramError> {
        self.lamports
            .try_borrow()
            .map_err(|_| ProgramError::BorrowFailed)
    }

    pub fn try_borrow_mut_lamports(
        &self,
    ) -> std::result::Result<std::cell::RefMut<'_, u64>, ProgramError> {
        self.lamports
            .try_borrow_mut()
            .map_err(|_| ProgramError::BorrowFailed)
    }

    pub fn try_borrow_data(&self) -> std::result::Result<std::cell::Ref<'_, Vec<u8>>, ProgramError> {
        self.data.try_borrow().map_err(|_| ProgramError::BorrowFailed)
    }
}

impl<'info> Key for AccountInfo<'info> {
    fn key(&self) -> Pubkey {
        self.key
    }
}

#[derive(Clone, Debug)]
pub struct Signer<'info> {
    pub info: AccountInfo<'info>,
}

impl<'info> Signer<'info> {
    pub fn new(info: AccountInfo<'info>) -> Result<Self> {
        if !info.is_signer {
            return Err(ProgramError::MissingRequiredSignature.into());
        }
        Ok(Self { info })
    }

    pub fn lamports(&self) -> u64 {
        self.info.lamports()
    }

    pub fn to_account_info(&self) -> AccountInfo<'info> {
        self.info.clone()
    }
}

impl<'info> Key for Signer<'info> {
    fn key(&self) -> Pubkey {
        self.info.key
    }
}

#[derive(Clone, Debug)]
pub struct UncheckedAccount<'info> {
    pub info: AccountInfo<'info>,
}

impl<'info> UncheckedAccount<'info> {
    pub fn new(info: AccountInfo<'info>) -> Self {
        Self { info }
    }

    pub fn lamports(&self) -> u64 {
        self.info.lamports()
    }

    pub fn to_account_info(&self) -> AccountInfo<'info> {
        self.info.clone()
    }
}

impl<'info> Key for UncheckedAccount<'info> {
    fn key(&self) -> Pubkey {
        self.info.key
    }
}

#[derive(Clone, Debug)]
pub struct Account<'info, T> {
    pub info: AccountInfo<'info>,
    pub inner: T,
}

impl<'info, T> Account<'info, T> {
    pub fn new(info: AccountInfo<'info>, inner: T) -> Self {
        Self { info, inner }
    }

    pub fn to_account_info(&self) -> AccountInfo<'info> {
        self.info.clone()
    }
}

impl<'info, T> std::ops::Deref for Account<'info, T> {
    type Target = T;
    fn deref(&self) -> &Self::Target {
        &self.inner
    }
}

impl<'info, T> std::ops::DerefMut for Account<'info, T> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.inner
    }
}

impl<'info, T> Key for Account<'info, T> {
    fn key(&self) -> Pubkey {
        self.info.key
    }
}

#[derive(Clone, Debug, Default)]
pub struct System;

impl System {
    pub fn id() -> Pubkey {
        Pubkey([0u8; 32])
    }
}

#[derive(Clone, Debug)]
pub struct Program<'info, T> {
    pub info: AccountInfo<'info>,
    pub _marker: std::marker::PhantomData<T>,
}

impl<'info, T> Program<'info, T> {
    pub fn new(info: AccountInfo<'info>) -> Self {
        Self {
            info,
            _marker: std::marker::PhantomData,
        }
    }
}

pub struct Context<'a, 'b, 'c, 'info, T> {
    pub program_id: &'a Pubkey,
    pub accounts: &'b mut T,
    pub remaining_accounts: &'c [AccountInfo<'info>],
}

impl<'a, 'b, 'c, 'info, T> Context<'a, 'b, 'c, 'info, T> {
    pub fn new(
        program_id: &'a Pubkey,
        accounts: &'b mut T,
        remaining_accounts: &'c [AccountInfo<'info>],
    ) -> Self {
        Self {
            program_id,
            accounts,
            remaining_accounts,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProgramError {
    Custom(u32),
    MissingRequiredSignature,
    InsufficientFunds,
    InvalidAccountData,
    BorrowFailed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnchorError {
    pub error_name: String,
    pub error_code_number: u32,
    pub error_msg: String,
}

impl fmt::Display for AnchorError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "AnchorError [{} ({})]: {}",
            self.error_name, self.error_code_number, self.error_msg
        )
    }
}

impl std::error::Error for AnchorError {}

impl From<ProgramError> for AnchorError {
    fn from(err: ProgramError) -> Self {
        match err {
            ProgramError::Custom(code) => Self {
                error_name: "CustomProgramError".to_string(),
                error_code_number: code,
                error_msg: format!("Custom error code {}", code),
            },
            other => Self {
                error_name: format!("{:?}", other),
                error_code_number: 1,
                error_msg: format!("{:?}", other),
            },
        }
    }
}

pub type Result<T> = std::result::Result<T, AnchorError>;

/// Computes the canonical 8-byte Anchor SHA-256 discriminator (`sha256("<namespace>:<name>")[..8]`).
pub fn anchor_discriminator(namespace: &str, name: &str) -> [u8; 8] {
    let mut hasher = Sha256::new();
    hasher.update(format!("{}:{}", namespace, name).as_bytes());
    let digest = hasher.finalize();
    let mut out = [0u8; 8];
    out.copy_from_slice(&digest[..8]);
    out
}

pub mod system_program {
    use super::{AccountInfo, AnchorError, ProgramError, Result};

    pub struct Transfer<'info> {
        pub from: AccountInfo<'info>,
        pub to: AccountInfo<'info>,
    }

    pub fn transfer<'info>(from: &AccountInfo<'info>, to: &AccountInfo<'info>, lamports: u64) -> Result<()> {
        if !from.is_signer || !from.is_writable || !to.is_writable {
            return Err(AnchorError::from(ProgramError::MissingRequiredSignature));
        }
        let mut from_lamports = from
            .try_borrow_mut_lamports()
            .map_err(AnchorError::from)?;
        let mut to_lamports = to
            .try_borrow_mut_lamports()
            .map_err(AnchorError::from)?;
        if *from_lamports < lamports {
            return Err(AnchorError::from(ProgramError::InsufficientFunds));
        }
        *from_lamports -= lamports;
        *to_lamports = to_lamports
            .checked_add(lamports)
            .ok_or_else(|| AnchorError::from(ProgramError::InvalidAccountData))?;
        Ok(())
    }
}

#[macro_export]
macro_rules! declare_id {
    ($id:expr) => {
        pub const ID_STR: &str = $id;
        pub fn id() -> $crate::Pubkey {
            $crate::Pubkey::from_str_const($id)
        }
    };
}

#[macro_export]
macro_rules! require {
    ($invariant:expr, $err:expr $(,)?) => {
        if !($invariant) {
            return Err($crate::AnchorError::from($err));
        }
    };
}

#[macro_export]
macro_rules! require_gte {
    ($lhs:expr, $rhs:expr, $err:expr $(,)?) => {
        if ($lhs) < ($rhs) {
            return Err($crate::AnchorError::from($err));
        }
    };
}

#[macro_export]
macro_rules! require_eq {
    ($lhs:expr, $rhs:expr, $err:expr $(,)?) => {
        if ($lhs) != ($rhs) {
            return Err($crate::AnchorError::from($err));
        }
    };
}

#[macro_export]
macro_rules! require_keys_eq {
    ($lhs:expr, $rhs:expr, $err:expr $(,)?) => {
        if ($lhs) != ($rhs) {
            return Err($crate::AnchorError::from($err));
        }
    };
}

#[macro_export]
macro_rules! err {
    ($err:expr) => {
        Err($crate::AnchorError::from($err))
    };
}

#[macro_export]
macro_rules! error {
    ($err:expr) => {
        $crate::AnchorError::from($err)
    };
}

#[macro_export]
macro_rules! program {
    ($($tt:tt)*) => {
        $($tt)*
    };
}
