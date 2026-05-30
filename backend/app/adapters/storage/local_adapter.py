"""LocalStorageAdapter — file storage on local filesystem."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

from app.adapters.storage.utils import build_storage_key
from app.core.ports.storage import FileMetadata, FileStoragePort


class LocalStorageAdapter(FileStoragePort):
    def __init__(self, base_path: str = "./data/files") -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    async def save(
        self, file: BinaryIO, filename: str, user_id: str, content_type: str
    ) -> FileMetadata:
        file_id = str(uuid.uuid4())
        storage_key = build_storage_key(user_id, file_id, filename)
        dest = self._base / storage_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = file.read()
        dest.write_bytes(data)
        return FileMetadata(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            storage_key=storage_key,
            user_id=user_id,
        )

    async def get(self, file_id: str) -> bytes:
        for p in self._base.rglob(f"{file_id}_*"):
            return p.read_bytes()
        raise FileNotFoundError(f"File {file_id} not found")

    async def delete(self, file_id: str) -> bool:
        for p in self._base.rglob(f"{file_id}_*"):
            p.unlink()
            return True
        return False

    async def list(self, user_id: str, prefix: str = "") -> list[FileMetadata]:
        user_dir = self._base / user_id
        if not user_dir.exists():
            return []
        results: list[FileMetadata] = []
        for p in user_dir.rglob("*"):
            if p.is_file() and (not prefix or p.name.startswith(prefix)):
                parts = p.name.split("_", 1)
                results.append(
                    FileMetadata(
                        file_id=parts[0] if len(parts) > 1 else p.stem,
                        filename=parts[1] if len(parts) > 1 else p.name,
                        content_type="application/octet-stream",
                        size_bytes=p.stat().st_size,
                        storage_key=str(p.relative_to(self._base)),
                        user_id=user_id,
                    )
                )
        return results
