"""
ReportRendererPort — Protocol for rendering reports to different formats.

Implementations: WeasyPrintReportAdapter (PDF), OpenpyxlReportAdapter (Excel)
(app/adapters/report/).
Wiring: app/api/deps.py via dependency injection.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.domain.report import ReportData


@runtime_checkable
class ReportRendererPort(Protocol):
    """Port for rendering report data to PDF or Excel formats."""

    async def render_pdf(
        self,
        template: str,
        data: ReportData,
    ) -> bytes:
        """
        Render report data to PDF format using a template.

        Args:
            template: Template name (e.g., "scadenze_mensili", "riepilogo_trimestrale_fisco").
            data: The assembled report data to render.

        Returns:
            PDF file content as bytes.

        Raises:
            ValueError: If template is not found or invalid.
            RuntimeError: If rendering fails (template error, missing fonts, etc.).
        """
        ...

    async def render_excel(
        self,
        template: str,
        data: ReportData,
    ) -> bytes:
        """
        Render report data to Excel format using a template.

        Args:
            template: Template name (e.g., "scadenze_mensili", "riepilogo_trimestrale_fisco").
            data: The assembled report data to render.

        Returns:
            Excel file content as bytes.

        Raises:
            ValueError: If template is not found or invalid.
            RuntimeError: If rendering fails (template error, invalid data structure, etc.).
        """
        ...
