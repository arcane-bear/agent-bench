"""Load custom benchmark suites defined in YAML."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from agent_bench.suites.base import Score, Suite, Task


class CustomSuite(Suite):
    """A suite loaded from a YAML definition.

    YAML shape::

        name: my-suite
        tasks:
          - id: t1
            prompt: "Sum 2 and 2, answer with just the number."
            system: "You are concise."
            expected:
              contains: "4"          # substring (case-insensitive)
              regex: "^\\d+$"         # regex
              equals: "4"             # full-string equality (normalized)
              format_regex: "Answer:" # presence → format compliance
            max_tokens: 128
    """

    def __init__(self, name: str, raw_tasks: list[dict]) -> None:
        self.name = name
        self._tasks = [
            Task(
                id=str(t["id"]),
                prompt=str(t["prompt"]),
                system=t.get("system"),
                expected=t.get("expected") or {},
                max_tokens=int(t.get("max_tokens", 512)),
                tools=t.get("tools"),
                meta={"type": "custom"},
            )
            for t in raw_tasks
        ]

    def tasks(self) -> list[Task]:
        return list(self._tasks)

    def score(self, task: Task, output: str, tool_calls: list[dict]) -> Score:
        expected: dict[str, Any] = task.expected or {}
        text = output.strip()
        checks: list[bool] = []

        if "contains" in expected:
            checks.append(str(expected["contains"]).lower() in text.lower())
        if "equals" in expected:
            want = re.sub(r"\s+", " ", str(expected["equals"]).strip().lower())
            got = re.sub(r"\s+", " ", text.lower())
            checks.append(want == got)
        if "regex" in expected:
            checks.append(bool(re.search(str(expected["regex"]), text)))

        format_compliance = 1.0
        if "format_regex" in expected:
            format_compliance = (
                1.0 if re.search(str(expected["format_regex"]), text) else 0.0
            )

        if not checks:
            accuracy = 1.0  # no content checks requested → format-only task
        else:
            accuracy = sum(checks) / len(checks)

        passed = accuracy == 1.0 and format_compliance == 1.0
        return Score(
            accuracy=round(accuracy, 3),
            format_compliance=format_compliance,
            passed=passed,
            detail=f"checks={sum(checks)}/{len(checks)}",
        )


def load_custom_suite(path: str | Path) -> CustomSuite:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level.")
    name = data.get("name") or Path(path).stem
    raw_tasks = data.get("tasks") or []
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError(f"{path}: `tasks` must be a non-empty list.")
    return CustomSuite(name=str(name), raw_tasks=raw_tasks)
