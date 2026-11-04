#!/usr/bin/env bash
# ==============================================================================
# SOVEREIGN TITAN OS — 4-LANE LOCAL LLM SWARM LAUNCHER (LIVE ONBOARD FLEET)
# Hardware Topology:
#   - Lane 1 (Port 8005 | GPU 1, 15% VRAM):
#       Hermes-3-8B-AWQ (vLLM, --enable-prefix-caching, --tool-call-parser hermes)
#       [Sub-45ms Tactical Gatekeeper & Tool Router]
#   - Lane 2 & 3 (Port 8002 | GPU 0+1 Split, BF16 GGUF, 1M KV Pool):
#       Qwen3.8-27B-Uncensored-BF16.gguf via llama-server
#       [Vision Banner/OCR + Deep Reasoner & GEPA 60-Trace Evolver]
#   - Lane 4 (Port 8006 | GPU 0, 18% VRAM):
#       Qwen2.5-3B-Instruct (vLLM, --enable-prefix-caching)
#       [Fast Triage Micro-Classifier (<25ms)]
#   - Lane 5 / Semantic Memory (Port 8007 | CUDA/CPU):
#       BGE-M3 + bge-reranker-v2 (/ai/tools/embed_service.py)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="/mnt/ramdisk/execution_state/llm_logs"
PID_DIR="/mnt/ramdisk/execution_state/llm_pids"
mkdir -p "${LOG_DIR}" "${PID_DIR}"

MODE="${1:---status}"
TARGET_LANE="${2:-all}"

MODEL_8005="${LLM_GATEKEEPER_MODEL_PATH:-/ai/models/Hermes-3-8B-AWQ}"
MODEL_8002="${LLM_DEEP_REASONER_GGUF_PATH:-/ai/models/JonathanColetti/Qwen3.8-27B-Uncensored-GGUF/Qwen3.8-27B-Uncensored-BF16.gguf}"
MODEL_8006="${LLM_FAST_L3_MODEL_PATH:-/ai/models/Qwen2.5-3B-Instruct}"
EMBED_SCRIPT="${LLM_EMBED_SCRIPT_PATH:-/ai/tools/embed_service.py}"
LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-/home/titanagentik/.unsloth/llama.cpp/llama-server}"
VLLM_BIN="${VLLM_BIN:-/ai/venvs/vllm/bin/vllm}"
DATA_PYTHON="${DATA_PYTHON:-/ai/venvs/data/bin/python}"

is_port_listening() {
    local port="$1"
    ss -tln "sport = :${port}" | grep -q LISTEN
}

start_lane_8005() {
    if is_port_listening 8005; then
        echo "[LANE 8005] Already listening on 127.0.0.1:8005 (Hermes-3-8B-AWQ Tactical Gatekeeper & MCP Router)"
        return 0
    fi
    if systemctl --user start fleet-8b.service 2>/dev/null; then
        echo "[LANE 8005] Started systemd unit fleet-8b.service on 127.0.0.1:8005"
        return 0
    fi
    echo "[LANE 8005] Launching ${MODEL_8005} on GPU 1 (:8005, 15% VRAM, prefix-caching, hermes)..."
    CUDA_VISIBLE_DEVICES=1 "${VLLM_BIN}" serve "${MODEL_8005}" \
        --host 127.0.0.1 \
        --port 8005 \
        --served-model-name hermes3-8b-awq \
        --quantization awq \
        --tensor-parallel-size 1 \
        --max-model-len 8192 \
        --max-num-seqs 32 \
        --gpu-memory-utilization 0.15 \
        --enable-prefix-caching \
        --enable-chunked-prefill \
        --trust-remote-code \
        --enable-auto-tool-choice \
        --tool-call-parser hermes \
        > "${LOG_DIR}/lane_8005_gatekeeper.log" 2>&1 &
    echo $! > "${PID_DIR}/lane_8005.pid"
    echo "[LANE 8005] Started PID $(cat "${PID_DIR}/lane_8005.pid")"
}

start_lane_8002() {
    if is_port_listening 8002; then
        echo "[LANE 8002] Already listening on 127.0.0.1:8002 (Qwen3.8-27B-Uncensored BF16 Vision & Deep Reasoner)"
        return 0
    fi
    if systemctl --user start fleet-32b.service 2>/dev/null; then
        echo "[LANE 8002] Started systemd unit fleet-32b.service on 127.0.0.1:8002"
        return 0
    fi
    echo "[LANE 8002] Launching ${MODEL_8002} on GPU 0+1 (:8002, 1M KV pool)..."
    "${LLAMA_SERVER_BIN}" \
        -m "${MODEL_8002}" \
        --host 127.0.0.1 \
        --port 8002 \
        --alias qwen3.8-27b-uncensored-bf16 \
        -ngl 99 --split-mode layer --tensor-split 1,1 \
        -c 1048576 --kv-unified --kv-unified-per-slot 1048576 -np 2 -fa on \
        --rope-scaling yarn --rope-scale 4 \
        --jinja --metrics \
        > "${LOG_DIR}/lane_8002_deep_reasoner.log" 2>&1 &
    echo $! > "${PID_DIR}/lane_8002.pid"
    echo "[LANE 8002] Started PID $(cat "${PID_DIR}/lane_8002.pid")"
}

