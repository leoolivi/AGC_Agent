"""Unit tests for ReportGeneratorService."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.dummy.report import DummyReportRendererAdapter
from app.core.domain.report import ReportFilters, ReportRequest
from app.core.services.report_generator_service import ReportGeneratorService


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=None)
    return session


@pytest.fixture
def report_service(mock_session: AsyncMock) -> ReportGeneratorService:
    renderer = DummyReportRendererAdapter()
    return ReportGeneratorService(mock_session, renderer)


class TestReportGeneratorService:
    @pytest.mark.asyncio
    async def test_data_assembly(
        self, report_service: ReportGeneratorService, mock_session: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        deadline = MagicMock()
        deadline.title = "IVA Q1"
        deadline.due_date = date(2026, 3, 16)
        deadline.status = "active"
        deadline.deadline_type = "fiscale"
        deadline.document_id = doc_id

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [deadline]
        mock_session.execute.return_value = mock_result

        doc = MagicMock()
        doc.id = doc_id
        doc.original_filename = "fattura_q1.pdf"
        mock_session.get = AsyncMock(return_value=doc)

        request = ReportRequest(
            user_id=user_id,
            template_name="scadenze_mensili",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            filters=ReportFilters(deadline_types=["fiscale"]),
            format="pdf",
        )

        data = await report_service.assemble_data(request)
        assert len(data.rows) == 1
        assert data.rows[0].deadline_title == "IVA Q1"
        assert data.rows[0].source_document == "fattura_q1.pdf"
        assert data.rows[0].source_document_id == doc_id

    @pytest.mark.asyncio
    async def test_filter_application(
        self, report_service: ReportGeneratorService, mock_session: AsyncMock
    ) -> None:
        dl_fiscale = MagicMock()
        dl_fiscale.title = "IVA"
        dl_fiscale.due_date = date(2026, 3, 1)
        dl_fiscale.status = "active"
        dl_fiscale.deadline_type = "fiscale"
        dl_fiscale.document_id = None

        dl_contratto = MagicMock()
        dl_contratto.title = "Contratto"
        dl_contratto.due_date = date(2026, 4, 1)
        dl_contratto.status = "active"
        dl_contratto.deadline_type = "contrattuale"
        dl_contratto.document_id = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [dl_fiscale]
        mock_session.execute.return_value = mock_result

        request = ReportRequest(
            user_id=uuid.uuid4(),
            template_name="scadenze_mensili",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            filters=ReportFilters(deadline_types=["fiscale"]),
            format="excel",
        )

        data = await report_service.assemble_data(request)
        assert len(data.rows) == 1
        assert data.rows[0].deadline_type == "fiscale"

    @pytest.mark.asyncio
    async def test_source_traceability(
        self, report_service: ReportGeneratorService, mock_session: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        deadline = MagicMock()
        deadline.title = "Pagamento fornitore"
        deadline.due_date = date(2026, 5, 1)
        deadline.status = "active"
        deadline.deadline_type = "pagamento"
        deadline.document_id = doc_id

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [deadline]
        mock_session.execute.return_value = mock_result

        doc = MagicMock()
        doc.id = doc_id
        doc.original_filename = "ordine_123.pdf"
        mock_session.get = AsyncMock(return_value=doc)

        request = ReportRequest(
            user_id=user_id,
            template_name="scadenze_mensili",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            filters=ReportFilters(),
            format="pdf",
        )

        _, content = await report_service.generate_report(request)
        assert content.startswith(b"%PDF-dummy-")
        renderer = report_service._renderer
        assert isinstance(renderer, DummyReportRendererAdapter)
        assert len(renderer.pdf_calls) == 1

    def test_list_templates(self, report_service: ReportGeneratorService) -> None:
        templates = report_service.list_templates()
        names = [t["name"] for t in templates]
        assert "scadenze_mensili" in names
        assert "contratti_in_scadenza" in names
