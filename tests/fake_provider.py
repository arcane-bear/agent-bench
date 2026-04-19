"""Fake provider for tests — returns a scripted response and fake usage."""

from __future__ import annotations

import time
from collections.abc import Callable

from agent_bench.providers.base import Provider, ProviderResponse


class FakeProvider(Provider):
    name = "fake"

    def __init__(
        self,
        model: str = "fake-1",
        responder: Callable[[str], str] | str = "Answer: 42",
        tool_calls: list[dict] | None = None,
        latency_s: float = 0.01,
    ) -> None:
        super().__init__(model=model)
        self._responder = responder
        self._tool_calls = tool_calls or []
        self._latency = latency_s

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 512,
        tools: list[dict] | None = None,
    ) -> ProviderResponse:
        t0 = time.perf_counter()
        time.sleep(self._latency)
        if callable(self._responder):
            text = self._responder(prompt)
        else:
            text = self._responder
        return ProviderResponse(
            text=text,
            prompt_tokens=len(prompt.split()),
            completion_tokens=max(1, len(text.split())),
            ttft_s=time.perf_counter() - t0,
            tool_calls=list(self._tool_calls),
        )
