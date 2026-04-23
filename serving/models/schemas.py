from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatRequest(BaseModel):
    messages: list[Message]
    temperature: float = 0.0
    max_tokens: int = 512
    model: str | None = None


class ChatResponse(BaseModel):
    content: str
    tool_rounds: int = Field(default=0)
    raw: dict[str, Any] | None = None
