from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "output"
RUN_DIR = OUTPUT_DIR / "run"
SERVE_CACHE_DIR = OUTPUT_DIR / "serve"
DATA_DIR = PROJECT_ROOT / "data"
TRACK_DIR = PROJECT_ROOT / "track"

for path in (LOG_DIR, OUTPUT_DIR, RUN_DIR, SERVE_CACHE_DIR, DATA_DIR, TRACK_DIR):
    path.mkdir(parents=True, exist_ok=True)

# Backend <-> vLLM
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "local-dev-key")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
DEFAULT_SERVED_MODEL = os.getenv("SERVED_MODEL_PATH", str(RUN_DIR / "default_run" / "final"))

# Backend behavior
MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "5"))
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.0"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "512"))

# Ports
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "9000"))
VLLM_PORT = int(os.getenv("VLLM_PORT", "8000"))
MAX_MODEL_LEN = os.getenv("MAX_MODEL_LEN", "4096")

# vLLM distributed serving
DISTRIBUTED_EXECUTOR_BACKEND = os.getenv("DISTRIBUTED_EXECUTOR_BACKEND", "mp")  # mp | ray
TENSOR_PARALLEL_SIZE = int(os.getenv("TENSOR_PARALLEL_SIZE", "1"))
PIPELINE_PARALLEL_SIZE = int(os.getenv("PIPELINE_PARALLEL_SIZE", "1"))

# Ray
RAY_PORT = int(os.getenv("RAY_PORT", "6379"))
RAY_DASHBOARD_PORT = int(os.getenv("RAY_DASHBOARD_PORT", "8265"))
RAY_HEAD_HOST = os.getenv("RAY_HEAD_HOST", "127.0.0.1")

# Monitoring / load test
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
GRAFANA_PORT = int(os.getenv("GRAFANA_PORT", "3000"))
OPEN_WEBUI_PORT = int(os.getenv("OPEN_WEBUI_PORT", "8080"))
JMETER_RMI_PORT = int(os.getenv("JMETER_RMI_PORT", "1099"))
