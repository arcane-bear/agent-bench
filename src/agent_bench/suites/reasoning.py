"""Reasoning suite: math and logic problems with short final answers."""

from __future__ import annotations

import re

from agent_bench.suites.base import Score, Suite, Task

SYSTEM = (
    "You are a careful reasoner. Think step-by-step, then output the final answer on the "
    "last line in the form: `Answer: <value>`."
)

_TASKS: list[Task] = [
    Task(
        id="math-1",
        system=SYSTEM,
        prompt="A train travels 60 miles in 1.5 hours. What is its average speed in mph?",
        expected="40",
        meta={"type": "math"},
    ),
    Task(
        id="math-2",
        system=SYSTEM,
        prompt="If 3x + 7 = 22, what is x?",
        expected="5",
        meta={"type": "math"},
    ),
    Task(
        id="math-3",
        system=SYSTEM,
        prompt="Compute: (12 * 11) - (7 * 8) + 4.",
        expected="80",
        meta={"type": "math"},
    ),
    Task(
        id="logic-1",
        system=SYSTEM,
        prompt=(
            "All bloops are razzies. All razzies are lazzies. "
            "Is it true that all bloops are lazzies? Answer yes or no."
        ),
        expected="yes",
        meta={"type": "logic"},
    ),
    Task(
        id="logic-2",
        system=SYSTEM,
        prompt=(
            "Alice is taller than Bob. Bob is taller than Carol. "
            "Who is the shortest of the three? Answer with just the name."
        ),
        expected="carol",
        meta={"type": "logic"},
    ),
    Task(
        id="logic-3",
        system=SYSTEM,
        prompt=(
            "A farmer has ducks and cows. He counts 12 heads and 34 legs. "
            "How many cows are there?"
        ),
        expected="5",
        meta={"type": "logic"},
    ),
]


_ANSWER_RE = re.compile(r"answer\s*[:\-]\s*(.+?)(?:\n|$)", re.IGNORECASE)


def _extract_answer(output: str) -> str:
    match = _ANSWER_RE.search(output.strip())
    if match:
        return match.group(1).strip().rstrip(".").strip()
    # Fall back to last non-empty line.
    for line in reversed(output.strip().splitlines()):
        if line.strip():
            return line.strip().rstrip(".").strip()
    return ""


def _normalize(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\.\-]", "", value).lower()


class ReasoningSuite(Suite):
    name = "reasoning"

    def tasks(self) -> list[Task]:
        return list(_TASKS)

    def score(self, task: Task, output: str, tool_calls: list[dict]) -> Score:
        extracted = _extract_answer(output)
        format_ok = bool(_ANSWER_RE.search(output))
        got = _normalize(extracted)
        want = _normalize(str(task.expected))
        correct = bool(got) and (got == want or want in got)
        return Score(
            accuracy=1.0 if correct else 0.0,
            format_compliance=1.0 if format_ok else 0.0,
            passed=correct,
            detail=f"expected={task.expected!r} extracted={extracted!r}",
        )
