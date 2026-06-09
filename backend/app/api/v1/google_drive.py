"""Google Drive API — list folders and files."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.adapters.google.drive_adapter import GoogleDriveAdapter

router = APIRouter(prefix="/google/drive", tags=["google-drive"])

@router.get("/folders")
async def list_drive_folders(
    parent_id: str = "root",
    user: dict = Depends(get_current_user)
):
    """List folders in a specific Google Drive folder."""
    adapter = GoogleDriveAdapter()
    # Use the refactored mime_type filtering
    files = await adapter.list_files(
        user["sub"], 
        folder_id=parent_id, 
        mime_type="application/vnd.google-apps.folder", 
        max_results=50
    )
    return files

@router.get("/files")
async def list_drive_files(
    folder_id: str,
    user: dict = Depends(get_current_user)
):
    """List all files in a specific Google Drive folder."""
    adapter = GoogleDriveAdapter()
    files = await adapter.list_files(user["sub"], folder_id=folder_id, max_results=50)
    return files
