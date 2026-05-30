"""Integration tests for DocumentPipeline."""
from __future__ import annotations

import json

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.adapters.dummy.parser import DummyParserAdapter
from app.adapters.dummy.vector import DummyVectorAdapter
from app.adapters.parsers.parser_with_fallback import ParserWithFallback
from app.core.services.document_pipeline import DocumentPipeline


@pytest.fixture
def pipeline_with_good_parser() -> DocumentPipeline:
    llm = DummyLLMAdapter(
        content=json.dumps({"document_type": "fattura", "confidence": 0.92})
    )
    parser = DummyParserAdapter(text="Fattura n. 123 del 01/01/2026", confidence=0.90)
    vector = DummyVectorAdapter()
    return DocumentPipeline(parser=parser, llm=llm, vector_store=vector)


@pytest.fixture
def pipeline_with_failing_parser() -> DocumentPipeline:
    class FailingParser(DummyParserAdapter):
        async def parse(self, file: bytes, filename: str):
            raise RuntimeError("Parser crashed")

    llm = DummyLLMAdapter(content=json.dumps({"document_type": "altro", "confidence": 0.5}))
    parser = FailingParser()
    vector = DummyVectorAdapter()
    return DocumentPipeline(parser=parser, llm=llm, vector_store=vector)


@pytest.fixture
def pipeline_with_fallback() -> DocumentPipeline:
    primary = DummyParserAdapter(text="low quality", confidence=0.40)
    fallback = DummyParserAdapter(text="Fattura n. 456 importo 1000 EUR", confidence=0.85)
    parser = ParserWithFallback(primary=primary, fallback=fallback)
    llm = DummyLLMAdapter(
        content=json.dumps({"document_type": "fattura", "confidence": 0.88})
    )
    vector = DummyVectorAdapter()
    return DocumentPipeline(parser=parser, llm=llm, vector_store=vector)


class TestDocumentPipeline:
    @pytest.mark.asyncio
    async def test_successful_pipeline(self, pipeline_with_good_parser: DocumentPipeline) -> None:
        result = await pipeline_with_good_parser.run("doc-1", b"fake pdf", "test.pdf", "user-1")
        assert result["status"] == "parsed"
        assert result["document_type"] == "fattura"
        assert result["document_type_confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_parser_failure(self, pipeline_with_failing_parser: DocumentPipeline) -> None:
        result = await pipeline_with_failing_parser.run("doc-2", b"bad", "bad.pdf", "user-1")
        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fallback_parser(self, pipeline_with_fallback: DocumentPipeline) -> None:
        result = await pipeline_with_fallback.run("doc-3", b"data", "test.pdf", "user-1")
        assert result["status"] == "parsed"
        assert result["parse_confidence"] == 0.85  # fallback confidence

    @pytest.mark.asyncio
    async def test_chunking_and_embedding(self) -> None:
        long_text = " ".join(["word"] * 1000)
        parser = DummyParserAdapter(text=long_text, confidence=0.90)
        llm = DummyLLMAdapter(
            content=json.dumps({"document_type": "altro", "confidence": 0.7})
        )
        vector = DummyVectorAdapter()
        pipeline = DocumentPipeline(parser=parser, llm=llm, vector_store=vector)
        await pipeline.run("doc-4", b"data", "big.pdf", "user-1")
        # Vector store should have chunks
        results = await vector.search("word", "user-1")
        assert len(results) > 0
