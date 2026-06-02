"""Escalation domain models for notification escalation rules and execution."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


class EscalationStep(BaseModel):
    """A single step in an escalation sequence.

    Each step defines when to fire (delay_seconds from escalation start),
    which channel to use, who to notify, and what message to send.
    """

    delay_seconds: int  # time to wait before this step fires
    channel: Literal["in_app", "email", "calendar"]
    recipient: str  # user_id, email address, or calendar_id
    message_template: str

    @field_validator("delay_seconds")
    @classmethod
    def validate_delay_seconds(cls, v: int) -> int:
        """Delay must be at least 1 hour and at most 7 days."""
        if v < 3600:
            msg = "delay_seconds must be >= 3600 (1 hour)"
            raise ValueError(msg)
        if v > 604800:
            msg = "delay_seconds must be <= 604800 (7 days)"
            raise ValueError(msg)
        return v

    @field_validator("recipient")
    @classmethod
    def validate_recipient_not_empty(cls, v: str) -> str:
        """Recipient must be a non-empty string."""
        if not v.strip():
            msg = "recipient must not be empty"
            raise ValueError(msg)
        return v

    @field_validator("message_template")
    @classmethod
    def validate_message_template_not_empty(cls, v: str) -> str:
        """Message template must be a non-empty string."""
        if not v.strip():
            msg = "message_template must not be empty"
            raise ValueError(msg)
        return v


class EscalationRule(BaseModel):
    """An escalation rule defining a notification sequence for a deadline type.

    Rules contain up to 5 steps with strictly increasing delays. Each step
    specifies a channel (in_app, email, calendar) and recipient. The rule
    is activated when a deadline of the matching type times out without
    user action.
    """

    id: UUID
    user_id: UUID
    name: str
    deadline_type: Literal["fiscale", "contrattuale", "pagamento", "generico"]
    steps: list[EscalationStep]
    is_active: bool = True

    @field_validator("steps")
    @classmethod
    def validate_max_steps(cls, v: list[EscalationStep]) -> list[EscalationStep]:
        """Escalation rule must have at most 5 steps and at least 1."""
        if len(v) == 0:
            msg = "Escalation rule must have at least 1 step"
            raise ValueError(msg)
        if len(v) > 5:
            msg = "Escalation rule must have at most 5 steps"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_increasing_delays(self) -> EscalationRule:
        """Steps must have strictly increasing delay_seconds values."""
        for i in range(1, len(self.steps)):
            if self.steps[i].delay_seconds <= self.steps[i - 1].delay_seconds:
                msg = "Steps must have strictly increasing delay_seconds"
                raise ValueError(msg)
        return self


class EscalationHistoryEntry(BaseModel):
    """A record of a single escalation step execution.

    Tracks which step was executed, when, via which channel, and the result.
    """

    step: int
    timestamp: datetime
    channel: str
    result: Literal["sent", "pending_hitl", "failed", "skipped"]


class EscalationExecution(BaseModel):
    """The runtime state of an escalation sequence for a specific deadline.

    Models the escalation state machine with states:
    - active: escalation is in progress, steps are being executed
    - resolved: user acted on the deadline, escalation stopped
    - exhausted: all steps have been executed without resolution
    - cancelled: escalation was manually cancelled
    """

    id: UUID
    deadline_id: UUID
    rule_id: UUID
    current_step: int = 0
    status: Literal["active", "resolved", "exhausted", "cancelled"] = "active"
    history: list[EscalationHistoryEntry] = []
