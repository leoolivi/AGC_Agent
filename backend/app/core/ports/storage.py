"""
FileStoragePort — Protocol for file storage backends.

Implementations: LocalStorageAdapter, MinIOAdapter, S3Adapter (app/adapters/storage/).
Wiring: app/api/deps.py via FILE_STORAGE_BACKEND env var.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol, runtime_checkable


@dataclass
class FileMetadata:
    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    user_id: str


@runtime_checkable
class FileStoragePort(Protocol):
    async def save(
        self,
        file: BinaryIO,
        filename: str,
        user_id: str,
        content_type: str,
    ) -> FileMetadata: ...

    async def get(self, file_id: str) -> bytes: ...

    async def delete(self, file_id: str) -> bool: ...

    async def list(
        self,
        user_id: str,
        prefix: str = "",
    ) -> list[FileMetadata]: ...
