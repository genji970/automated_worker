from __future__ import annotations

import ast
import json
import operator
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression exactly. Use for arithmetic.",
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
            "description": "Get the current time for an IANA timezone.",
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


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ValueError("Unsupported operator.")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _ALLOWED_BINOPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY:
            raise ValueError("Unsupported unary operator.")
        return _ALLOWED_UNARY[op_type](_safe_eval_node(node.operand))

    raise ValueError("Unsafe expression.")


def calculator(expression: str) -> dict[str, Any]:
    expression = expression.replace("×", "*").replace("÷", "/")
    tree = ast.parse(expression, mode="eval")
    result = _safe_eval_node(tree)
    return {"expression": expression, "result": result}


def get_time(timezone_name: str) -> dict[str, Any]:
    now = datetime.now(ZoneInfo(timezone_name) if timezone_name else timezone.utc)
    return {"timezone": timezone_name, "iso": now.isoformat()}


def get_weather(location: str) -> dict[str, Any]:
    return {"location": location, "forecast": "sunny", "temperature_c": 22}


TOOL_FUNCTIONS = {
    "calculator": calculator,
    "get_time": get_time,
    "get_weather": get_weather,
}


def parse_tool_arguments(arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    return json.loads(arguments)


def list_tools() -> list[dict[str, Any]]:
    return TOOLS


def execute_tool_call(name: str, arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    if name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown local tool: {name}")
    parsed = parse_tool_arguments(arguments)
    return TOOL_FUNCTIONS[name](**parsed)
