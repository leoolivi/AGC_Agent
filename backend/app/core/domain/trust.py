"""UserExtractionTrust domain model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserExtractionTrust(BaseModel):
    user_id: UUID
    document_type: str
    field_name: str
    total_extractions: int = 0
    confirmed_without_edit: int = 0
    edited_extractions: int = 0
    accuracy: float | None = None
    last_updated: datetime
