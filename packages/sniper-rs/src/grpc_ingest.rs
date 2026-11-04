//! Step 2.1 — Yellowstone gRPC (`Dragon's Mouth` `.so` Geyser Plugin) Intra-Slot Streamer
//! & Zero-RPC Deterministic Fire-Time PDA Calculator.
//!
//! Eliminates standard HTTP JSON-RPC polling and `getProgramAccounts` latency by streaming
//! raw validator bank account writes directly over HTTP/2 via Triton's Yellowstone gRPC
//! (`Dragon's Mouth`) and deriving all bonding-curve / AMM pool Program Derived Addresses
//! (PDAs) in local memory with `blocking_rpc_calls_at_fire_time == 0`.

use std::collections::{HashMap, HashSet};
use std::time::Instant;

/// Official Pump.fun Bonding Curve Program ID on Solana Mainnet-Beta.
pub const PUMPFUN_BONDING_CURVE_PROGRAM_ID: &str = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";

/// Official PumpSwap AMM Program ID on Solana Mainnet-Beta.
pub const PUMPSWAP_AMM_PROGRAM_ID: &str = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA";

/// Official Raydium Liquidity Pool V4 Program ID on Solana Mainnet-Beta.
pub const RAYDIUM_AMM_V4_PROGRAM_ID: &str = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8";

/// Official Raydium Concentrated Liquidity (CLMM) Program ID on Solana Mainnet-Beta.
pub const RAYDIUM_CLMM_PROGRAM_ID: &str = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK";

/// Official Orca Whirlpool Concentrated Liquidity Program ID on Solana Mainnet-Beta.
pub const ORCA_WHIRLPOOL_PROGRAM_ID: &str = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc";

/// Official Meteora DLMM Program ID on Solana Mainnet-Beta.
pub const METEORA_DLMM_PROGRAM_ID: &str = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo";

/// Official Phoenix CLOB Program ID on Solana Mainnet-Beta.
pub const PHOENIX_CLOB_PROGRAM_ID: &str = "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY";

/// Official Lifinity V2 Proactive Market Maker Program ID on Solana Mainnet-Beta.
pub const LIFINITY_V2_PROGRAM_ID: &str = "2wT8Yq49kHgDzXuPxZSaeLaH1qbmGXtEyPy64bL7aD3c";

/// Official Sanctum S-Controller (Infinity / LST Pool) Program ID on Solana Mainnet-Beta.
pub const SANCTUM_S_CONTROLLER_PROGRAM_ID: &str = "5ocnV1qiCgaQR8Jb8xWnVbApfaygJ8tNoZfgPwsgx9kx";

/// Official MarginFi V2 Lending Program ID on Solana Mainnet-Beta.
pub const MARGINFI_V2_PROGRAM_ID: &str = "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA";

/// Official Kamino Lend (KLend) Program ID on Solana Mainnet-Beta.
pub const KAMINO_KLEND_PROGRAM_ID: &str = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD";

/// Official Save (formerly Solend) Lending Program ID on Solana Mainnet-Beta.
pub const SAVE_SOLEND_PROGRAM_ID: &str = "So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo";

/// Wrapped SOL (WSOL) canonical Mint address.
pub const WSOL_MINT_ADDRESS: &str = "So11111111111111111111111111111111111111112";

/// Standard Pump.fun total token supply (1,000,000,000 tokens).
pub const PUMPFUN_TOTAL_SUPPLY: u64 = 1_000_000_000;

/// Standard Pump.fun bonding curve graduation threshold (`85.0 SOL` raised, `~$69,000` market cap).
pub const PUMPFUN_GRADUATION_SOL_THRESHOLD: f64 = 85.0;

/// Approximate USD market cap at Pump.fun bonding curve graduation (`~$69,000`).
pub const PUMPFUN_GRADUATION_MCAP_USD: f64 = 69_000.0;

/// Solana ProgramDerivedAddress domain-separation marker.
const PDA_MARKER: &[u8] = b"ProgramDerivedAddress";

/// Base58 alphabet used by Solana public keys.
const BASE58_ALPHABET: &[u8; 58] = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

const fn build_base58_decode_lut() -> [i8; 256] {
    let mut lut = [-1i8; 256];
    let mut i = 0usize;
    while i < 58 {
        lut[BASE58_ALPHABET[i] as usize] = i as i8;
        i += 1;
    }
    lut
}

