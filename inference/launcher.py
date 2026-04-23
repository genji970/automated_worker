from __future__ import annotations

import os
import subprocess
import sys

from inference.config import (
    DISTRIBUTED_EXECUTOR_BACKEND,
    MAX_MODEL_LEN,
    MODEL_NAME,
    PIPELINE_PARALLEL_SIZE,
    TENSOR_PARALLEL_SIZE,
    VLLM_API_KEY,
    VLLM_PORT,
)


def build_vllm_command(model_path: str, enable_tools: bool = True) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        model_path,
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
        "--dtype",
        "auto",
        "--api-key",
        VLLM_API_KEY,
        "--generation-config",
        "vllm",
        "--distributed-executor-backend",
        str(DISTRIBUTED_EXECUTOR_BACKEND),
        "--tensor-parallel-size",
        str(TENSOR_PARALLEL_SIZE),
        "--pipeline-parallel-size",
        str(PIPELINE_PARALLEL_SIZE),
    ]
    if MAX_MODEL_LEN:
        cmd.extend(["--max-model-len", str(MAX_MODEL_LEN)])
    if enable_tools:
        cmd.extend(["--enable-auto-tool-choice", "--tool-call-parser", "hermes"])
    return cmd


def launch_vllm(model_path: str | None = None, enable_tools: bool = True) -> int:
    cmd = build_vllm_command(model_path or MODEL_NAME, enable_tools=enable_tools)
    print("[vllm]", " ".join(cmd), flush=True)
    return subprocess.call(cmd, env=os.environ.copy())
