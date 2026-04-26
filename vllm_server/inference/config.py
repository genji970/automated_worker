from __future__ import annotations

import os

# vLLM model server settings
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "local-dev-key")
VLLM_PORT = int(os.getenv("VLLM_PORT", "8000"))
MAX_MODEL_LEN = os.getenv("MAX_MODEL_LEN", "4096")

# Single-node: mp | Multi-node: ray
DISTRIBUTED_EXECUTOR_BACKEND = os.getenv("DISTRIBUTED_EXECUTOR_BACKEND", "mp")
TENSOR_PARALLEL_SIZE = int(os.getenv("TENSOR_PARALLEL_SIZE", "1"))
PIPELINE_PARALLEL_SIZE = int(os.getenv("PIPELINE_PARALLEL_SIZE", "1"))

# Ray multi-node settings
RAY_PORT = int(os.getenv("RAY_PORT", "6379"))
RAY_DASHBOARD_PORT = int(os.getenv("RAY_DASHBOARD_PORT", "8265"))
RAY_HEAD_HOST = os.getenv("RAY_HEAD_HOST", "0.0.0.0")
