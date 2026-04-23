from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression safely.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time for a timezone.",
            "parameters": {
                "type": "object",
                "properties": {"timezone_name": {"type": "string"}},
                "required": ["timezone_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Return a mock weather result for a location.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
    },
]


def calculator(expression: str) -> dict:
    allowed = set("0123456789+-*/(). %")
    if not set(expression) <= allowed:
        raise ValueError("Unsafe expression.")
    return {"expression": expression, "result": eval(expression, {"__builtins__": {}}, {})}


def get_time(timezone_name: str) -> dict:
    now = datetime.now(ZoneInfo(timezone_name) if timezone_name else timezone.utc)
    return {"timezone": timezone_name, "iso": now.isoformat()}


def get_weather(location: str) -> dict:
    return {"location": location, "forecast": "sunny", "temperature_c": 22}


TOOL_FUNCTIONS = {
    "calculator": calculator,
    "get_time": get_time,
    "get_weather": get_weather,
}


def parse_tool_arguments(arguments: str | dict | None) -> dict:
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    return json.loads(arguments)


def execute_tool_call(name: str, arguments: str | dict | None) -> dict:
    if name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown tool: {name}")
    parsed = parse_tool_arguments(arguments)
    return TOOL_FUNCTIONS[name](**parsed)
