"""Anthropic Claude provider adapter (optional dependency: `agent-bench[anthropic]`)."""

from __future__ import annotations

import os
import time

from agent_bench.providers.base import Provider, ProviderResponse


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, model: str = "claude-haiku-4-5", api_key: str | None = None) -> None:
        super().__init__(model=model)
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic is required for the Anthropic provider. "
                "Install with: pip install 'agent-bench[anthropic]'"
            ) from e
        self._client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 512,
        tools: list[dict] | None = None,
    ) -> ProviderResponse:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
                }
                for t in tools
            ]

        t0 = time.perf_counter()
        ttft: float | None = None
        chunks: list[str] = []
        tool_calls: list[dict] = []
        usage_in = 0
        usage_out = 0

        with self._client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    delta = event.delta
                    if getattr(delta, "text", None):
                        chunks.append(delta.text)
                elif event.type == "content_block_stop":
                    block = getattr(event, "content_block", None)
                    if block is not None and getattr(block, "type", None) == "tool_use":
                        tool_calls.append(
                            {"name": block.name, "arguments": getattr(block, "input", {})}
                        )
            final = stream.get_final_message()
            usage_in = final.usage.input_tokens
            usage_out = final.usage.output_tokens
            # catch tool_use blocks from the final message as well
            for block in final.content:
                if block.type == "tool_use" and not any(
                    tc.get("name") == block.name for tc in tool_calls
                ):
                    tool_calls.append({"name": block.name, "arguments": block.input})

        text = "".join(chunks)
        return ProviderResponse(
            text=text,
            prompt_tokens=usage_in,
            completion_tokens=usage_out,
            ttft_s=ttft,
            tool_calls=tool_calls,
        )
