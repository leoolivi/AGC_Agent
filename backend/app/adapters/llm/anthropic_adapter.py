"""AnthropicLLMAdapter — LLM provider via Anthropic Claude API."""
from __future__ import annotations

from typing import AsyncIterator

import anthropic

from app.core.ports.llm import LLMProviderPort, LLMResponse


class AnthropicLLMAdapter(LLMProviderPort):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", timeout: int = 45) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)
        self._model = model

    async def generate(
        self, prompt: str, system: str, context: list[dict] | None = None
    ) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        if context:
            messages = [*[{"role": m.get("role", "user"), "content": m["content"]} for m in context], messages[-1]]
        resp = await self._client.messages.create(
            model=self._model, max_tokens=4096, system=system, messages=messages
        )
        content = resp.content[0].text if resp.content else ""
        return LLMResponse(content=content, model=self._model, confidence=None, raw={"id": resp.id})

    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model, max_tokens=4096, system=system, messages=[{"role": "user", "content": prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text
