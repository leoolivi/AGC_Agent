"""Risky clause domain model for contract analysis."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


class RiskyClause(BaseModel):
    """A risky clause detected in a contract document.

    Represents a potentially problematic clause identified by the
    Risky_Clause_Detector, with source attribution, severity, and
    a plain-language explanation for the end user.
    """

    id: UUID
    document_id: UUID
    category: Literal[
        "rinnovo_automatico",
        "penale",
        "limitazione_responsabilita",
        "recesso",
        "esclusiva",
        "non_concorrenza",
    ]
    severity: Literal["alto", "medio", "basso"]
    clause_text: str
    page_number: int | None = None
    paragraph_ref: str | None = None
    plain_language_explanation: str
    confidence_score: float

    @field_validator("plain_language_explanation")
    @classmethod
    def plain_language_explanation_max_length(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError(
                "plain_language_explanation must be at most 200 characters"
            )
        return v

    @field_validator("confidence_score")
    @classmethod
    def confidence_score_range(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return v
