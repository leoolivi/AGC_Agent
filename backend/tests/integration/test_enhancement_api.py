"""API tests for enhancement routers."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.services.auth_service import create_access_token
from app.main import app

USER_ID = str(uuid.uuid4())
TOKEN = create_access_token(USER_ID, "test@example.com")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_db():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

    async def fake_db():
        yield session

    from app.api.deps import get_db, get_escalation_scheduler, get_notifier, get_report_renderer, get_source_monitor

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_source_monitor] = lambda: MagicMock()
    app.dependency_overrides[get_report_renderer] = lambda: MagicMock()
    app.dependency_overrides[get_escalation_scheduler] = lambda: MagicMock()
    app.dependency_overrides[get_notifier] = lambda: MagicMock()

    with patch("app.api.v1.sources.validate_source_oauth_scope", new=AsyncMock()):
        with patch("app.api.v1.sources.check_oauth_scopes", new=AsyncMock(return_value={"sufficient": True, "missing_scopes": []})):
            yield session
    app.dependency_overrides = {}


class TestSourcesAPI:
    def test_list_sources(self) -> None:
        with patch("app.api.v1.sources.SourceMonitorService") as MockSvc:
            MockSvc.return_value.list_sources = AsyncMock(return_value=[])
            resp = client.get("/api/v1/sources", headers=HEADERS)
            assert resp.status_code == 200

    def test_create_source_invalid_config(self) -> None:
        resp = client.post(
            "/api/v1/sources",
            json={"source_type": "drive", "config": {"folder_id": "x"}},
            headers=HEADERS,
        )
        assert resp.status_code == 422


class TestClausesAPI:
    def test_get_clauses_empty(self, mock_db: AsyncMock) -> None:
        with patch("app.api.v1.clauses.RiskyClauseService") as MockSvc:
            MockSvc.return_value.get_clauses_by_document = AsyncMock(return_value=[])
            resp = client.get(f"/api/v1/clauses/{uuid.uuid4()}", headers=HEADERS)
            assert resp.status_code == 200
            assert resp.json() == []


class TestCorrelationsAPI:
    def test_get_correlations(self) -> None:
        with patch("app.api.v1.correlations.CrossDocumentService") as MockSvc:
            MockSvc.return_value.get_correlations_by_document = AsyncMock(return_value=[])
            resp = client.get(f"/api/v1/correlations/{uuid.uuid4()}", headers=HEADERS)
            assert resp.status_code == 200


class TestDossiersAPI:
    def test_list_dossiers(self) -> None:
        with patch("app.api.v1.dossiers.DossierService") as MockSvc:
            MockSvc.return_value.get_dossiers_by_user = AsyncMock(return_value=[])
            resp = client.get("/api/v1/dossiers", headers=HEADERS)
            assert resp.status_code == 200


class TestEscalationAPI:
    def test_invalid_steps_rejected(self) -> None:
        resp = client.post(
            "/api/v1/escalation-rules",
            json={
                "name": "Bad",
                "deadline_type": "fiscale",
                "steps": [
                    {"delay_seconds": 7200, "channel": "in_app", "recipient": "u", "message_template": "m"},
                    {"delay_seconds": 3600, "channel": "in_app", "recipient": "u", "message_template": "m"},
                ],
            },
            headers=HEADERS,
        )
        assert resp.status_code == 422


class TestReportsAPI:
    def test_list_templates(self) -> None:
        resp = client.get("/api/v1/reports/templates", headers=HEADERS)
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "scadenze_mensili" in names

    def test_generate_report(self) -> None:
        with patch("app.api.v1.reports.ReportGeneratorService") as MockSvc:
            report = MagicMock()
            report.id = uuid.uuid4()
            report.template_name = "scadenze_mensili"
            report.format = "pdf"
            data = MagicMock()
            data.rows = []
            MockSvc.return_value.generate_report = AsyncMock(return_value=(report, b"pdf"))
            MockSvc.return_value.assemble_data = AsyncMock(return_value=data)
            resp = client.post(
                "/api/v1/reports",
                json={
                    "template_name": "scadenze_mensili",
                    "date_from": "2026-01-01",
                    "date_to": "2026-12-31",
                    "format": "pdf",
                },
                headers=HEADERS,
            )
            assert resp.status_code == 201
