"""Unit tests for authentication — JWT, password hashing, middleware."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from app.config import settings
from app.core.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password,
    verify_password,
)
from app.api.deps import get_current_user, require_owner


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        h = hash_password("securepass123")
        assert verify_password("securepass123", h)

    def test_wrong_password_fails(self) -> None:
        h = hash_password("correct")
        assert not verify_password("wrong", h)

    def test_validate_password_min_length(self) -> None:
        assert validate_password("12345678") is True
        assert validate_password("1234567") is False


class TestJWT:
    def test_valid_token(self) -> None:
        token = create_access_token("user-1", "a@b.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"
        assert payload["email"] == "a@b.com"

    def test_expired_token_raises(self) -> None:
        expired_payload = {
            "sub": "user-1",
            "email": "a@b.com",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        token = jwt.encode(
            expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(Exception):  # JWTError (ExpiredSignatureError)
            decode_access_token(token)

    def test_invalid_token_raises(self) -> None:
        with pytest.raises(Exception):
            decode_access_token("not.a.valid.token")

    def test_wrong_secret_raises(self) -> None:
        token = jwt.encode(
            {"sub": "user-1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256",
        )
        with pytest.raises(Exception):
            decode_access_token(token)


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_payload(self) -> None:
        token = create_access_token("user-1", "a@b.com")

        class FakeCreds:
            credentials = token

        result = await get_current_user(FakeCreds())  # type: ignore[arg-type]
        assert result["sub"] == "user-1"

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self) -> None:
        expired_payload = {
            "sub": "user-1",
            "email": "a@b.com",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        token = jwt.encode(
            expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        class FakeCreds:
            credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(FakeCreds())  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self) -> None:
        class FakeCreds:
            credentials = "garbage"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(FakeCreds())  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401


class TestRequireOwner:
    def test_matching_user_passes(self) -> None:
        require_owner("user-1", {"sub": "user-1"})  # no exception

    def test_different_user_raises_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            require_owner("user-1", {"sub": "user-2"})
        assert exc_info.value.status_code == 403
