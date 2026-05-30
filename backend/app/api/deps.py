"""API dependencies — JWT auth middleware and adapter wiring."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ports.llm import LLMProviderPort
from app.core.ports.storage import FileStoragePort
from app.core.services.auth_service import decode_access_token
from app.db.session import build_session_factory

_bearer_scheme = HTTPBearer()
_session_factory = build_session_factory(settings.database_url)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with _session_factory() as session:
        yield session  # type: ignore[misc]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """Extract and validate JWT from Authorization header. Returns user payload."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        ) from e
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        )
    return payload


def require_owner(resource_user_id: str, current_user: dict) -> None:
    """Raise 403 if current user doesn't own the resource."""
    if current_user.get("sub") != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )


def get_storage() -> FileStoragePort:
    """Build storage adapter based on FILE_STORAGE_BACKEND env var."""
    backend = settings.file_storage_backend
    if backend == "local":
        from app.adapters.storage.local_adapter import LocalStorageAdapter

        return LocalStorageAdapter(settings.file_storage_path)
    elif backend == "minio":
        from app.adapters.storage.minio_adapter import MinIOAdapter

        return MinIOAdapter(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
        )
    elif backend == "s3":
        from app.adapters.storage.s3_adapter import S3Adapter

        return S3Adapter(bucket=settings.s3_bucket, region=settings.s3_region)
    else:
        raise ValueError(f"Unknown FILE_STORAGE_BACKEND: {backend}")


def get_llm() -> LLMProviderPort:
    """Build LLM adapter based on LLM_PROVIDER env var."""
    provider = settings.llm_provider
    if provider == "ollama":
        from app.adapters.llm.ollama_adapter import OllamaAdapter

        return OllamaAdapter(model=settings.ollama_model, base_url=settings.ollama_base_url)
    elif provider == "anthropic" and settings.anthropic_api_key:
        from app.adapters.llm.anthropic_adapter import AnthropicLLMAdapter

        return AnthropicLLMAdapter(api_key=settings.anthropic_api_key)
    elif provider == "openai" and settings.openai_api_key:
        from app.adapters.llm.openai_adapter import OpenAILLMAdapter

        return OpenAILLMAdapter(api_key=settings.openai_api_key)
    else:
        from app.adapters.dummy.llm import DummyLLMAdapter

        return DummyLLMAdapter(content='{"document_type": "altro", "confidence": 0.5}')
