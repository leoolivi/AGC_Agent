"""Google Drive adapter — import files and poll for changes."""
from __future__ import annotations

import io

import structlog
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.adapters.google.credentials import get_credentials

logger = structlog.get_logger()


class GoogleDriveAdapter:
    """Import files from Google Drive."""

    async def list_files(
        self, 
        user_id: str, 
        folder_id: str = "", 
        query: str = "", 
        mime_type: str = "",
        max_results: int = 20
    ) -> list[dict]:
        try:
            creds = await get_credentials(user_id)
            service = build("drive", "v3", credentials=creds)

            q_parts: list[str] = ["trashed = false"]
            if folder_id:
                q_parts.append(f"'{folder_id}' in parents")
            if query:
                q_parts.append(f"name contains '{query}'")
            if mime_type:
                q_parts.append(f"mimeType = '{mime_type}'")
            
            q = " and ".join(q_parts)

            result = service.files().list(
                q=q, pageSize=max_results,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            return result.get("files", [])
        except Exception as e:
            logger.error("drive_list_failed", error=str(e), q=q if 'q' in locals() else None)
            return []

    async def download_file(self, user_id: str, file_id: str) -> tuple[bytes, str, str]:
        """Download file content. Returns (data, filename, mime_type)."""
        creds = await get_credentials(user_id)
        service = build("drive", "v3", credentials=creds)

        # Get file metadata
        meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        name = meta["name"]
        mime = meta["mimeType"]

        # Google Docs → export as PDF; others → direct download
        buf = io.BytesIO()
        if mime.startswith("application/vnd.google-apps."):
            export_mime = "application/pdf"
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            name = f"{name}.pdf"
            mime = export_mime
        else:
            request = service.files().get_media(fileId=file_id)

        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        logger.info("drive_file_downloaded", file_id=file_id, name=name, size=buf.tell())
        return buf.getvalue(), name, mime

    async def import_to_acg(self, user_id: str, file_id: str) -> dict:
        """Download from Drive and save to ACG storage + trigger pipeline."""
        from app.api.deps import get_storage

        data, filename, mime = await self.download_file(user_id, file_id)
        storage = get_storage()
        meta = await storage.save(io.BytesIO(data), filename, user_id, mime)

        return {
            "file_id": meta.file_id,
            "filename": filename,
            "content_type": mime,
            "size_bytes": len(data),
        }

    async def get_changes(self, user_id: str, page_token: str | None = None) -> tuple[list[dict], str]:
        """Get changes since last sync. Returns (changed_files, new_page_token)."""
        try:
            creds = await get_credentials(user_id)
            service = build("drive", "v3", credentials=creds)

            if not page_token:
                resp = service.changes().getStartPageToken().execute()
                return [], resp["startPageToken"]

            result = service.changes().list(
                pageToken=page_token, spaces="drive",
                fields="nextPageToken, newStartPageToken, changes(fileId, file(name, mimeType, trashed))"
            ).execute()

            changes = [
                {"file_id": c["fileId"], "name": c["file"]["name"], "mime": c["file"]["mimeType"]}
                for c in result.get("changes", [])
                if c.get("file") and not c["file"].get("trashed")
            ]
            new_token = result.get("newStartPageToken", result.get("nextPageToken", page_token))
            return changes, new_token
        except Exception as e:
            logger.error("drive_changes_failed", error=str(e))
            return [], page_token or ""
