from __future__ import annotations

from inference.config import MODEL_NAME
from inference.launcher import launch_vllm


if __name__ == "__main__":
    raise SystemExit(launch_vllm(MODEL_NAME, enable_tools=True))
