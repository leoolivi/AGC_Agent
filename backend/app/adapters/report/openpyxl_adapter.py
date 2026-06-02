"""Openpyxl report adapter for Excel rendering."""
from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

from app.core.domain.report import ReportData
from app.core.ports.report import ReportRendererPort


class OpenpyxlReportAdapter:
    """Render reports to Excel using openpyxl."""

    async def render_pdf(self, template: str, data: ReportData) -> bytes:
        msg = "OpenpyxlReportAdapter does not support PDF rendering"
        raise NotImplementedError(msg)

    async def render_excel(self, template: str, data: ReportData) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = data.title[:31]

        headers = [
            "Titolo Scadenza",
            "Data Scadenza",
            "Stato",
            "Tipo",
            "Documento Sorgente",
        ]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for row in data.rows:
            ws.append([
                row.deadline_title,
                row.due_date.isoformat(),
                row.status,
                row.deadline_type,
                row.source_document or "",
            ])

        if data.summary:
            ws.append([])
            ws.append(["Riepilogo"])
            for key, value in data.summary.items():
                ws.append([key, value])

        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()


def _assert_protocol() -> None:
    _: ReportRendererPort = OpenpyxlReportAdapter()  # type: ignore[assignment]


_assert_protocol()
