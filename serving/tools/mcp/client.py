from __future__ import annotations

import os
import shlex
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _server_params() -> StdioServerParameters:
    command = os.getenv("MCP_SERVER_COMMAND", "python")
    args_text = os.getenv("MCP_SERVER_ARGS", "-m serving.tools.mcp.server")
    return StdioServerParameters(command=command, args=shlex.split(args_text))


def _mcp_tool_to_openai_tool(tool: Any) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema or {"type": "object", "properties": {}},
        },
    }


def _content_to_jsonable(content: Any) -> Any:
    if hasattr(content, "model_dump"):
        return content.model_dump()
    if isinstance(content, list):
        return [_content_to_jsonable(item) for item in content]
    if isinstance(content, dict):
        return {k: _content_to_jsonable(v) for k, v in content.items()}
    return content


async def list_mcp_tools_async() -> list[dict[str, Any]]:
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [_mcp_tool_to_openai_tool(tool) for tool in result.tools]


async def call_mcp_tool_async(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            return {
                "tool_name": name,
                "content": _content_to_jsonable(result.content),
                "is_error": getattr(result, "isError", False),
            }
