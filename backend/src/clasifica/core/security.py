"""Seguridad: hashing de contraseñas y JWT."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from clasifica.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_MIN = 15
REFRESH_DAYS = 7


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def _token(sub: str, expires: timedelta, tipo: str) -> str:
    now = datetime.now(UTC)
    payload = {"sub": sub, "type": tipo, "iat": now, "exp": now + expires}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(sub: str) -> str:
    return _token(sub, timedelta(minutes=ACCESS_MIN), "access")


def create_refresh_token(sub: str) -> str:
    return _token(sub, timedelta(days=REFRESH_DAYS), "refresh")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
