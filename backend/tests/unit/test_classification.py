"""Unit tests for classification and field extraction."""
from __future__ import annotations

import json

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.core.ports.parser import ParsedDocument
from app.core.services.classification import classify_document, extract_fields


@pytest.fixture
def parsed_fattura() -> ParsedDocument:
    return ParsedDocument(
        text="Fattura n. 2024-089 del 15/01/2026. Fornitore: ABC Srl. Importo: 4200 EUR.",
        confidence=0.90,
    )


class TestClassifyDocument:
    @pytest.mark.asyncio
    async def test_classify_fattura(self, parsed_fattura: ParsedDocument) -> None:
        llm = DummyLLMAdapter(content=json.dumps({"document_type": "fattura", "confidence": 0.92}))
        result = await classify_document(llm, parsed_fattura)
        assert result["document_type"] == "fattura"
        assert result["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_classify_contratto(self) -> None:
        parsed = ParsedDocument(text="Contratto di servizi tra...", confidence=0.85)
        llm = DummyLLMAdapter(content=json.dumps({"document_type": "contratto", "confidence": 0.88}))
        result = await classify_document(llm, parsed)
        assert result["document_type"] == "contratto"

    @pytest.mark.asyncio
    async def test_classify_llm_failure(self, parsed_fattura: ParsedDocument) -> None:
        class FailingLLM(DummyLLMAdapter):
            async def generate(self, prompt, system, context=None):
                raise RuntimeError("LLM down")

        result = await classify_document(FailingLLM(), parsed_fattura)
        assert result["document_type"] == "altro"
        assert result["confidence"] == 0.0


class TestExtractFields:
    @pytest.mark.asyncio
    async def test_extract_fattura_fields(self, parsed_fattura: ParsedDocument) -> None:
        fields_response = {
            "fields": {
                "numero_fattura": {"value": "2024-089", "confidence": 0.95},
                "importo_totale": {"value": 4200, "confidence": 0.90},
                "fornitore": {"value": "ABC Srl", "confidence": 0.88},
            }
        }
        llm = DummyLLMAdapter(content=json.dumps(fields_response))
        result = await extract_fields(llm, parsed_fattura, "fattura")
        assert result["numero_fattura"]["value"] == "2024-089"
        assert result["numero_fattura"]["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_extract_null_field(self, parsed_fattura: ParsedDocument) -> None:
        fields_response = {
            "fields": {
                "metodo_pagamento": {"value": None, "confidence": 0.0},
            }
        }
        llm = DummyLLMAdapter(content=json.dumps(fields_response))
        result = await extract_fields(llm, parsed_fattura, "fattura")
        assert result["metodo_pagamento"]["value"] is None
        assert result["metodo_pagamento"]["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_extract_llm_failure(self, parsed_fattura: ParsedDocument) -> None:
        class FailingLLM(DummyLLMAdapter):
            async def generate(self, prompt, system, context=None):
                raise RuntimeError("LLM down")

        result = await extract_fields(FailingLLM(), parsed_fattura, "fattura")
        assert result == {}

    @pytest.mark.asyncio
    async def test_fallback_chain_on_failure(self) -> None:
        """Test FallbackChain triggers fallback on primary failure."""
        from app.adapters.llm.fallback_chain import FallbackChain

        class FailingLLM(DummyLLMAdapter):
            async def generate(self, prompt, system, context=None):
                raise ConnectionError("Primary down")

        primary = FailingLLM()
        fallback = DummyLLMAdapter(content=json.dumps({"document_type": "fattura", "confidence": 0.85}))
        chain = FallbackChain(providers=[primary, fallback])

        parsed = ParsedDocument(text="test", confidence=0.9)
        result = await classify_document(chain, parsed)
        assert result["document_type"] == "fattura"
