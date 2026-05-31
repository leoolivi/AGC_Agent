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
            text = df.to_string(index=False)
            tables = [df.to_dict(orient="records")]
            metadata: dict[str, object] = {"rows": len(df), "columns": list(df.columns)}
        else:
            sheets = pd.read_excel(buf, sheet_name=None, engine="openpyxl")
            parts: list[str] = []
            tables = []
            total_rows = 0
            all_columns: list[str] = []
            for sheet_name, df in sheets.items():
                parts.append(f"--- {sheet_name} ---")
                parts.append(df.to_string(index=False))
                tables.append(df.to_dict(orient="records"))
                total_rows += len(df)
                all_columns.extend(c for c in df.columns if c not in all_columns)
            text = "\n\n".join(parts)
            metadata = {
                "rows": total_rows,
                "columns": all_columns,
                "sheets": list(sheets.keys()),
            }

        has_data = metadata["rows"] > 0 if isinstance(metadata["rows"], int) else bool(text.strip())
        return ParsedDocument(
            text=text,
            tables=tables,
            metadata=metadata,
            confidence=0.85 if has_data else 0.0,
        )