/// Compile-time 256-entry O(1) lookup table for Base58 decoding (`-1` for invalid ASCII bytes).
pub const BASE58_DECODE_LUT: [i8; 256] = build_base58_decode_lut();

/// Compile-time deterministic Base58 decoder into a 32-byte array.
pub const fn decode_base58_32_const(input: &str) -> [u8; 32] {
    let raw = input.as_bytes();
    let mut buf = [0u8; 48];
    let mut buf_len = 0usize;
    let mut idx = 0usize;
    while idx < raw.len() {
        let val = BASE58_DECODE_LUT[raw[idx] as usize];
        if val < 0 {
            panic!("Invalid Base58 character in compile-time pubkey constant");
        }
        let mut carry = val as u32;
        let mut j = 0usize;
        while j < buf_len {
            carry += (buf[j] as u32) * 58;
            buf[j] = (carry & 0xff) as u8;
            carry >>= 8;
            j += 1;
        }
        while carry > 0 {
            buf[buf_len] = (carry & 0xff) as u8;
            buf_len += 1;
            carry >>= 8;
        }
        idx += 1;
    }

    let mut leading_ones = 0usize;
    while leading_ones < raw.len() && raw[leading_ones] == b'1' {
        leading_ones += 1;
    }
    if leading_ones + buf_len > 32 {
        panic!("Decoded Base58 pubkey constant exceeds 32 bytes");
    }
    let mut out = [0u8; 32];
    let start = 32 - buf_len;
    let mut k = 0usize;
    while k < buf_len {
        out[start + k] = buf[buf_len - 1 - k];
        k += 1;
    }
    out
}

/// Pre-decoded 32-byte constant for Pump.fun Bonding Curve Program ID.
pub const PUMPFUN_PROGRAM_ID_BYTES: [u8; 32] =
    decode_base58_32_const(PUMPFUN_BONDING_CURVE_PROGRAM_ID);

/// Pre-decoded 32-byte constant for PumpSwap AMM Program ID.
pub const PUMPSWAP_PROGRAM_ID_BYTES: [u8; 32] = decode_base58_32_const(PUMPSWAP_AMM_PROGRAM_ID);

/// Pre-decoded 32-byte constant for Raydium AMM V4 Program ID.
pub const RAYDIUM_V4_PROGRAM_ID_BYTES: [u8; 32] = decode_base58_32_const(RAYDIUM_AMM_V4_PROGRAM_ID);

/// Pre-decoded 32-byte constant for Wrapped SOL (WSOL) Mint.
pub const WSOL_MINT_BYTES: [u8; 32] = decode_base58_32_const(WSOL_MINT_ADDRESS);

/// Pure-Rust FIPS 180-4 SHA-256 round constants.
const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

