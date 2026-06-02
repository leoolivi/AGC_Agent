"""Cross-document correlation and dossier domain models."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


class DocumentCorrelation(BaseModel):
    """A detected correlation between two documents."""

    id: UUID
    source_document_id: UUID
    target_document_id: UUID
    correlation_type: Literal[
        "derivato_da", "versione_di", "allegato_di", "in_conflitto_con"
    ]
    confidence_score: float
    source_passage: str | None = None
    target_passage: str | None = None
    source_page: int | None = None
    target_page: int | None = None

    @field_validator("confidence_score")
    @classmethod
    def confidence_score_in_range(cls, v: float) -> float:
        """Confidence score must be between 0.0 and 1.0 inclusive."""
        if not 0.0 <= v <= 1.0:
            msg = "confidence_score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def source_and_target_differ(self) -> DocumentCorrelation:
        """Source and target documents must be different."""
        if self.source_document_id == self.target_document_id:
            msg = "source_document_id and target_document_id must be different"
            raise ValueError(msg)
        return self


class MissingItem(BaseModel):
    """An item identified as missing from a dossier."""

    description: str
    certainty: Literal["certain", "probable"]


class DossierDocument(BaseModel):
    """A document belonging to a dossier with an optional role."""

    document_id: UUID
    role: str | None = None


class Dossier(BaseModel):
    """A logical grouping of correlated documents."""

    id: UUID
    user_id: UUID
    title: str
    dossier_type: str | None = None
    completeness_status: Literal["complete", "incomplete"] = "incomplete"
    missing_items: list[MissingItem] = []
    documents: list[DossierDocument] = []
