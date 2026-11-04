#!/usr/bin/env bash
# ==============================================================================
# SOVEREIGN TITAN v2.0 — 24/7/365 UNATTENDED SYSTEMD SERVICE & WATCHDOG INSTALLER
# ==============================================================================
# Generates and optionally enables the systemd user/system service units that
# keep the 128GB RAMDisk, 4-Lane GPU LLM Fleet (:8005/:8002/:8006/:8007),
# Local jupiter-swap-api (:8080), TitanIPCDaemon, NVMe Checkpoint Mirror,
# and ONLY the 3-Day (72h) GitHub, arXiv, Hugging Face & Institutional Research
# Harvester + ACE/ExpeL Self-Improvement Cron running 24/7.
# ==============================================================================
set -euo pipefail

SOURCE_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SOURCE_PATH}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
mkdir -p "${SYSTEMD_USER_DIR}"

# Remove any legacy 6h or 5d timer units so ONLY the 3-day schedule exists
rm -f "${SYSTEMD_USER_DIR}/sovereign-titan-expel-6h.service" \
      "${SYSTEMD_USER_DIR}/sovereign-titan-expel-6h.timer" \
      "${SYSTEMD_USER_DIR}/sovereign-titan-research-harvester-5d.service" \
      "${SYSTEMD_USER_DIR}/sovereign-titan-research-harvester-5d.timer"

cat > "${SYSTEMD_USER_DIR}/sovereign-titan-llm-fleet.service" <<EOF
[Unit]
Description=Sovereign Titan 4-Lane Local GPU LLM Inference Fleet (:8005/:8002/:8006/:8007)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=-${REPO_ROOT}/.env
ExecStart=${REPO_ROOT}/scripts/start_llm_swarm.sh
Restart=always
RestartSec=5
LimitMEMLOCK=infinity
LimitNOFILE=1048576

[Install]
WantedBy=default.target
EOF

cat > "${SYSTEMD_USER_DIR}/sovereign-titan-daemon.service" <<EOF
[Unit]
Description=Sovereign Titan 120Hz Execution & IPC Daemon (24/7 Zero-Disturbance Warm-Resume & Auto-Compounding)
After=network-online.target sovereign-titan-llm-fleet.service

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=-${REPO_ROOT}/.env
Environment=PYTHONPATH=${REPO_ROOT}
ExecStartPre=${REPO_ROOT}/.venv/bin/python -m src.cli.titan_cli swarm reboot-recover
ExecStart=${REPO_ROOT}/.venv/bin/python -m src.cli.titan_ipc_daemon
ExecStopPost=${REPO_ROOT}/.venv/bin/python -m src.cli.titan_cli swarm checkpoint
KillSignal=SIGTERM
TimeoutStopSec=15
Restart=always
RestartSec=1
LimitMEMLOCK=infinity
LimitNOFILE=1048576

[Install]
WantedBy=default.target
EOF

cat > "${SYSTEMD_USER_DIR}/sovereign-titan-research-harvester-3d.service" <<EOF
[Unit]
Description=Sovereign Titan 3-Day GitHub, arXiv, Hugging Face & Institutional Research Harvester + ACE/ExpeL Evolution

[Service]
Type=oneshot
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=-${REPO_ROOT}/.env
Environment=PYTHONPATH=${REPO_ROOT}
ExecStart=${REPO_ROOT}/.venv/bin/python -m src.cli.titan_cli swarm harvest-research --live-probe
EOF

cat > "${SYSTEMD_USER_DIR}/sovereign-titan-research-harvester-3d.timer" <<EOF
[Unit]
Description=Run Sovereign Titan GitHub/arXiv/HuggingFace Research Harvester ONLY Every 3 Days (72h)

[Timer]
OnBootSec=15min
OnUnitActiveSec=3d
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "[OK] Generated 24/7 systemd user unit files in: ${SYSTEMD_USER_DIR}"
echo "  1. ${SYSTEMD_USER_DIR}/sovereign-titan-llm-fleet.service"
echo "  2. ${SYSTEMD_USER_DIR}/sovereign-titan-daemon.service"
echo "  3. ${SYSTEMD_USER_DIR}/sovereign-titan-research-harvester-3d.service"
echo "  4. ${SYSTEMD_USER_DIR}/sovereign-titan-research-harvester-3d.timer"

if [[ "${1:-}" == "--enable" ]]; then
    systemctl --user daemon-reload
    systemctl --user enable --now sovereign-titan-daemon.service sovereign-titan-research-harvester-3d.timer
    loginctl enable-linger "${USER}" 2>/dev/null || true
    echo "[OK] Enabled and started 24/7 Sovereign Titan systemd services + 3-day research harvester timer."
fi
