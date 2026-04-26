from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from prometheus_client import Counter, Histogram

from inference.config import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    MAX_TOOL_ROUNDS,
    MODEL_NAME,
)
from serving.orchestration.history_store import (
    append_message,
    ensure_conversation,
    extract_last_user_message,
    load_history,
)
from serving.orchestration.llm_runner import call_llm, stream_llm
from serving.orchestration.planner import plan_request_with_llm
from serving.orchestration.prompt_builder import (
    final_answer_messages,
    normalize_messages,
    tool_agent_messages,
)
from serving.orchestration.schemas import AgentPlan, AgentRunResult
from serving.orchestration.tool_executor import (
    execute_tool_with_metrics,
    get_tool_policy,
    select_tools,
)


BACKEND_CHAT_REQUESTS = Counter(
    "backend_chat_requests_total",
    "Total chat requests handled by backend",
    ["endpoint", "status"],
)

BACKEND_CHAT_LATENCY = Histogram(
    "backend_chat_latency_seconds",
    "End-to-end backend chat latency in seconds",
    ["endpoint"],
)

AGENT_ROUTE_COUNTER = Counter(
    "backend_agent_route_total",
    "Total requests routed by backend planner",
    ["route"],
)


def _message_to_dict(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump()

    if isinstance(message, dict):
        return message

    return {}


def _extract_tool_calls(message: Any) -> list[Any]:
    tool_calls = getattr(message, "tool_calls", None)

    if tool_calls is None and isinstance(message, dict):
        tool_calls = message.get("tool_calls")

    return list(tool_calls or [])


def _extract_content(message: Any) -> str:
    content = getattr(message, "content", None)

    if content is None and isinstance(message, dict):
        content = message.get("content")

    return content or ""


def _tool_call_to_dict(tool_call: Any) -> dict[str, Any]:
    if hasattr(tool_call, "model_dump"):
        return tool_call.model_dump()

    if isinstance(tool_call, dict):
        return tool_call

    return {}


def _tool_name_and_arguments(
    tool_call: Any,
) -> tuple[str, str | dict | None, str | None]:
    if isinstance(tool_call, dict):
        function = tool_call.get("function", {})
        return (
            function.get("name", ""),
            function.get("arguments"),
            tool_call.get("id"),
        )

    function = getattr(tool_call, "function", None)
    tool_name = getattr(function, "name", "") if function is not None else ""
    arguments = getattr(function, "arguments", None) if function is not None else None
    tool_call_id = getattr(tool_call, "id", None)

    return tool_name, arguments, tool_call_id


async def _prepare_working_messages(
    *,
    incoming_messages: list[dict[str, Any]],
    conversation_id: str | None,
) -> tuple[str, list[dict[str, Any]]]:
    cid = await ensure_conversation(conversation_id)

    last_user_message = extract_last_user_message(incoming_messages)

    if last_user_message is not None:
        await append_message(
            conversation_id=cid,
            role="user",
            content=str(last_user_message.get("content", "")),
            payload={},
        )

    history_messages = await load_history(conversation_id=cid, limit=20)

    working_messages = normalize_messages(
        incoming_messages=incoming_messages,
        history_messages=history_messages,
    )

    return cid, working_messages


async def _execute_tool_calls(
    *,
    tool_calls: list[Any],
    working_messages: list[dict[str, Any]],
    conversation_id: str,
) -> None:
    parallel_items: list[tuple[str, str | dict | None, str | None]] = []
    sequential_items: list[tuple[str, str | dict | None, str | None]] = []

    for tool_call in tool_calls:
        tool_name, arguments, tool_call_id = _tool_name_and_arguments(tool_call)
        policy = get_tool_policy(tool_name)
        item = (tool_name, arguments, tool_call_id)

        if policy.parallel_safe and not policy.state_changing:
            parallel_items.append(item)
        else:
            sequential_items.append(item)

    async def run_one(
        item: tuple[str, str | dict | None, str | None]
    ) -> tuple[str, str | None, dict[str, Any]]:
        tool_name, arguments, tool_call_id = item
        result = await execute_tool_with_metrics(
            tool_name=tool_name,
            arguments=arguments,
        )
        return tool_name, tool_call_id, result

    results: list[tuple[str, str | None, dict[str, Any]]] = []

    if parallel_items:
        gathered = await asyncio.gather(
            *[run_one(item) for item in parallel_items],
            return_exceptions=True,
        )

        for item, value in zip(parallel_items, gathered, strict=False):
            tool_name, _, tool_call_id = item
            if isinstance(value, Exception):
                results.append(
                    (
                        tool_name,
                        tool_call_id,
                        {"error": str(value), "tool_name": tool_name},
                    )
                )
            else:
                results.append(value)

    for item in sequential_items:
        try:
            results.append(await run_one(item))
        except Exception as exc:
            tool_name, _, tool_call_id = item
            results.append(
                (
                    tool_name,
                    tool_call_id,
                    {"error": str(exc), "tool_name": tool_name},
                )
            )

    for tool_name, tool_call_id, result in results:
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": json.dumps(result, ensure_ascii=False),
        }

        working_messages.append(tool_message)

        await append_message(
            conversation_id=conversation_id,
            role="tool",
            content=tool_message["content"],
            payload={
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
            },
        )


