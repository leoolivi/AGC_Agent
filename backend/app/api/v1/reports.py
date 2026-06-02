"""Reports API — generation, export, templates, history."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_report_renderer
from app.core.domain.report import ReportFilters, ReportRequest
from app.core.services.confirmation_flow_service import ConfirmationFlowService
from app.core.services.report_generator_service import ReportGeneratorService

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    template_name: str
    date_from: date
    date_to: date
    format: Literal["pdf", "excel"] = "pdf"
    deadline_types: list[str] | None = None
    statuses: list[str] | None = None


class ExportReportRequest(BaseModel):
    destination_type: Literal["drive", "email"]
    folder_id: str | None = None
    recipient: str | None = None
    subject: str | None = None


@router.get("/templates")
async def list_templates(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, str]]:
    service = ReportGeneratorService(db, get_report_renderer())
    return service.list_templates()


@router.get("/history")
async def report_history(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    service = ReportGeneratorService(db, get_report_renderer())
    reports = await service.get_report_history(uuid.UUID(user["sub"]))
    return [
        {
            "id": str(r.id),
            "template_name": r.template_name,
            "format": r.format,
            "parameters": r.parameters,
            "export_destination": r.export_destination,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def generate_report(
    body: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = ReportGeneratorService(db, get_report_renderer())
    request = ReportRequest(
        user_id=uuid.UUID(user["sub"]),
        template_name=body.template_name,
        date_from=body.date_from,
        date_to=body.date_to,
        filters=ReportFilters(deadline_types=body.deadline_types, statuses=body.statuses),
        format=body.format,
    )
    try:
        report, content = await service.generate_report(request)
        data = await service.assemble_data(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    import base64
    return {
        "id": str(report.id),
        "template_name": report.template_name,
        "format": report.format,
        "row_count": len(data.rows),
        "preview_rows": [r.model_dump(mode="json") for r in data.rows[:20]],
        "content_base64": base64.b64encode(content).decode(),
    }


@router.post("/{report_id}/export")
async def export_report(
    report_id: str,
    body: ExportReportRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = ReportGeneratorService(db, get_report_renderer())
    report = await service.get_report(uuid.UUID(report_id), uuid.UUID(user["sub"]))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    conf_service = ConfirmationFlowService(db)
    action_type = "export_drive" if body.destination_type == "drive" else "export_email"
    preview = {
        "report_id": report_id,
        "template_name": report.template_name,
        "destination_type": body.destination_type,
        "folder_id": body.folder_id,
        "recipient": body.recipient,
        "subject": body.subject,
    }
    confirmation = await conf_service.create_confirmation(
        user_id=uuid.UUID(user["sub"]),
        action_type=action_type,
        description=f"Conferma export report {report.template_name}",
        preview=preview,
        source_attribution={"report_id": report_id, "template": report.template_name},
    )

    return {
        "status": "pending_confirmation",
        "confirmation_id": str(confirmation.id),
        "report_id": report_id,
    }
