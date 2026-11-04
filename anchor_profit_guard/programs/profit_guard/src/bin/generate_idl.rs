//! Generates `target/idl/profit_guard.json` for Sovereign Titan OS.

use std::fs;
use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let workspace_root = manifest_dir
        .parent()
        .and_then(|p| p.parent())
        .expect("workspace root");
    let idl_dir = workspace_root.join("target").join("idl");
    fs::create_dir_all(&idl_dir).expect("create target/idl directory");

    let idl_json = profit_guard::generate_anchor_idl_json();
    let idl_path = idl_dir.join("profit_guard.json");
    let formatted = serde_json::to_string_pretty(&idl_json).expect("serialize IDL JSON");
    fs::write(&idl_path, formatted).expect("write target/idl/profit_guard.json");
    println!("[IDL] Generated {}", idl_path.display());
}
