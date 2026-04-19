"""Built-in benchmark suites."""

from __future__ import annotations

from agent_bench.suites.base import Score, Suite, Task
from agent_bench.suites.coding import CodingSuite
from agent_bench.suites.reasoning import ReasoningSuite
from agent_bench.suites.tool_use import ToolUseSuite
from agent_bench.suites.writing import WritingSuite

BUILTIN_SUITES: dict[str, type[Suite]] = {
    "reasoning": ReasoningSuite,
    "coding": CodingSuite,
    "writing": WritingSuite,
    "tool-use": ToolUseSuite,
}


def load_suite(name: str) -> Suite:
    key = name.strip().lower()
    if key not in BUILTIN_SUITES:
        raise ValueError(
            f"Unknown suite {name!r}. Built-ins: {', '.join(sorted(BUILTIN_SUITES))}"
        )
    return BUILTIN_SUITES[key]()


__all__ = [
    "BUILTIN_SUITES",
    "CodingSuite",
    "ReasoningSuite",
    "Score",
    "Suite",
    "Task",
    "ToolUseSuite",
    "WritingSuite",
    "load_suite",
]
