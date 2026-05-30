"""MinIOAdapter — file storage via MinIO (S3-compatible)."""
from __future__ import annotations

import uuid
from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.adapters.storage.utils import build_storage_key
from app.core.ports.storage import FileMetadata, FileStoragePort


class MinIOAdapter(FileStoragePort):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        use_ssl: bool = False,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=f"{'https' if use_ssl else 'http'}://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        # Ensure bucket exists
        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError:
            self._client.create_bucket(Bucket=bucket)

    async def save(
        self, file: BinaryIO, filename: str, user_id: str, content_type: str
    ) -> FileMetadata:
        file_id = str(uuid.uuid4())
        storage_key = build_storage_key(user_id, file_id, filename)
        data = file.read()
        self._client.put_object(
            Bucket=self._bucket,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
        )
        return FileMetadata(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            storage_key=storage_key,
            user_id=user_id,
        )

    async def get(self, file_id: str) -> bytes:
        # Search by prefix pattern
        resp = self._client.list_objects_v2(Bucket=self._bucket, MaxKeys=1000)
        for obj in resp.get("Contents", []):
            if file_id in obj["Key"]:
                result = self._client.get_object(Bucket=self._bucket, Key=obj["Key"])
                return result["Body"].read()  # type: ignore[no-any-return]
        raise FileNotFoundError(f"File {file_id} not found")

    async def delete(self, file_id: str) -> bool:
        resp = self._client.list_objects_v2(Bucket=self._bucket, MaxKeys=1000)
        for obj in resp.get("Contents", []):
            if file_id in obj["Key"]:
                self._client.delete_object(Bucket=self._bucket, Key=obj["Key"])
                return True
        return False

    async def list(self, user_id: str, prefix: str = "") -> list[FileMetadata]:
        search_prefix = f"{user_id}/"
        resp = self._client.list_objects_v2(Bucket=self._bucket, Prefix=search_prefix)
        results: list[FileMetadata] = []
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            name = key.rsplit("/", 1)[-1]
            parts = name.split("_", 1)
            results.append(
                FileMetadata(
                    file_id=parts[0] if len(parts) > 1 else name,
                    filename=parts[1] if len(parts) > 1 else name,
                    content_type="application/octet-stream",
                    size_bytes=obj["Size"],
                    storage_key=key,
                    user_id=user_id,
                )
            )
        return results
