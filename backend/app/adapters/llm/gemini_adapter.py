"""GeminiLLMAdapter — LLM provider via Google Gemini API."""
from __future__ import annotations

from typing import AsyncIterator

import google.generativeai as genai

from app.core.ports.llm import LLMProviderPort, LLMResponse


class GeminiLLMAdapter(LLMProviderPort):
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro") -> None:
        genai.configure(api_key=api_key)
        self._model_name = model
        self._model = genai.GenerativeModel(model, system_instruction=None)

    async def generate(
        self, prompt: str, system: str, context: list[dict] | None = None
    ) -> LLMResponse:
        model = genai.GenerativeModel(self._model_name, system_instruction=system)
        full_prompt = prompt
        if context:
            history = "\n".join(f"{m.get('role','user')}: {m['content']}" for m in context)
            full_prompt = f"{history}\nuser: {prompt}"
        resp = await model.generate_content_async(full_prompt)
        content = resp.text or ""
        return LLMResponse(content=content, model=self._model_name, confidence=None, raw={})

    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]:
        model = genai.GenerativeModel(self._model_name, system_instruction=system)
        resp = await model.generate_content_async(prompt, stream=True)
        async for chunk in resp:
            if chunk.text:
                yield chunk.text
