"""PandasAdapter — spreadsheet/CSV parsing via pandas."""
from __future__ import annotations

import io

from app.core.ports.parser import DocumentParserPort, ParsedDocument


class PandasAdapter(DocumentParserPort):
    SUPPORTED = {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    def can_parse(self, content_type: str, filename: str) -> bool:
        return content_type in self.SUPPORTED or filename.endswith((".csv", ".xls", ".xlsx"))

    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas package not installed")

        buf = io.BytesIO(file)
        if filename.endswith(".csv") or "csv" in filename:
            df = pd.read_csv(buf)
        else:
            df = pd.read_excel(buf)

        text = df.to_string(index=False)
        tables = [df.to_dict(orient="records")]
        return ParsedDocument(
            text=text,
            tables=tables,
            metadata={"rows": len(df), "columns": list(df.columns)},
            confidence=0.85 if len(df) > 0 else 0.0,
        )
