"""ParserRegistry — selects parser via can_parse() without hardcoded logic."""
from __future__ import annotations

from app.core.ports.parser import DocumentParserPort


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[DocumentParserPort] = []

    def register(self, parser: DocumentParserPort) -> None:
        self._parsers.append(parser)

    def get_parser(self, content_type: str, filename: str) -> DocumentParserPort | None:
        for parser in self._parsers:
            if parser.can_parse(content_type, filename):
                return parser
        return None
