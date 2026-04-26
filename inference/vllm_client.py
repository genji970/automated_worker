from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from inference.config import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, MODEL_NAME


_CLIENT: AsyncOpenAI | None = None


def _base_url() -> str:
    return os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")


def _api_key() -> str:
    return os.getenv("VLLM_API_KEY", "local-dev-key")


def get_client() -> AsyncOpenAI:
    global _CLIENT

    if _CLIENT is None:
        _CLIENT = AsyncOpenAI(
            base_url=_base_url(),
            api_key=_api_key(),
            timeout=120.0,
            max_retries=1,
        )

    return _CLIENT


def _completion_kwargs(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model or MODEL_NAME,
        "messages": messages,
        "temperature": DEFAULT_TEMPERATURE if temperature is None else temperature,
        "max_tokens": DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    return kwargs


async def create_chat_completion(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
):
    client = get_client()
    return await client.chat.completions.create(
        **_completion_kwargs(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
    )


async def stream_chat_completion(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> AsyncIterator[Any]:
    client = get_client()
    stream = await client.chat.completions.create(
        **_completion_kwargs(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        ),
        stream=True,
    )

    async for chunk in stream:
        yield chunk
