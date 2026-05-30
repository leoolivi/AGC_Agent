"""UnstructuredAdapter — document parsing via Unstructured library."""
from __future__ import annotations

from app.core.ports.parser import DocumentParserPort, ParsedDocument


class UnstructuredAdapter(DocumentParserPort):
    SUPPORTED = {
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    def can_parse(self, content_type: str, filename: str) -> bool:
        return content_type in self.SUPPORTED

    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        try:
            from unstructured.partition.auto import partition
        except ImportError:
            raise RuntimeError("unstructured package not installed")

        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(file)
            tmp_path = tmp.name

        elements = partition(filename=tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

        text = "\n".join(str(el) for el in elements)
        tables = [
            {"content": str(el)} for el in elements if hasattr(el, "category") and "table" in str(getattr(el, "category", "")).lower()
        ]
        return ParsedDocument(
            text=text,
            tables=tables,
            metadata={"element_count": len(elements)},
            confidence=0.75 if text else 0.0,
        )