/// Computes a deterministic SHA-256 digest in pure Rust with zero external dependencies,
/// using a stack buffer (`[u8; 256]`) for typical PDA seed inputs to avoid heap allocations.
pub fn sha256_digest(chunks: &[&[u8]]) -> [u8; 32] {
    let mut state: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];

    let total_len: usize = chunks.iter().map(|c| c.len()).sum();
    let bit_len = (total_len as u64) * 8;

    let mut stack_buf = [0u8; 256];
    let mut heap_buf: Vec<u8> = Vec::new();

    let msg_slice: &[u8] = if total_len + 72 <= stack_buf.len() {
        let mut pos = 0usize;
        for chunk in chunks {
            stack_buf[pos..pos + chunk.len()].copy_from_slice(chunk);
            pos += chunk.len();
        }
        stack_buf[pos] = 0x80;
        pos += 1;
        while (pos % 64) != 56 {
            stack_buf[pos] = 0x00;
            pos += 1;
        }
        stack_buf[pos..pos + 8].copy_from_slice(&bit_len.to_be_bytes());
        pos += 8;
        &stack_buf[..pos]
    } else {
        heap_buf.reserve(total_len + 72);
        for chunk in chunks {
            heap_buf.extend_from_slice(chunk);
        }
        heap_buf.push(0x80);
        while (heap_buf.len() % 64) != 56 {
            heap_buf.push(0x00);
        }
        heap_buf.extend_from_slice(&bit_len.to_be_bytes());
        &heap_buf[..]
    };

    for block in msg_slice.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (i, word) in w.iter_mut().take(16).enumerate() {
            let offset = i * 4;
            *word = u32::from_be_bytes([
                block[offset],
                block[offset + 1],
                block[offset + 2],
                block[offset + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }

        let mut a = state[0];
        let mut b = state[1];
        let mut c = state[2];
        let mut d = state[3];
        let mut e = state[4];
        let mut f = state[5];
        let mut g = state[6];
        let mut h = state[7];

        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(SHA256_K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }

        state[0] = state[0].wrapping_add(a);
        state[1] = state[1].wrapping_add(b);
        state[2] = state[2].wrapping_add(c);
        state[3] = state[3].wrapping_add(d);
        state[4] = state[4].wrapping_add(e);
        state[5] = state[5].wrapping_add(f);
        state[6] = state[6].wrapping_add(g);
        state[7] = state[7].wrapping_add(h);
    }

    let mut out = [0u8; 32];
    for (i, word) in state.iter().enumerate() {
        let bytes = word.to_be_bytes();
        out[i * 4..i * 4 + 4].copy_from_slice(&bytes);
    }
    out
}

/// Encodes a 32-byte Solana public key into a canonical Base58 string.
pub fn encode_base58(bytes: &[u8; 32]) -> String {
    let mut zeros = 0usize;
    while zeros < bytes.len() && bytes[zeros] == 0 {
        zeros += 1;
    }
    let mut digits = [0u8; 44];
    let mut digits_len = 0usize;
    for &byte in &bytes[zeros..] {
        let mut carry = byte as u32;
        for d in digits[..digits_len].iter_mut() {
            carry += (*d as u32) << 8;
            *d = (carry % 58) as u8;
            carry /= 58;
        }
        while carry > 0 {
            digits[digits_len] = (carry % 58) as u8;
            digits_len += 1;
            carry /= 58;
        }
    }
    let mut result = String::with_capacity(zeros + digits_len);
    for _ in 0..zeros {
        result.push('1');
    }
    for &d in digits[..digits_len].iter().rev() {
        result.push(BASE58_ALPHABET[d as usize] as char);
    }
    result
}

/// Decodes a Base58 string (or falls back to SHA-256 domain hash for symbolic test identifiers)
/// into a 32-byte array using a stack buffer (`[u8; 48]`) and `BASE58_DECODE_LUT` with zero heap allocation.
pub fn decode_base58_32(input: &str) -> [u8; 32] {
    if input.is_empty() || input.len() > 64 {
        return sha256_digest(&[b"solana-pubkey-fallback:", input.as_bytes()]);
    }
    let mut buf = [0u8; 48];
    let mut buf_len = 0usize;
    for ch in input.bytes() {
        let val = BASE58_DECODE_LUT[ch as usize];
        if val < 0 {
            return sha256_digest(&[b"solana-pubkey-fallback:", input.as_bytes()]);
        }
        let mut carry = val as u32;
        for b in buf[..buf_len].iter_mut() {
            carry += (*b as u32) * 58;
            *b = (carry & 0xff) as u8;
            carry >>= 8;
        }
        while carry > 0 {
            if buf_len >= buf.len() {
                return sha256_digest(&[b"solana-pubkey-oversize:", input.as_bytes()]);
            }
            buf[buf_len] = (carry & 0xff) as u8;
            buf_len += 1;
            carry >>= 8;
        }
    }

    let leading_ones = input.bytes().take_while(|&b| b == b'1').count();
    let total_len = leading_ones + buf_len;
    if total_len > 32 {
        return sha256_digest(&[b"solana-pubkey-oversize:", input.as_bytes()]);
    }

    let mut out = [0u8; 32];
    let start = 32 - buf_len;
    for i in 0..buf_len {
        out[start + i] = buf[buf_len - 1 - i];
    }
    out
}

const MASK_51: u64 = (1u64 << 51) - 1;

/// Ed25519 twisted Edwards curve constant `d = -121665 / 121666 mod (2^255 - 19)` in 5x51-bit limbs.
const ED25519_D: [u64; 5] = [
    929955233495203,
    466365720129213,
    1662059464998953,
    2033849074728123,
    1442794654840575,
];

#[inline(always)]
fn is_non_canonical_ed25519_y(candidate: &[u8; 32]) -> bool {
    if (candidate[31] & 0x7f) != 0x7f || candidate[0] < 0xed {
        return false;
    }
    let mut i = 1usize;
    while i < 31 {
        if candidate[i] != 0xff {
            return false;
        }
        i += 1;
    }
    true
}

#[inline(always)]
fn fe_from_bytes(bytes: &[u8; 32]) -> [u64; 5] {
    let load8 = |offset: usize| -> u64 {
        let mut buf = [0u8; 8];
        buf.copy_from_slice(&bytes[offset..offset + 8]);
        u64::from_le_bytes(buf)
    };
    let l0 = load8(0) & MASK_51;
    let l1 = (load8(6) >> 3) & MASK_51;
    let l2 = (load8(12) >> 6) & MASK_51;
    let l3 = (load8(19) >> 1) & MASK_51;
    let l4 = (load8(24) >> 12) & MASK_51;
    [l0, l1, l2, l3, l4]
}

#[inline(always)]
fn fe_carry(mut h: [u64; 5]) -> [u64; 5] {
    for _ in 0..2 {
        let c0 = h[0] >> 51;
        h[0] &= MASK_51;
        h[1] += c0;
        let c1 = h[1] >> 51;
        h[1] &= MASK_51;
        h[2] += c1;
        let c2 = h[2] >> 51;
        h[2] &= MASK_51;
        h[3] += c2;
        let c3 = h[3] >> 51;
        h[3] &= MASK_51;
        h[4] += c3;
        let c4 = h[4] >> 51;
        h[4] &= MASK_51;
        h[0] += c4 * 19;
    }
    h
}

#[inline(always)]
fn fe_reduce_canonical(h: [u64; 5]) -> [u64; 5] {
    let mut r = fe_carry(h);
    let mut q = (r[0].wrapping_add(19)) >> 51;
    q = (r[1].wrapping_add(q)) >> 51;
    q = (r[2].wrapping_add(q)) >> 51;
    q = (r[3].wrapping_add(q)) >> 51;
    q = (r[4].wrapping_add(q)) >> 51;

    r[0] = r[0].wrapping_add(19 * q);
    let c0 = r[0] >> 51;
    r[0] &= MASK_51;
    r[1] = r[1].wrapping_add(c0);
    let c1 = r[1] >> 51;
    r[1] &= MASK_51;
    r[2] = r[2].wrapping_add(c1);
    let c2 = r[2] >> 51;
    r[2] &= MASK_51;
    r[3] = r[3].wrapping_add(c2);
    let c3 = r[3] >> 51;
    r[3] &= MASK_51;
    r[4] = (r[4].wrapping_add(c3)) & MASK_51;
    r
}

#[inline(always)]
fn fe_add(a: &[u64; 5], b: &[u64; 5]) -> [u64; 5] {
    fe_carry([
        a[0] + b[0],
        a[1] + b[1],
        a[2] + b[2],
        a[3] + b[3],
        a[4] + b[4],
    ])
}

#[inline(always)]
fn fe_sub(a: &[u64; 5], b: &[u64; 5]) -> [u64; 5] {
    // Add 2*p before subtraction to avoid unsigned underflow
    const TWO_P0: u64 = 0x000f_ffff_ffff_ffda;
    const TWO_PN: u64 = 0x000f_ffff_ffff_fffe;
    fe_carry([
        (a[0] + TWO_P0) - b[0],
        (a[1] + TWO_PN) - b[1],
        (a[2] + TWO_PN) - b[2],
        (a[3] + TWO_PN) - b[3],
        (a[4] + TWO_PN) - b[4],
    ])
}

#[inline(always)]
fn fe_mul(a: &[u64; 5], b: &[u64; 5]) -> [u64; 5] {
    let a0 = a[0] as u128;
    let a1 = a[1] as u128;
    let a2 = a[2] as u128;
    let a3 = a[3] as u128;
    let a4 = a[4] as u128;

    let b0 = b[0] as u128;
    let b1 = b[1] as u128;
    let b2 = b[2] as u128;
    let b3 = b[3] as u128;
    let b4 = b[4] as u128;

    let b1_19 = b1 * 19;
    let b2_19 = b2 * 19;
    let b3_19 = b3 * 19;
    let b4_19 = b4 * 19;

    let mut t0 = a0 * b0 + a1 * b4_19 + a2 * b3_19 + a3 * b2_19 + a4 * b1_19;
    let mut t1 = a0 * b1 + a1 * b0 + a2 * b4_19 + a3 * b3_19 + a4 * b2_19;
    let mut t2 = a0 * b2 + a1 * b1 + a2 * b0 + a3 * b4_19 + a4 * b3_19;
    let mut t3 = a0 * b3 + a1 * b2 + a2 * b1 + a3 * b0 + a4 * b4_19;
    let mut t4 = a0 * b4 + a1 * b3 + a2 * b2 + a3 * b1 + a4 * b0;

    let mask = MASK_51 as u128;
    let c0 = t0 >> 51;
    t0 &= mask;
    t1 += c0;
    let c1 = t1 >> 51;
    t1 &= mask;
    t2 += c1;
    let c2 = t2 >> 51;
    t2 &= mask;
    t3 += c2;
    let c3 = t3 >> 51;
    t3 &= mask;
    t4 += c3;
    let c4 = t4 >> 51;
    t4 &= mask;
    t0 += c4 * 19;

    fe_carry([t0 as u64, t1 as u64, t2 as u64, t3 as u64, t4 as u64])
}

/// Evaluates whether a 32-byte candidate lies off the Ed25519 curve so it is a valid Solana PDA.
/// Uses exact GF(2^255 - 19) limb arithmetic and Euler's criterion on
/// `w = (y^2 - 1) * (d * y^2 + 1) (mod p)`, which has the same Legendre symbol as `x^2 = (y^2 - 1) / (d * y^2 + 1)`.
fn is_off_ed25519_curve_deterministic(candidate: &[u8; 32]) -> bool {
    if is_non_canonical_ed25519_y(candidate) {
        return true;
    }

    let one: [u64; 5] = [1, 0, 0, 0, 0];
    let p_minus_one: [u64; 5] = [
        0x0007_ffff_ffff_ffec,
        MASK_51,
        MASK_51,
        MASK_51,
        MASK_51,
    ];

    let y = fe_from_bytes(candidate);
    let y2 = fe_mul(&y, &y);
    let u = fe_sub(&y2, &one);
    let v = fe_add(&fe_mul(&ED25519_D, &y2), &one);
    let w = fe_reduce_canonical(fe_mul(&u, &v));

    if w == [0, 0, 0, 0, 0] {
        // x^2 == 0 => x == 0; in RFC 8032 Ed25519 decompression, x == 0 with negative sign bit is invalid (off-curve)
        return (candidate[31] >> 7) == 1;
    }

    // Compute w^((p - 1) / 2) mod p where (p - 1) / 2 = 2^254 - 10.
    // In binary, 2^254 - 10 has bits 253..=4 set to 1, bit 3 set to 0, bits 2..=1 set to 1, and bit 0 set to 0.
    let mut result = one;
    for bit_idx in (0..254).rev() {
        result = fe_mul(&result, &result);
        let bit_is_one = bit_idx != 3 && bit_idx != 0;
        if bit_is_one {
            result = fe_mul(&result, &w);
        }
    }
    let euler = fe_reduce_canonical(result);
    euler == p_minus_one
}

/// Pure-Rust implementation of Solana's `Pubkey::find_program_address(seeds, program_id)`.
/// Iterates `bump` from `255` down to `0` and hashes `[seeds..., &[bump], program_id, b"ProgramDerivedAddress"]`
/// until a valid off-curve Program Derived Address is found.
pub fn find_program_address(seeds: &[&[u8]], program_id: &[u8; 32]) -> ([u8; 32], u8) {
    for bump in (0..=255u8).rev() {
        let bump_slice = [bump];
        let candidate = if seeds.len() + 3 <= 8 {
            let mut stack_chunks: [&[u8]; 8] = [&[]; 8];
            let mut idx = 0usize;
            for seed in seeds {
                stack_chunks[idx] = seed;
                idx += 1;
            }
            stack_chunks[idx] = &bump_slice;
            stack_chunks[idx + 1] = program_id;
            stack_chunks[idx + 2] = PDA_MARKER;
            sha256_digest(&stack_chunks[..idx + 3])
        } else {
            let mut chunks: Vec<&[u8]> = Vec::with_capacity(seeds.len() + 3);
            for seed in seeds {
                chunks.push(seed);
            }
            chunks.push(&bump_slice);
            chunks.push(program_id);
            chunks.push(PDA_MARKER);
            sha256_digest(&chunks)
        };
        if is_off_ed25519_curve_deterministic(&candidate) {
            return (candidate, bump);
        }
    }
    // Fallback (mathematically unreachable with 256 trials at p=0.5 per trial)
    let bump_slice = [0u8];
    let first_seed: &[u8] = seeds.first().copied().unwrap_or(b"");
    let candidate = sha256_digest(&[first_seed, &bump_slice, program_id, PDA_MARKER]);
    (candidate, 0)
}

/// Result of a fire-time zero-RPC Program Derived Address computation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PdaDerivation {
    /// Base58-encoded Program Derived Address.
    pub pda_address: String,
    /// Raw 32-byte Program Derived Address.
    pub pda_bytes: [u8; 32],
    /// Canonical bump seed (`255` down to `0`).
    pub bump_seed: u8,
    /// Program ID that owns or derives this PDA.
    pub program_id: String,
    /// Human-readable seed labels used in the derivation.
    pub seeds_used: Vec<String>,
    /// Number of blocking network RPC calls made at fire time (strictly `0`).
    pub blocking_rpc_calls_at_fire_time: u32,
    /// Execution latency in nanoseconds (sub-microsecond local memory execution).
    pub compute_latency_ns: u64,
}

