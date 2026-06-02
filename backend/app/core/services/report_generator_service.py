"""ReportGeneratorService — report data assembly, rendering, and export history.

Assembles report data from deadlines/documents, applies filters and templates,
tracks export history, and ensures source traceability per row.

Requirements: 11, 12
Properties: 21, 22
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.report import ReportData, ReportFilters, ReportRequest, ReportRow
from app.core.ports.report import ReportRendererPort
from app.db.models import Deadline, Document, Report as ReportORM

logger = structlog.get_logger()

REPORT_TEMPLATES: dict[str, dict[str, str]] = {
    "scadenze_mensili": {
        "title": "Scadenze Mensili",
        "description": "Elenco scadenze nel periodo selezionato",
    },
    "riepilogo_trimestrale_fisco": {
        "title": "Riepilogo Trimestrale Fiscale",
        "description": "Scadenze fiscali per il trimestre",
    },
    "contratti_in_scadenza": {
        "title": "Contratti in Scadenza",
        "description": "Contratti e scadenze contrattuali imminenti",
    },
}

TEMPLATE_DEFAULT_FILTERS: dict[str, ReportFilters] = {
    "scadenze_mensili": ReportFilters(),
    "riepilogo_trimestrale_fisco": ReportFilters(deadline_types=["fiscale"]),
    "contratti_in_scadenza": ReportFilters(deadline_types=["contrattuale"]),
}


class ReportGeneratorService:
    """Service for generating and tracking reports."""

    def __init__(
        self,
        session: AsyncSession,
        renderer: ReportRendererPort,
    ) -> None:
        self._session = session
        self._renderer = renderer

    def list_templates(self) -> list[dict[str, str]]:
        """Return available report templates."""
        return [
            {"name": name, **meta}
            for name, meta in REPORT_TEMPLATES.items()
        ]

    async def assemble_data(self, request: ReportRequest) -> ReportData:
        """Assemble report data from deadlines matching filters."""
        rows = await self._fetch_rows(request.user_id, request.date_from, request.date_to, request.filters)
        template_meta = REPORT_TEMPLATES.get(request.template_name, {"title": request.template_name})
        period = f"{request.date_from.isoformat()} — {request.date_to.isoformat()}"

        summary: dict[str, str] = {
            "total_rows": str(len(rows)),
            "template": request.template_name,
        }
        by_status: dict[str, int] = {}
        for row in rows:
            by_status[row.status] = by_status.get(row.status, 0) + 1
        for status, count in by_status.items():
            summary[f"status_{status}"] = str(count)

        return ReportData(
            title=template_meta["title"],
            period=period,
            generated_at=datetime.now(UTC),
            rows=rows,
            summary=summary,
        )

    async def generate_report(self, request: ReportRequest) -> tuple[ReportORM, bytes]:
        """Assemble data, render, and persist report record."""
        if request.template_name not in REPORT_TEMPLATES:
            msg = f"Unknown template: {request.template_name}"
            raise ValueError(msg)

        data = await self.assemble_data(request)

        if request.format == "pdf":
            content = await self._renderer.render_pdf(request.template_name, data)
        else:
            content = await self._renderer.render_excel(request.template_name, data)

        report_id = uuid.uuid4()
        storage_key = f"reports/{request.user_id}/{report_id}.{request.format}"

        orm_report = ReportORM(
            id=report_id,
            user_id=request.user_id,
            template_name=request.template_name,
            parameters={
                "date_from": request.date_from.isoformat(),
                "date_to": request.date_to.isoformat(),
                "filters": request.filters.model_dump(),
                "format": request.format,
            },
            format=request.format,
            storage_key=storage_key,
        )
        self._session.add(orm_report)
        await self._session.commit()
        await self._session.refresh(orm_report)

        logger.info(
            "report_generated",
            report_id=str(report_id),
            template=request.template_name,
            format=request.format,
            row_count=len(data.rows),
        )
        return orm_report, content

    async def get_report_history(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> list[ReportORM]:
        result = await self._session.execute(
            select(ReportORM)
            .where(ReportORM.user_id == user_id)
            .order_by(ReportORM.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_report(self, report_id: uuid.UUID, user_id: uuid.UUID) -> ReportORM | None:
        result = await self._session.execute(
            select(ReportORM)
            .where(ReportORM.id == report_id)
            .where(ReportORM.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def record_export(
        self,
        report_id: uuid.UUID,
        user_id: uuid.UUID,
        destination: dict,
    ) -> ReportORM | None:
        report = await self.get_report(report_id, user_id)
        if not report:
            return None
        report.export_destination = {
            **destination,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self._session.commit()
        await self._session.refresh(report)
        return report

    async def _fetch_rows(
        self,
        user_id: uuid.UUID,
        date_from: date,
        date_to: date,
        filters: ReportFilters,
    ) -> list[ReportRow]:
        """Fetch deadline rows matching date range and filters."""
        conditions = [
            Deadline.user_id == user_id,
            Deadline.due_date >= date_from,
            Deadline.due_date <= date_to,
        ]

        if filters.deadline_types:
            conditions.append(Deadline.deadline_type.in_(filters.deadline_types))
        if filters.statuses:
            conditions.append(Deadline.status.in_(filters.statuses))

        query = select(Deadline).where(and_(*conditions)).order_by(Deadline.due_date)
        result = await self._session.execute(query)
        deadlines = result.scalars().all()

        rows: list[ReportRow] = []
        for dl in deadlines:
            source_doc_name: str | None = None
            source_doc_id: uuid.UUID | None = None

            if dl.document_id:
                doc = await self._session.get(Document, dl.document_id)
                if doc:
                    source_doc_name = doc.original_filename
                    source_doc_id = doc.id

            rows.append(
                ReportRow(
                    deadline_title=dl.title,
                    due_date=dl.due_date,
                    status=dl.status,
                    deadline_type=dl.deadline_type,
                    source_document=source_doc_name,
                    source_document_id=source_doc_id,
                )
            )

        if filters.categories:
            rows = [
                r for r in rows
                if r.deadline_type in filters.categories
            ]

        return rows
