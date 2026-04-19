"""Coding suite: generate a Python function, extract it, and verify against tests."""

from __future__ import annotations

import re
import textwrap
from typing import Any

from agent_bench.suites.base import Score, Suite, Task

SYSTEM = (
    "You are a Python coding assistant. Return ONLY a Python function in a fenced code block: "
    "```python\\n<function>\\n```. Do not include example usage, tests, or explanations."
)


def _task(task_id: str, prompt: str, function_name: str, cases: list[tuple[tuple, Any]]) -> Task:
    return Task(
        id=task_id,
        system=SYSTEM,
        prompt=prompt,
        expected={"function": function_name, "cases": cases},
        meta={"type": "coding"},
    )


_TASKS: list[Task] = [
    _task(
        "code-fizzbuzz",
        "Write a Python function `fizzbuzz(n)` that returns a list of strings from 1..n where "
        "multiples of 3 are 'Fizz', multiples of 5 are 'Buzz', multiples of both are 'FizzBuzz', "
        "and other numbers are the number as a string.",
        "fizzbuzz",
        [
            ((5,), ["1", "2", "Fizz", "4", "Buzz"]),
            ((15,), [
                "1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz",
                "Buzz", "11", "Fizz", "13", "14", "FizzBuzz",
            ]),
        ],
    ),
    _task(
        "code-reverse-words",
        "Write a Python function `reverse_words(s)` that reverses the order of whitespace-"
        "separated words in `s`, collapsing any internal whitespace to a single space and "
        "stripping leading/trailing whitespace.",
        "reverse_words",
        [
            (("hello world",), "world hello"),
            (("  the   quick brown fox  ",), "fox brown quick the"),
            (("single",), "single"),
        ],
    ),
    _task(
        "code-is-palindrome",
        "Write a Python function `is_palindrome(s)` that returns True if `s` is a palindrome "
        "ignoring case and non-alphanumeric characters, else False.",
        "is_palindrome",
        [
            (("A man, a plan, a canal: Panama",), True),
            (("race a car",), False),
            (("",), True),
        ],
    ),
]


_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_code(output: str) -> str:
    match = _CODE_BLOCK_RE.search(output)
    if match:
        return textwrap.dedent(match.group(1)).strip()
    return output.strip()


def _run_cases(code: str, function_name: str, cases: list[tuple[tuple, Any]]) -> tuple[int, int]:
    """Return (passes, total). Never raises."""
    ns: dict[str, Any] = {}
    try:
        exec(compile(code, f"<bench:{function_name}>", "exec"), ns)  # noqa: S102
    except Exception:
        return 0, len(cases)
    fn = ns.get(function_name)
    if not callable(fn):
        return 0, len(cases)
    passes = 0
    for args, expected in cases:
        try:
            got = fn(*args)
        except Exception:
            continue
        if got == expected:
            passes += 1
    return passes, len(cases)


class CodingSuite(Suite):
    name = "coding"

    def tasks(self) -> list[Task]:
        return list(_TASKS)

    def score(self, task: Task, output: str, tool_calls: list[dict]) -> Score:
        format_ok = bool(_CODE_BLOCK_RE.search(output))
        code = _extract_code(output)
        fn_name = task.expected["function"]
        cases = task.expected["cases"]
        passed, total = _run_cases(code, fn_name, cases)
        accuracy = passed / total if total else 0.0
        return Score(
            accuracy=accuracy,
            format_compliance=1.0 if format_ok else 0.0,
            passed=(passed == total and total > 0),
            detail=f"{passed}/{total} cases passed",
        )
