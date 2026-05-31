"""Tests for PandasAdapter — xlsx and csv parsing."""
from __future__ import annotations

import io

import pytest

from app.adapters.parsers.pandas_adapter import PandasAdapter


@pytest.fixture
def adapter() -> PandasAdapter:
    return PandasAdapter()


def _make_xlsx(sheets: dict[str, list[dict[str, object]]]) -> bytes:
    import pandas as pd

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False)
    return buf.getvalue()


class TestCanParse:
    def test_xlsx_by_extension(self, adapter: PandasAdapter) -> None:
        assert adapter.can_parse("application/octet-stream", "file.xlsx")

    def test_xlsx_by_content_type(self, adapter: PandasAdapter) -> None:
        ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert adapter.can_parse(ct, "file.bin")

    def test_rejects_pdf(self, adapter: PandasAdapter) -> None:
        assert not adapter.can_parse("application/pdf", "file.pdf")


class TestParseXlsx:
    async def test_single_sheet(self, adapter: PandasAdapter) -> None:
        data = _make_xlsx({"Sheet1": [{"col_a": 1, "col_b": "hello"}]})
        result = await adapter.parse(data, "test.xlsx")
        assert "hello" in result.text
        assert result.tables[0] == [{"col_a": 1, "col_b": "hello"}]
        assert result.metadata["rows"] == 1
        assert result.confidence > 0

    async def test_multi_sheet(self, adapter: PandasAdapter) -> None:
        data = _make_xlsx({
            "Fatture": [{"importo": 100}],
            "Scadenze": [{"data": "2026-06-01"}, {"data": "2026-07-01"}],
        })
        result = await adapter.parse(data, "report.xlsx")
        assert "Fatture" in result.text
        assert "Scadenze" in result.text
        assert result.metadata["rows"] == 3
        assert result.metadata["sheets"] == ["Fatture", "Scadenze"]
        assert len(result.tables) == 2

    async def test_empty_sheet(self, adapter: PandasAdapter) -> None:
        data = _make_xlsx({"Vuoto": []})
        result = await adapter.parse(data, "empty.xlsx")
        assert result.confidence == 0.0