/// Derives the canonical Pump.fun bonding curve PDA and associated bonding curve vault PDA
/// for a given token `mint` in local memory (`blocking_rpc_calls_at_fire_time == 0`).
///
/// Seeds: `[b"bonding-curve", mint_pubkey_bytes]` under program `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`.
pub fn derive_pumpfun_bonding_curve_pda(mint: &str) -> PdaDerivation {
    let started = Instant::now();
    let mint_bytes = decode_base58_32(mint);
    let (pda_bytes, bump_seed) =
        find_program_address(&[b"bonding-curve", &mint_bytes], &PUMPFUN_PROGRAM_ID_BYTES);
    let pda_address = encode_base58(&pda_bytes);
    let compute_latency_ns = started.elapsed().as_nanos() as u64;

    PdaDerivation {
        pda_address,
        pda_bytes,
        bump_seed,
        program_id: PUMPFUN_BONDING_CURVE_PROGRAM_ID.to_string(),
        seeds_used: vec!["bonding-curve".to_string(), mint.to_string()],
        blocking_rpc_calls_at_fire_time: 0,
        compute_latency_ns,
    }
}

/// Derives the canonical PumpSwap AMM (`pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`) or
/// Raydium AMM V4 (`675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`) liquidity pool PDA
/// in local memory (`blocking_rpc_calls_at_fire_time == 0`).
pub fn derive_pumpswap_or_raydium_pool_pda(
    mint: &str,
    quote_mint: &str,
    venue: &str,
) -> PdaDerivation {
    let started = Instant::now();
    let mint_bytes = decode_base58_32(mint);
    let quote_bytes = if quote_mint == WSOL_MINT_ADDRESS {
        WSOL_MINT_BYTES
    } else {
        decode_base58_32(quote_mint)
    };

    let (program_id, program_bytes, seed_prefix): (&str, [u8; 32], &[u8]) =
        if venue.eq_ignore_ascii_case("raydium") || venue == RAYDIUM_AMM_V4_PROGRAM_ID {
            (
                RAYDIUM_AMM_V4_PROGRAM_ID,
                RAYDIUM_V4_PROGRAM_ID_BYTES,
                b"amm_associated_seed",
            )
        } else {
            (PUMPSWAP_AMM_PROGRAM_ID, PUMPSWAP_PROGRAM_ID_BYTES, b"pool")
        };

    let (pda_bytes, bump_seed) =
        find_program_address(&[seed_prefix, &mint_bytes, &quote_bytes], &program_bytes);
    let pda_address = encode_base58(&pda_bytes);
    let compute_latency_ns = started.elapsed().as_nanos() as u64;

    PdaDerivation {
        pda_address,
        pda_bytes,
        bump_seed,
        program_id: program_id.to_string(),
        seeds_used: vec![
            String::from_utf8_lossy(seed_prefix).to_string(),
            mint.to_string(),
            quote_mint.to_string(),
        ],
        blocking_rpc_calls_at_fire_time: 0,
        compute_latency_ns,
    }
}

