
"""
Alert database model for LabGuardian AI.

Stores laboratory alerts, their source events, risk information,
acknowledgment details, and resolution history.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class Alert(Base):
    """Represents a persistent laboratory alert."""

    __tablename__ = "alerts"

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
    # Sample and source event
    # ─────────────────────────────────────────────

    sample_id: Mapped[int | None] = mapped_column(
        ForeignKey("samples.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sample_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("sample_events.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    # ─────────────────────────────────────────────
    # Alert information
    # ─────────────────────────────────────────────

    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="LABORATORY_ALERT",
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MEDIUM",
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        default="Laboratory alert",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # ─────────────────────────────────────────────
    # Risk information
    # ─────────────────────────────────────────────

    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Source
    # ─────────────────────────────────────────────

    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SYSTEM",
    )

    # ─────────────────────────────────────────────
    # Acknowledgment
    # ─────────────────────────────────────────────

    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    acknowledged_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Resolution
    # ─────────────────────────────────────────────

    resolved_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Dates
    # ─────────────────────────────────────────────

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # SQLAlchemy relationships
    # These fix alert.sample and alert.event access.
    # ─────────────────────────────────────────────

    sample: Mapped["Sample | None"] = relationship(
        "Sample",
        foreign_keys=[sample_id],
    )

    event: Mapped["SampleEvent | None"] = relationship(
        "SampleEvent",
        foreign_keys=[event_id],
    )

    # ─────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Convert the alert to a JSON-compatible dictionary."""

        return {
            "id": self.id,
            "sample_id": self.sample_id,
            "sample_code": (
                self.sample.code
                if self.sample is not None
                else self.sample_code
            ),
            "event_id": self.event_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "status": self.status,
            "title": self.title,
            "message": self.message,
            "risk_score": self.risk_score,
            "source": self.source,
            "acknowledged_at": (
                self.acknowledged_at.isoformat()
                if self.acknowledged_at
                else None
            ),
            "acknowledged_by": self.acknowledged_by,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
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
            "resolved_at": (
                self.resolved_at.isoformat()
                if self.resolved_at
                else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"<Alert("
            f"id={self.id}, "
            f"sample_code={self.sample_code!r}, "
            f"type={self.alert_type!r}, "
            f"severity={self.severity!r}, "
            f"status={self.status!r}"
            f")>"
        )
