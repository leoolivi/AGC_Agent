"""
DummyLLMAdapter — in-memory implementation of LLMProviderPort.

Returns deterministic canned responses. No network calls.
Safe to use in unit tests.
"""
from __future__ import annotations

from typing import AsyncIterator

from app.core.ports.llm import LLMProviderPort, LLMResponse


class DummyLLMAdapter:
    """In-memory LLMProviderPort implementation for testing."""

    DEFAULT_CONTENT = "dummy response"
    DEFAULT_MODEL = "dummy-model-1.0"

    def __init__(
        self,
        content: str = DEFAULT_CONTENT,
        model: str = DEFAULT_MODEL,
        confidence: float | None = None,
    ) -> None:
        self._content = content
        self._model = model
        self._confidence = confidence

    async def generate(
        self,
        prompt: str,
        system: str,
        context: list[dict] | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            content=self._content,
            model=self._model,
            confidence=self._confidence,
            raw={"prompt": prompt, "system": system, "context": context},
        )

    async def stream(
        self,
        prompt: str,
        system: str,
    ) -> AsyncIterator[str]:
        async def _gen() -> AsyncIterator[str]:
            for token in self._content.split():
                yield token

        return _gen()


# Verify structural compatibility at import time.
def _assert_protocol() -> None:
    _: LLMProviderPort = DummyLLMAdapter()  # type: ignore[assignment]


_assert_protocol()
