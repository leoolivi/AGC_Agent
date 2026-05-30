"""PyMuPDF PDF parser — extracts real text from PDF files."""
from __future__ import annotations

import structlog

from app.core.ports.parser import DocumentParserPort, ParsedDocument

logger = structlog.get_logger()


class PyMuPDFParser(DocumentParserPort):
    """Real PDF parser using PyMuPDF. Extracts actual text content."""

    SUPPORTED = {"application/pdf"}

    def can_parse(self, content_type: str, filename: str) -> bool:
        return content_type in self.SUPPORTED or filename.lower().endswith(".pdf")

    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        import pymupdf

        doc = pymupdf.open(stream=file, filetype="pdf")
        pages: list[str] = []
        tables: list[dict] = []

        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)

        doc.close()

        full_text = "\n\n".join(pages)

        # Confidence based on text extraction quality
        if not full_text.strip():
            # Scanned PDF with no text layer
            confidence = 0.1
        elif len(full_text) < 50:
            confidence = 0.4
        else:
            confidence = 0.90

        logger.info(
            "pdf_parsed",
            filename=filename,
            pages=len(pages),
            chars=len(full_text),
            confidence=confidence,
        )

        return ParsedDocument(
            text=full_text,
            tables=tables,
            metadata={"pages": len(pages), "chars": len(full_text)},
            raw_pages=pages,
            confidence=confidence,
        )
