#!/usr/bin/env bash
# ==============================================================================
# SOVEREIGN TITAN OS — LOW-LATENCY TAURI v2 GUI & IPC DAEMON LAUNCHER
# Pins IPC & GUI threads to Threadripper Cores 32-35 so MEV Hot-Path Cores
# (0-31) remain 100% isolated from UI rendering interrupts.
# ==============================================================================
set -euo pipefail

SOURCE_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SOURCE_PATH}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GUI_BIN="${WORKSPACE_ROOT}/hermes-skills/sovereign-gui-command-center/src-tauri/target/release/sovereign-gui-command-center"
VENV_PYTHON="${WORKSPACE_ROOT}/.venv/bin/python3"

if [[ "${1:-}" == "--verify-only" ]]; then
    [[ -x "${GUI_BIN}" ]] || { echo "[ERR] Missing GUI binary: ${GUI_BIN}" >&2; exit 1; }
    echo "[OK] titan-gui launcher verified (binary=${GUI_BIN})"
    exit 0
fi

mkdir -p /mnt/ramdisk/execution_state

cd "${WORKSPACE_ROOT}"
export PYTHONPATH="${WORKSPACE_ROOT}:${PYTHONPATH:-}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"

IPC_LOG="/mnt/ramdisk/execution_state/titan_ipc_daemon.log"
IPC_SOCK="/mnt/ramdisk/titan_ipc.sock"

DAEMON_SRC="${WORKSPACE_ROOT}/src/ipc/titan_ipc_daemon.py"
if pgrep -f "[s]rc.ipc.titan_ipc_daemon" >/dev/null 2>&1 && [[ -S "${IPC_SOCK}" ]] && [[ "${DAEMON_SRC}" -nt "${IPC_SOCK}" ]]; then
    echo "[TITAN-GUI] Detected updated titan_ipc_daemon.py -> restarting daemon..."
    pkill -f "[s]rc.ipc.titan_ipc_daemon" || true
    sleep 0.3
fi

if ! pgrep -f "[s]rc.ipc.titan_ipc_daemon" >/dev/null 2>&1; then
    echo "[TITAN-GUI] Starting sub-0.25ms TitanIPCDaemon on Cores 32-35..."
    rm -f "${IPC_SOCK}"
    setsid taskset -c 32-35 "${VENV_PYTHON}" -m src.ipc.titan_ipc_daemon > "${IPC_LOG}" 2>&1 < /dev/null &
    for _ in {1..120}; do
        if [[ -S "${IPC_SOCK}" ]]; then
            break
        fi
        sleep 0.05
    done
fi

if [[ "${1:-}" == "--daemon-only" ]]; then
    echo "[TITAN-GUI] TitanIPCDaemon running (--daemon-only)."
    exit 0
fi

export DISPLAY="${DISPLAY:-:0}"
if [[ -z "${WAYLAND_DISPLAY:-}" && -S "${XDG_RUNTIME_DIR}/wayland-1" ]]; then
    export WAYLAND_DISPLAY="wayland-1"
elif [[ -z "${WAYLAND_DISPLAY:-}" && -S "${XDG_RUNTIME_DIR}/wayland-0" ]]; then
    export WAYLAND_DISPLAY="wayland-0"
fi
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export WEBKIT_DISABLE_COMPOSITING_MODE=1

echo "[TITAN-GUI] Launching Sovereign Titan Command Center (Tauri v2 + React 19) on Cores 32-35..."
exec taskset -c 32-35 "${GUI_BIN}" "$@"
