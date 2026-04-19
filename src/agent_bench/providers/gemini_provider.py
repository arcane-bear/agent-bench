"""Google Gemini provider adapter (optional dependency: `agent-bench[gemini]`)."""

from __future__ import annotations

import os
import time

from agent_bench.providers.base import Provider, ProviderResponse


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, model: str = "gemini-1.5-flash", api_key: str | None = None) -> None:
        super().__init__(model=model)
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ImportError(
                "google-generativeai is required for the Gemini provider. "
                "Install with: pip install 'agent-bench[gemini]'"
            ) from e
        genai.configure(api_key=api_key or os.environ.get("GOOGLE_API_KEY"))
        self._genai = genai

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 512,
        tools: list[dict] | None = None,
    ) -> ProviderResponse:
        model_kwargs: dict = {}
        if system:
            model_kwargs["system_instruction"] = system
        if tools:
            model_kwargs["tools"] = [
                {
                    "function_declarations": [
                        {
                            "name": t["name"],
                            "description": t.get("description", ""),
                            "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                        }
                        for t in tools
                    ]
                }
            ]
        model = self._genai.GenerativeModel(model_name=self.model, **model_kwargs)

        t0 = time.perf_counter()
        ttft: float | None = None
        chunks: list[str] = []
        tool_calls: list[dict] = []
        usage_in = 0
        usage_out = 0

        stream = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens},
            stream=True,
        )
        for event in stream:
            if ttft is None and event.text:
                ttft = time.perf_counter() - t0
            if event.text:
                chunks.append(event.text)
            for cand in getattr(event, "candidates", []) or []:
                for part in getattr(cand.content, "parts", []) or []:
                    fc = getattr(part, "function_call", None)
                    if fc is not None and getattr(fc, "name", None):
                        tool_calls.append({"name": fc.name, "arguments": dict(fc.args or {})})

        # Resolve to capture usage metadata.
        stream.resolve()
        meta = getattr(stream, "usage_metadata", None)
        if meta is not None:
            usage_in = getattr(meta, "prompt_token_count", 0) or 0
            usage_out = getattr(meta, "candidates_token_count", 0) or 0

        return ProviderResponse(
            text="".join(chunks),
            prompt_tokens=usage_in,
            completion_tokens=usage_out,
            ttft_s=ttft,
            tool_calls=tool_calls,
        )
