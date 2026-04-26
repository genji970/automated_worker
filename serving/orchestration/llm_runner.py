from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from prometheus_client import Counter, Histogram

from inference.vllm_client import create_chat_completion, stream_chat_completion


AGENT_LLM_CALLS = Counter(
    "backend_agent_llm_calls_total",
    "Total LLM calls made by backend agents",
    ["agent", "status"],
)

AGENT_LLM_LATENCY = Histogram(
    "backend_agent_llm_latency_seconds",
    "Latency of LLM calls made by backend agents",
    ["agent"],
)

BACKEND_VLLM_CALLS = Counter(
    "backend_vllm_calls_total",
    "Total backend-to-vLLM calls",
    ["status"],
)

BACKEND_VLLM_LATENCY = Histogram(
    "backend_vllm_latency_seconds",
    "Latency of backend-to-vLLM calls in seconds",
)


async def call_llm(
    *,
    agent: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    temperature: float,
    max_tokens: int,
    model: str | None,
):
    start = time.perf_counter()

    try:
        response = await create_chat_completion(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
        AGENT_LLM_CALLS.labels(agent=agent, status="success").inc()
        BACKEND_VLLM_CALLS.labels(status="success").inc()
        return response

    except Exception:
        AGENT_LLM_CALLS.labels(agent=agent, status="error").inc()
        BACKEND_VLLM_CALLS.labels(status="error").inc()
        raise

    finally:
        elapsed = time.perf_counter() - start
        AGENT_LLM_LATENCY.labels(agent=agent).observe(elapsed)
        BACKEND_VLLM_LATENCY.observe(elapsed)


async def stream_llm(
    *,
    agent: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    temperature: float,
    max_tokens: int,
    model: str | None,
) -> AsyncIterator[Any]:
    start = time.perf_counter()

    try:
        async for chunk in stream_chat_completion(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        ):
            yield chunk

        AGENT_LLM_CALLS.labels(agent=agent, status="success").inc()
        BACKEND_VLLM_CALLS.labels(status="success").inc()

    except Exception:
        AGENT_LLM_CALLS.labels(agent=agent, status="error").inc()
        BACKEND_VLLM_CALLS.labels(status="error").inc()
        raise

    finally:
        elapsed = time.perf_counter() - start
        AGENT_LLM_LATENCY.labels(agent=agent).observe(elapsed)
        BACKEND_VLLM_LATENCY.observe(elapsed)
