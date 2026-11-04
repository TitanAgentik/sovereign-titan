#!/usr/bin/env bash
# ==============================================================================
# SOVEREIGN TITAN OS — On-Chain ProfitGuard Smart Contract Deployment Utility
# File: scripts/deploy_profit_guard_mainnet.sh
#
# Supports:
#   --check               Verify solana CLI, anchor CLI, profit_guard.so & keypairs
#   --generate-program-id Generate target/deploy/profit_guard-keypair.json & print ID
#   --deploy-devnet       Build & deploy profit_guard to Solana Devnet
#   --deploy-mainnet      Verify deployer balance (>= 2.0 SOL), build & deploy to Mainnet-Beta
# ==============================================================================
set -euo pipefail

export PATH="${HOME}/.local/share/solana/install/active_release/bin:${HOME}/.cargo/bin:${PATH}"

WORKSPACE_ROOT="/home/titanagentik/sovereign-titan"
ANCHOR_DIR="${WORKSPACE_ROOT}/anchor_profit_guard"
DEPLOY_DIR="${ANCHOR_DIR}/target/deploy"
SO_PATH="${DEPLOY_DIR}/profit_guard.so"
PROGRAM_KEYPAIR="${DEPLOY_DIR}/profit_guard-keypair.json"
DEPLOYER_KEYPAIR="${DEPLOYER_KEYPAIR:-${HOME}/.config/solana/deployer.json}"
PYTHON_BIN="${WORKSPACE_ROOT}/.venv/bin/python"

