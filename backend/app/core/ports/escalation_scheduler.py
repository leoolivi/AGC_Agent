"""
EscalationSchedulerPort — Protocol for scheduling escalation step transitions.

Implementations: APSchedulerEscalationAdapter (app/adapters/scheduler/).
Wiring: app/api/deps.py.

This port abstracts the scheduling mechanism for delayed escalation step execution.
Each escalation sequence is modeled as a state machine, and this port handles
scheduling the transition to the next step after a configurable delay.

Requirements: 9, 10
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EscalationSchedulerPort(Protocol):
    """Port for scheduling delayed escalation step transitions."""

    async def schedule_step(
        self,
        escalation_id: str,
        delay_seconds: int,
    ) -> str:
        """
        Schedule an escalation step to execute after the specified delay.

        Args:
            escalation_id: UUID of the escalation execution record
            delay_seconds: Time to wait before triggering the next step (1 hour to 7 days)

        Returns:
            job_id: Unique identifier for the scheduled job (used for cancellation)

        Raises:
            ValueError: If delay_seconds is out of valid range (3600–604800)
        """
        ...

    async def cancel_step(self, job_id: str) -> None:
        """
        Cancel a previously scheduled escalation step.

        Called when:
        - User takes action on the deadline (escalation resolved)
        - Escalation rule is deleted or deactivated
        - Manual cancellation by admin

        Args:
            job_id: The job identifier returned by schedule_step()

        Raises:
            ValueError: If job_id does not exist or job already executed
        """
        ...
