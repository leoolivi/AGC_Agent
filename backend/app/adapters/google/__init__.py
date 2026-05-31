"""Google OAuth token store — encrypted refresh token storage."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ports.oauth import OAuthTokenPort
from app.db.models import GoogleOAuthToken
from app.db.session import build_session_factory


class GoogleTokenStore(OAuthTokenPort):
    def __init__(self) -> None:
        key = settings.google_token_encryption_key
        if not key:
            key = Fernet.generate_key().decode()
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def _get_factory(self):
        return build_session_factory(settings.database_url)

    async def store_token(self, user_id: str, provider: str, refresh_token: str, scopes: list[str]) -> None:
        encrypted = self._fernet.encrypt(refresh_token.encode()).decode()
        factory = self._get_factory()
        async with factory() as session:
            existing = await session.get(GoogleOAuthToken, (uuid.UUID(user_id), provider))
            if existing:
                existing.encrypted_refresh_token = encrypted
                existing.scopes = scopes
                existing.revoked_at = None
            else:
                session.add(GoogleOAuthToken(
                    user_id=uuid.UUID(user_id),
                    provider=provider,
                    encrypted_refresh_token=encrypted,
                    scopes=scopes,
                ))
            await session.commit()

    async def get_token(self, user_id: str, provider: str) -> str | None:
        factory = self._get_factory()
        async with factory() as session:
            token = await session.get(GoogleOAuthToken, (uuid.UUID(user_id), provider))
            if token and not token.revoked_at:
                return self._fernet.decrypt(token.encrypted_refresh_token.encode()).decode()
        return None

    async def revoke_token(self, user_id: str, provider: str) -> None:
        factory = self._get_factory()
        async with factory() as session:
            await session.execute(
                update(GoogleOAuthToken)
                .where(GoogleOAuthToken.user_id == uuid.UUID(user_id))
                .where(GoogleOAuthToken.provider == provider)
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()

    async def has_valid_token(self, user_id: str, provider: str, scope: str | None = None) -> bool:
        factory = self._get_factory()
        async with factory() as session:
            token = await session.get(GoogleOAuthToken, (uuid.UUID(user_id), provider))
            if not token or token.revoked_at:
                return False
            if scope and scope not in token.scopes:
                return False
            return True
