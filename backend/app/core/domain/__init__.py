"""Core domain entities and value objects (Pydantic v2 models)."""
from app.core.domain.audit_entry import AuditEntry
from app.core.domain.correlation import (
    DocumentCorrelation,
    Dossier,
    DossierDocument,
    MissingItem,
)
from app.core.domain.deadline import Deadline
from app.core.domain.document import Document
from app.core.domain.email_draft import EmailDraft
from app.core.domain.inbox import AgentEvent, AgentInboxItem
from app.core.domain.notification import Notification
from app.core.domain.pending_confirmation import PendingConfirmation
from app.core.domain.realtime import RealtimeEvent
from app.core.domain.source import (
    CalendarSourceConfig,
    ChangeSet,
    DriveSourceConfig,
    FileChange,
    GmailSourceConfig,
    SourceConfig,
)
from app.core.domain.task import AgentTask
from app.core.domain.trust import UserExtractionTrust

__all__ = [
    "AgentEvent",
    "AgentInboxItem",
    "AgentTask",
    "AuditEntry",
    "CalendarSourceConfig",
    "ChangeSet",
    "Deadline",
    "Document",
    "DocumentCorrelation",
    "Dossier",
    "DossierDocument",
    "DriveSourceConfig",
    "EmailDraft",
    "FileChange",
    "GmailSourceConfig",
    "MissingItem",
    "Notification",
    "PendingConfirmation",
    "RealtimeEvent",
    "SourceConfig",
    "UserExtractionTrust",
]
