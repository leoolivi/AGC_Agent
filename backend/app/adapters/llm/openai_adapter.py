"""OpenAILLMAdapter — LLM provider via OpenAI GPT-4o API."""
from __future__ import annotations

from typing import AsyncIterator

import openai

from app.core.ports.llm import LLMProviderPort, LLMResponse


class OpenAILLMAdapter(LLMProviderPort):
    def __init__(self, api_key: str, model: str = "gpt-4o", timeout: int = 45) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    async def generate(
        self, prompt: str, system: str, context: list[dict] | None = None
    ) -> LLMResponse:
        messages: list[dict] = [{"role": "system", "content": system}]
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})
        resp = await self._client.chat.completions.create(model=self._model, messages=messages)
        content = resp.choices[0].message.content or ""
        return LLMResponse(content=content, model=self._model, confidence=None, raw={"id": resp.id})

    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
