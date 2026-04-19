"""Metrics collection for benchmark runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Metrics:
    """Per-task metrics collected during a benchmark run."""

    ttft_s: float | None = None
    total_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    accuracy: float = 0.0
    format_compliance: float = 1.0
    error: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def tokens_per_sec(self) -> float:
        if self.total_s <= 0 or self.completion_tokens <= 0:
            return 0.0
        return self.completion_tokens / self.total_s

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_tokens"] = self.total_tokens
        d["tokens_per_sec"] = round(self.tokens_per_sec, 2)
        return d


# Token pricing per 1M tokens (USD). Update as providers change pricing.
# Input / output rates.
PRICING: dict[str, dict[str, tuple[float, float]]] = {
    "openai": {
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.00),
        "o1-mini": (3.00, 12.00),
    },
    "anthropic": {
        "claude-haiku-4-5": (1.00, 5.00),
        "claude-sonnet-4-6": (3.00, 15.00),
        "claude-opus-4-7": (15.00, 75.00),
    },
    "gemini": {
        "gemini-1.5-flash": (0.075, 0.30),
        "gemini-1.5-pro": (1.25, 5.00),
        "gemini-2.0-flash": (0.10, 0.40),
    },
    "ollama": {
        "*": (0.0, 0.0),
    },
}


def estimate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost using the built-in pricing table. Unknown models return 0."""
    provider_table = PRICING.get(provider, {})
    rates = provider_table.get(model) or provider_table.get("*")
    if not rates:
        return 0.0
    input_rate, output_rate = rates
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
