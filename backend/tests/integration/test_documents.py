"""Integration tests for document upload endpoint."""
from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.services.auth_service import create_access_token
from app.main import app

client = TestClient(app)

USER_ID = str(uuid.uuid4())
TOKEN = create_access_token(USER_ID, "test@example.com")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _mock_storage():
    """Return a mock storage that behaves like DummyStorageAdapter."""
    from app.core.ports.storage import FileMetadata

    storage = AsyncMock()
    storage.save = AsyncMock(
        return_value=FileMetadata(
            file_id=str(uuid.uuid4()),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=100,
            storage_key=f"{USER_ID}/2026/05/test.pdf",
            user_id=USER_ID,
        )
    )
    storage.get = AsyncMock(return_value=b"file content")
    storage.delete = AsyncMock(return_value=True)
    return storage


@pytest.fixture(autouse=True)
def _patch_deps():
    """Patch DB and storage dependencies for all tests."""
    mock_storage = _mock_storage()

    # Mock DB session
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = lambda x: None

    async def fake_db():
        yield mock_session

    app.dependency_overrides = {}
    from app.api.deps import get_db, get_storage

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_storage] = lambda: mock_storage
    yield mock_storage, mock_session
    app.dependency_overrides = {}


class TestUploadDocument:
    def test_upload_valid_pdf(self, _patch_deps) -> None:
        mock_storage, mock_session = _patch_deps
        file = io.BytesIO(b"%PDF-1.4 fake content")
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", file, "application/pdf")},
            headers=HEADERS,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["parse_status"] == "pending"
        mock_storage.save.assert_called_once()

    def test_upload_unsupported_content_type(self) -> None:
        file = io.BytesIO(b"not an image")
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.png", file, "image/png")},
            headers=HEADERS,
        )
        assert resp.status_code == 415

    def test_upload_storage_unavailable(self, _patch_deps) -> None:
        mock_storage, _ = _patch_deps
        mock_storage.save.side_effect = ConnectionError("Storage down")
        file = io.BytesIO(b"%PDF-1.4 content")
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", file, "application/pdf")},
            headers=HEADERS,
        )
        assert resp.status_code == 503

    def test_upload_no_auth(self) -> None:
        file = io.BytesIO(b"%PDF-1.4 content")
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", file, "application/pdf")},
        )
        assert resp.status_code == 403  # HTTPBearer returns 403 when no header


class TestDeleteDocument:
    def test_delete_returns_202_with_confirmation(self, _patch_deps) -> None:
        _, mock_session = _patch_deps
        from app.db.models import Document as DocModel

        doc = DocModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(USER_ID),
            filename="test.pdf",
            original_filename="test.pdf",
            storage_key="key",
            content_type="application/pdf",
            parse_status="parsed",
        )
        mock_session.get = AsyncMock(return_value=doc)

        resp = client.delete(f"/api/v1/documents/{doc.id}", headers=HEADERS)
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "pending_confirmation"
        assert "confirmation_id" in data