start_lane_8006() {
    if is_port_listening 8006; then
        echo "[LANE 8006] Already listening on 127.0.0.1:8006 (Qwen2.5-3B-Instruct Fast Triage)"
        return 0
    fi
    if systemctl --user start fleet-3b.service 2>/dev/null; then
        echo "[LANE 8006] Started systemd unit fleet-3b.service on 127.0.0.1:8006"
        return 0
    fi
    echo "[LANE 8006] Launching ${MODEL_8006} on GPU 0 (:8006, 18% VRAM)..."
    CUDA_VISIBLE_DEVICES=0 "${VLLM_BIN}" serve "${MODEL_8006}" \
        --host 127.0.0.1 \
        --port 8006 \
        --served-model-name qwen2.5-3b \
        --tensor-parallel-size 1 \
        --max-model-len 4096 \
        --max-num-seqs 64 \
        --gpu-memory-utilization 0.18 \
        --enable-prefix-caching \
        --enable-chunked-prefill \
        --trust-remote-code \
        > "${LOG_DIR}/lane_8006_fast_l3.log" 2>&1 &
    echo $! > "${PID_DIR}/lane_8006.pid"
    echo "[LANE 8006] Started PID $(cat "${PID_DIR}/lane_8006.pid")"
}

start_lane_8007() {
    if is_port_listening 8007; then
        echo "[LANE 8007] Already listening on 127.0.0.1:8007 (BGE-M3 + bge-reranker-v2 Embed/Rerank)"
        return 0
    fi
    if systemctl --user start fleet-embed.service 2>/dev/null; then
        echo "[LANE 8007] Started systemd unit fleet-embed.service on 127.0.0.1:8007"
        return 0
    fi
    echo "[LANE 8007] Launching ${EMBED_SCRIPT} on :8007..."
    PYTHONPATH="" "${DATA_PYTHON}" "${EMBED_SCRIPT}" \
        > "${LOG_DIR}/lane_8007_embed.log" 2>&1 &
    echo $! > "${PID_DIR}/lane_8007.pid"
    echo "[LANE 8007] Started PID $(cat "${PID_DIR}/lane_8007.pid")"
}

show_status() {
    echo "=============================================================================="
    echo "[SOVEREIGN TITAN] Live Local LLM Swarm Status (:8005, :8002, :8006, :8007)"
    echo "=============================================================================="
    for port in 8005 8002 8006 8007; do
        if is_port_listening "${port}"; then
            if [[ "${port}" == "8007" ]]; then
                echo "  [PORT ${port}] ONLINE  (http://127.0.0.1:${port}/health)"
            else
                echo "  [PORT ${port}] ONLINE  (http://127.0.0.1:${port}/v1)"
            fi
        else
            if [[ "${port}" == "8007" ]]; then
                echo "  [PORT ${port}] OFFLINE (http://127.0.0.1:${port}/health)"
            else
                echo "  [PORT ${port}] OFFLINE (http://127.0.0.1:${port}/v1)"
            fi
        fi
    done
    echo "=============================================================================="
}

stop_lanes() {
    for port in 8005 8002 8006 8007; do
        if [[ -f "${PID_DIR}/lane_${port}.pid" ]]; then
            pid="$(cat "${PID_DIR}/lane_${port}.pid")"
            if kill -0 "${pid}" 2>/dev/null; then
                echo "[STOP] Stopping Lane ${port} (PID ${pid})..."
                kill "${pid}" || true
            fi
            rm -f "${PID_DIR}/lane_${port}.pid"
        fi
    done
}

case "${MODE}" in
    --start)
        case "${TARGET_LANE}" in
            8005|8000) start_lane_8005 ;;
            8002|8001) start_lane_8002 ;;
            8006|8003) start_lane_8006 ;;
            8007) start_lane_8007 ;;
            all)
                start_lane_8005
                start_lane_8002
                start_lane_8006
                start_lane_8007
                ;;
            *)
                echo "Unknown lane: ${TARGET_LANE} (expected 8005|8002|8006|8007|all)"
                exit 1
                ;;
        esac
        show_status
        ;;
    --stop)
        stop_lanes
        show_status
        ;;
    --status|--check-only)
        show_status
        ;;
    *)
        echo "Usage: $0 [--start|--stop|--status|--check-only] [8005|8002|8006|8007|all]"
        exit 1
        ;;
esac