/// Computes bonding curve fill velocity $V_{\text{curve}} = \Delta \text{SOL} / \Delta t$ (in SOL/sec).
pub fn compute_curve_fill_velocity(delta_sol: f64, delta_seconds: f64) -> f64 {
    if delta_seconds <= 1e-9 || !delta_sol.is_finite() || !delta_seconds.is_finite() {
        return 0.0;
    }
    (delta_sol / delta_seconds).max(0.0)
}

/// Real-time Pump.fun bonding curve state evaluated from a Yellowstone gRPC `Dragon's Mouth` account write.
#[derive(Debug, Clone, PartialEq)]
pub struct BondingCurveEvaluation {
    /// Token mint address.
    pub mint: String,
    /// Deterministically derived bonding curve PDA (`blocking_rpc_calls_at_fire_time == 0`).
    pub bonding_curve_pda: PdaDerivation,
    /// Deterministically pre-computed PumpSwap migration pool PDA.
    pub migration_pool_pda: PdaDerivation,
    /// Total token supply (`1,000,000,000`).
    pub total_supply: u64,
    /// Current real SOL accumulated in the bonding curve.
    pub real_sol_reserves: f64,
    /// Graduation threshold in SOL (`85.0 SOL`).
    pub graduation_threshold_sol: f64,
    /// Completion ratio (`0.0..=1.0+`).
    pub completion_ratio: f64,
    /// Instantaneous fill velocity $V_{\text{curve}} = \Delta \text{SOL} / \Delta t$ in SOL/sec.
    pub fill_velocity_sol_per_sec: f64,
    /// True when the curve has reached or exceeded the `85.0 SOL` (`~$69,000` mcap) graduation threshold
    /// or is within imminent slot-0 graduation window (`>= 96%` filled with high velocity).
    pub is_graduation_ready: bool,
}

