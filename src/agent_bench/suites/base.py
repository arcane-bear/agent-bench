"""Suite and Task base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    id: str
    prompt: str
    system: str | None = None
    expected: Any = None
    max_tokens: int = 512
    tools: list[dict] | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class Score:
    accuracy: float
    format_compliance: float = 1.0
    passed: bool = False
    detail: str = ""


class Suite(ABC):
    name: str = "base"

    @abstractmethod
    def tasks(self) -> list[Task]:
        """Return the task list for this suite."""

    @abstractmethod
    def score(self, task: Task, output: str, tool_calls: list[dict]) -> Score:
        """Score a task's output. Implementations should never raise."""
