#!/usr/bin/env python3
"""Sovereign Titan OS — Phase 2 On-Chain Rust & Atomic V0 Execution Verification Suite.

Validates:
1. Rust Anchor contract (`anchor_profit_guard/programs/profit_guard/src/lib.rs`) compilation
   (`cargo check`, `cargo test`, `anchor build`) and generated IDL (`target/idl/profit_guard.json`).
2. Proactive Address Lookup Table (ALT) Warmer (`/mnt/ramdisk/execution_state/active_alts.json`)
   with Kamino/Marginfi vaults, all 8 Jito Tip PDAs, DEX program IDs, and 500 active pool vaults.
3. Full 1,000 SOL Kamino Lend Flash-Loan + 2-Leg Arb + ProfitGuard V0 transaction AND
   5,000 SOL Marginfi + 3-Hop Agave 4.5 Triangular Arb V0 transaction (`< 1,150 bytes`).
4. `jitodontfront111111111111111111111111111111` read-only injection into Instruction 0 on
   directional buys, and `spl_token::instruction::close_account` (`0.00203928 SOL` rent reclaim)
   on 100% token exits.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import orjson
from solders.keypair import Keypair
from solders.pubkey import Pubkey

WORKSPACE_ROOT = Path("/home/titanagentik/sovereign-titan")
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.execution.alt_manager import (
    ALTManager,
    KAMINO_LEND_PROGRAM_ID,
    MARGINFI_V2_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID,
    OFFICIAL_JITO_TIP_PDAS,
    ORCA_WHIRLPOOL_PROGRAM_ID,
    PROFIT_GUARD_PROGRAM_ID,
    RAYDIUM_V4_PROGRAM_ID,
    SPL_TOKEN_PROGRAM_ID,
    WSOL_MINT_PUBKEY,
    deterministic_pubkey,
)
from src.execution.atomic_tx_builder import (
    ATA_RENT_LAMPORTS,
    AtomicV0TransactionBuilder,
    CLOSE_ACCOUNT_IX_TAG,
    JITO_DONT_FRONT_PUBKEY_STR,
    derive_associated_token_address,
)
from src.execution.flash_loan_builder import (
    DEXSwapLegSpec,
    FlashLoanBuilder,
    anchor_ix_discriminator,
)


def verify_step_1_rust_anchor_program_and_idl() -> None:
    print("\n[CHECK 1/4] Compiling & Testing Rust Anchor `profit_guard` Program + Verifying IDL...")
    env = os.environ.copy()
    env["PATH"] = (
        f"{Path.home() / '.cargo' / 'bin'}:{Path.home() / '.local' / 'bin'}:{env.get('PATH', '')}"
    )

    manifest_path = WORKSPACE_ROOT / "anchor_profit_guard" / "Cargo.toml"
    lib_rs_path = (
        WORKSPACE_ROOT
        / "anchor_profit_guard"
        / "programs"
        / "profit_guard"
        / "src"
        / "lib.rs"
    )
    assert lib_rs_path.exists(), f"Missing {lib_rs_path}"
    lib_source = lib_rs_path.read_text(encoding="utf-8")
    assert (
        "post_lamports >= pre_lamports + min_net_profit_lamports + jito_tip_lamports"
        in lib_source
    ), "Missing mandatory profit invariant in lib.rs"
    assert "MevError::InsufficientProfit" in lib_source

    # Run cargo check, cargo test, and anchor build
    subprocess.run(
        ["cargo", "check", "--manifest-path", str(manifest_path)],
        check=True,
        env=env,
        cwd=str(WORKSPACE_ROOT / "anchor_profit_guard"),
    )
    subprocess.run(
        ["cargo", "test", "--manifest-path", str(manifest_path), "--", "--nocapture"],
        check=True,
        env=env,
        cwd=str(WORKSPACE_ROOT / "anchor_profit_guard"),
    )
    subprocess.run(
        ["anchor", "build"],
        check=True,
        env=env,
        cwd=str(WORKSPACE_ROOT / "anchor_profit_guard"),
    )

    idl_path = WORKSPACE_ROOT / "anchor_profit_guard" / "target" / "idl" / "profit_guard.json"
    so_path = WORKSPACE_ROOT / "anchor_profit_guard" / "target" / "deploy" / "profit_guard.so"
    assert idl_path.exists(), f"Missing generated IDL at {idl_path}"
    assert so_path.exists(), f"Missing compiled shared object at {so_path}"

    idl = orjson.loads(idl_path.read_bytes())
    assert idl["address"] == PROFIT_GUARD_PROGRAM_ID
    ix_names = {ix["name"]: ix for ix in idl["instructions"]}
    assert "record_pre_balance" in ix_names
    assert "assert_min_profit_and_tip" in ix_names

    # Verify discriminators match Python FlashLoanBuilder
    assert bytes(ix_names["record_pre_balance"]["discriminator"]) == anchor_ix_discriminator(
        "record_pre_balance"
    )
    assert bytes(
        ix_names["assert_min_profit_and_tip"]["discriminator"]
    ) == anchor_ix_discriminator("assert_min_profit_and_tip")
    error_codes = {err["code"]: err["name"] for err in idl["errors"]}
    assert error_codes.get(6000) == "InsufficientProfit"
    print(
        f"  [OK] Rust `profit_guard` compiled (`profit_guard.so` + `profit_guard.json` IDL verified)."
    )


def verify_step_2_proactive_alt_warmer() -> ALTManager:
    print("\n[CHECK 2/4] Verifying Proactive Address Lookup Table (ALT) Warmer in /mnt/ramdisk...")
    alt_mgr = ALTManager()
    state = alt_mgr.initialize_warm_alts(top_pool_count=500)
    assert alt_mgr.active_alts_file.exists()
    assert state.top_pool_vault_count == 500
    assert state.total_unique_addresses > 520

    flat_addresses = {addr for tbl in state.tables for addr in tbl.addresses}
    assert KAMINO_LEND_PROGRAM_ID in flat_addresses
    assert MARGINFI_V2_PROGRAM_ID in flat_addresses
    assert PROFIT_GUARD_PROGRAM_ID in flat_addresses
    assert RAYDIUM_V4_PROGRAM_ID in flat_addresses
    assert METEORA_DLMM_PROGRAM_ID in flat_addresses
    for jito_pda in OFFICIAL_JITO_TIP_PDAS:
        assert jito_pda in flat_addresses, f"Missing Jito Tip PDA {jito_pda} in warm ALT"

    t0 = time.perf_counter()
    reloaded = alt_mgr.load_from_ramdisk()
    reload_ms = (time.perf_counter() - t0) * 1000.0
    assert len(reloaded.tables) == len(state.tables)
    print(
        f"  [OK] Pre-warmed {len(state.tables)} ALTs ({state.total_unique_addresses} addresses including 500 pool vaults & 8 Jito Tip PDAs) in {alt_mgr.active_alts_file} (Reload: {reload_ms:.3f} ms)"
    )
    return alt_mgr


def verify_step_3_flash_loan_and_agave45_v0_builder(alt_mgr: ALTManager) -> None:
    print(
        "\n[CHECK 3/4] Constructing 1,000 SOL Kamino 2-Leg Arb & 5,000 SOL Marginfi 3-Hop Agave 4.5 V0 Transactions..."
    )
    tx_builder = AtomicV0TransactionBuilder(alt_manager=alt_mgr)
    payer = Keypair()
    wsol_mint = Pubkey.from_string(WSOL_MINT_PUBKEY)
    token_b_mint = deterministic_pubkey("mint:token_b")
    token_c_mint = deterministic_pubkey("mint:token_c")

    user_wsol_ata = derive_associated_token_address(payer.pubkey(), wsol_mint)
    user_token_b_ata = derive_associated_token_address(payer.pubkey(), token_b_mint)
    user_token_c_ata = derive_associated_token_address(payer.pubkey(), token_c_mint)

    # Pre-register user ATAs into the warm ALT so they compress to 1-byte indices
    alt_mgr.register_custom_addresses(
        [str(user_wsol_ata), str(user_token_b_ata), str(user_token_c_ata)]
    )

    leg_1 = DEXSwapLegSpec(
        program_id=Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID),
        pool_state=alt_mgr.get_pool_vault(0),
        pool_Authority=alt_mgr.get_pool_vault(1),
        vault_in=alt_mgr.get_pool_vault(2),
        vault_out=alt_mgr.get_pool_vault(3),
        user_source_token_account=user_wsol_ata,
        user_destination_token_account=user_token_b_ata,
        amount_in_lamports=1_000_000_000_000,  # 1,000 SOL
        min_amount_out_lamports=250_000_000_000,
        label="DEX_Leg_1_Raydium_V4",
    )
    leg_2 = DEXSwapLegSpec(
        program_id=Pubkey.from_string(METEORA_DLMM_PROGRAM_ID),
        pool_state=alt_mgr.get_pool_vault(4),
        pool_Authority=alt_mgr.get_pool_vault(5),
        vault_in=alt_mgr.get_pool_vault(6),
        vault_out=alt_mgr.get_pool_vault(7),
        user_source_token_account=user_token_b_ata,
        user_destination_token_account=user_wsol_ata,
        amount_in_lamports=250_000_000_000,
        min_amount_out_lamports=1_001_500_000_000,  # +1.5 SOL gross return
        label="DEX_Leg_2_Meteora_DLMM",
    )

    seq_2hop, tx_2hop = tx_builder.build_flash_loan_arb_v0(
        payer_keypair=payer,
        user_wsol_ata=user_wsol_ata,
        borrow_sol=1000.0,
        dex_legs=[leg_1, leg_2],
        min_net_profit_lamports=500_000_000,  # 0.5 SOL min profit
        jito_tip_lamports=100_000_000,  # 0.1 SOL conditional Jito tip
        provider="KAMINO",
        exact_compute_units=380_000,
        agave_45_enabled=False,
    )

    expected_7_labels = [
        "SetComputeUnitLimit",
        "FlashBorrow",
        "ProfitGuard::record_pre_balance",
        "DEX_Leg_1",
        "DEX_Leg_2",
        "FlashRepay",
        "ProfitGuard::assert_min_profit_and_tip",
    ]
    assert seq_2hop.instruction_labels == expected_7_labels, (
        f"Unexpected instruction sequence: {seq_2hop.instruction_labels}"
    )
    assert tx_2hop.instruction_count == 7
    assert tx_2hop.serialized_size_bytes < 1150, (
        f"Serialized V0 size {tx_2hop.serialized_size_bytes} >= 1,150 bytes"
    )
    assert tx_2hop.total_unique_accounts <= 64
    assert tx_2hop.alt_lookup_count >= 15
    print(
        f"  [OK] 1,000 SOL Kamino Flash-Loan + 2-Leg Arb + ProfitGuard V0 Tx: "
        f"{tx_2hop.serialized_size_bytes} bytes (<1,150 limit, MTU 1,232) | "
        f"Accounts={tx_2hop.total_unique_accounts}/64 | ALT Lookups={tx_2hop.alt_lookup_count}"
    )

    # Test 3-Hop Triangular Arb (5,000 SOL Marginfi Flash-Loan under Agave 4.5 96-account mode)
    leg_2_tri = DEXSwapLegSpec(
        program_id=Pubkey.from_string(METEORA_DLMM_PROGRAM_ID),
        pool_state=alt_mgr.get_pool_vault(4),
        pool_Authority=alt_mgr.get_pool_vault(5),
        vault_in=alt_mgr.get_pool_vault(6),
        vault_out=alt_mgr.get_pool_vault(7),
        user_source_token_account=user_token_b_ata,
        user_destination_token_account=user_token_c_ata,
        amount_in_lamports=250_000_000_000,
        min_amount_out_lamports=500_000_000_000,
        label="DEX_Leg_2_Meteora_DLMM",
    )
    leg_3_tri = DEXSwapLegSpec(
        program_id=Pubkey.from_string(ORCA_WHIRLPOOL_PROGRAM_ID),
        pool_state=alt_mgr.get_pool_vault(8),
        pool_Authority=alt_mgr.get_pool_vault(9),
        vault_in=alt_mgr.get_pool_vault(10),
        vault_out=alt_mgr.get_pool_vault(11),
        user_source_token_account=user_token_c_ata,
        user_destination_token_account=user_wsol_ata,
        amount_in_lamports=500_000_000_000,
        min_amount_out_lamports=5_003_000_000_000,
        label="DEX_Leg_3_Orca_Whirlpool",
    )

    seq_3hop, tx_3hop = tx_builder.build_flash_loan_arb_v0(
        payer_keypair=payer,
        user_wsol_ata=user_wsol_ata,
        borrow_sol=5000.0,
        dex_legs=[leg_1, leg_2_tri, leg_3_tri],
        min_net_profit_lamports=1_000_000_000,
        jito_tip_lamports=250_000_000,
        provider="MARGINFI",
        exact_compute_units=520_000,
        agave_45_enabled=True,
    )
    assert seq_3hop.hop_count == 3
    assert tx_3hop.instruction_count == 8
    assert tx_3hop.max_allowed_accounts == 96
    assert tx_3hop.serialized_size_bytes < 1150
    print(
        f"  [OK] 5,000 SOL Marginfi Flash-Loan + 3-Hop Triangular Arb V0 Tx (Agave 4.5 96-Account Mode): "
        f"{tx_3hop.serialized_size_bytes} bytes (<1,150 limit) | Accounts={tx_3hop.total_unique_accounts}/96"
    )


def verify_step_4_directional_guards_and_rent_reclaim(alt_mgr: ALTManager) -> None:
    print(
        "\n[CHECK 4/4] Verifying `jitodontfront` Buy Guard & `close_account` (0.00203928 SOL) Exit Rent Reclaim..."
    )
    tx_builder = AtomicV0TransactionBuilder(alt_manager=alt_mgr)
    payer = Keypair()
    wsol_mint = Pubkey.from_string(WSOL_MINT_PUBKEY)
    meme_mint = deterministic_pubkey("mint:trench_alpha_token")
    user_wsol_ata = derive_associated_token_address(payer.pubkey(), wsol_mint)
    user_meme_ata = derive_associated_token_address(payer.pubkey(), meme_mint)

    buy_leg = DEXSwapLegSpec(
        program_id=Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID),
        pool_state=alt_mgr.get_pool_vault(20),
        pool_Authority=alt_mgr.get_pool_vault(21),
        vault_in=alt_mgr.get_pool_vault(22),
        vault_out=alt_mgr.get_pool_vault(23),
        user_source_token_account=user_wsol_ata,
        user_destination_token_account=user_meme_ata,
        amount_in_lamports=1_000_000_000,
        min_amount_out_lamports=50_000_000_000,
        label="Shadow_Buy_Leg",
    )

    buy_res = tx_builder.build_directional_buy_v0(
        payer_keypair=payer,
        swap_leg=buy_leg,
    )
    assert buy_res.has_jito_dont_front_in_ix0 is True
    assert buy_res.serialized_size_bytes < 1150
    print(
        f"  [OK] Directional Buy V0 Tx: `{JITO_DONT_FRONT_PUBKEY_STR}` injected read-only in Instruction 0 ({buy_res.serialized_size_bytes} bytes)."
    )

    exit_leg = DEXSwapLegSpec(
        program_id=Pubkey.from_string(RAYDIUM_V4_PROGRAM_ID),
        pool_state=alt_mgr.get_pool_vault(20),
        pool_Authority=alt_mgr.get_pool_vault(21),
        vault_in=alt_mgr.get_pool_vault(23),
        vault_out=alt_mgr.get_pool_vault(22),
        user_source_token_account=user_meme_ata,
        user_destination_token_account=user_wsol_ata,
        amount_in_lamports=50_000_000_000,
        min_amount_out_lamports=1_450_000_000,
        label="Full_Exit_Leg",
    )

    exit_res = tx_builder.build_full_token_exit_v0(
        payer_keypair=payer,
        swap_leg=exit_leg,
        token_ata_to_close=user_meme_ata,
    )
    assert exit_res.has_close_account_rent_reclaim is True
    assert exit_res.reclaimed_rent_lamports == ATA_RENT_LAMPORTS  # 2,039,280 lamports = 0.00203928 SOL
    assert exit_res.serialized_size_bytes < 1150
    print(
        f"  [OK] 100% Token Exit V0 Tx: `spl_token::instruction::close_account` (tag={CLOSE_ACCOUNT_IX_TAG}) appended, reclaiming {exit_res.reclaimed_rent_lamports / 1e9:.8f} SOL ({exit_res.serialized_size_bytes} bytes)."
    )


def main() -> int:
    print("==============================================================================")
    print("SOVEREIGN TITAN OS — PHASE 2 ON-CHAIN & ATOMIC V0 VERIFICATION SUITE")
    print("==============================================================================")
    t_start = time.perf_counter()
    verify_step_1_rust_anchor_program_and_idl()
    alt_mgr = verify_step_2_proactive_alt_warmer()
    verify_step_3_flash_loan_and_agave45_v0_builder(alt_mgr)
    verify_step_4_directional_guards_and_rent_reclaim(alt_mgr)
    elapsed_s = time.perf_counter() - t_start
    print("\n==============================================================================")
    print(f"[PASS] 100% OF PHASE 2 ON-CHAIN & ATOMIC V0 CHECKS PASSED IN {elapsed_s:.3f}s")
    print("==============================================================================")
    return 0


def test_phase2_step_1_rust_anchor_program_and_idl() -> None:
    verify_step_1_rust_anchor_program_and_idl()


def test_phase2_steps_2_to_4_alt_warmer_flash_loan_and_directional_guards() -> None:
    alt_mgr = verify_step_2_proactive_alt_warmer()
    verify_step_3_flash_loan_and_agave45_v0_builder(alt_mgr)
    verify_step_4_directional_guards_and_rent_reclaim(alt_mgr)


if __name__ == "__main__":
    raise SystemExit(main())

