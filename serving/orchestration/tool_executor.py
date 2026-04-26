from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from prometheus_client import Counter, Histogram

from serving.tools.registry import execute_tool_call, list_tools


BACKEND_TOOL_CALLS = Counter(
    "backend_tool_calls_total",
    "Total backend tool calls",
    ["tool_name", "status"],
)

BACKEND_TOOL_LATENCY = Histogram(
    "backend_tool_latency_seconds",
    "Latency of backend tool calls in seconds",
    ["tool_name"],
)


@dataclass(frozen=True)
class ToolPolicy:
    parallel_safe: bool = False
    state_changing: bool = False
    requires_confirmation: bool = False


TOOL_POLICIES: dict[str, ToolPolicy] = {
    # Gmail read/search operations.
    "gmail_list_labels": ToolPolicy(parallel_safe=True),
    "gmail_search_messages": ToolPolicy(parallel_safe=True),
    # Keep read sequential because it usually depends on IDs discovered by search.
    "gmail_read_messages": ToolPolicy(parallel_safe=False),

    # Proposal tools do not mutate Gmail but should stay sequential for clearer user-confirmation flow.
    "gmail_propose_archive_messages": ToolPolicy(parallel_safe=False, requires_confirmation=False),
    "gmail_propose_apply_label": ToolPolicy(parallel_safe=False, requires_confirmation=False),
    "gmail_propose_trash_messages": ToolPolicy(parallel_safe=False, requires_confirmation=False),
    "gmail_propose_mark_read": ToolPolicy(parallel_safe=False, requires_confirmation=False),
    "gmail_propose_mark_unread": ToolPolicy(parallel_safe=False, requires_confirmation=False),
    "gmail_propose_send_draft": ToolPolicy(parallel_safe=False, requires_confirmation=False),

    # Gmail state-changing operations.
    "gmail_archive_messages": ToolPolicy(parallel_safe=False, state_changing=True, requires_confirmation=True),
    "gmail_apply_label": ToolPolicy(parallel_safe=False, state_changing=True, requires_confirmation=True),
    "gmail_trash_messages": ToolPolicy(parallel_safe=False, state_changing=True, requires_confirmation=True),
    "gmail_mark_read": ToolPolicy(parallel_safe=False, state_changing=True, requires_confirmation=True),
    "gmail_mark_unread": ToolPolicy(parallel_safe=False, state_changing=True, requires_confirmation=True),
    "gmail_send_draft": ToolPolicy(parallel_safe=False, state_changing=True, requires_confirmation=True),

    # Draft creation changes Gmail state but does not send. Keep sequential.
    "gmail_create_draft": ToolPolicy(parallel_safe=False, state_changing=True, requires_confirmation=False),
}


def get_tool_policy(tool_name: str) -> ToolPolicy:
    return TOOL_POLICIES.get(tool_name, ToolPolicy(parallel_safe=False))


async def select_tools(tool_names: list[str]) -> list[dict[str, Any]]:
    if not tool_names:
        return []
    selected: list[dict[str, Any]] = []
    available_tools = await list_tools()
    for tool in available_tools:
        function = tool.get("function", {})
        name = function.get("name")
        if name in tool_names:
            selected.append(tool)
    return selected


async def execute_tool_with_metrics(*, tool_name: str, arguments: str | dict | None) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = await execute_tool_call(tool_name, arguments)
        BACKEND_TOOL_CALLS.labels(tool_name=tool_name, status="success").inc()
        return result
    except Exception as exc:
        BACKEND_TOOL_CALLS.labels(tool_name=tool_name, status="error").inc()
        return {"error": str(exc), "tool_name": tool_name}
    finally:
        BACKEND_TOOL_LATENCY.labels(tool_name=tool_name).observe(time.perf_counter() - start)


async def execute_tool_calls_with_policy(
    *,
    tool_items: list[tuple[str, str | dict | None, str | None]],
) -> list[tuple[str, str | None, dict[str, Any]]]:
    """Execute independent read-only tools concurrently and dependent/state-changing tools sequentially.

    Returns tuples of (tool_name, tool_call_id, result) in a deterministic order.
    Agent loops that do not use this helper can still call execute_tool_with_metrics directly.
    """
    parallel: list[tuple[int, str, str | dict | None, str | None]] = []
    sequential: list[tuple[int, str, str | dict | None, str | None]] = []

    for idx, (tool_name, arguments, tool_call_id) in enumerate(tool_items):
        policy = get_tool_policy(tool_name)
        item = (idx, tool_name, arguments, tool_call_id)
        if policy.parallel_safe and not policy.state_changing:
            parallel.append(item)
        else:
            sequential.append(item)

    results: dict[int, tuple[str, str | None, dict[str, Any]]] = {}

    if parallel:
        gathered = await asyncio.gather(
            *[
                execute_tool_with_metrics(tool_name=name, arguments=args)
                for _, name, args, _ in parallel
            ],
            return_exceptions=True,
        )
        for (idx, name, _args, tool_call_id), value in zip(parallel, gathered):
            if isinstance(value, Exception):
                result = {"error": str(value), "tool_name": name}
            else:
                result = value
            results[idx] = (name, tool_call_id, result)

    for idx, name, args, tool_call_id in sequential:
        result = await execute_tool_with_metrics(tool_name=name, arguments=args)
        results[idx] = (name, tool_call_id, result)

    return [results[i] for i in sorted(results)]
