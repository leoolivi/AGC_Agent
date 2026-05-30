"""Document domain model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Document(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    original_filename: str
    storage_key: str
    content_type: str
    size_bytes: int | None = None
    document_type: str | None = None
    document_type_confidence: float | None = None
    extracted_metadata: dict = {}
    tags: list[str] = []
    parse_status: str = "pending"
    created_at: datetime
    archived_at: datetime | None = None
