"""Core benchmark runner."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agent_bench.metrics import Metrics, estimate_cost
from agent_bench.providers.base import Provider, ProviderResponse
from agent_bench.suites.base import Suite, Task


@dataclass
class TaskResult:
    """Outcome of a single task on a single provider."""

    task_id: str
    suite: str
    provider: str
    model: str
    prompt: str
    output: str
    metrics: Metrics
    passed: bool

    def to_dict(self) -> dict:
        d = asdict(self)
        d["metrics"] = self.metrics.to_dict()
        return d


@dataclass
class RunResult:
    """Results of a full benchmark run."""

    started_at: float
    finished_at: float
    suites: list[str]
    providers: list[str]
    tasks: list[TaskResult] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        return self.finished_at - self.started_at

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": round(self.duration_s, 3),
            "suites": self.suites,
            "providers": self.providers,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> dict:
        """Load the JSON document; returns a plain dict (not typed objects)."""
        return json.loads(Path(path).read_text())


class BenchmarkRunner:
    """Runs suites against providers and aggregates results."""

    def __init__(self, providers: list[Provider], suites: list[Suite]) -> None:
        self.providers = providers
        self.suites = suites

    def run(self, verbose_cb: Any = None) -> RunResult:
        started = time.time()
        results: list[TaskResult] = []
        for suite in self.suites:
            for task in suite.tasks():
                for provider in self.providers:
                    if verbose_cb:
                        verbose_cb(suite.name, task.id, provider.name)
                    result = self._run_one(suite, task, provider)
                    results.append(result)
        return RunResult(
            started_at=started,
            finished_at=time.time(),
            suites=[s.name for s in self.suites],
            providers=[p.name for p in self.providers],
            tasks=results,
        )

    def _run_one(self, suite: Suite, task: Task, provider: Provider) -> TaskResult:
        metrics = Metrics()
        output = ""
        t_start = time.perf_counter()
        try:
            response: ProviderResponse = provider.complete(
                prompt=task.prompt,
                system=task.system,
                max_tokens=task.max_tokens,
                tools=task.tools,
            )
            output = response.text
            metrics.ttft_s = response.ttft_s
            metrics.prompt_tokens = response.prompt_tokens
            metrics.completion_tokens = response.completion_tokens
            metrics.extra["tool_calls"] = response.tool_calls
        except Exception as e:
            metrics.error = f"{type(e).__name__}: {e}"
        metrics.total_s = time.perf_counter() - t_start

        passed = False
        if metrics.error is None:
            score = suite.score(task, output, metrics.extra.get("tool_calls") or [])
            metrics.accuracy = score.accuracy
            metrics.format_compliance = score.format_compliance
            passed = score.passed

        metrics.cost_usd = estimate_cost(
            provider.name, provider.model, metrics.prompt_tokens, metrics.completion_tokens
        )

        return TaskResult(
            task_id=task.id,
            suite=suite.name,
            provider=provider.name,
            model=provider.model,
            prompt=task.prompt,
            output=output,
            metrics=metrics,
            passed=passed,
        )
