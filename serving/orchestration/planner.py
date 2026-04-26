from __future__ import annotations

import json
import re
from typing import Any

from inference.config import MODEL_NAME
from serving.orchestration.llm_runner import call_llm
from serving.orchestration.schemas import AgentPlan
from serving.tools.registry import list_tool_names, list_tools


GMAIL_KEYWORDS = [
    "gmail",
    "지메일",
    "메일",
    "이메일",
    "받은편지함",
    "받은 편지함",
    "보낸편지함",
    "보낸 편지함",
    "메일함",
    "inbox",
    "sent",
    "스팸",
    "spam",
    "안읽은",
    "안 읽은",
    "unread",
    "중요 메일",
    "중요한 이메일",
    "gmail 들어가",
    "지메일 들어가",
    "메일 검색",
    "메일 읽",
    "메일 요약",
    "메일 찾아",
]


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _looks_like_gmail_intent(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in GMAIL_KEYWORDS)


async def _tool_descriptions_for_prompt() -> str:
    lines: list[str] = []

    for tool in await list_tools():
        fn = tool.get("function", {})
        name = fn.get("name", "")
        desc = fn.get("description", "")

        if name:
            lines.append(f"- {name}: {desc}")

    return "\n".join(lines) or "- none"


async def _planner_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last_user = _last_user_text(messages)

    prompt = f"""You are a planner agent for a tool-using assistant.

Decide whether the request should use tools. Return JSON only with this schema:
{{
  "route": "direct" | "tool",
  "tools": ["tool_name"],
  "max_rounds": integer,
  "reason": "short reason"
}}

Available tools:
{await _tool_descriptions_for_prompt()}

Rules:
- Use direct only for general conversation that does not need external data.
- Only choose tool names from the available tools list.
- If the request requires external data, choose route="tool".

Critical Gmail rules:
- If the user mentions Gmail, 지메일, 메일, 이메일, 받은편지함, 보낸편지함, 스팸, 안읽은 메일, 중요 메일, or asks to "gmail 들어가줘", route to "tool".
- For any Gmail/email search, review, summarize, classify, inbox, sent-mail, spam-filtering, unread-mail, or important-mail request, choose gmail_search_messages.
- "gmail 들어가줘" means: use gmail_search_messages to show recent Gmail messages. Do not explain how to log in.
- Never ask for Gmail password.
- Never invent email contents.
- If Gmail data is needed and gmail_search_messages is available, tools must include ["gmail_search_messages"].
- Use gmail_read_messages only after message ids are known from gmail_search_messages.
- Do not archive, trash, label, mark read/unread, send, or modify emails unless the user explicitly confirms.
"""

    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Plan this request:\n\n{last_user}"},
    ]


def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)

    if not match:
        raise ValueError(f"Planner did not return JSON: {text!r}")

    return json.loads(match.group(0))


async def _forced_gmail_plan_if_needed(messages: list[dict[str, Any]]) -> AgentPlan | None:
    last_user = _last_user_text(messages)
    allowed = await list_tool_names()

    if _looks_like_gmail_intent(last_user) and "gmail_search_messages" in allowed:
        return AgentPlan(
            route="tool",
            tools=["gmail_search_messages"],
            max_rounds=3,
            reason=(
                "Forced Gmail route: Gmail/email requests must use "
                "gmail_search_messages and must not be answered directly."
            ),
        )

    return None


async def _fallback_plan(messages: list[dict[str, Any]]) -> AgentPlan:
    forced = await _forced_gmail_plan_if_needed(messages)
    if forced is not None:
        return forced

    last_user = _last_user_text(messages)
    text = last_user.lower()
    allowed = await list_tool_names()
    tools: list[str] = []

    if "get_time" in allowed and any(
        k in text
        for k in [
            "time",
            "what time",
            "current time",
            "몇 시",
            "시간",
            "asia/seoul",
            "seoul",
        ]
    ):
        tools.append("get_time")

    if "get_weather" in allowed and any(
        k in text
        for k in ["weather", "forecast", "날씨", "기온"]
    ):
        tools.append("get_weather")

    if "calculator" in allowed and (
        any(k in text for k in ["calculate", "compute", "calculator", "계산"])
        or any(op in last_user for op in ["+", "-", "*", "/", "%", "×"])
    ):
        tools.append("calculator")

    if tools:
        return AgentPlan(
            route="tool",
            tools=tools,
            max_rounds=4,
            reason="fallback rule-based plan",
        )

    return AgentPlan(
        route="direct",
        tools=[],
        max_rounds=0,
        reason="fallback direct plan",
    )


async def plan_request_with_llm(
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
) -> AgentPlan:
    # Deterministic guard first.
    # Gmail/email requests must never go direct because the model can hallucinate email contents.
    forced = await _forced_gmail_plan_if_needed(messages)
    if forced is not None:
        return forced

    try:
        response = await call_llm(
            agent="planner",
            messages=await _planner_messages(messages),
            tools=None,
            temperature=0.0,
            max_tokens=256,
            model=model or MODEL_NAME,
        )

        content = response.choices[0].message.content or ""
        parsed = _json_from_text(content)

        route = str(parsed.get("route", "direct")).strip().lower()

        if route not in {"direct", "tool"}:
            route = "direct"

        tools = parsed.get("tools", [])

        if not isinstance(tools, list):
            tools = []

        allowed = await list_tool_names()
        clean_tools: list[str] = []

        for tool in tools:
            tool = str(tool)

            if tool in allowed and tool not in clean_tools:
                clean_tools.append(tool)

        # Deterministic guard again after the LLM planner.
        last_user = _last_user_text(messages)
        if _looks_like_gmail_intent(last_user) and "gmail_search_messages" in allowed:
            return AgentPlan(
                route="tool",
                tools=["gmail_search_messages"],
                max_rounds=3,
                reason="Overrode LLM planner: Gmail/email request must use gmail_search_messages.",
            )

        if not clean_tools and route == "tool":
            route = "direct"

        max_rounds = parsed.get("max_rounds", 0)

        try:
            max_rounds = int(max_rounds)
        except Exception:
            max_rounds = 0

        return AgentPlan(
            route=route,
            tools=clean_tools,
            max_rounds=max(0, min(max_rounds, 8)),
            reason=str(parsed.get("reason", "llm planner")),
        )

    except Exception:
        return await _fallback_plan(messages)
