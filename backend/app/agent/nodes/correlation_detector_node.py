"""Correlation detector node — entity matching and semantic correlation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from app.core.ports.llm import LLMProviderPort

logger = structlog.get_logger()

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "cross_document_correlation.md"


class CorrelationDetectorNode:
    """Detect cross-document correlations using LLM and entity matching."""

    def __init__(self, llm: LLMProviderPort) -> None:
        self._llm = llm
        self._system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    async def run(
        self,
        source_document_id: str,
        source_text: str,
        candidate_documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect correlations between source and candidate documents."""
        entities = self._extract_entities(source_text)
        prompt = self._build_prompt(source_document_id, source_text, candidate_documents, entities)

        try:
            resp = await self._llm.generate(prompt=prompt, system=self._system_prompt)
            data = json.loads(resp.content)
            correlations = data.get("correlations", [])
            return self._validate_correlations(source_document_id, correlations)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("correlation_detection_failed", error=str(e))
            return self._entity_match_fallback(source_document_id, entities, candidate_documents)

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract basic entities for matching."""
        return {
            "dates": re.findall(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", text),
            "amounts": re.findall(r"€\s?[\d.,]+|[\d.,]+\s?EUR", text, re.IGNORECASE),
            "references": re.findall(r"(?:n\.|num\.|rif\.)\s*\d+", text, re.IGNORECASE),
            "parties": re.findall(r"(?:Sig\.|Dott\.|S\.r\.l\.|S\.p\.A\.)\s[\w\s]+", text),
        }

    def _build_prompt(
        self,
        source_id: str,
        source_text: str,
        candidates: list[dict[str, Any]],
        entities: dict[str, list[str]],
    ) -> str:
        candidates_summary = json.dumps(
            [{"id": c["id"], "filename": c.get("filename", ""), "type": c.get("document_type", "")}
             for c in candidates],
            ensure_ascii=False,
        )
        return (
            f"Documento sorgente ID: {source_id}\n"
            f"Entità estratte: {json.dumps(entities, ensure_ascii=False)}\n"
            f"Testo sorgente (estratto): {source_text[:8000]}\n"
            f"Documenti candidati: {candidates_summary}\n"
            "Identifica le correlazioni."
        )

    def _validate_correlations(
        self,
        source_id: str,
        correlations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        valid_types = {"derivato_da", "versione_di", "allegato_di", "in_conflitto_con"}
        result = []
        for corr in correlations:
            if corr.get("correlation_type") not in valid_types:
                continue
            target_id = corr.get("target_document_id", "")
            if target_id == source_id:
                continue
            confidence = float(corr.get("confidence_score", 0.5))
            corr["confidence_score"] = max(0.0, min(1.0, confidence))
            result.append(corr)
        return result

    def _entity_match_fallback(
        self,
        source_id: str,
        entities: dict[str, list[str]],
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Fallback correlation via entity overlap."""
        correlations: list[dict[str, Any]] = []
        source_refs = set(entities.get("references", []))

        for candidate in candidates:
            cand_text = candidate.get("text", "")
            cand_refs = set(re.findall(r"(?:n\.|num\.|rif\.)\s*\d+", cand_text, re.IGNORECASE))
            overlap = source_refs & cand_refs
            if overlap:
                correlations.append({
                    "target_document_id": candidate["id"],
                    "correlation_type": "derivato_da",
                    "confidence_score": 0.65,
                    "source_passage": ", ".join(overlap),
                    "target_passage": ", ".join(overlap),
                })

        return correlations
