"""IngestPipelineService — orchestrates passive document ingestion from monitored sources.

This service coordinates:
1. File download from external sources (Drive, Gmail, Calendar)
2. Document record creation with source attribution
3. Delegation to existing DocumentPipeline for processing
4. Real-time status emission to connected clients
5. Format filtering (PDF, XLS, XLSX, CSV only)

Requirements: 2, 4
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

import structlog

from app.core.domain.document import Document
from app.core.domain.realtime import RealtimeEvent
from app.core.domain.source import FileChange
from app.core.ports.realtime import RealtimePort
from app.core.ports.source_monitor import SourceMonitorPort
from app.core.services.document_pipeline import DocumentPipeline

logger = structlog.get_logger()

# Supported file formats for ingestion (Requirement 2.6)
SUPPORTED_FORMATS = {
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}


class IngestPipelineService:
    """Orchestrates document ingestion from monitored sources.

    This service acts as the bridge between source monitoring and document
    processing. It handles:
    - Downloading files from external sources
    - Creating document records with source attribution
    - Filtering unsupported formats
    - Delegating to DocumentPipeline for analysis
    - Emitting real-time status updates

    The service enforces format restrictions (PDF/XLS/XLSX/CSV only) and
    provides real-time feedback to users via WebSocket/SSE.
    """

    def __init__(
        self,
        source_monitor: SourceMonitorPort,
        document_pipeline: DocumentPipeline,
        realtime: RealtimePort,
    ) -> None:
        """Initialize the ingest pipeline service.

        Args:
            source_monitor: Port for downloading files from sources
            document_pipeline: Existing pipeline for document processing
            realtime: Port for emitting real-time events to clients
        """
        self._source_monitor = source_monitor
        self._document_pipeline = document_pipeline
        self._realtime = realtime

    async def ingest_file(
        self,
        file_change: FileChange,
        source_type: Literal["drive", "gmail", "calendar"],
        user_id: str,
    ) -> Document | None:
        """Ingest a single file from a monitored source.

        This method orchestrates the complete ingestion flow:
        1. Validate file format (skip unsupported formats)
        2. Emit "ingesting" status
        3. Download file content
        4. Create document record with source attribution
        5. Emit "parsing" status
        6. Delegate to DocumentPipeline
        7. Emit final status (completed/needs_attention/failed)

        Args:
            file_change: File metadata from source monitor
            source_type: Type of source (drive, gmail, calendar)
            user_id: User who owns the monitored source

        Returns:
            Document domain model if successful, None if skipped or failed

        Raises:
            RuntimeError: If download or processing fails critically
        """
        document_id = str(uuid.uuid4())

        # Step 1: Format validation (Requirement 2.6)
        if not self._is_supported_format(file_change.mime_type):
            logger.debug(
                "ingest_skipped_unsupported_format",
                file_id=file_change.file_id,
                filename=file_change.filename,
                mime_type=file_change.mime_type,
                source_type=source_type,
            )
            return None

        # Step 2: Emit ingesting status (Requirement 2.8, 4.2)
        await self._emit_status(
            user_id=user_id,
            document_id=document_id,
            filename=file_change.filename,
            source_type=source_type,
            status="ingesting",
        )

        try:
            # Step 3: Download file content (Requirement 2.2, 2.3)
            file_data = await self._source_monitor.download_file(
                source_type=source_type,
                file_ref=file_change.file_id,
            )

            # Step 4: Create document record with source attribution (Requirement 2.2, 2.3)
            # Note: In a real implementation, this would persist to database via a repository
            # For now, we create the domain model that would be persisted
            document = Document(
                id=uuid.UUID(document_id),
                user_id=uuid.UUID(user_id),
                filename=file_change.filename,
                original_filename=file_change.filename,
                storage_key=f"{source_type}/{user_id}/{document_id}",
                content_type=file_change.mime_type,
                size_bytes=len(file_data),
                source=source_type,
                source_ref_id=file_change.file_id,
                parse_status="pending",
                created_at=datetime.now(),
            )

            logger.info(
                "document_created_from_source",
                document_id=document_id,
                source_type=source_type,
                source_ref_id=file_change.file_id,
                filename=file_change.filename,
            )

            # Step 5: Emit parsing status (Requirement 4.2)
            await self._emit_status(
                user_id=user_id,
                document_id=document_id,
                filename=file_change.filename,
                source_type=source_type,
                status="parsing",
            )

            # Step 6: Delegate to DocumentPipeline (Requirement 2.2)
            pipeline_result = await self._document_pipeline.run(
                document_id=document_id,
                file_data=file_data,
                filename=file_change.filename,
                user_id=user_id,
            )

            # Step 7: Emit final status based on pipeline result (Requirement 4.3, 4.4)
            final_status = self._determine_final_status(pipeline_result)
            await self._emit_status(
                user_id=user_id,
                document_id=document_id,
                filename=file_change.filename,
                source_type=source_type,
                status=final_status,
                pipeline_result=pipeline_result,
            )

            logger.info(
                "ingest_completed",
                document_id=document_id,
                source_type=source_type,
                final_status=final_status,
            )

            return document

        except Exception as e:
            logger.error(
                "ingest_failed",
                document_id=document_id,
                filename=file_change.filename,
                source_type=source_type,
                error=str(e),
            )

            # Emit failed status (Requirement 4.4)
            await self._emit_status(
                user_id=user_id,
                document_id=document_id,
                filename=file_change.filename,
                source_type=source_type,
                status="failed",
                error=str(e),
            )

            return None

    def _is_supported_format(self, mime_type: str) -> bool:
        """Check if the file format is supported for ingestion.

        Requirement 2.6: Only PDF, XLS, XLSX, CSV are supported.

        Args:
            mime_type: MIME type of the file

        Returns:
            True if format is supported, False otherwise
        """
        return mime_type in SUPPORTED_FORMATS

    def _determine_final_status(self, pipeline_result: dict[str, Any]) -> str:
        """Determine the final status based on pipeline result.

        Maps DocumentPipeline result to processing feed status.

        Args:
            pipeline_result: Result dict from DocumentPipeline.run()

        Returns:
            Status string: "completed", "needs_attention", or "failed"
        """
        status = pipeline_result.get("status", "failed")

        if status == "failed":
            return "failed"

        # Check if document needs attention based on confidence thresholds
        doc_type_confidence = pipeline_result.get("document_type_confidence", 0.0)
        parse_confidence = pipeline_result.get("parse_confidence", 0.0)

        # Low confidence requires human attention (Requirement 4.4)
        if doc_type_confidence < 0.70 or parse_confidence < 0.70:
            return "needs_attention"

        return "completed"

    async def _emit_status(
        self,
        user_id: str,
        document_id: str,
        filename: str,
        source_type: str,
        status: str,
        pipeline_result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Emit a real-time processing status event.

        Requirement 4.2: Real-time status updates via WebSocket/SSE.

        Args:
            user_id: Target user ID
            document_id: Document being processed
            filename: Original filename
            source_type: Source type (drive, gmail, calendar)
            status: Current status (ingesting, parsing, completed, needs_attention, failed)
            pipeline_result: Optional pipeline result for completed status
            error: Optional error message for failed status
        """
        payload: dict[str, Any] = {
            "document_id": document_id,
            "filename": filename,
            "source": source_type,
            "status": status,
        }

        # Add additional context based on status
        if status == "completed" and pipeline_result:
            payload["document_type"] = pipeline_result.get("document_type")
            payload["extracted_fields"] = pipeline_result.get("extracted_fields", {})

        if status == "failed" and error:
            payload["error"] = error

        event = RealtimeEvent(
            event_type="processing_status",
            payload=payload,
            timestamp=datetime.now(),
            user_id=user_id,
        )

        try:
            await self._realtime.emit(user_id=user_id, event=event)
        except Exception as e:
            # Don't fail ingestion if real-time emission fails
            logger.warning(
                "realtime_emit_failed",
                user_id=user_id,
                document_id=document_id,
                error=str(e),
            )
