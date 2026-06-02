"""Composite report renderer that delegates to PDF or Excel adapters."""

from __future__ import annotations

from pathlib import Path

import structlog

from app.adapters.report.openpyxl_adapter import OpenpyxlReportAdapter
from app.adapters.report.weasyprint_adapter import WeasyPrintReportAdapter
from app.core.domain.report import ReportData
from app.core.ports.report import ReportRendererPort

logger = structlog.get_logger()


class CompositeReportRenderer(ReportRendererPort):
    """Composite renderer that delegates to PDF or Excel adapters."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialize both PDF and Excel renderers.

        Args:
            templates_dir: Optional custom templates directory.
        """
        self._pdf_renderer = WeasyPrintReportAdapter(templates_dir)
        self._excel_renderer = OpenpyxlReportAdapter()

    async def render_pdf(self, template: str, data: ReportData) -> bytes:
        """Render report to PDF format.

        Args:
            template: Template name (without extension).
            data: Report data to render.

        Returns:
            PDF file content as bytes.
        """
        logger.info("rendering_pdf", template=template)
        return await self._pdf_renderer.render_pdf(template, data)

    async def render_excel(self, template: str, data: ReportData) -> bytes:
        """Render report to Excel format.

        Args:
            template: Template name (not used for Excel, kept for interface).
            data: Report data to render.

        Returns:
            Excel file content as bytes.
        """
        logger.info("rendering_excel", template=template)
        return await self._excel_renderer.render_excel(template, data)
