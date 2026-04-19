"""Provider adapters."""

from __future__ import annotations

from agent_bench.providers.base import Provider, ProviderResponse


def load_provider(spec: str) -> Provider:
    """Load a provider by spec like 'openai' or 'anthropic:claude-haiku-4-5'.

    The model portion is optional; each provider has a sensible default.
    Import of provider SDKs is lazy so that optional deps stay optional.
    """
    name, _, model = spec.partition(":")
    name = name.lower()
    model = model or None  # type: ignore[assignment]

    if name == "openai":
        from agent_bench.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(model=model or "gpt-4o-mini")
    if name in ("anthropic", "claude"):
        from agent_bench.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model or "claude-haiku-4-5")
    if name in ("gemini", "google"):
        from agent_bench.providers.gemini_provider import GeminiProvider

        return GeminiProvider(model=model or "gemini-1.5-flash")
    if name in ("ollama", "local"):
        from agent_bench.providers.ollama_provider import OllamaProvider

        return OllamaProvider(model=model or "llama3.2")
    raise ValueError(f"Unknown provider: {name!r}")


__all__ = ["Provider", "ProviderResponse", "load_provider"]
