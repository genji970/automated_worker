#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME=${MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}
VLLM_API_KEY=${VLLM_API_KEY:-local-dev-key}
VLLM_PORT=${VLLM_PORT:-8000}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-4096}
RAY_PORT=${RAY_PORT:-6379}
RAY_DASHBOARD_PORT=${RAY_DASHBOARD_PORT:-8265}
TENSOR_PARALLEL_SIZE=${TENSOR_PARALLEL_SIZE:-1}
PIPELINE_PARALLEL_SIZE=${PIPELINE_PARALLEL_SIZE:-2}
RAY_HEAD_HOST=${RAY_HEAD_HOST:-0.0.0.0}

export PYTHONUNBUFFERED=1
export DISTRIBUTED_EXECUTOR_BACKEND=ray

ray stop || true
ray start \
  --head \
  --node-ip-address="${RAY_HEAD_HOST}" \
  --port="${RAY_PORT}" \
  --dashboard-host=0.0.0.0 \
  --dashboard-port="${RAY_DASHBOARD_PORT}"

python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL_NAME}" \
  --host 0.0.0.0 \
  --port "${VLLM_PORT}" \
  --api-key "${VLLM_API_KEY}" \
  --dtype auto \
  --generation-config vllm \
  --distributed-executor-backend ray \
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}" \
  --pipeline-parallel-size "${PIPELINE_PARALLEL_SIZE}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
