"""Base Provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    ttft_s: float | None = None
    tool_calls: list[dict] = field(default_factory=list)
    raw: dict | None = None


class Provider(ABC):
    """Abstract provider adapter. Implementations own SDK loading and pricing keys."""

    name: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 512,
        tools: list[dict] | None = None,
    ) -> ProviderResponse:
        """Run a single completion and return the provider response."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.name}:{self.model}"
