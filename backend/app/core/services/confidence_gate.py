"""ConfidenceGate — checks field confidence against thresholds, creates PendingConfirmations."""
from __future__ import annotations

import uuid

import structlog

from app.agent.risk.engine import RiskEngine

logger = structlog.get_logger()


class ConfidenceGateResult:
    def __init__(self) -> None:
        self.accepted_fields: dict = {}
        self.pending_fields: list[dict] = []
        self.group_id: str | None = None


def evaluate_confidence(
    fields: dict,
    document_type_confidence: float,
    risk_engine: RiskEngine,
    user_id: str = "",
    document_type: str = "altro",
) -> ConfidenceGateResult:
    """Evaluate extracted fields against confidence thresholds.

    Returns a result with accepted fields and fields needing confirmation.
    """
    result = ConfidenceGateResult()

    # Check document type confidence first
    doc_threshold = risk_engine.get_threshold("document_classification")
    if document_type_confidence < doc_threshold:
        result.group_id = str(uuid.uuid4())
        result.pending_fields.append({
            "field_name": "document_type",
            "value": document_type,
            "confidence": document_type_confidence,
            "threshold": doc_threshold,
        })

    # Check each field
    group_id = result.group_id or str(uuid.uuid4())
    has_pending = False

    for field_name, field_data in fields.items():
        confidence = field_data.get("confidence", 0.0)
        value = field_data.get("value")

        # Determine threshold for this field type
        if "importo" in field_name or "amount" in field_name:
            threshold = risk_engine.get_threshold("amount_extraction")
        elif "scadenza" in field_name or "deadline" in field_name or "data" in field_name:
            threshold = risk_engine.get_threshold("deadline_extraction")
        else:
            threshold = risk_engine.get_threshold("field_extraction")

        if confidence >= threshold:
            result.accepted_fields[field_name] = field_data
        else:
            has_pending = True
            result.pending_fields.append({
                "field_name": field_name,
                "value": value,
                "confidence": confidence,
                "threshold": threshold,
            })

    if has_pending:
        result.group_id = group_id

    return result