# Load .env if present
if [[ -f "${WORKSPACE_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${WORKSPACE_ROOT}/.env"
    set +a
elif [[ -f "${WORKSPACE_ROOT}/.env.example" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${WORKSPACE_ROOT}/.env.example"
    set +a
fi

HELIUS_RPC_URL="${HELIUS_RPC_URL:-https://api.mainnet-beta.solana.com}"
ACTION="${1:---check}"

extract_program_id() {
    if [[ ! -f "${PROGRAM_KEYPAIR}" ]]; then
        echo "PrftGrd111111111111111111111111111111111111"
        return
    fi
    if command -v solana-keygen >/dev/null 2>&1; then
        solana-keygen pubkey "${PROGRAM_KEYPAIR}"
    else
        "${PYTHON_BIN}" -c "
import json
from solders.keypair import Keypair
raw = json.load(open('${PROGRAM_KEYPAIR}'))
kp = Keypair.from_bytes(bytes(raw))
print(str(kp.pubkey()))
"
    fi
}

generate_keypair_if_missing() {
    local target_path="$1"
    mkdir -p "$(dirname "${target_path}")"
    if [[ -f "${target_path}" ]]; then
        return 0
    fi
    if command -v solana-keygen >/dev/null 2>&1; then
        solana-keygen new --no-bip39-passphrase --silent -o "${target_path}"
    else
        "${PYTHON_BIN}" -c "
import json, os
from solders.keypair import Keypair
kp = Keypair()
with open('${target_path}', 'w') as f:
    json.dump(list(bytes(kp)), f)
os.chmod('${target_path}', 0o600)
"
    fi
}

case "${ACTION}" in
    --check)
        echo "=================================================================="
        echo " SOVEREIGN TITAN OS — PROFIT_GUARD ON-CHAIN DEPLOYMENT CHECK"
        echo "=================================================================="
        if command -v solana >/dev/null 2>&1; then
            echo "[OK] solana CLI: $(solana --version)"
        else
            echo "[WARN] solana CLI not in PATH (install via: sh -c \"\$(curl -sSfL https://release.anza.xyz/stable/install)\")"
        fi

        if command -v anchor >/dev/null 2>&1; then
            echo "[OK] anchor CLI: $(anchor --version)"
        else
            echo "[WARN] anchor CLI not in PATH (install via: cargo install --git https://github.com/coral-xyz/anchor avm)"
        fi

        if [[ -f "${SO_PATH}" ]]; then
            SO_SIZE=$(stat -c%s "${SO_PATH}" 2>/dev/null || echo "0")
            echo "[OK] Compiled SBF Binary: ${SO_PATH} (${SO_SIZE} bytes)"
        else
            echo "[MISSING] Compiled SBF Binary: ${SO_PATH} (run: cd ${ANCHOR_DIR} && anchor build)"
        fi

        if [[ -f "${PROGRAM_KEYPAIR}" ]]; then
            PROG_ID=$(extract_program_id)
            echo "[OK] Program Keypair: ${PROGRAM_KEYPAIR} -> Program ID: ${PROG_ID}"
        else
            echo "[INFO] Program Keypair not yet generated at ${PROGRAM_KEYPAIR} (using default PrftGrd111111111111111111111111111111111111)"
        fi

        if [[ -f "${DEPLOYER_KEYPAIR}" ]]; then
            echo "[OK] Deployer Wallet Keypair: ${DEPLOYER_KEYPAIR}"
        else
            echo "[INFO] Deployer Wallet Keypair not yet created at ${DEPLOYER_KEYPAIR}"
        fi
        echo "=================================================================="
        exit 0
        ;;

    --generate-program-id)
        generate_keypair_if_missing "${PROGRAM_KEYPAIR}"
        PROG_ID=$(extract_program_id)
        echo "PROGRAM_KEYPAIR=${PROGRAM_KEYPAIR}"
        echo "PROFIT_GUARD_PROGRAM_ID=${PROG_ID}"
        exit 0
        ;;

    --deploy-devnet)
        echo "[DEPLOY-DEVNET] Building and deploying profit_guard to Solana Devnet..."
        generate_keypair_if_missing "${PROGRAM_KEYPAIR}"
        generate_keypair_if_missing "${DEPLOYER_KEYPAIR}"
        PROG_ID=$(extract_program_id)
        echo "[DEPLOY-DEVNET] Target Program ID: ${PROG_ID}"
        if ! command -v anchor >/dev/null 2>&1; then
            echo "[ERROR] anchor CLI is required for --deploy-devnet" >&2
            exit 1
        fi
        cd "${ANCHOR_DIR}"
        anchor build
        anchor deploy \
            --provider.cluster "https://api.devnet.solana.com" \
            --provider.wallet "${DEPLOYER_KEYPAIR}"
        echo "[DEPLOY-DEVNET] Successfully deployed profit_guard (${PROG_ID}) to Devnet."
        exit 0
        ;;

    --deploy-mainnet)
        echo "[DEPLOY-MAINNET] Verifying Mainnet-Beta prerequisites..."
        generate_keypair_if_missing "${PROGRAM_KEYPAIR}"
        if [[ ! -f "${DEPLOYER_KEYPAIR}" ]]; then
            echo "[ERROR] Deployer wallet missing at ${DEPLOYER_KEYPAIR}. Create and fund with >= 2.0 SOL first." >&2
            exit 1
        fi
        if ! command -v solana >/dev/null 2>&1 || ! command -v anchor >/dev/null 2>&1; then
            echo "[ERROR] Both 'solana' and 'anchor' CLIs are required for --deploy-mainnet." >&2
            exit 1
        fi
        BALANCE_RAW=$(solana balance "${DEPLOYER_KEYPAIR}" --url "${HELIUS_RPC_URL}" | awk '{print $1}')
        HAS_ENOUGH=$("${PYTHON_BIN}" -c "print('1' if float('${BALANCE_RAW:-0}') >= 2.0 else '0')")
        if [[ "${HAS_ENOUGH}" != "1" ]]; then
            echo "[ERROR] Deployer balance (${BALANCE_RAW:-0} SOL) is below the required 2.0 SOL minimum for Mainnet-Beta program deployment." >&2
            exit 1
        fi
        PROG_ID=$(extract_program_id)
        echo "[DEPLOY-MAINNET] Deployer balance verified (${BALANCE_RAW} SOL >= 2.0 SOL). Deploying Program ID ${PROG_ID}..."
        cd "${ANCHOR_DIR}"
        anchor build
        anchor deploy \
            --provider.cluster "${HELIUS_RPC_URL}" \
            --provider.wallet "${DEPLOYER_KEYPAIR}"
        echo "[DEPLOY-MAINNET] Successfully deployed profit_guard (${PROG_ID}) to Solana Mainnet-Beta."
        exit 0
        ;;

    *)
        echo "Usage: $0 [--check | --generate-program-id | --deploy-devnet | --deploy-mainnet]"
        exit 1
        ;;
esac
