"""Documents API — upload, list, get, download, delete, search."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_storage, require_owner
from app.core.ports.storage import FileStoragePort
from app.db.models import Document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_SIZE = 20 * 1024 * 1024  # 20MB


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int | None
    document_type: str | None
    parse_status: str
    created_at: str

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    document_type: str | None = None


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
    storage: FileStoragePort = Depends(get_storage),
) -> dict[str, Any]:
    """Upload a document. Max 20MB. Validates Content-Type."""
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Content-Type {content_type} not supported",
        )

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Max 20MB")

    from io import BytesIO

    try:
        meta = await storage.save(
            BytesIO(data), file.filename or "unnamed", user["sub"], content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage unavailable",
        ) from e

    doc = Document(
        id=uuid.UUID(meta.file_id),
        user_id=uuid.UUID(user["sub"]),
        filename=meta.filename,
        original_filename=file.filename or "unnamed",
        storage_key=meta.storage_key,
        content_type=content_type,
        size_bytes=meta.size_bytes,
        parse_status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Trigger pipeline in background
    import asyncio
    asyncio.create_task(_run_pipeline(str(doc.id), data, doc.filename, user["sub"], content_type))

    return {"id": str(doc.id), "filename": doc.filename, "parse_status": doc.parse_status}


@router.get("")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Document)
        .where(Document.user_id == uuid.UUID(user["sub"]))
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "content_type": d.content_type,
            "document_type": d.document_type,
            "parse_status": d.parse_status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await db.get(Document, uuid.UUID(doc_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_owner(str(doc.user_id), user)
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "document_type": doc.document_type,
        "document_type_confidence": doc.document_type_confidence,
        "extracted_metadata": doc.extracted_metadata,
        "tags": doc.tags,
        "parse_status": doc.parse_status,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
    storage: FileStoragePort = Depends(get_storage),
) -> Response:
    doc = await db.get(Document, uuid.UUID(doc_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_owner(str(doc.user_id), user)
    data = await storage.get(str(doc.id))
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.delete("/{doc_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Delete requires PendingConfirmation (risk_level=4). Returns 202."""
    doc = await db.get(Document, uuid.UUID(doc_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_owner(str(doc.user_id), user)

    from app.db.models import AgentTask, PendingConfirmation

    task = AgentTask(
        user_id=doc.user_id,
        action_type="delete_document",
        tool_name="delete_document",
        tool_args={"document_id": doc_id},
        risk_score=4,
        status="waiting_confirmation",
    )
    db.add(task)
    await db.flush()

    confirmation = PendingConfirmation(
        task_id=task.id,
        user_id=doc.user_id,
        description=f"Conferma eliminazione documento: {doc.original_filename}",
        data_for_review={"document_id": doc_id, "filename": doc.original_filename},
        risk_level="4",
        status="pending",
    )
    db.add(confirmation)
    await db.commit()

    return {"status": "pending_confirmation", "confirmation_id": str(confirmation.id)}


@router.post("/search")
async def search_documents(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    query = select(Document).where(Document.user_id == uuid.UUID(user["sub"]))
    if body.document_type:
        query = query.where(Document.document_type == body.document_type)
    query = query.where(
        Document.filename.ilike(f"%{body.query}%")
        | Document.original_filename.ilike(f"%{body.query}%")
    )
    result = await db.execute(query.order_by(Document.created_at.desc()).limit(20))
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "document_type": d.document_type,
            "parse_status": d.parse_status,
        }
        for d in docs
    ]


async def _run_pipeline(
    document_id: str, file_data: bytes, filename: str, user_id: str, content_type: str
) -> None:
    """Run document pipeline + triage in background."""
    import uuid as _uuid

    import structlog

    from app.adapters.dummy.parser import DummyParserAdapter
    from app.adapters.dummy.vector import DummyVectorAdapter
    from app.agent.graphs.triage_graph import TriageGraph
    from app.api.deps import get_llm
    from app.config import settings
    from app.core.services.document_pipeline import DocumentPipeline
    from app.db.models import AgentInbox, Document
    from app.db.session import build_session_factory

    logger = structlog.get_logger()

    llm = get_llm()
    parser = DummyParserAdapter(
        text=file_data[:2000].decode("utf-8", errors="replace"),
        confidence=0.85,
        supported_types=(content_type,),
    )
    vector = DummyVectorAdapter()
    pipeline = DocumentPipeline(parser=parser, llm=llm, vector_store=vector)

    try:
        result = await pipeline.run(document_id, file_data, filename, user_id)

        factory = build_session_factory(settings.database_url)
        async with factory() as session:
            doc = await session.get(Document, _uuid.UUID(document_id))
            if doc:
                doc.parse_status = result.get("status", "failed")
                doc.document_type = result.get("document_type")
                doc.document_type_confidence = result.get("document_type_confidence")
                doc.extracted_metadata = result.get("extracted_fields", {})
                await session.commit()

            triage = TriageGraph(llm=llm)
            event = {
                "event_type": "DOCUMENT_UPLOADED",
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                "payload": result.get("extracted_fields", {}),
            }
            inbox_item = await triage.run(event)

            inbox = AgentInbox(
                user_id=_uuid.UUID(user_id),
                event_type=inbox_item["event_type"],
                event_source=inbox_item["event_source"],
                source_ref_id=_uuid.UUID(document_id),
                agent_analysis=inbox_item["agent_analysis"],
                urgency=inbox_item["urgency"],
                suggested_actions=inbox_item["suggested_actions"],
                status="pending",
            )
            session.add(inbox)
            await session.commit()

        logger.info("pipeline_complete", document_id=document_id, status=result["status"])
    except Exception as e:
        logger.error("pipeline_background_error", document_id=document_id, error=str(e))