async def _run_planner_and_tools(
    *,
    working_messages: list[dict[str, Any]],
    conversation_id: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> tuple[AgentPlan, int]:
    plan = await plan_request_with_llm(messages=working_messages, model=model)
    AGENT_ROUTE_COUNTER.labels(route=plan.route).inc()

    if plan.route == "direct":
        return plan, 0

    selected_tools = await select_tools(plan.tools)
    tool_rounds = 0

    while tool_rounds <= min(plan.max_rounds, MAX_TOOL_ROUNDS):
        response = await call_llm(
            agent="tool_use",
            messages=tool_agent_messages(working_messages),
            tools=selected_tools,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )

        message = response.choices[0].message
        content = _extract_content(message)
        tool_calls = _extract_tool_calls(message)

        assistant_message = {
            "role": "assistant",
            "content": content,
        }

        if tool_calls:
            assistant_message["tool_calls"] = [
                _tool_call_to_dict(tool_call) for tool_call in tool_calls
            ]

        working_messages.append(assistant_message)

        if not tool_calls:
            break

        await _execute_tool_calls(
            tool_calls=tool_calls,
            working_messages=working_messages,
            conversation_id=conversation_id,
        )

        tool_rounds += 1

    return plan, tool_rounds


async def run_agent_from_messages_direct(
    *,
    incoming_messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    conversation_id: str | None = None,
    endpoint: str = "/chat",
) -> AgentRunResult:
    start_total = time.perf_counter()

    temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    max_tokens = DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens
    model = model or MODEL_NAME

    try:
        cid, working_messages = await _prepare_working_messages(
            incoming_messages=incoming_messages,
            conversation_id=conversation_id,
        )

        plan, tool_rounds = await _run_planner_and_tools(
            working_messages=working_messages,
            conversation_id=cid,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        final_response = await call_llm(
            agent="final_answer",
            messages=final_answer_messages(working_messages),
            tools=None,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )

        final_message = final_response.choices[0].message
        final_content = _extract_content(final_message)

        await append_message(
            conversation_id=cid,
            role="assistant",
            content=final_content,
            payload={
                "agent": "final_answer",
                "route": plan.route,
                "tool_rounds": tool_rounds,
            },
        )

        BACKEND_CHAT_REQUESTS.labels(endpoint=endpoint, status="success").inc()

        return AgentRunResult(
            content=final_content,
            tool_rounds=tool_rounds,
            messages=[*working_messages, _message_to_dict(final_message)],
            raw_response=final_response.model_dump(),
            conversation_id=cid,
            plan=plan,
        )

    except Exception:
        BACKEND_CHAT_REQUESTS.labels(endpoint=endpoint, status="error").inc()
        raise

    finally:
        BACKEND_CHAT_LATENCY.labels(endpoint=endpoint).observe(
            time.perf_counter() - start_total
        )


async def run_agent_from_openai_payload_direct(
    payload: dict[str, Any],
) -> AgentRunResult:
    messages = payload.get("messages", [])
    model = payload.get("model", MODEL_NAME)
    temperature = payload.get("temperature", DEFAULT_TEMPERATURE)
    max_tokens = payload.get("max_tokens", DEFAULT_MAX_TOKENS)

    conversation_id = None
    metadata = payload.get("metadata")

    if isinstance(metadata, dict):
        conversation_id = metadata.get("conversation_id")

    conversation_id = (
        payload.get("conversation_id")
        or payload.get("conversationId")
        or conversation_id
    )

    if not isinstance(messages, list):
        raise ValueError("`messages` must be a list.")

    return await run_agent_from_messages_direct(
        incoming_messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        conversation_id=conversation_id,
        endpoint="/v1/chat/completions",
    )


async def stream_agent_from_openai_payload_direct(
    payload: dict[str, Any],
) -> AsyncIterator[str]:
    """Stream only the final-answer phase.

    Planner/tool execution remains non-streaming. This is the safest pattern for
    tool-using agents because the final answer can stream after tool results are ready.
    Queue-mode streaming is intentionally not implemented in this patch.
    """
    start_total = time.perf_counter()

    messages = payload.get("messages", [])
    model = payload.get("model", MODEL_NAME)
    temperature = payload.get("temperature", DEFAULT_TEMPERATURE)
    max_tokens = payload.get("max_tokens", DEFAULT_MAX_TOKENS)

    if not isinstance(messages, list):
        raise ValueError("`messages` must be a list.")

    metadata = payload.get("metadata")
    conversation_id = metadata.get("conversation_id") if isinstance(metadata, dict) else None
    conversation_id = payload.get("conversation_id") or payload.get("conversationId") or conversation_id

    cid, working_messages = await _prepare_working_messages(
        incoming_messages=messages,
        conversation_id=conversation_id,
    )

    plan, tool_rounds = await _run_planner_and_tools(
        working_messages=working_messages,
        conversation_id=cid,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    final_content_parts: list[str] = []

    try:
        async for chunk in stream_llm(
            agent="final_answer",
            messages=final_answer_messages(working_messages),
            tools=None,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        ):
            chunk_dict = chunk.model_dump() if hasattr(chunk, "model_dump") else chunk

            try:
                delta = chunk_dict.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content") or ""
                if content:
                    final_content_parts.append(content)
            except Exception:
                pass

            yield f"data: {json.dumps(chunk_dict, ensure_ascii=False)}\n\n"

        metadata_chunk = {
            "object": "chat.completion.chunk",
            "backend": {
                "conversation_id": cid,
                "tool_rounds": tool_rounds,
                "plan": plan.__dict__,
                "queue_enabled": False,
                "streamed": True,
            },
        }
        yield f"data: {json.dumps(metadata_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

        await append_message(
            conversation_id=cid,
            role="assistant",
            content="".join(final_content_parts),
            payload={
                "agent": "final_answer",
                "route": plan.route,
                "tool_rounds": tool_rounds,
                "streamed": True,
            },
        )

        BACKEND_CHAT_REQUESTS.labels(endpoint="/v1/chat/completions:stream", status="success").inc()

    except Exception:
        BACKEND_CHAT_REQUESTS.labels(endpoint="/v1/chat/completions:stream", status="error").inc()
        raise

    finally:
        BACKEND_CHAT_LATENCY.labels(endpoint="/v1/chat/completions:stream").observe(
            time.perf_counter() - start_total
        )
