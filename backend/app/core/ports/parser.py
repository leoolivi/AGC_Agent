"""
DocumentParserPort — Protocol for document parsing backends.

Implementations: LlamaParseAdapter, UnstructuredAdapter, PandasAdapter,
ParserWithFallback (app/adapters/parsers/).
Wiring: app/api/deps.py / DocumentPipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ParsedDocument:
    text: str
    tables: list[dict] = field(default_factory=list)   # Tables extracted as structures
    metadata: dict = field(default_factory=dict)        # Title, dates, author if present
    raw_pages: list[str] = field(default_factory=list)  # Text per page
    confidence: float = 0.0                             # 0.0–1.0: extraction reliability


@runtime_checkable
class DocumentParserPort(Protocol):
    def can_parse(self, content_type: str, filename: str) -> bool: ...

    async def parse(self, file: bytes, filename: str) -> ParsedDocument: ...
