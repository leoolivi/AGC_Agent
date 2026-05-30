"""
LLMProviderPort — Protocol for LLM provider backends.

Implementations: AnthropicAdapter, OpenAIAdapter, GeminiAdapter, FallbackChain
(app/adapters/llm/).
Wiring: app/api/deps.py via LLM_PROVIDER env var.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol, runtime_checkable


@dataclass
class LLMResponse:
    content: str
    model: str
    confidence: float | None  # None if the model does not expose it
    raw: dict = field(default_factory=dict)  # Raw provider response for debugging


@runtime_checkable
class LLMProviderPort(Protocol):
    async def generate(
        self,
        prompt: str,
        system: str,
        context: list[dict] | None = None,
    ) -> LLMResponse: ...

    async def stream(
        self,
        prompt: str,
        system: str,
    ) -> AsyncIterator[str]: ...
