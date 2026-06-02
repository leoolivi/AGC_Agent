"""Gmail monitor adapter implementing SourceMonitorPort."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import structlog
from googleapiclient.discovery import build

from app.adapters.google.credentials import get_credentials
from app.core.domain.source import ChangeSet, FileChange, GmailSourceConfig, SourceConfig

logger = structlog.get_logger()


class GmailMonitorAdapter:
    """Poll Gmail for new messages with attachments using the history API."""

    async def list_changes(
        self,
        source_config: SourceConfig,
        sync_token: str | None,
    ) -> ChangeSet:
        if not isinstance(source_config.config, GmailSourceConfig):
            msg = "Expected GmailSourceConfig"
            raise ValueError(msg)

        gmail_config = source_config.config
        user_id = str(source_config.user_id)

        try:
            creds = await get_credentials(user_id)
            service = build("gmail", "v1", credentials=creds)

            if sync_token:
                return await self._list_history(service, sync_token, gmail_config.label_ids)

            return await self._initial_sync(service, gmail_config.label_ids)

        except Exception as e:
            logger.error("gmail_list_changes_failed", error=str(e))
            raise RuntimeError(f"Gmail API failed: {e}") from e

    async def _initial_sync(self, service: object, label_ids: list[str]) -> ChangeSet:
        gmail = service  # type: ignore[attr-defined]
        label_query = " OR ".join(f"label:{lid}" for lid in label_ids) if label_ids else "is:inbox"
        result = gmail.users().messages().list(
            userId="me", q=label_query, maxResults=50
        ).execute()

        changes: list[FileChange] = []
        for msg_ref in result.get("messages", []):
            changes.extend(await self._extract_attachments(gmail, msg_ref["id"]))

        profile = gmail.users().getProfile(userId="me").execute()
        history_id = str(profile.get("historyId", ""))

        return ChangeSet(new_files=changes, new_sync_token=history_id)

    async def _list_history(
        self,
        service: object,
        sync_token: str,
        label_ids: list[str],
    ) -> ChangeSet:
        gmail = service  # type: ignore[attr-defined]
        changes: list[FileChange] = []
        new_token = sync_token

        try:
            result = gmail.users().history().list(
                userId="me",
                startHistoryId=sync_token,
                historyTypes=["messageAdded"],
                labelId=label_ids[0] if label_ids else None,
            ).execute()

            for record in result.get("history", []):
                for added in record.get("messagesAdded", []):
                    msg_id = added["message"]["id"]
                    changes.extend(await self._extract_attachments(gmail, msg_id))

            new_token = str(result.get("historyId", sync_token))

        except Exception as e:
            if "404" in str(e) or "historyId" in str(e).lower():
                logger.warning("gmail_history_expired", error=str(e))
                return await self._initial_sync(service, label_ids)
            raise

        return ChangeSet(new_files=changes, new_sync_token=new_token)

    async def _extract_attachments(self, gmail: object, message_id: str) -> list[FileChange]:
        msg = gmail.users().messages().get(  # type: ignore[attr-defined]
            userId="me", id=message_id, format="full"
        ).execute()

        changes: list[FileChange] = []
        internal_date = int(msg.get("internalDate", 0))
        modified_at = datetime.fromtimestamp(internal_date / 1000, tz=UTC)

        for part in msg.get("payload", {}).get("parts", []):
            filename = part.get("filename", "")
            mime = part.get("mimeType", "")
            if filename and part.get("body", {}).get("attachmentId"):
                attachment_id = part["body"]["attachmentId"]
                file_ref = f"{message_id}:{attachment_id}"
                changes.append(
                    FileChange(
                        file_id=file_ref,
                        filename=filename,
                        mime_type=mime,
                        modified_at=modified_at,
                    )
                )

        return changes

    async def download_file(
        self,
        source_type: Literal["drive", "gmail", "calendar"],
        file_ref: str,
    ) -> bytes:
        if source_type != "gmail":
            msg = f"GmailMonitorAdapter only supports gmail, got {source_type}"
            raise ValueError(msg)

        parts = file_ref.split(":", 1)
        if len(parts) != 2:
            msg = f"Invalid Gmail file_ref format: {file_ref}"
            raise ValueError(msg)

        message_id, attachment_id = parts
        creds = await get_credentials("")
        service = build("gmail", "v1", credentials=creds)

        attachment = service.users().messages().attachments().get(
            userId="me", messageId=message_id, id=attachment_id
        ).execute()

        import base64

        data = attachment.get("data", "")
        return base64.urlsafe_b64decode(data)
