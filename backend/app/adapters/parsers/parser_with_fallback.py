"""ParserWithFallback — tries primary parser, falls back if confidence < 0.60."""
from __future__ import annotations

import structlog

from app.core.ports.parser import DocumentParserPort, ParsedDocument

logger = structlog.get_logger()


class ParserWithFallback(DocumentParserPort):
    CONFIDENCE_THRESHOLD = 0.60

    def __init__(self, primary: DocumentParserPort, fallback: DocumentParserPort) -> None:
        self._primary = primary
        self._fallback = fallback

    def can_parse(self, content_type: str, filename: str) -> bool:
        return self._primary.can_parse(content_type, filename) or self._fallback.can_parse(
            content_type, filename
        )

    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        result: ParsedDocument | None = None
        try:
            result = await self._primary.parse(file, filename)
            if result.confidence >= self.CONFIDENCE_THRESHOLD:
                return result
            logger.info(
                "primary_parser_low_confidence",
                confidence=result.confidence,
                filename=filename,
            )
        except Exception as e:
            logger.warning("primary_parser_failed", error=str(e), filename=filename)

        try:
            fallback_result = await self._fallback.parse(file, filename)
            if result is None or fallback_result.confidence > result.confidence:
                return fallback_result
            return result
        except Exception as e:
            logger.warning("fallback_parser_failed", error=str(e), filename=filename)
            if result is not None:
                return result
            raise
