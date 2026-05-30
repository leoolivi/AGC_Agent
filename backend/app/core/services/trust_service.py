"""TrustService — updates user_extraction_trust from ReviewCard interactions."""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TrustService:
    """Manages progressive trust based on user confirmation behavior."""

    @staticmethod
    async def record_confirmation(
        session: AsyncSession,
        user_id: str,
        document_type: str,
        field_name: str,
        was_edited: bool,
    ) -> None:
        """Record a user's confirmation/edit action. Atomic upsert."""
        if was_edited:
            await session.execute(
                text("""
                    INSERT INTO user_extraction_trust (user_id, document_type, field_name, total_extractions, confirmed_without_edit, edited_extractions, last_updated)
                    VALUES (:uid, :dtype, :fname, 1, 0, 1, NOW())
                    ON CONFLICT (user_id, document_type, field_name)
                    DO UPDATE SET
                        total_extractions = user_extraction_trust.total_extractions + 1,
                        edited_extractions = user_extraction_trust.edited_extractions + 1,
                        last_updated = NOW()
                """),
                {"uid": user_id, "dtype": document_type, "fname": field_name},
            )
        else:
            await session.execute(
                text("""
                    INSERT INTO user_extraction_trust (user_id, document_type, field_name, total_extractions, confirmed_without_edit, edited_extractions, last_updated)
                    VALUES (:uid, :dtype, :fname, 1, 1, 0, NOW())
                    ON CONFLICT (user_id, document_type, field_name)
                    DO UPDATE SET
                        total_extractions = user_extraction_trust.total_extractions + 1,
                        confirmed_without_edit = user_extraction_trust.confirmed_without_edit + 1,
                        last_updated = NOW()
                """),
                {"uid": user_id, "dtype": document_type, "fname": field_name},
            )

    @staticmethod
    async def get_accuracy(
        session: AsyncSession, user_id: str, document_type: str, field_name: str
    ) -> float | None:
        """Get user's accuracy for a specific field type."""
        result = await session.execute(
            text("""
                SELECT accuracy FROM user_extraction_trust
                WHERE user_id = :uid AND document_type = :dtype AND field_name = :fname
            """),
            {"uid": user_id, "dtype": document_type, "fname": field_name},
        )
        row = result.first()
        return float(row[0]) if row and row[0] is not None else None
