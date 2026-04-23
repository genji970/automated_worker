from __future__ import annotations

from typing import Any, Iterable

from openai import OpenAI

from inference.config import MODEL_NAME, VLLM_API_KEY, VLLM_BASE_URL


_client = OpenAI(base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY)


def create_chat_completion(
    messages: Iterable[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    model: str | None = None,
):
    return _client.chat.completions.create(
        model=model or MODEL_NAME,
        messages=list(messages),
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    )