/// Evaluates a Pump.fun bonding curve state update and pre-derives both the bonding curve PDA
/// and the target PumpSwap AMM pool PDA with zero network RPC calls.
pub fn evaluate_bonding_curve_state(
    mint: &str,
    real_sol_reserves: f64,
    delta_sol: f64,
    delta_seconds: f64,
) -> BondingCurveEvaluation {
    let bonding_curve_pda = derive_pumpfun_bonding_curve_pda(mint);
    let migration_pool_pda =
        derive_pumpswap_or_raydium_pool_pda(mint, WSOL_MINT_ADDRESS, "pumpswap");
    let fill_velocity_sol_per_sec = compute_curve_fill_velocity(delta_sol, delta_seconds);
    let completion_ratio = (real_sol_reserves / PUMPFUN_GRADUATION_SOL_THRESHOLD).clamp(0.0, 2.0);
    let is_graduation_ready = real_sol_reserves >= PUMPFUN_GRADUATION_SOL_THRESHOLD
        || (completion_ratio >= 0.96 && fill_velocity_sol_per_sec >= 2.5);

    BondingCurveEvaluation {
        mint: mint.to_string(),
        bonding_curve_pda,
        migration_pool_pda,
        total_supply: PUMPFUN_TOTAL_SUPPLY,
        real_sol_reserves,
        graduation_threshold_sol: PUMPFUN_GRADUATION_SOL_THRESHOLD,
        completion_ratio,
        fill_velocity_sol_per_sec,
        is_graduation_ready,
    }
}

