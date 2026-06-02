"""Unit tests for CrossDocumentService and DossierService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.domain.correlation import DocumentCorrelation, MissingItem
from app.core.services.cross_document_service import (
    CONFIDENCE_THRESHOLD_CERTAIN,
    CONFIDENCE_THRESHOLD_PROBABLE,
    CrossDocumentService,
)
from app.core.services.dossier_service import DossierService


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


class TestCrossDocumentService:
    def test_classify_confidence_certain(self) -> None:
        service = CrossDocumentService(AsyncMock())
        corr = DocumentCorrelation(
            id=uuid.uuid4(),
            source_document_id=uuid.uuid4(),
            target_document_id=uuid.uuid4(),
            correlation_type="derivato_da",
            confidence_score=0.90,
        )
        assert service.classify_confidence(corr) == "certain"

    def test_classify_confidence_probable(self) -> None:
        service = CrossDocumentService(AsyncMock())
        corr = DocumentCorrelation(
            id=uuid.uuid4(),
            source_document_id=uuid.uuid4(),
            target_document_id=uuid.uuid4(),
            correlation_type="allegato_di",
            confidence_score=0.70,
        )
        assert service.classify_confidence(corr) == "probable"

    def test_classify_confidence_hidden(self) -> None:
        service = CrossDocumentService(AsyncMock())
        corr = DocumentCorrelation(
            id=uuid.uuid4(),
            source_document_id=uuid.uuid4(),
            target_document_id=uuid.uuid4(),
            correlation_type="versione_di",
            confidence_score=0.50,
        )
        assert service.classify_confidence(corr) == "hidden"

    def test_threshold_constants(self) -> None:
        assert CONFIDENCE_THRESHOLD_CERTAIN == 0.85
        assert CONFIDENCE_THRESHOLD_PROBABLE == 0.60

    @pytest.mark.asyncio
    async def test_conflict_creates_inbox_item(self, mock_session: AsyncMock) -> None:
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        user_id = uuid.uuid4()

        from datetime import UTC, datetime

        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "created_at", datetime.now(UTC))
        )

        service = CrossDocumentService(mock_session)
        result = await service.store_correlation(
            user_id=user_id,
            source_document_id=source_id,
            target_document_id=target_id,
            correlation_type="in_conflitto_con",
            confidence_score=0.88,
            source_passage="Importo 1000 EUR",
            target_passage="Importo 1500 EUR",
        )

        assert result.correlation_type == "in_conflitto_con"
        assert mock_session.add.call_count >= 2
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_same_document_rejected(self, mock_session: AsyncMock) -> None:
        service = CrossDocumentService(mock_session)
        doc_id = uuid.uuid4()
        with pytest.raises(ValueError, match="must be different"):
            await service.store_correlation(
                user_id=uuid.uuid4(),
                source_document_id=doc_id,
                target_document_id=doc_id,
                correlation_type="derivato_da",
                confidence_score=0.80,
            )


class TestDossierService:
    @pytest.mark.asyncio
    async def test_completeness_update(self, mock_session: AsyncMock) -> None:
        dossier_id = uuid.uuid4()
        orm_dossier = MagicMock()
        orm_dossier.id = dossier_id
        orm_dossier.user_id = uuid.uuid4()
        orm_dossier.title = "Test Dossier"
        orm_dossier.dossier_type = "contratto_quadro"
        orm_dossier.completeness_status = "incomplete"
        orm_dossier.missing_items = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_dossier
        mock_session.execute.return_value = mock_result

        docs_result = MagicMock()
        docs_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_result, docs_result]

        service = DossierService(mock_session)
        missing = [MissingItem(description="Allegato A", certainty="certain")]
        result = await service.update_completeness(
            dossier_id=dossier_id,
            completeness_status="incomplete",
            missing_items=missing,
        )

        assert result.completeness_status == "incomplete"
        assert len(result.missing_items) == 1
        assert result.missing_items[0].certainty == "certain"

    @pytest.mark.asyncio
    async def test_add_missing_item(self, mock_session: AsyncMock) -> None:
        dossier_id = uuid.uuid4()
        orm_dossier = MagicMock()
        orm_dossier.id = dossier_id
        orm_dossier.user_id = uuid.uuid4()
        orm_dossier.title = "Test"
        orm_dossier.dossier_type = None
        orm_dossier.completeness_status = "complete"
        orm_dossier.missing_items = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_dossier
        docs_result = MagicMock()
        docs_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_result, docs_result]

        service = DossierService(mock_session)
        result = await service.add_missing_item(
            dossier_id, "Fattura mancante", "probable"
        )
        assert result.completeness_status == "incomplete"
