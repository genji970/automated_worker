#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)"

export MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}"
export VLLM_API_KEY="${VLLM_API_KEY:-local-dev-key}"
export VLLM_PORT="${VLLM_PORT:-8000}"
export MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"

export RAY_PORT="${RAY_PORT:-6379}"
export RAY_DASHBOARD_PORT="${RAY_DASHBOARD_PORT:-8265}"
export RAY_HEAD_HOST="${RAY_HEAD_HOST:-0.0.0.0}"

export TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
export PIPELINE_PARALLEL_SIZE="${PIPELINE_PARALLEL_SIZE:-2}"
export DISTRIBUTED_EXECUTOR_BACKEND="ray"
export PYTHONUNBUFFERED=1

ray stop || true
ray start \
  --head \
  --node-ip-address="${RAY_HEAD_HOST}" \
  --port="${RAY_PORT}" \
  --dashboard-host=0.0.0.0 \
  --dashboard-port="${RAY_DASHBOARD_PORT}"

python -m scripts.run_vllm
