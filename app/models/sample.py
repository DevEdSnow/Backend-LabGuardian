
"""
Clinical sample database model for LabGuardian AI.

This module defines the SQLAlchemy model for clinical
samples and their traceability information.

The model supports:
- Sample identification and QR traceability
- Sample type and laboratory area
- Collection, reception and processing timestamps
- Storage and transportation conditions
- Risk assessment and anomaly detection
- Sample lifecycle status
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Returns the current UTC datetime."""
    return datetime.now(timezone.utc)


class Sample(Base):
    """Represents a clinical sample tracked by LabGuardian AI."""

    __tablename__ = "samples"

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

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    sample_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )

    laboratory_area: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NORMAL",
        index=True,
    )

    # ─────────────────────────────────────────────
    # Lifecycle status
    # ─────────────────────────────────────────────

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="RECEIVED",
        index=True,
    )

    # ─────────────────────────────────────────────
    # Collection and processing timestamps
    # ─────────────────────────────────────────────

    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    result_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Transportation and storage
    # ─────────────────────────────────────────────

    transport_minutes: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    processing_minutes: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    storage_minutes: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    current_temperature: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    minimum_temperature: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    maximum_temperature: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    storage_location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Risk assessment
    # ─────────────────────────────────────────────

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        index=True,
    )

    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="LOW",
        index=True,
    )

    anomaly_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    risk_explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Additional information
    # ─────────────────────────────────────────────

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    # Serialization
    # ─────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Converts the sample into a JSON-compatible dictionary."""

        datetime_fields = (
            "collected_at",
            "received_at",
            "processing_started_at",
            "processed_at",
            "result_at",
            "created_at",
            "updated_at",
        )

        data = {
            "id": self.id,
            "code": self.code,
            "sample_type": self.sample_type,
            "laboratory_area": self.laboratory_area,
            "priority": self.priority,
            "status": self.status,
            "transport_minutes": self.transport_minutes,
            "processing_minutes": self.processing_minutes,
            "storage_minutes": self.storage_minutes,
            "current_temperature": self.current_temperature,
            "minimum_temperature": self.minimum_temperature,
            "maximum_temperature": self.maximum_temperature,
            "storage_location": self.storage_location,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "anomaly_detected": self.anomaly_detected,
            "risk_explanation": self.risk_explanation,
            "notes": self.notes,
        }

        for field in datetime_fields:
            value = getattr(self, field)
            data[field] = value.isoformat() if value else None

        return data

    def __repr__(self) -> str:
        return (
            f"<Sample("
            f"id={self.id}, "
            f"code={self.code!r}, "
            f"sample_type={self.sample_type!r}, "
            f"status={self.status!r}, "
            f"risk_level={self.risk_level!r}"
            f")>"
        )

