"""OpenAI provider adapter (optional dependency: `agent-bench[openai]`)."""

from __future__ import annotations

import os
import time

from agent_bench.providers.base import Provider, ProviderResponse


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        super().__init__(model=model)
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "openai is required for the OpenAI provider. "
                "Install with: pip install 'agent-bench[openai]'"
            ) from e
        self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 512,
        tools: list[dict] | None = None,
    ) -> ProviderResponse:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

        t0 = time.perf_counter()
        ttft: float | None = None
        chunks: list[str] = []
        tool_calls: list[dict] = []
        usage = None

        stream = self._client.chat.completions.create(**kwargs)
        for event in stream:
            if ttft is None and event.choices and event.choices[0].delta:
                delta = event.choices[0].delta
                if (delta.content or "") or delta.tool_calls:
                    ttft = time.perf_counter() - t0
            if event.choices:
                delta = event.choices[0].delta
                if delta.content:
                    chunks.append(delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls.append(
                            {
                                "name": (tc.function.name if tc.function else None),
                                "arguments": (tc.function.arguments if tc.function else None),
                            }
                        )
            if getattr(event, "usage", None):
                usage = event.usage

        text = "".join(chunks)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return ProviderResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            ttft_s=ttft,
            tool_calls=tool_calls,
        )
