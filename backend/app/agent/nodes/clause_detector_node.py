"""Clause detector node — LLM analysis with retry and fallback."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from app.core.ports.llm import LLMProviderPort

logger = structlog.get_logger()

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "risky_clause_detection.md"
MAX_RETRIES = 2


class ClauseDetectorNode:
    """LLM node for risky clause detection with retry and fallback."""

    def __init__(self, llm: LLMProviderPort) -> None:
        self._llm = llm
        self._system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    async def run(self, document_text: str, document_id: str) -> list[dict[str, Any]]:
        """Analyze document text and return detected clauses."""
        prompt = (
            f"Documento ID: {document_id}\n\n"
            f"Testo del contratto:\n{document_text[:15000]}\n\n"
            "Identifica tutte le clausole rischiose."
        )

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await self._llm.generate(
                    prompt=prompt,
                    system=self._system_prompt,
                )
                data = json.loads(resp.content)
                clauses = data.get("clauses", [])
                return self._validate_clauses(clauses)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(
                    "clause_detection_parse_failed",
                    attempt=attempt,
                    error=str(e),
                )
                if attempt == MAX_RETRIES:
                    return self._fallback_response(document_text)

        return []

    def _validate_clauses(self, clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        valid_categories = {
            "rinnovo_automatico", "penale", "limitazione_responsabilita",
            "recesso", "esclusiva", "non_concorrenza",
        }
        valid_severities = {"alto", "medio", "basso"}
        result = []
        for clause in clauses:
            if clause.get("category") not in valid_categories:
                continue
            if clause.get("severity") not in valid_severities:
                clause["severity"] = "medio"
            explanation = clause.get("plain_language_explanation", "")
            if len(explanation) > 200:
                clause["plain_language_explanation"] = explanation[:200]
            confidence = clause.get("confidence_score", 0.5)
            clause["confidence_score"] = max(0.0, min(1.0, float(confidence)))
            result.append(clause)
        return result

    def _fallback_response(self, document_text: str) -> list[dict[str, Any]]:
        """Pattern-based fallback when LLM fails."""
        keywords = {
            "rinnovo_automatico": ["rinnovo automatico", "rinnovo tacito", "silenzio-assenso"],
            "penale": ["penale", "multa", "sanzione"],
            "limitazione_responsabilita": ["limitazione di responsabilità", "esclusione di garanzia"],
        }
        clauses: list[dict[str, Any]] = []
        text_lower = document_text.lower()
        for category, terms in keywords.items():
            for term in terms:
                if term in text_lower:
                    idx = text_lower.index(term)
                    snippet = document_text[max(0, idx - 50): idx + 100]
                    clauses.append({
                        "category": category,
                        "severity": "medio",
                        "clause_text": snippet.strip(),
                        "plain_language_explanation": f"Rilevata possibile clausola di tipo {category.replace('_', ' ')}",
                        "confidence_score": 0.55,
                    })
                    break
        return clauses
