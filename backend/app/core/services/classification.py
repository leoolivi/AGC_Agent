"""Classification and field extraction service."""
from __future__ import annotations

import json

import structlog

from app.core.ports.llm import LLMProviderPort
from app.core.ports.parser import ParsedDocument

logger = structlog.get_logger()

CLASSIFICATION_PROMPT = (
    "Classifica il seguente documento in una delle categorie:\n"
    "- fattura\n- contratto\n- nota_spese\n- altro\n\n"
    'Rispondi SOLO con un JSON: {{"document_type": "...", "confidence": 0.XX}}\n\n'
    "Testo del documento (primi 2000 caratteri):\n{text}"
)

EXTRACTION_PROMPTS: dict[str, str] = {
    "fattura": (
        "Estrai i seguenti campi dalla fattura. Per ogni campo fornisci il valore e un confidence score (0.0-1.0).\n"
        "Campi: numero_fattura, data_emissione, data_scadenza, fornitore, partita_iva_fornitore, importo_netto, iva, importo_totale, metodo_pagamento, note\n"
        'Rispondi SOLO con JSON: {{"fields": {{"campo": {{"value": ..., "confidence": 0.XX}}, ...}}}}\n\n'
        "Testo:\n{text}"
    ),
    "contratto": (
        "Estrai i seguenti campi dal contratto. Per ogni campo fornisci il valore e un confidence score (0.0-1.0).\n"
        "Campi: parti_contraenti, data_stipula, data_scadenza, oggetto, importo, durata, clausola_recesso, foro_competente, note\n"
        'Rispondi SOLO con JSON: {{"fields": {{"campo": {{"value": ..., "confidence": 0.XX}}, ...}}}}\n\n'
        "Testo:\n{text}"
    ),
    "nota_spese": (
        "Estrai i seguenti campi dalla nota spese. Per ogni campo fornisci il valore e un confidence score (0.0-1.0).\n"
        "Campi: periodo, totale, numero_voci, categoria_principale, note\n"
        'Rispondi SOLO con JSON: {{"fields": {{"campo": {{"value": ..., "confidence": 0.XX}}, ...}}}}\n\n'
        "Testo:\n{text}"
    ),
    "altro": (
        "Estrai i seguenti campi dal documento. Per ogni campo fornisci il valore e un confidence score (0.0-1.0).\n"
        "Campi: titolo, data, mittente, destinatario, oggetto\n"
        'Rispondi SOLO con JSON: {{"fields": {{"campo": {{"value": ..., "confidence": 0.XX}}, ...}}}}\n\n'
        "Testo:\n{text}"
    ),
}


async def classify_document(llm: LLMProviderPort, parsed: ParsedDocument) -> dict:
    """Classify document type using LLM."""
    text_preview = parsed.text[:2000]
    prompt = CLASSIFICATION_PROMPT.format(text=text_preview)
    try:
        response = await llm.generate(prompt, system="Sei un classificatore di documenti.")
        content = response.content.strip()
        if "{" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            data = json.loads(content[json_start:json_end])
            return {
                "document_type": data.get("document_type", "altro"),
                "confidence": float(data.get("confidence", 0.0)),
            }
        return {"document_type": "altro", "confidence": 0.0}
    except Exception as e:
        logger.error("classification_failed", error=str(e))
        return {"document_type": "altro", "confidence": 0.0}


async def extract_fields(
    llm: LLMProviderPort, parsed: ParsedDocument, doc_type: str
) -> dict:
    """Extract fields based on document type using LLM."""
    prompt_template = EXTRACTION_PROMPTS.get(doc_type, EXTRACTION_PROMPTS["altro"])
    text_preview = parsed.text[:4000]
    prompt = prompt_template.format(text=text_preview)
    try:
        response = await llm.generate(prompt, system="Sei un estrattore di dati da documenti.")
        content = response.content.strip()
        # Extract JSON from response
        if "{" in content:
            json_start = content.index("{")
            # Try to find matching closing brace
            json_str = content[json_start:]
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix truncated JSON by closing it
                json_str = json_str.rstrip()
                for suffix in ['"}}}', '"}}', '}}', '}']:
                    try:
                        data = json.loads(json_str + suffix)
                        break
                    except json.JSONDecodeError:
                        continue
                else:
                    return {}
        else:
            return {}

        fields = data.get("fields", {})
        # Normalize: ensure every field is a dict with value and confidence
        normalized: dict = {}
        for field_name, field_data in fields.items():
            if isinstance(field_data, dict):
                if field_data.get("value") is None:
                    field_data["confidence"] = 0.0
                normalized[field_name] = field_data
            else:
                normalized[field_name] = {"value": field_data, "confidence": 0.5}
        return normalized
    except Exception as e:
        logger.error("extraction_failed", error=str(e), doc_type=doc_type)
        return {}
