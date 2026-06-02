"""CalendarIngestService — processes calendar events and proposes deadline creation.

This service coordinates:
1. Calendar event relevance classification (confidence threshold 0.70)
2. AgentInboxItem creation for relevant events
3. Duplicate detection via calendar_event_id
4. Update proposal for modified events via HITL

Requirements: 3
Properties: 7, 8, 9
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.inbox import AgentInboxItem
from app.db.models import AgentInbox, Deadline

logger = structlog.get_logger()

# Confidence threshold for calendar event relevance (Requirement 3.2, Property 7)
RELEVANCE_CONFIDENCE_THRESHOLD = 0.70


class CalendarEvent(dict[str, Any]):
    """Type alias for calendar event metadata from source monitor."""

    pass


class CalendarRelevanceResult(dict[str, Any]):
    """Type alias for calendar relevance classification result.

    Expected fields:
    - is_relevant: bool
    - confidence: float
    - suggested_category: str
    - suggested_title: str
    - reasoning: str (optional)
    """

    pass


class CalendarIngestService:
    """Service for processing calendar events and proposing deadline creation.

    This service acts as the bridge between calendar monitoring and deadline
    management. It handles:
    - Relevance classification of calendar events
    - AgentInboxItem creation for relevant events
    - Duplicate detection via calendar_event_id
    - Update proposals for modified events

    The service enforces a confidence threshold (0.70) and only creates inbox
    items for events that are likely to be administratively relevant.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """Initialize the calendar ingest service.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self._session = session

    async def process_calendar_event(
        self,
        event: CalendarEvent,
        user_id: uuid.UUID,
        relevance_result: CalendarRelevanceResult,
    ) -> AgentInboxItem | None:
        """Process a calendar event and create an inbox item if relevant.

        This method orchestrates the complete calendar event processing flow:
        1. Check relevance confidence threshold (>= 0.70)
        2. Check for existing deadline with same calendar_event_id
        3. If exists and modified, propose update via HITL
        4. If new and relevant, create AgentInboxItem with import suggestion

        Args:
            event: Calendar event metadata (title, description, date, participants, event_id)
            user_id: User who owns the monitored calendar
            relevance_result: Result from CalendarRelevanceGraph classification

        Returns:
            AgentInboxItem domain model if created, None if skipped or low confidence

        Raises:
            ValueError: If event is missing required fields
        """
        # Validate required event fields
        event_id = event.get("event_id")
        if not event_id:
            msg = "Calendar event missing required field: event_id"
            raise ValueError(msg)

        # Step 1: Check relevance confidence (Property 7, Requirement 3.2, 3.4)
        is_relevant = relevance_result.get("is_relevant", False)
        confidence = relevance_result.get("confidence", 0.0)

        if not is_relevant or confidence < RELEVANCE_CONFIDENCE_THRESHOLD:
            event_title = event.get("title", "Untitled Event")
            logger.debug(
                "calendar_event_not_relevant",
                event_id=event_id,
                event_title=event_title,
                confidence=confidence,
                threshold=RELEVANCE_CONFIDENCE_THRESHOLD,
            )
            return None

        # Step 2: Check for existing deadline with this calendar_event_id
        # (Property 9, Requirement 3.5)
        existing_deadline = await self._find_deadline_by_calendar_event_id(
            calendar_event_id=event_id,
            user_id=user_id,
        )

        if existing_deadline:
            # Check if event has been modified
            event_modified = self._has_event_changed(existing_deadline, event)

            if event_modified:
                # Propose update via HITL (Requirement 3.5)
                return await self._create_update_proposal_inbox_item(
                    existing_deadline=existing_deadline,
                    updated_event=event,
                    relevance_result=relevance_result,
                    user_id=user_id,
                )
            else:
                # Event unchanged, no action needed
                logger.debug(
                    "calendar_event_unchanged",
                    event_id=event_id,
                    deadline_id=str(existing_deadline.id),
                )
                return None

        # Step 3: Create AgentInboxItem for new relevant event (Requirement 3.2, 3.3)
        return await self._create_import_proposal_inbox_item(
            event=event,
            relevance_result=relevance_result,
            user_id=user_id,
        )

    async def _find_deadline_by_calendar_event_id(
        self,
        calendar_event_id: str,
        user_id: uuid.UUID,
    ) -> Deadline | None:
        """Find an existing deadline linked to a calendar event.

        Args:
            calendar_event_id: Google Calendar event ID
            user_id: User ID for authorization

        Returns:
            Deadline ORM model if found, None otherwise
        """
        result = await self._session.execute(
            select(Deadline)
            .where(Deadline.calendar_event_id == calendar_event_id)
            .where(Deadline.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _has_event_changed(self, deadline: Deadline, event: CalendarEvent) -> bool:
        """Check if a calendar event has been modified since deadline creation.

        Compares key fields: title, date, description.

        Args:
            deadline: Existing deadline record
            event: Updated calendar event metadata

        Returns:
            True if event has changed, False otherwise
        """
        # Compare title
        if deadline.title != event.get("title", ""):
            return True

        # Compare date
        event_date = event.get("date")
        if event_date and deadline.due_date != event_date:
            return True

        # Compare description (stored in deadline.description)
        event_description = event.get("description", "")
        return deadline.description != event_description

    async def _create_import_proposal_inbox_item(
        self,
        event: CalendarEvent,
        relevance_result: CalendarRelevanceResult,
        user_id: uuid.UUID,
    ) -> AgentInboxItem:
        """Create an AgentInboxItem proposing to import a calendar event as a deadline.

        This creates an inbox item with HITL approval required before creating
        the deadline (Property 8, Requirement 3.3).

        Args:
            event: Calendar event metadata
            relevance_result: Classification result with suggested fields
            user_id: User ID

        Returns:
            Created AgentInboxItem domain model
        """
        event_id = event["event_id"]
        event_title = event.get("title", "Untitled Event")
        event_date = event.get("date")
        event_description = event.get("description", "")
        event_participants = event.get("participants", [])
        calendar_name = event.get("calendar_name", "Google Calendar")

        suggested_title = relevance_result.get("suggested_title", event_title)
        suggested_category = relevance_result.get("suggested_category", "generico")
        confidence = relevance_result.get("confidence", 0.0)
        reasoning = relevance_result.get("reasoning", "")

        # Build agent analysis text
        analysis_parts = [
            f"Ho rilevato un evento rilevante nel calendario '{calendar_name}':",
            f"**{event_title}**",
        ]

        if event_date:
            analysis_parts.append(f"Data: {event_date}")

        if event_participants:
            participants_str = ", ".join(event_participants[:3])
            if len(event_participants) > 3:
                participants_str += f" (+{len(event_participants) - 3} altri)"
            analysis_parts.append(f"Partecipanti: {participants_str}")

        if reasoning:
            analysis_parts.append(f"\n{reasoning}")

        analysis_parts.append(
            f"\nConfidenza: {confidence:.0%} | Categoria suggerita: {suggested_category}"
        )

        agent_analysis = "\n".join(analysis_parts)

        # Build suggested actions with pre-filled deadline data
        suggested_actions = [
            {
                "id": "import_as_deadline",
                "label": "Importa come scadenza",
                "verb": "import",
                "risk_level": 1,  # Internal write only
                "preview_data": {
                    "title": suggested_title,
                    "due_date": str(event_date) if event_date else None,
                    "deadline_type": suggested_category,
                    "description": event_description,
                    "source": "calendar",
                    "source_ref_id": event_id,
                    "calendar_event_id": event_id,
                },
                "source_attribution": {
                    "calendar_name": calendar_name,
                    "event_id": event_id,
                    "event_link": event.get("event_link"),
                },
            },
            {
                "id": "dismiss",
                "label": "Ignora",
                "verb": "dismiss",
                "risk_level": 0,
            },
        ]

        # Create inbox item
        inbox_item = AgentInbox(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type="calendar_event_detected",
            event_source={
                "type": "calendar",
                "calendar_event_id": event_id,
                "calendar_name": calendar_name,
                "event_title": event_title,
                "event_date": str(event_date) if event_date else None,
            },
            source_ref_id=None,  # No document reference for calendar events
            agent_analysis=agent_analysis,
            urgency="this_week",  # Calendar events are typically not urgent
            suggested_actions=suggested_actions,
            status="pending",
        )

        self._session.add(inbox_item)
        await self._session.commit()
        await self._session.refresh(inbox_item)

        logger.info(
            "calendar_import_proposal_created",
            inbox_item_id=str(inbox_item.id),
            event_id=event_id,
            event_title=event_title,
            confidence=confidence,
        )

        # Convert to domain model
        return self._to_domain(inbox_item)

    async def _create_update_proposal_inbox_item(
        self,
        existing_deadline: Deadline,
        updated_event: CalendarEvent,
        relevance_result: CalendarRelevanceResult,
        user_id: uuid.UUID,
    ) -> AgentInboxItem:
        """Create an AgentInboxItem proposing to update an existing deadline.

        This creates an inbox item with HITL approval required before updating
        the deadline (Requirement 3.5).

        Args:
            existing_deadline: Existing deadline record
            updated_event: Updated calendar event metadata
            relevance_result: Classification result
            user_id: User ID

        Returns:
            Created AgentInboxItem domain model
        """
        event_id = updated_event["event_id"]
        event_title = updated_event.get("title", "Untitled Event")
        event_date = updated_event.get("date")
        event_description = updated_event.get("description", "")
        calendar_name = updated_event.get("calendar_name", "Google Calendar")

        # Build agent analysis showing what changed
        changes = []
        if existing_deadline.title != event_title:
            changes.append(f"- Titolo: '{existing_deadline.title}' → '{event_title}'")
        if event_date and existing_deadline.due_date != event_date:
            changes.append(f"- Data: {existing_deadline.due_date} → {event_date}")
        if existing_deadline.description != event_description:
            changes.append("- Descrizione modificata")

        changes_text = "\n".join(changes) if changes else "Modifiche rilevate"

        agent_analysis = (
            f"L'evento '{event_title}' nel calendario '{calendar_name}' è stato modificato.\n\n"
            f"**Modifiche rilevate:**\n{changes_text}\n\n"
            f"Vuoi aggiornare la scadenza collegata?"
        )

        # Build suggested actions
        suggested_actions = [
            {
                "id": "update_deadline",
                "label": "Aggiorna scadenza",
                "verb": "update",
                "risk_level": 1,  # Internal write only
                "preview_data": {
                    "deadline_id": str(existing_deadline.id),
                    "title": event_title,
                    "due_date": str(event_date) if event_date else None,
                    "description": event_description,
                },
                "source_attribution": {
                    "calendar_name": calendar_name,
                    "event_id": event_id,
                    "event_link": updated_event.get("event_link"),
                },
            },
            {
                "id": "keep_current",
                "label": "Mantieni scadenza attuale",
                "verb": "dismiss",
                "risk_level": 0,
            },
        ]

        # Create inbox item
        inbox_item = AgentInbox(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type="calendar_event_modified",
            event_source={
                "type": "calendar",
                "calendar_event_id": event_id,
                "calendar_name": calendar_name,
                "event_title": event_title,
                "event_date": str(event_date) if event_date else None,
                "existing_deadline_id": str(existing_deadline.id),
            },
            source_ref_id=existing_deadline.id,  # Reference to existing deadline
            agent_analysis=agent_analysis,
            urgency="this_week",
            suggested_actions=suggested_actions,
            status="pending",
        )

        self._session.add(inbox_item)
        await self._session.commit()
        await self._session.refresh(inbox_item)

        logger.info(
            "calendar_update_proposal_created",
            inbox_item_id=str(inbox_item.id),
            event_id=event_id,
            deadline_id=str(existing_deadline.id),
            event_title=event_title,
        )

        # Convert to domain model
        return self._to_domain(inbox_item)

    def _to_domain(self, inbox_item: AgentInbox) -> AgentInboxItem:
        """Convert ORM model to domain model.

        Args:
            inbox_item: SQLAlchemy ORM model

        Returns:
            AgentInboxItem domain model
        """
        return AgentInboxItem(
            id=inbox_item.id,
            user_id=inbox_item.user_id,
            event_type=inbox_item.event_type,
            event_source=inbox_item.event_source,
            source_ref_id=inbox_item.source_ref_id,
            agent_analysis=inbox_item.agent_analysis,
            urgency=inbox_item.urgency,
            suggested_actions=inbox_item.suggested_actions,
            status=inbox_item.status,
            chosen_action_id=inbox_item.chosen_action_id,
            chosen_at=inbox_item.chosen_at,
            created_at=inbox_item.created_at,
            expires_at=inbox_item.expires_at,
        )