/// Configuration for Triton's Yellowstone gRPC (`Dragon's Mouth` `.so` Geyser Plugin) intra-slot stream.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct YellowstoneDragonMouthSubscription {
    /// Validator Geyser gRPC HTTP/2 endpoint.
    pub endpoint: String,
    /// Watched on-chain program IDs (`Pump.fun`, `PumpSwap`, `Raydium V4`).
    pub tracked_programs: Vec<String>,
    /// Watched `SERIAL_RUNNER_SYNDICATE` shadow-cluster wallets.
    pub tracked_syndicate_wallets: Vec<String>,
    /// Pre-indexed O(1) HashSet of watched on-chain program IDs.
    pub tracked_program_set: HashSet<String>,
    /// Pre-indexed O(1) HashSet of watched `SERIAL_RUNNER_SYNDICATE` wallets.
    pub tracked_wallet_set: HashSet<String>,
    /// Whether intra-slot shred/bank-write streaming is enabled (`processed` commitment).
    pub intra_slot_shred_stream: bool,
}

impl YellowstoneDragonMouthSubscription {
    /// Constructs the canonical Slot-Zero subscription covering Pump.fun, PumpSwap, Raydium V4,
    /// and the resolved `SERIAL_RUNNER_SYNDICATE` shadow-cluster wallets.
    pub fn new_default(endpoint: &str, syndicate_wallets: Vec<String>) -> Self {
        let tracked_programs = vec![
            PUMPFUN_BONDING_CURVE_PROGRAM_ID.to_string(),
            PUMPSWAP_AMM_PROGRAM_ID.to_string(),
            RAYDIUM_AMM_V4_PROGRAM_ID.to_string(),
        ];
        let tracked_program_set: HashSet<String> = tracked_programs.iter().cloned().collect();
        let tracked_wallet_set: HashSet<String> = syndicate_wallets.iter().cloned().collect();
        Self {
            endpoint: endpoint.to_string(),
            tracked_programs,
            tracked_syndicate_wallets: syndicate_wallets,
            tracked_program_set,
            tracked_wallet_set,
            intra_slot_shred_stream: true,
        }
    }

