
"""
Equipment database model for LabGuardian AI.

This module defines the SQLAlchemy model used to store
laboratory equipment and its monitoring information.

The model supports:

- Equipment identification
- Equipment type
- Laboratory area
- Operational status
- Temperature monitoring
- Anomaly detection
- Maintenance tracking
- Last communication
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Equipment(Base):
    """
    Represents laboratory equipment monitored by
    LabGuardian AI.
    """

    __tablename__ = "equipment"

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

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    equipment_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )

    manufacturer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    serial_number: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    # ─────────────────────────────────────────────
    # Laboratory location
    # ─────────────────────────────────────────────

    area: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Operational status
    # ─────────────────────────────────────────────

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="OPERATIONAL",
        index=True,
    )

    # ─────────────────────────────────────────────
    # Monitoring
    # ─────────────────────────────────────────────

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

    anomaly_detected: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    anomaly_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    anomaly_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Maintenance
    # ─────────────────────────────────────────────

    last_maintenance_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    next_maintenance_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Communication / IoT
    # ─────────────────────────────────────────────

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sensor_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Additional information
    # ─────────────────────────────────────────────

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ─────────────────────────────────────────────
    # Dates
    # ─────────────────────────────────────────────

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ─────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the equipment model into a dictionary.
        """

        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "equipment_type": self.equipment_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "area": self.area,
            "location": self.location,
            "status": self.status,
            "current_temperature": self.current_temperature,
            "minimum_temperature": self.minimum_temperature,
            "maximum_temperature": self.maximum_temperature,
            "anomaly_detected": self.anomaly_detected,
            "anomaly_type": self.anomaly_type,
            "anomaly_message": self.anomaly_message,
            "last_maintenance_at": (
                self.last_maintenance_at.isoformat()
                if self.last_maintenance_at
                else None
            ),
            "next_maintenance_at": (
                self.next_maintenance_at.isoformat()
                if self.next_maintenance_at
                else None
            ),
            "last_seen_at": (
                self.last_seen_at.isoformat()
                if self.last_seen_at
                else None
            ),
            "sensor_id": self.sensor_id,
            "description": self.description,
            "notes": self.notes,
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
        return (
            f"<Equipment("
            f"id={self.id}, "
            f"code={self.code!r}, "
            f"name={self.name!r}, "
            f"status={self.status!r}"
            f")>"

