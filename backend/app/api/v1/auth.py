"""Auth API — login endpoint."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.services.auth_service import create_access_token, verify_password
from app.db.models import User
from app.db.session import build_session_factory
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

_session_factory = build_session_factory(settings.database_url)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


async def _get_session() -> AsyncSession:  # type: ignore[misc]
    async with _session_factory() as session:
        yield session  # type: ignore[misc]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(_get_session)) -> TokenResponse:
    """Authenticate user and return JWT. Generic 401 to prevent user enumeration."""
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(str(user.id), user.email)
    return TokenResponse(access_token=token)
