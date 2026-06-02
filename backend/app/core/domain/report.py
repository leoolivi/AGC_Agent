"""Report generation domain models."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator


class ReportFilters(BaseModel):
    """Filters applied when generating a report."""

    deadline_types: list[str] | None = None
    statuses: list[str] | None = None
    categories: list[str] | None = None


class ReportRequest(BaseModel):
    """A request to generate a report for a given period and filters."""

    user_id: UUID
    template_name: str
    date_from: date
    date_to: date
    filters: ReportFilters
    format: Literal["pdf", "excel"]

    @model_validator(mode="after")
    def _validate_date_range(self) -> ReportRequest:
        if self.date_from > self.date_to:
            msg = "date_from must be less than or equal to date_to"
            raise ValueError(msg)
        return self


class ReportRow(BaseModel):
    """A single row in a generated report."""

    deadline_title: str
    due_date: date
    status: str
    deadline_type: str
    source_document: str | None = None
    source_document_id: UUID | None = None


class ReportData(BaseModel):
    """The assembled data for a generated report, ready for rendering."""

    title: str
    period: str
    generated_at: datetime
    rows: list[ReportRow]
    summary: dict[str, str] = {}
