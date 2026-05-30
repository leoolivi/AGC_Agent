"""Phase 2 workflow templates — registered at import time."""
from __future__ import annotations

from app.agent.workflows.registry import WorkflowStep, WorkflowTemplate, WorkflowTemplateRegistry


def build_registry() -> WorkflowTemplateRegistry:
    """Build registry with Phase 2 + Phase 3 templates."""
    registry = WorkflowTemplateRegistry()

    # Phase 2 templates
    registry.register(WorkflowTemplate(
        workflow_id="draft_payment_reminder",
        name="Sollecito pagamento",
        description="Cerca documenti correlati e prepara bozza email di sollecito",
        required_args=["document_id"],
        optional_args=["recipient_email"],
        steps=[
            WorkflowStep(tool="search_documents", risk=1, args_mapping={"query": "document_id"}),
            WorkflowStep(tool="draft_email", risk=3, args_mapping={"context": "search_result"}),
        ],
        applicable_to=["DOCUMENT_UPLOADED", "DEADLINE_OVERDUE"],
    ))

    registry.register(WorkflowTemplate(
        workflow_id="process_document",
        name="Processa documento",
        description="Classifica, estrai campi e crea scadenza dal documento",
        required_args=["document_id"],
        steps=[
            WorkflowStep(tool="read_document", risk=0, args_mapping={"id": "document_id"}),
            WorkflowStep(tool="classify_document", risk=1, args_mapping={"doc": "read_result"}),
            WorkflowStep(tool="create_deadline", risk=2, args_mapping={"fields": "classify_result"}),
        ],
        applicable_to=["DOCUMENT_UPLOADED"],
    ))

    registry.register(WorkflowTemplate(
        workflow_id="create_deadline_from_document",
        name="Crea scadenza da documento",
        description="Cerca documenti e crea una scadenza basata sui dati estratti",
        required_args=["document_id"],
        optional_args=["title", "due_date"],
        steps=[
            WorkflowStep(tool="search_documents", risk=1, args_mapping={"query": "document_id"}),
            WorkflowStep(tool="create_deadline", risk=2, args_mapping={"data": "search_result"}),
        ],
        applicable_to=["DOCUMENT_UPLOADED"],
    ))

    # Phase 3 templates
    registry.register(WorkflowTemplate(
        workflow_id="reply_to_email",
        name="Rispondi a email",
        description="Cerca documenti correlati e prepara bozza di risposta email con contesto",
        required_args=["document_id"],
        optional_args=["recipient_email", "subject"],
        steps=[
            WorkflowStep(tool="search_documents", risk=1, args_mapping={"query": "document_id"}),
            WorkflowStep(tool="draft_email", risk=3, args_mapping={"context": "search_result", "type": "reply"}),
        ],
        applicable_to=["EMAIL_RECEIVED"],
    ))

    registry.register(WorkflowTemplate(
        workflow_id="generate_payment_status_report",
        name="Report stato pagamenti",
        description="Genera un riepilogo dello stato pagamenti con scadenze e documenti correlati",
        required_args=[],
        optional_args=["period"],
        steps=[
            WorkflowStep(tool="search_documents", risk=1, args_mapping={"query": "fattura"}),
            WorkflowStep(tool="search_documents", risk=1, args_mapping={"query": "deadlines"}),
            WorkflowStep(tool="draft_email", risk=2, args_mapping={"context": "combined", "type": "report"}),
        ],
        applicable_to=["MANUAL_TRIGGER"],
    ))

    registry.register(WorkflowTemplate(
        workflow_id="batch_send_reminders",
        name="Invio solleciti multipli",
        description="Genera solleciti per tutte le fatture scadute e crea bozze email in batch",
        required_args=[],
        optional_args=["days_overdue_min"],
        steps=[
            WorkflowStep(tool="search_documents", risk=1, args_mapping={"query": "overdue"}),
            WorkflowStep(tool="batch_send_reminders", risk=5, args_mapping={"documents": "search_result"}),
        ],
        applicable_to=["DEADLINE_OVERDUE", "MANUAL_TRIGGER"],
    ))

    return registry
