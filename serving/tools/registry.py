from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from serving.tools.local.registry import execute_tool_call as execute_local_tool_call
from serving.tools.local.registry import list_tools as list_local_tools
from serving.tools.mcp.client import call_mcp_tool_async, list_mcp_tools_async


_TOOLS_CACHE: list[dict[str, Any]] | None = None


def _backend() -> str:
    return os.getenv("TOOL_BACKEND", "local").strip().lower()


def parse_tool_arguments(
    arguments: str | dict[str, Any] | None,
) -> dict[str, Any]:
    if arguments is None:
        return {}

    if isinstance(arguments, dict):
        return arguments

    return json.loads(arguments)


async def list_tools(*, refresh: bool = False) -> list[dict[str, Any]]:
    global _TOOLS_CACHE

    backend = _backend()

    if backend == "local":
        return await asyncio.to_thread(list_local_tools)

    if backend != "mcp":
        raise ValueError("TOOL_BACKEND must be either 'local' or 'mcp'.")

    if refresh or _TOOLS_CACHE is None:
        _TOOLS_CACHE = await list_mcp_tools_async()

    return _TOOLS_CACHE


async def list_tool_names() -> set[str]:
    tools = await list_tools()
    return {
        str(tool.get("function", {}).get("name"))
        for tool in tools
        if tool.get("function", {}).get("name")
    }


async def execute_tool_call(
    name: str,
    arguments: str | dict[str, Any] | None,
) -> dict[str, Any]:
    parsed = parse_tool_arguments(arguments)
    backend = _backend()

    if backend == "local":
        # Local tools are sync today, so isolate them in a thread.
        return await asyncio.to_thread(execute_local_tool_call, name, parsed)

    if backend == "mcp":
        return await call_mcp_tool_async(name, parsed)

    raise ValueError("TOOL_BACKEND must be either 'local' or 'mcp'.")
