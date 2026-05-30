"""FallbackChain — LLM provider with automatic failover: PRIMARY → FALLBACK_1 → FALLBACK_2."""
from __future__ import annotations

from typing import AsyncIterator

import structlog

from app.core.ports.llm import LLMProviderPort, LLMResponse

logger = structlog.get_logger()

# Errors that trigger fallback
_FALLBACK_ERRORS = (ConnectionError, TimeoutError, OSError)


class FallbackChain(LLMProviderPort):
    def __init__(self, providers: list[LLMProviderPort]) -> None:
        if not providers:
            raise ValueError("FallbackChain requires at least one provider")
        self._providers = providers

    async def generate(
        self, prompt: str, system: str, context: list[dict] | None = None
    ) -> LLMResponse:
        last_error: Exception | None = None
        for i, provider in enumerate(self._providers):
            try:
                return await provider.generate(prompt, system, context)
            except Exception as e:
                last_error = e
                logger.warning(
                    "llm_fallback",
                    provider_index=i,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]:
        last_error: Exception | None = None
        for i, provider in enumerate(self._providers):
            try:
                gen = await provider.stream(prompt, system)
                async for token in gen:
                    yield token
                return
            except Exception as e:
                last_error = e
                logger.warning("llm_stream_fallback", provider_index=i, error=str(e))
                continue
        raise RuntimeError(f"All LLM providers failed streaming. Last error: {last_error}")
