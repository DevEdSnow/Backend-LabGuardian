"""
Sample event database model for LabGuardian AI.

This module stores the traceability history of clinical
samples throughout their laboratory lifecycle.

Examples of events:
- Sample reception
- Identification
- Transportation
- Storage
- Temperature monitoring
- Processing
- Result generation
- Sample rejection
- Manual review
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SampleEvent(Base):
    """Represents a traceability event for a clinical sample."""

    __tablename__ = "sample_events"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    # Sample reference
    sample_id: Mapped[int] = mapped_column(
        ForeignKey("samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event identification
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Event status and severity
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="COMPLETED",
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="INFO",
        index=True,
    )

    # Measurements recorded during the event
    temperature: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    duration_minutes: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Location and responsible person
    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    performed_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Equipment associated with the event
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Additional metadata for sensors, QR scans, etc.
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Event timestamp
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Serialization
    def to_dict(self) -> dict[str, Any]:
        """Converts the event into a JSON-compatible dictionary."""

        return {
            "id": self.id,
            "sample_id": self.sample_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "severity": self.severity,
            "temperature": self.temperature,
            "duration_minutes": self.duration_minutes,
            "location": self.location,
            "performed_by": self.performed_by,
            "equipment_id": self.equipment_id,
            "metadata": self.event_metadata,
            "occurred_at": (
                self.occurred_at.isoformat()
                if self.occurred_at
                else None
            ),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"<SampleEvent("
            f"id={self.id}, "
            f"sample_id={self.sample_id}, "
            f"event_type={self.event_type!r}, "
            f"status={self.status!r}"
            f")>"
        )

