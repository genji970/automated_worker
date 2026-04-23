from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from inference.config import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, MAX_TOOL_ROUNDS
from inference.vllm_client import create_chat_completion
from serving.models.schemas import ChatRequest, ChatResponse
from serving.services.tools import TOOLS, execute_tool_call


router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "serving-backend"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/tools")
def tools() -> dict[str, Any]:
    return {"tools": TOOLS}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    working_messages = [m.model_dump(exclude_none=True) for m in request.messages]
    tool_rounds = 0

    while tool_rounds <= MAX_TOOL_ROUNDS:
        response = create_chat_completion(
            messages=working_messages,
            tools=TOOLS,
            temperature=request.temperature if request.temperature is not None else DEFAULT_TEMPERATURE,
            max_tokens=request.max_tokens if request.max_tokens is not None else DEFAULT_MAX_TOKENS,
            model=request.model,
        )
        message = response.choices[0].message
        content = message.content or ""
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            return ChatResponse(
                content=content,
                tool_rounds=tool_rounds,
                raw=response.model_dump(),
            )

        assistant_message = {
            "role": "assistant",
            "content": content,
            "tool_calls": [tool_call.model_dump() for tool_call in tool_calls],
        }
        working_messages.append(assistant_message)

        for tool_call in tool_calls:
            result = execute_tool_call(tool_call.function.name, tool_call.function.arguments)
            working_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        tool_rounds += 1

    return ChatResponse(content="Tool loop limit reached.", tool_rounds=tool_rounds)
