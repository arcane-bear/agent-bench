"""Ollama (local) provider adapter (optional dependency: `agent-bench[ollama]`)."""

from __future__ import annotations

import time

from agent_bench.providers.base import Provider, ProviderResponse


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self, model: str = "llama3.2", host: str | None = None) -> None:
        super().__init__(model=model)
        try:
            import ollama
        except ImportError as e:
            raise ImportError(
                "ollama is required for the Ollama provider. "
                "Install with: pip install 'agent-bench[ollama]'"
            ) from e
        self._client = ollama.Client(host=host) if host else ollama

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
            "options": {"num_predict": max_tokens},
            "stream": True,
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

        t0 = time.perf_counter()
        ttft: float | None = None
        chunks: list[str] = []
        tool_calls: list[dict] = []
        prompt_tokens = 0
        completion_tokens = 0

        for event in self._client.chat(**kwargs):
            msg = event.get("message", {}) if isinstance(event, dict) else {}
            content = msg.get("content") or ""
            if content:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                chunks.append(content)
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function", {})
                tool_calls.append({"name": fn.get("name"), "arguments": fn.get("arguments")})
            if isinstance(event, dict) and event.get("done"):
                prompt_tokens = event.get("prompt_eval_count", 0) or 0
                completion_tokens = event.get("eval_count", 0) or 0

        return ProviderResponse(
            text="".join(chunks),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            ttft_s=ttft,
            tool_calls=tool_calls,
        )
