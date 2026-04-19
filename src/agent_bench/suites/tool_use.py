"""Tool-use suite: evaluates function-calling accuracy."""

from __future__ import annotations

import json
from typing import Any

from agent_bench.suites.base import Score, Suite, Task

WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Get the current weather for a city.",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "The city name."},
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature unit.",
            },
        },
        "required": ["city"],
    },
}

SEARCH_TOOL = {
    "name": "search_docs",
    "description": "Search internal documentation.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
}

SEND_EMAIL_TOOL = {
    "name": "send_email",
    "description": "Send an email to a recipient.",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to", "subject", "body"],
    },
}


_TASKS: list[Task] = [
    Task(
        id="tool-weather-basic",
        system="Use the provided tools when appropriate. Do not answer from memory.",
        prompt="What is the weather in Paris in celsius right now?",
        tools=[WEATHER_TOOL],
        expected={
            "tool": "get_weather",
            "required_args": {"city": "paris"},
            "optional_args": {"unit": "celsius"},
        },
        meta={"type": "tool-use"},
    ),
    Task(
        id="tool-search-docs",
        system="Use the provided tools when appropriate.",
        prompt="Find our docs about OAuth refresh token rotation. Return the top 3.",
        tools=[SEARCH_TOOL],
        expected={
            "tool": "search_docs",
            "required_args": {"query": "oauth refresh token rotation"},
            "optional_args": {"top_k": 3},
        },
        meta={"type": "tool-use"},
    ),
    Task(
        id="tool-send-email",
        system="Use the provided tools when appropriate.",
        prompt=(
            "Send an email to ops@example.com with subject 'Deploy complete' and a body "
            "saying the deploy finished successfully."
        ),
        tools=[SEND_EMAIL_TOOL],
        expected={
            "tool": "send_email",
            "required_args": {
                "to": "ops@example.com",
                "subject": "deploy complete",
            },
            "optional_args": {},
        },
        meta={"type": "tool-use"},
    ),
]


def _coerce_args(args: Any) -> dict:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            return json.loads(args)
        except Exception:
            return {}
    return {}


def _normalize(value: Any) -> str:
    return str(value).strip().lower()


class ToolUseSuite(Suite):
    name = "tool-use"

    def tasks(self) -> list[Task]:
        return list(_TASKS)

    def score(self, task: Task, output: str, tool_calls: list[dict]) -> Score:
        expected_tool = task.expected["tool"]
        required = task.expected.get("required_args") or {}
        optional = task.expected.get("optional_args") or {}

        matching = [tc for tc in tool_calls if tc.get("name") == expected_tool]
        if not matching:
            return Score(
                accuracy=0.0,
                format_compliance=1.0 if tool_calls else 0.0,
                passed=False,
                detail=f"expected tool {expected_tool!r} not called",
            )

        args = _coerce_args(matching[0].get("arguments"))
        required_hits = sum(
            1
            for k, v in required.items()
            if k in args and _normalize(v) in _normalize(args[k])
        )
        optional_hits = sum(
            1
            for k, v in optional.items()
            if k in args and _normalize(v) in _normalize(args[k])
        )

        required_score = required_hits / max(1, len(required))
        optional_bonus = (optional_hits / len(optional)) if optional else 1.0
        accuracy = 0.8 * required_score + 0.2 * optional_bonus
        return Score(
            accuracy=round(accuracy, 3),
            format_compliance=1.0,
            passed=required_score == 1.0,
            detail=(
                f"required={required_hits}/{len(required)} "
                f"optional={optional_hits}/{len(optional)}"
            ),
        )
