from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentPlan:
    route: str
    tools: list[str] = field(default_factory=list)
    max_rounds: int = 0
    reason: str = ""


@dataclass
class AgentRunResult:
    content: str
    tool_rounds: int
    messages: list[dict[str, Any]]
    raw_response: dict[str, Any] | None = None
    conversation_id: str | None = None
    plan: AgentPlan | None = None
