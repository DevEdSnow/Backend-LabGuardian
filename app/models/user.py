
"""
User database model for LabGuardian AI.

This module defines the users who access the laboratory
management and sample traceability platform.

Features:
- User identification
- Secure password hash storage
- Role-based access control
- Account activation and verification
- Login tracking
- Audit timestamps
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Returns the current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """Represents a user authorized to access LabGuardian AI."""

    __tablename__ = "users"

    # ─────────────────────────────────────────────
    # Primary key
    # ─────────────────────────────────────────────

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    # ─────────────────────────────────────────────
    # Identification
    # ─────────────────────────────────────────────

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # ─────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ─────────────────────────────────────────────
    # Role and permissions
    # ─────────────────────────────────────────────

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="LAB_TECHNICIAN",
        index=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Account status
    # ─────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # ─────────────────────────────────────────────
    # Login tracking
    # ─────────────────────────────────────────────

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ─────────────────────────────────────────────
    # Audit timestamps
    # ─────────────────────────────────────────────

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # ─────────────────────────────────────────────
    # Computed properties
    # ─────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        """Returns the user's full name."""

        return f"{self.first_name} {self.last_name}".strip()

    # ─────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """
        Returns public user information.

        The password hash is deliberately excluded.
        """

        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "role": self.role,
            "department": self.department,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login_at": (
                self.last_login_at.isoformat()
                if self.last_login_at
                else None
            ),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }

    def __repr__(self) -> str:
        """Returns a safe representation of the user."""

        return (
            f"<User("
            f"id={self.id}, "
            f"username={self.username!r}, "
            f"role={self.role!r}, "
            f"is_active={self.is_active}"
            f")>"
        )

