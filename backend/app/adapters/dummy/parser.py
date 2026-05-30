"""
DummyParserAdapter — in-memory implementation of DocumentParserPort.

Returns a canned ParsedDocument. No external dependencies.
Safe to use in unit tests.
"""
from __future__ import annotations

from app.core.ports.parser import DocumentParserPort, ParsedDocument


class DummyParserAdapter:
    """In-memory DocumentParserPort implementation for testing."""

    def __init__(
        self,
        text: str = "dummy parsed text",
        confidence: float = 1.0,
        supported_types: tuple[str, ...] = ("application/pdf", "text/plain"),
    ) -> None:
        self._text = text
        self._confidence = confidence
        self._supported_types = supported_types

    def can_parse(self, content_type: str, filename: str) -> bool:
        return content_type in self._supported_types

    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        return ParsedDocument(
            text=self._text,
            tables=[],
            metadata={"filename": filename, "size_bytes": len(file)},
            raw_pages=[self._text],
            confidence=self._confidence,
        )


# Verify structural compatibility at import time.
def _assert_protocol() -> None:
    _: DocumentParserPort = DummyParserAdapter()  # type: ignore[assignment]


_assert_protocol()
