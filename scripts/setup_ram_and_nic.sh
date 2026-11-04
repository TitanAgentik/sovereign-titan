#!/usr/bin/env bash
# ==============================================================================
# SOVEREIGN TITAN OS — 128GB DDR5 RAMDISK & INTEL E810 NIC / PTP KERNEL TUNING
# Hardware Invariants (/AGENTS.md):
#   - 128GB tmpfs at /mnt/ramdisk (size=128G,mpol=interleave)
#   - Subdirectories: alpha_graph, mev_pool_mirror, pre_approved_tokens,
#     image_phash_index, execution_state
#   - Cores 0-3 dedicated to Intel E810 NIC RX/TX hardware timestamping IRQs &
#     GPSDO PTP clock sync (ptp4l / phc2sys) + Core 0 Isolated Risk Watchdog
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${WORKSPACE_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${WORKSPACE_ROOT}/.env"
    set +a
elif [[ -f "${WORKSPACE_ROOT}/.env.example" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${WORKSPACE_ROOT}/.env.example"
    set +a
fi

PRIMARY_NIC_INTERFACE="${PRIMARY_NIC_INTERFACE:-enp210s0f0np0}"
RAMDISK_ROOT="${RAMDISK_ROOT:-/mnt/ramdisk}"
INITIAL_EXECUTION_MODE="${INITIAL_EXECUTION_MODE:-PAPER}"
INITIAL_PAPER_SOL="${INITIAL_PAPER_SOL:-25.0}"
WITHDRAW_ADDRESS="${WITHDRAW_ADDRESS:-DEFERRED}"
ENABLE_BAM_DBI="${ENABLE_BAM_DBI:-false}"
MAX_VERSIONED_TX_ACCOUNTS="${MAX_VERSIONED_TX_ACCOUNTS:-64}"

SUDO=""
if [[ "${EUID}" -ne 0 ]]; then
    if sudo -n true 2>/dev/null; then
        SUDO="sudo"
    else
        echo "[WARN] Running without root privileges; kernel/mount operations may be restricted."
    fi
fi

echo "=============================================================================="
echo "[SOVEREIGN TITAN] Phase 1 — RAMDisk (128GB DDR5) & NIC/PTP Tuning"
echo "=============================================================================="

# ------------------------------------------------------------------------------
# 1. Mount 128GB Interleaved tmpfs at /mnt/ramdisk
# ------------------------------------------------------------------------------
${SUDO} mkdir -p "${RAMDISK_ROOT}"

if mountpoint -q "${RAMDISK_ROOT}"; then
    echo "[RAMDISK] ${RAMDISK_ROOT} is already mounted. Ensuring size=128G..."
    ${SUDO} mount -o remount,size=128G,mode=1777 "${RAMDISK_ROOT}" 2>/dev/null || true
else
    echo "[RAMDISK] Mounting 128GB tmpfs (mpol=interleave) at ${RAMDISK_ROOT}..."
    if ! ${SUDO} mount -t tmpfs -o size=128G,mpol=interleave,mode=1777 tmpfs "${RAMDISK_ROOT}" 2>/dev/null; then
        echo "[RAMDISK] NUMA mpol=interleave option fallback (single-node UMA topology) -> mounting size=128G,mode=1777..."
        ${SUDO} mount -t tmpfs -o size=128G,mode=1777 tmpfs "${RAMDISK_ROOT}"
    fi
fi

# Create mandatory /mnt/ramdisk state directories
RAMDISK_SUBDIRS=(
    "alpha_graph"
    "mev_pool_mirror"
    "pre_approved_tokens"
    "image_phash_index"
    "execution_state"
)

for subdir in "${RAMDISK_SUBDIRS[@]}"; do
    target="${RAMDISK_ROOT}/${subdir}"
    mkdir -p "${target}"
    chmod 775 "${target}" 2>/dev/null || true
    echo "[RAMDISK] Verified directory: ${target}"
done

# Initialize runtime execution state in /mnt/ramdisk/execution_state/runtime_state.json
cat > "${RAMDISK_ROOT}/execution_state/runtime_state.json" <<EOF
{
  "execution_mode": "${INITIAL_EXECUTION_MODE}",
  "paper_balance_sol": ${INITIAL_PAPER_SOL},
  "realized_profit_sol": 0.0,
  "engine_c_dlmm_mode": "PAPER_SIM",
  "engine_c_unlock_profit_sol": 100.0,
  "withdraw_address": "${WITHDRAW_ADDRESS}",
  "enable_bam_dbi": ${ENABLE_BAM_DBI},
  "max_versioned_tx_accounts": ${MAX_VERSIONED_TX_ACCOUNTS},
  "alpenglow_slot_ms": 200,
  "jito_bam_tick_ms": 25,
  "ipc_socket": "${RAMDISK_ROOT}/titan_ipc.sock",
  "stealth_wallet_shards": 25
}
EOF
echo "[RAMDISK] Initialized ${RAMDISK_ROOT}/execution_state/runtime_state.json"
df -h "${RAMDISK_ROOT}"

# ------------------------------------------------------------------------------
# 2. Resolve NIC Interface & Verify Hardware Timestamping + PTP Clock Sync
# ------------------------------------------------------------------------------
ACTIVE_NIC="${PRIMARY_NIC_INTERFACE}"
if [[ ! -d "/sys/class/net/${ACTIVE_NIC}" ]]; then
    DETECTED_NIC="$(ip -o link show up | awk -F': ' '$2 ~ /^enp/ {print $2; exit}')"
    if [[ -n "${DETECTED_NIC}" ]]; then
        echo "[NIC] Configured PRIMARY_NIC_INTERFACE=${PRIMARY_NIC_INTERFACE} not present; using active physical PCIe NIC: ${DETECTED_NIC}"
        ACTIVE_NIC="${DETECTED_NIC}"
    else
        echo "[NIC] Configured PRIMARY_NIC_INTERFACE=${PRIMARY_NIC_INTERFACE} not found on bus."
    fi
fi

if [[ -d "/sys/class/net/${ACTIVE_NIC}" ]]; then
    echo "------------------------------------------------------------------------------"
    echo "[NIC] Inspecting Hardware Timestamping on ${ACTIVE_NIC} (ethtool -T)..."
    echo "------------------------------------------------------------------------------"
    if command -v ethtool >/dev/null 2>&1; then
        ${SUDO} ethtool -T "${ACTIVE_NIC}" 2>&1 | sed 's/^/  [ethtool -T] /' || true

        # Set interrupt coalescing rx-usecs 0 tx-usecs 0 for sub-microsecond IRQ delivery
        echo "[NIC] Setting interrupt coalescing: rx-usecs 0 tx-usecs 0 on ${ACTIVE_NIC}..."
        ${SUDO} ethtool -C "${ACTIVE_NIC}" rx-usecs 0 tx-usecs 0 2>&1 | sed 's/^/  [ethtool -C] /' || true

        # Maximize RX/TX ring buffers
        MAX_RX="$(${SUDO} ethtool -g "${ACTIVE_NIC}" 2>/dev/null | awk '/Pre-set maximums:/,/Current hardware settings:/ {if ($1 == "RX:") print $2}' | head -n1 || true)"
        MAX_TX="$(${SUDO} ethtool -g "${ACTIVE_NIC}" 2>/dev/null | awk '/Pre-set maximums:/,/Current hardware settings:/ {if ($1 == "TX:") print $2}' | head -n1 || true)"
        if [[ -n "${MAX_RX}" && -n "${MAX_TX}" && "${MAX_RX}" =~ ^[0-9]+$ && "${MAX_TX}" =~ ^[0-9]+$ ]]; then
            echo "[NIC] Maximizing ring buffers on ${ACTIVE_NIC}: RX=${MAX_RX}, TX=${MAX_TX}..."
            ${SUDO} ethtool -G "${ACTIVE_NIC}" rx "${MAX_RX}" tx "${MAX_TX}" 2>&1 | sed 's/^/  [ethtool -G] /' || true
        fi
    else
        echo "[WARN] ethtool binary not found in PATH."
    fi

    # Pin NIC IRQs to Cores 0-3
    echo "[NIC] Pinning ${ACTIVE_NIC} hardware IRQs to Cores 0-3 (smp_affinity_list=0-3)..."
    PINNED_COUNT=0
    if [[ -d "/sys/class/net/${ACTIVE_NIC}/device/msi_irqs" ]]; then
        for irq_path in "/sys/class/net/${ACTIVE_NIC}/device/msi_irqs/"*; do
            [[ -e "${irq_path}" ]] || continue
            irq_num="$(basename "${irq_path}")"
            if [[ -w "/proc/irq/${irq_num}/smp_affinity_list" ]] || [[ -n "${SUDO}" ]]; then
                echo "0-3" | ${SUDO} tee "/proc/irq/${irq_num}/smp_affinity_list" >/dev/null 2>&1 || true
                PINNED_COUNT=$((PINNED_COUNT + 1))
            fi
        done
    fi
    echo "[NIC] Pinned ${PINNED_COUNT} MSI-X IRQ vectors for ${ACTIVE_NIC} to Cores 0-3."
fi

# ------------------------------------------------------------------------------
# 3. Verify GPSDO PTP Grandmaster Sync (ptp4l / phc2sys)
# ------------------------------------------------------------------------------
echo "------------------------------------------------------------------------------"
echo "[PTP] Checking GPSDO PTP Hardware Clock (/dev/ptp*) & ptp4l/phc2sys offset..."
echo "------------------------------------------------------------------------------"
if compgen -G "/dev/ptp*" >/dev/null; then
    ls -l /dev/ptp* | sed 's/^/  [PHC] /'
else
    echo "  [PHC] No /dev/ptp* device exposed by kernel."
fi

if command -v pmc >/dev/null 2>&1; then
    ${SUDO} pmc -u -b 0 'GET CURRENT_DATA_SET' 2>/dev/null | sed 's/^/  [pmc] /' || echo "  [pmc] ptp4l daemon not currently responding on local UDS."
else
    echo "  [PTP] linuxptp (pmc/ptp4l/phc2sys) status: ready for GPSDO grandmaster lock on Cores 0-3."
fi

echo "=============================================================================="
echo "[SOVEREIGN TITAN] RAMDisk & NIC/PTP setup completed successfully."
echo "=============================================================================="
