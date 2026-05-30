"""OpenRouterAdapter — LLM provider via OpenRouter (OpenAI-compatible API)."""
from __future__ import annotations

from typing import AsyncIterator

import openai

from app.core.ports.llm import LLMProviderPort, LLMResponse


class OpenRouterAdapter(LLMProviderPort):
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b") -> None:
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "ACG Admin Compliance Guardian",
            },
        )
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
        return LLMResponse(content=content, model=self._model, confidence=None, raw={})

    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