    /// Returns true if an intra-slot account/transaction update matches our watched programs or wallets.
    pub fn matches_update(&self, program_id: &str, signer_wallet: &str) -> bool {
        self.tracked_program_set.contains(program_id)
            || self.tracked_wallet_set.contains(signer_wallet)
    }
}

/// Represents a single intra-slot account write pushed by Yellowstone gRPC (`Dragon's Mouth`).
#[derive(Debug, Clone)]
pub struct GeyserAccountUpdate {
    /// Current Solana slot number.
    pub slot: u64,
    /// Intra-slot write sequence index.
    pub write_version: u64,
    /// Owning program ID of the modified account or instruction.
    pub program_id: String,
    /// Signer or authority wallet that triggered the state transition.
    pub signer_wallet: String,
    /// Target token mint.
    pub mint: String,
    /// Real SOL reserves in the bonding curve after this write.
    pub real_sol_reserves: f64,
    /// SOL added in the trailing observation window ($\Delta \text{SOL}$).
    pub delta_sol: f64,
    /// Duration of the trailing observation window in seconds ($\Delta t$).
    pub delta_seconds: f64,
}

/// Processes an incoming Yellowstone gRPC `Dragon's Mouth` intra-slot update, returning
/// `Some(BondingCurveEvaluation)` if the update matches the subscription filter.
pub fn process_intra_slot_geyser_update(
    sub: &YellowstoneDragonMouthSubscription,
    update: &GeyserAccountUpdate,
) -> Option<BondingCurveEvaluation> {
    if !sub.matches_update(&update.program_id, &update.signer_wallet) {
        return None;
    }
    Some(evaluate_bonding_curve_state(
        &update.mint,
        update.real_sol_reserves,
        update.delta_sol,
        update.delta_seconds,
    ))
}

/// Processes a batch of Yellowstone gRPC `Dragon's Mouth` intra-slot account updates with
/// local mint PDA memoization so repeated writes to the same bonding curve within a slot
/// reuse derived PDAs in O(1) memory lookups (`blocking_rpc_calls_at_fire_time == 0`).
pub fn process_intra_slot_geyser_batch(
    sub: &YellowstoneDragonMouthSubscription,
    updates: &[GeyserAccountUpdate],
) -> Vec<BondingCurveEvaluation> {
    let mut pda_cache: HashMap<String, (PdaDerivation, PdaDerivation)> =
        HashMap::with_capacity(updates.len());
    let mut results = Vec::with_capacity(updates.len());

    for update in updates {
        if !sub.matches_update(&update.program_id, &update.signer_wallet) {
            continue;
        }
        let (bonding_curve_pda, migration_pool_pda) = pda_cache
            .entry(update.mint.clone())
            .or_insert_with(|| {
                (
                    derive_pumpfun_bonding_curve_pda(&update.mint),
                    derive_pumpswap_or_raydium_pool_pda(
                        &update.mint,
                        WSOL_MINT_ADDRESS,
                        "pumpswap",
                    ),
                )
            })
            .clone();

        let fill_velocity_sol_per_sec =
            compute_curve_fill_velocity(update.delta_sol, update.delta_seconds);
        let completion_ratio =
            (update.real_sol_reserves / PUMPFUN_GRADUATION_SOL_THRESHOLD).clamp(0.0, 2.0);
        let is_graduation_ready = update.real_sol_reserves >= PUMPFUN_GRADUATION_SOL_THRESHOLD
            || (completion_ratio >= 0.96 && fill_velocity_sol_per_sec >= 2.5);

        results.push(BondingCurveEvaluation {
            mint: update.mint.clone(),
            bonding_curve_pda,
            migration_pool_pda,
            total_supply: PUMPFUN_TOTAL_SUPPLY,
            real_sol_reserves: update.real_sol_reserves,
            graduation_threshold_sol: PUMPFUN_GRADUATION_SOL_THRESHOLD,
            completion_ratio,
            fill_velocity_sol_per_sec,
            is_graduation_ready,
        });
    }

    results
}
