#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$(pwd)}"
export MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}"
export VLLM_PORT="${VLLM_PORT:-8000}"
export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-9000}"

python -m scripts.run_vllm &
VLLM_PID=$!

sleep 15

python -m scripts.run_backend &
BACKEND_PID=$!

trap 'kill ${VLLM_PID} ${BACKEND_PID} || true' EXIT
wait
