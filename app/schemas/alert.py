
"""
Alert schemas for LabGuardian AI.

Defines request and response schemas for creating,
updating, resolving and retrieving laboratory alerts.
"""

from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class AlertType(str, Enum):
    TEMPERATURE = "TEMPERATURE"
    TRANSPORT_DELAY = "TRANSPORT_DELAY"
    PROCESSING_DELAY = "PROCESSING_DELAY"
    STORAGE_ISSUE = "STORAGE_ISSUE"
    SAMPLE_DEGRADATION = "SAMPLE_DEGRADATION"
    EQUIPMENT_ANOMALY = "EQUIPMENT_ANOMALY"
    ML_ANOMALY = "ML_ANOMALY"
    OTHER = "OTHER"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AlertSource(str, Enum):
    SYSTEM = "SYSTEM"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    IOT_SENSOR = "IOT_SENSOR"
    USER = "USER"


# ─────────────────────────────────────────────
# Base schema
# ─────────────────────────────────────────────

class AlertBase(BaseModel):
    """Shared fields for alert schemas."""

    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.MEDIUM
    title: str = Field(min_length=3, max_length=150)
    message: str = Field(min_length=3, max_length=5000)

    sample_id: int | None = Field(default=None, gt=0)
    sample_code: str | None = Field(
        default=None,
        max_length=50,
    )

    risk_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    source: AlertSource = AlertSource.SYSTEM

    @field_validator("sample_code")
    @classmethod
    def normalize_sample_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("title", "message")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("El texto no puede estar vacío.")

        return value


# ─────────────────────────────────────────────
# Create schema
# ─────────────────────────────────────────────

class AlertCreate(AlertBase):
    """Fields accepted when creating a new alert."""

    pass


# ─────────────────────────────────────────────
# Update schema
# ─────────────────────────────────────────────

class AlertUpdate(BaseModel):
    """Fields that may be updated on an existing alert."""

    severity: AlertSeverity | None = None
    status: AlertStatus | None = None
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )
    message: str | None = Field(
        default=None,
        min_length=3,
        max_length=5000,
    )
    risk_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    @field_validator("title", "message")
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("El texto no puede estar vacío.")

        return value


# ─────────────────────────────────────────────
# Resolve schema
# ─────────────────────────────────────────────

class AlertResolve(BaseModel):
    """Information required to resolve an alert."""

    resolved_by: str = Field(
        min_length=2,
        max_length=100,
    )
    resolution_notes: str = Field(
        min_length=3,
        max_length=5000,
    )

    @field_validator("resolved_by", "resolution_notes")
    @classmethod
    def normalize_resolution_text(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("El campo no puede estar vacío.")

        return value


# ─────────────────────────────────────────────
# Response schema
# ─────────────────────────────────────────────

class AlertResponse(AlertBase):
    """Alert representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: AlertStatus
    resolved_by: str | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


# ─────────────────────────────────────────────
# List response
# ─────────────────────────────────────────────

class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    success: bool = True
    total: int = Field(ge=0)
    alerts: list[AlertResponse]


# ─────────────────────────────────────────────
# Summary response
# ─────────────────────────────────────────────

class AlertSummary(BaseModel):
    """Aggregated alert statistics."""

    total: int = Field(ge=0)
    active: int = Field(ge=0)
    acknowledged: int = Field(ge=0)
    resolved: int = Field(ge=0)
    dismissed: int = Field(ge=0)

    low: int = Field(ge=0)
    medium: int = Field(ge=0)
    high: int = Field(ge=0)
    critical: int = Field(ge=0)


class AlertSummaryResponse(BaseModel):
    """API response containing alert statistics."""

    success: bool = True
    summary: AlertSummary

