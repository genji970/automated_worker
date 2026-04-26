#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)"

export VLLM_BASE_URL="${VLLM_BASE_URL:?VLLM_BASE_URL is required, e.g. https://xxxx-8000.proxy.runpod.net/v1}"
export VLLM_API_KEY="${VLLM_API_KEY:-local-dev-key}"
export MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}"

export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-9000}"

python -m scripts.run_backend
