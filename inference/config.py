from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "output"
TRACK_DIR = PROJECT_ROOT / "track"
STATE_DIR = PROJECT_ROOT / "state"

for path in (LOG_DIR, OUTPUT_DIR, TRACK_DIR, STATE_DIR):
    path.mkdir(parents=True, exist_ok=True)


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: str) -> int:
    return int(os.getenv(name, default).strip())


def _float_env(name: str, default: str) -> float:
    return float(os.getenv(name, default).strip())


# Backend -> remote/local vLLM
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "local-dev-key")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")

# Backend behavior
MAX_TOOL_ROUNDS = _int_env("MAX_TOOL_ROUNDS", "5")
DEFAULT_TEMPERATURE = _float_env("DEFAULT_TEMPERATURE", "0.0")
DEFAULT_MAX_TOKENS = _int_env("DEFAULT_MAX_TOKENS", "512")

# Backend API server
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = _int_env("BACKEND_PORT", "9000")

# Optional UI
OPEN_WEBUI_PORT = _int_env("OPEN_WEBUI_PORT", "8080")

# Kafka queue mode
QUEUE_ENABLED = _bool_env("QUEUE_ENABLED", "false")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
KAFKA_REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "agent.requests")
KAFKA_RESPONSE_TOPIC = os.getenv("KAFKA_RESPONSE_TOPIC", "agent.responses")
KAFKA_WORKER_GROUP = os.getenv("KAFKA_WORKER_GROUP", "agent-worker")
KAFKA_REQUEST_TIMEOUT_SEC = _float_env("KAFKA_REQUEST_TIMEOUT_SEC", "180")

# Worker micro-batching / concurrency.
KAFKA_BATCH_SIZE = _int_env("KAFKA_BATCH_SIZE", "8")
KAFKA_BATCH_WAIT_MS = _int_env("KAFKA_BATCH_WAIT_MS", "25")
KAFKA_WORKER_CONCURRENCY = _int_env("KAFKA_WORKER_CONCURRENCY", "8")

# Worker metrics
WORKER_METRICS_ENABLED = _bool_env("WORKER_METRICS_ENABLED", "true")
WORKER_METRICS_PORT = _int_env("WORKER_METRICS_PORT", "9101")
