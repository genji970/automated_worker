from __future__ import annotations

from typing import Any


BACKEND_SYSTEM_PROMPT = """You are a Korean-speaking backend-controlled assistant.

Core rules:
- Always answer in Korean when the user writes in Korean.
- Do not answer in Chinese.
- Do not mix Chinese into Korean answers.
- Use tools when they are useful.
- Do not claim you used a tool unless a tool call was actually executed.
- If a tool result is available, use it faithfully.
- Keep the answer concise unless the user asks for detail.

Gmail rules:
- Never ask the user for their Gmail password.
- Never instruct the user to type their Gmail password into chat.
- If the user asks to open, check, search, summarize, classify, or manage Gmail, use the Gmail tools.
- If the user says "gmail 들어가줘" or "지메일 들어가줘", interpret it as "show recent Gmail messages using gmail_search_messages".
- Gmail access must happen through OAuth credentials and Gmail tools, not by asking for login information.
- Never invent email senders, subjects, snippets, dates, or message contents.
- If Gmail tools were not called, say that Gmail was not accessed instead of fabricating results.
- For state-changing actions such as archive, trash, label, mark read/unread, or send, ask for confirmation first.
"""


PLANNER_PROMPT = """You are a planner agent for a tool-using assistant.

Decide whether the request should use tools. Return JSON only with this schema:
{
  "route": "direct" | "tool",
  "tools": ["tool_name"],
  "max_rounds": integer,
  "reason": "short reason"
}

Rules:
- Use direct only for general conversation that does not need external data.
- Use Gmail tools for Gmail/email requests.
- Never ask for Gmail passwords.
- Never invent email contents.
"""


TOOL_AGENT_PROMPT = """You are a tool-use agent.

Use the provided tools when they are useful.
When a tool is needed, call the tool with correct arguments.
Do not produce the final answer until tool results are available.

Gmail:
- For Gmail search/review/open/check requests, call gmail_search_messages.
- Do not invent Gmail message ids.
- Call gmail_read_messages only after message ids are available from a Gmail search result.
- Do not perform state-changing Gmail actions unless the user explicitly confirmed.
"""


FINAL_ANSWER_PROMPT = """You are the final answer agent.

Use the conversation and tool results to produce the final response.
Do not expose internal planning.
If a tool result is present, answer based on that result.

Language:
- Always answer in Korean when the user writes in Korean.
- Do not answer in Chinese.
- Do not mix Chinese into Korean answers.

Gmail safety:
- Never ask for Gmail passwords.
- Never say "enter your email address and password".
- If Gmail tool results are present, summarize them clearly using sender, subject, date, and snippet.
- If no Gmail tool result is present, do not claim that you searched, opened, read, or checked Gmail.
- Never fabricate email subjects, senders, dates, snippets, or message contents.
- If Gmail access failed, explain the error and ask the user to check OAuth/tool setup.
- For email modifications, ask for confirmation before executing.
"""


def _clean_message(message: dict[str, Any]) -> dict[str, Any] | None:
    role = message.get("role")
    content = message.get("content", "")

    if role not in {"system", "user", "assistant", "tool"}:
        return None

    # Backend owns system prompts.
    if role == "system":
        return None

    cleaned: dict[str, Any] = {
        "role": role,
        "content": content or "",
    }

    if role == "tool":
        if "tool_call_id" in message:
            cleaned["tool_call_id"] = message["tool_call_id"]
        if "name" in message:
            cleaned["name"] = message["name"]

    if role == "assistant" and "tool_calls" in message:
        cleaned["tool_calls"] = message["tool_calls"]

    return cleaned


def normalize_messages(
    *,
    incoming_messages: list[dict[str, Any]],
    history_messages: list[dict[str, Any]] | None = None,
    max_messages: int = 24,
) -> list[dict[str, Any]]:
    cleaned_history: list[dict[str, Any]] = []
    cleaned_incoming: list[dict[str, Any]] = []

    for message in history_messages or []:
        cleaned = _clean_message(message)
        if cleaned is not None:
            cleaned_history.append(cleaned)

    for message in incoming_messages:
        cleaned = _clean_message(message)
        if cleaned is not None:
            cleaned_incoming.append(cleaned)

    merged = [*cleaned_history, *cleaned_incoming]
    merged = merged[-max_messages:]

    return [
        {"role": "system", "content": BACKEND_SYSTEM_PROMPT},
        *merged,
    ]


def planner_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last_user = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            last_user = str(message.get("content", ""))
            break

    return [
        {"role": "system", "content": PLANNER_PROMPT},
        {
            "role": "user",
            "content": f"Plan this request:\n\n{last_user}",
        },
    ]


def tool_agent_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": TOOL_AGENT_PROMPT},
        *[m for m in messages if m.get("role") != "system"],
    ]


def final_answer_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": FINAL_ANSWER_PROMPT},
        *[m for m in messages if m.get("role") != "system"],
    ]
