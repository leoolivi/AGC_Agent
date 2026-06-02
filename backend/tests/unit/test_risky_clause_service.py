"""Unit tests for RiskyClauseService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.services.risky_clause_service import (
    CONFIDENCE_THRESHOLD_UNCERTAIN,
    RiskyClauseService,
    SEVERITY_ORDER,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


class TestRiskyClauseService:
    @pytest.mark.asyncio
    async def test_store_clause_persistence(self, mock_session: AsyncMock) -> None:
        orm_clause = MagicMock()
        orm_clause.id = uuid.uuid4()
        orm_clause.document_id = uuid.uuid4()
        orm_clause.category = "penale"
        orm_clause.severity = "alto"
        orm_clause.clause_text = "Penale del 5%"
        orm_clause.page_number = 3
        orm_clause.paragraph_ref = "Art. 7"
        orm_clause.plain_language_explanation = "Penale per ritardo"
        orm_clause.confidence_score = 0.90

        async def refresh_side_effect(obj: object) -> None:
            pass

        mock_session.refresh = refresh_side_effect

        service = RiskyClauseService(mock_session)
        doc_id = uuid.uuid4()
        result = await service.store_clause(
            document_id=doc_id,
            category="penale",
            severity="alto",
            clause_text="Penale del 5%",
            plain_language_explanation="Penale per ritardo",
            confidence_score=0.90,
            page_number=3,
            paragraph_ref="Art. 7",
        )

        assert result.category == "penale"
        assert result.severity == "alto"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_severity_ordering(self) -> None:
        assert SEVERITY_ORDER["alto"] < SEVERITY_ORDER["medio"]
        assert SEVERITY_ORDER["medio"] < SEVERITY_ORDER["basso"]

    def test_confidence_threshold(self) -> None:
        assert CONFIDENCE_THRESHOLD_UNCERTAIN == 0.75

    @pytest.mark.asyncio
    async def test_confidence_filtering(self, mock_session: AsyncMock) -> None:
        high = MagicMock()
        high.id = uuid.uuid4()
        high.document_id = uuid.uuid4()
        high.category = "recesso"
        high.severity = "medio"
        high.clause_text = "test"
        high.page_number = None
        high.paragraph_ref = None
        high.plain_language_explanation = "Recesso"
        high.confidence_score = 0.85

        low = MagicMock()
        low.id = uuid.uuid4()
        low.document_id = high.document_id
        low.category = "penale"
        low.severity = "basso"
        low.clause_text = "test2"
        low.page_number = None
        low.paragraph_ref = None
        low.plain_language_explanation = "Penale bassa"
        low.confidence_score = 0.60

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [high]
        mock_session.execute.return_value = mock_result

        service = RiskyClauseService(mock_session)
        clauses = await service.get_clauses_by_document(
            high.document_id, min_confidence=0.75
        )
        assert len(clauses) == 1
        assert clauses[0].confidence_score >= 0.75
