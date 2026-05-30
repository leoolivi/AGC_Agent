"""
DummyStorageAdapter — in-memory implementation of FileStoragePort.

Stores file bytes in a plain dict keyed by file_id.
No external dependencies. Safe to use in unit tests.
"""
from __future__ import annotations

import io
import uuid
from typing import BinaryIO

from app.core.ports.storage import FileMetadata, FileStoragePort


class DummyStorageAdapter:
    """In-memory FileStoragePort implementation for testing."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, FileMetadata]] = {}

    async def save(
        self,
        file: BinaryIO,
        filename: str,
        user_id: str,
        content_type: str,
    ) -> FileMetadata:
        file_id = str(uuid.uuid4())
        data = file.read() if not isinstance(file, (bytes, bytearray)) else file
        storage_key = f"{user_id}/dummy/{file_id}_{filename}"
        metadata = FileMetadata(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            storage_key=storage_key,
            user_id=user_id,
        )
        self._store[file_id] = (data, metadata)
        return metadata

    async def get(self, file_id: str) -> bytes:
        if file_id not in self._store:
            raise FileNotFoundError(f"file_id={file_id!r} not found in dummy storage")
        data, _ = self._store[file_id]
        return data

    async def delete(self, file_id: str) -> bool:
        if file_id not in self._store:
            return False
        del self._store[file_id]
        return True

    async def list(
        self,
        user_id: str,
        prefix: str = "",
    ) -> list[FileMetadata]:
        return [
            meta
            for _, meta in self._store.values()
            if meta.user_id == user_id and meta.storage_key.startswith(prefix)
        ]


# Verify structural compatibility at import time (fails fast if Protocol drifts).
def _assert_protocol() -> None:
    _: FileStoragePort = DummyStorageAdapter()  # type: ignore[assignment]


_assert_protocol()
