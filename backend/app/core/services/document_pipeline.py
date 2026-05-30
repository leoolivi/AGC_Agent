"""DocumentPipeline — async pipeline: parse → classify → extract → confidence_gate → chunk → triage."""
from __future__ import annotations

import structlog

from app.core.ports.llm import LLMProviderPort
from app.core.ports.parser import DocumentParserPort, ParsedDocument
from app.core.ports.vector import VectorStorePort

logger = structlog.get_logger()


class DocumentPipeline:
    """Orchestrates the full document processing pipeline."""

    def __init__(
        self,
        parser: DocumentParserPort,
        llm: LLMProviderPort,
        vector_store: VectorStorePort,
    ) -> None:
        self._parser = parser
        self._llm = llm
        self._vector_store = vector_store

    async def run(
        self,
        document_id: str,
        file_data: bytes,
        filename: str,
        user_id: str,
    ) -> dict:
        """Execute pipeline. Returns result dict with status and extracted data."""
        result: dict = {"document_id": document_id, "status": "pending"}

        # Step 1: Parse
        parsed = await self._parse(file_data, filename)
        if parsed is None:
            result["status"] = "failed"
            result["error"] = "All parsers failed"
            logger.warning("pipeline_parse_failed", document_id=document_id)
            return result

        result["parsed"] = True
        result["parse_confidence"] = parsed.confidence

        # Step 2: Classify
        classification = await self._classify(parsed)
        result["document_type"] = classification.get("document_type")
        result["document_type_confidence"] = classification.get("confidence", 0.0)

        # Step 3: Extract fields
        fields = await self._extract_fields(parsed, classification.get("document_type", "altro"))
        result["extracted_fields"] = fields

        # Step 4: Chunk and embed
        await self._chunk_and_embed(document_id, parsed, user_id)

        result["status"] = "parsed"
        return result

    async def _parse(self, file_data: bytes, filename: str) -> ParsedDocument | None:
        try:
            return await self._parser.parse(file_data, filename)
        except Exception as e:
            logger.error("parser_error", error=str(e), filename=filename)
            return None

    async def _classify(self, parsed: ParsedDocument) -> dict:
        from app.core.services.classification import classify_document

        return await classify_document(self._llm, parsed)

    async def _extract_fields(self, parsed: ParsedDocument, doc_type: str) -> dict:
        from app.core.services.classification import extract_fields

        return await extract_fields(self._llm, parsed, doc_type)

    async def _chunk_and_embed(
        self, document_id: str, parsed: ParsedDocument, user_id: str
    ) -> None:
        # chunk_text is a pure utility, acceptable to import here
        from app.adapters.vector.chunking import chunk_text  # noqa: adapter utility only

        chunks = chunk_text(parsed.text)
        if chunks:
            metadata = [{"user_id": user_id} for _ in chunks]
            try:
                await self._vector_store.upsert(document_id, chunks, metadata)
            except Exception as e:
                logger.error("vector_upsert_failed", document_id=document_id, error=str(e))
