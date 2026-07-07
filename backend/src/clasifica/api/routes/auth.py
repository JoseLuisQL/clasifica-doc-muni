"""Rutas de autenticación."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.api.deps import get_db
from clasifica.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from clasifica.schemas import LoginRequest, RefreshRequest, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    from clasifica.db.models import Usuario

    user = (
        await db.execute(select(Usuario).where(Usuario.username == body.username))
    ).scalar_one_or_none()
    if user is None or not user.activo or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    sub = str(user.id)
    return TokenPair(access_token=create_access_token(sub), refresh_token=create_refresh_token(sub))


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest) -> TokenPair:
    from jose import JWTError

    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise JWTError("tipo inválido")
        sub = payload["sub"]
    except (JWTError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh inválido") from exc
    return TokenPair(access_token=create_access_token(sub), refresh_token=create_refresh_token(sub))
