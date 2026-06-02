"""Dummy report renderer for testing."""
from __future__ import annotations

from app.core.domain.report import ReportData
from app.core.ports.report import ReportRendererPort


class DummyReportRendererAdapter:
    """In-memory ReportRendererPort returning mock bytes."""

    def __init__(self) -> None:
        self.pdf_calls: list[tuple[str, ReportData]] = []
        self.excel_calls: list[tuple[str, ReportData]] = []

    async def render_pdf(self, template: str, data: ReportData) -> bytes:
        self.pdf_calls.append((template, data))
        return b"%PDF-dummy-" + template.encode()

    async def render_excel(self, template: str, data: ReportData) -> bytes:
        self.excel_calls.append((template, data))
        return b"PK-dummy-" + template.encode()


def _assert_protocol() -> None:
    _: ReportRendererPort = DummyReportRendererAdapter()  # type: ignore[assignment]


_assert_protocol()
