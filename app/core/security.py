
"""
Security utilities for LabGuardian AI.

This module provides password hashing, JWT token
creation and JWT token validation.

Authentication will be connected to the User model
and FastAPI dependencies later.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ─────────────────────────────────────────────
# Password Hashing
# ─────────────────────────────────────────────

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password.

    The original password must never be stored
    directly in the database.
    """

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verifies a plain-text password against
    a previously generated password hash.
    """

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ─────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Creates a JWT access token.

    Parameters
    ----------
    data:
        Information that will be stored in the token.

    expires_delta:
        Optional custom token expiration time.

    Returns
    -------
    str
        Encoded JWT token.
    """

    payload = data.copy()

    if expires_delta is not None:
        expire = (
            datetime.now(timezone.utc)
            + expires_delta
        )
    else:
        expire = (
            datetime.now(timezone.utc)
            + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        )

    payload.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
    )

    encoded_jwt = jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    return encoded_jwt


def decode_access_token(
    token: str,
) -> dict[str, Any] | None:
    """
    Decodes and validates a JWT access token.

    Returns None when the token is invalid
    or has expired.
    """

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        return payload

    except JWTError:
        return None


# ─────────────────────────────────────────────
# Token Helpers
# ─────────────────────────────────────────────

def get_token_subject(
    token: str,
) -> str | None:
    """
    Returns the subject (`sub`) stored in a JWT.

    The subject will normally contain the user ID.
    """

    payload = decode_access_token(token)

    if payload is None:
        return None

    subject = payload.get("sub")

    if subject is None:
        return None

    return str(subject)


def is_token_valid(
    token: str,
) -> bool:
    """
    Checks whether a JWT token is valid.
    """

    return decode_access_token(token) is not None

