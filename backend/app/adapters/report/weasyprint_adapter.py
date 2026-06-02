"""WeasyPrint report adapter for PDF rendering."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.domain.report import ReportData
from app.core.ports.report import ReportRendererPort

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "reports"


class WeasyPrintReportAdapter:
    """Render reports to PDF using Jinja2 templates and WeasyPrint."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        template_path = templates_dir or TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=select_autoescape(["html"]),
        )

    async def render_pdf(self, template: str, data: ReportData) -> bytes:
        template_file = f"{template}.html"
        try:
            jinja_template = self._env.get_template(template_file)
        except Exception as e:
            msg = f"Template not found: {template_file}"
            raise ValueError(msg) from e

        html = jinja_template.render(
            title=data.title,
            period=data.period,
            generated_at=data.generated_at.isoformat(),
            rows=data.rows,
            summary=data.summary,
        )

        try:
            from weasyprint import HTML

            return HTML(string=html).write_pdf()
        except ImportError as e:
            msg = "WeasyPrint is not installed"
            raise RuntimeError(msg) from e

    async def render_excel(self, template: str, data: ReportData) -> bytes:
        msg = "WeasyPrintReportAdapter does not support Excel rendering"
        raise NotImplementedError(msg)


def _assert_protocol() -> None:
    _: ReportRendererPort = WeasyPrintReportAdapter()  # type: ignore[assignment]


_assert_protocol()
