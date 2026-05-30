"""LlamaParseAdapter — PDF parsing via LlamaParse API."""
from __future__ import annotations

import httpx

from app.core.ports.parser import DocumentParserPort, ParsedDocument


class LlamaParseAdapter(DocumentParserPort):
    SUPPORTED = {"application/pdf"}

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def can_parse(self, content_type: str, filename: str) -> bool:
        return content_type in self.SUPPORTED

    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        if not self._api_key:
            raise RuntimeError("LLAMAPARSE_API_KEY not configured")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.cloud.llamaindex.ai/api/parsing/upload",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (filename, file, "application/pdf")},
            )
            resp.raise_for_status()
            data = resp.json()
        text = data.get("text", "")
        return ParsedDocument(
            text=text,
            tables=data.get("tables", []),
            metadata=data.get("metadata", {}),
            raw_pages=data.get("pages", []),
            confidence=0.90 if text else 0.0,
        )
