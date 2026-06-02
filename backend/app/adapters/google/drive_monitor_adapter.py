"""Google Drive monitor adapter implementing SourceMonitorPort."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import structlog
from googleapiclient.discovery import build

from app.adapters.google.credentials import get_credentials
from app.core.domain.source import ChangeSet, DriveSourceConfig, FileChange, SourceConfig

logger = structlog.get_logger()

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
}


class GoogleDriveMonitorAdapter:
    """Poll Google Drive for changes using the changes API with sync tokens."""

    async def list_changes(
        self,
        source_config: SourceConfig,
        sync_token: str | None,
    ) -> ChangeSet:
        if not isinstance(source_config.config, DriveSourceConfig):
            msg = "Expected DriveSourceConfig"
            raise ValueError(msg)

        drive_config = source_config.config
        user_id = str(source_config.user_id)

        try:
            creds = await get_credentials(user_id)
            service = build("drive", "v3", credentials=creds)

            if sync_token:
                return await self._list_changes_with_token(service, sync_token)

            return await self._initial_sync(service, drive_config.folder_id)

        except Exception as e:
            logger.error("drive_list_changes_failed", error=str(e))
            raise RuntimeError(f"Drive API failed: {e}") from e

    async def _initial_sync(self, service: object, folder_id: str) -> ChangeSet:
        drive = service  # type: ignore[attr-defined]
        q = f"'{folder_id}' in parents and trashed = false"
        result = drive.files().list(
            q=q,
            pageSize=100,
            fields="files(id, name, mimeType, modifiedTime), nextPageToken",
        ).execute()

        files = result.get("files", [])
        changes = self._filter_files(files)

        start_token = drive.changes().getStartPageToken().execute()
        new_token = start_token.get("startPageToken")

        return ChangeSet(new_files=changes, new_sync_token=new_token)

    async def _list_changes_with_token(self, service: object, sync_token: str) -> ChangeSet:
        drive = service  # type: ignore[attr-defined]
        changes: list[FileChange] = []
        page_token = sync_token
        new_token: str | None = None

        while page_token:
            result = drive.changes().list(
                pageToken=page_token,
                fields="nextPageToken, newStartPageToken, changes(fileId, removed, file(id, name, mimeType, modifiedTime))",
                pageSize=100,
            ).execute()

            for change in result.get("changes", []):
                if change.get("removed"):
                    continue
                file_data = change.get("file")
                if file_data and file_data.get("mimeType") in SUPPORTED_MIME_TYPES:
                    changes.append(self._to_file_change(file_data))

            if "newStartPageToken" in result:
                new_token = result["newStartPageToken"]
                break
            page_token = result.get("nextPageToken")

        return ChangeSet(new_files=changes, new_sync_token=new_token or sync_token)

    async def download_file(
        self,
        source_type: Literal["drive", "gmail", "calendar"],
        file_ref: str,
    ) -> bytes:
        if source_type != "drive":
            msg = f"GoogleDriveMonitorAdapter only supports drive, got {source_type}"
            raise ValueError(msg)

        from app.adapters.google.drive_adapter import GoogleDriveAdapter

        adapter = GoogleDriveAdapter()
        data, _, _ = await adapter.download_file("", file_ref)
        return data

    def _filter_files(self, files: list[dict]) -> list[FileChange]:
        return [
            self._to_file_change(f)
            for f in files
            if f.get("mimeType") in SUPPORTED_MIME_TYPES
        ]

    def _to_file_change(self, file_data: dict) -> FileChange:
        modified = file_data.get("modifiedTime", "")
        try:
            modified_at = datetime.fromisoformat(modified.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            modified_at = datetime.now(UTC)

        return FileChange(
            file_id=file_data["id"],
            filename=file_data.get("name", "unknown"),
            mime_type=file_data.get("mimeType", "application/octet-stream"),
            modified_at=modified_at,
        )
