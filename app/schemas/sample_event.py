
"""
Pydantic schemas for sample traceability events.

LabGuardian AI
---------------
Define los esquemas de validación para registrar, actualizar
y consultar los eventos relacionados con las muestras clínicas.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# ENUMS
# ============================================================

class SampleEventType(str, Enum):
    """Tipos de eventos que pueden ocurrir durante la trazabilidad."""

    RECEIVED = "RECEIVED"
    IDENTIFIED = "IDENTIFIED"
    TRANSPORT_STARTED = "TRANSPORT_STARTED"
    TRANSPORT_COMPLETED = "TRANSPORT_COMPLETED"
    TEMPERATURE_RECORDED = "TEMPERATURE_RECORDED"
    STORAGE_STARTED = "STORAGE_STARTED"
    PROCESSING_STARTED = "PROCESSING_STARTED"
    PROCESSING_COMPLETED = "PROCESSING_COMPLETED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    RESULT_VALIDATED = "RESULT_VALIDATED"
    RESULT_RELEASED = "RESULT_RELEASED"
    SAMPLE_REJECTED = "SAMPLE_REJECTED"
    SAMPLE_DISCARDED = "SAMPLE_DISCARDED"
    EQUIPMENT_ASSIGNED = "EQUIPMENT_ASSIGNED"
    MAINTENANCE_RECORDED = "MAINTENANCE_RECORDED"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    MANUAL_UPDATE = "MANUAL_UPDATE"
    OTHER = "OTHER"


class SampleEventStatus(str, Enum):
    """Estado de ejecución del evento."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SampleEventSeverity(str, Enum):
    """Nivel de importancia del evento."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ============================================================
# BASE SCHEMA
# ============================================================

class SampleEventBase(BaseModel):
    """Campos compartidos para los eventos de trazabilidad."""

    event_type: SampleEventType = Field(
        ...,
        description="Tipo de evento registrado.",
    )

    title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Título breve del evento.",
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Descripción detallada del evento.",
    )

    status: SampleEventStatus = Field(
        default=SampleEventStatus.COMPLETED,
        description="Estado del evento.",
    )

    severity: SampleEventSeverity = Field(
        default=SampleEventSeverity.INFO,
        description="Nivel de severidad del evento.",
    )

    temperature: float | None = Field(
        default=None,
        ge=-100,
        le=150,
        description="Temperatura registrada en grados Celsius.",
    )

    duration_minutes: float | None = Field(
        default=None,
        ge=0,
        le=525600,
        description="Duración del evento en minutos.",
    )

    location: str | None = Field(
        default=None,
        max_length=200,
        description="Ubicación donde ocurrió el evento.",
    )

    performed_by: str | None = Field(
        default=None,
        max_length=150,
        description="Usuario o responsable que realizó la acción.",
    )

    equipment_id: int | None = Field(
        default=None,
        gt=0,
        description="Identificador del equipo relacionado, si aplica.",
    )

    event_metadata: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Información adicional del evento en formato clave-valor. "
            "No debe contener contraseñas ni datos personales innecesarios."
        ),
    )

    @field_validator(
        "title",
        "description",
        "location",
        "performed_by",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: Any) -> Any:
        """Elimina espacios sobrantes y convierte textos vacíos en None."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value

    @field_validator("event_metadata")
    @classmethod
    def validate_metadata_size(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Evita objetos de metadatos excesivamente grandes."""
        if value is not None and len(value) > 50:
            raise ValueError(
                "Los metadatos no pueden contener más de 50 propiedades."
            )

        return value


# ============================================================
# CREATE SCHEMA
# ============================================================

class SampleEventCreate(SampleEventBase):
    """Datos necesarios para registrar un evento."""

    sample_id: int = Field(
        ...,
        gt=0,
        description="ID de la muestra relacionada con el evento.",
    )

    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha y hora en que ocurrió el evento.",
    )

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        """Rechaza fechas sin zona horaria."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "occurred_at debe incluir una zona horaria."
            )

        return value


# ============================================================
# UPDATE SCHEMA
# ============================================================

class SampleEventUpdate(BaseModel):
    """Campos modificables de un evento existente."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    status: SampleEventStatus | None = None
    severity: SampleEventSeverity | None = None

    temperature: float | None = Field(
        default=None,
        ge=-100,
        le=150,
    )

    duration_minutes: float | None = Field(
        default=None,
        ge=0,
        le=525600,
    )

    location: str | None = Field(
        default=None,
        max_length=200,
    )

    performed_by: str | None = Field(
        default=None,
        max_length=150,
    )

    equipment_id: int | None = Field(
        default=None,
        gt=0,
    )

    event_metadata: dict[str, Any] | None = None

    @field_validator(
        "title",
        "description",
        "location",
        "performed_by",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        """Normaliza los campos de texto opcionales."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value

    @model_validator(mode="after")
    def validate_update_fields(self):
        """Exige al menos un campo para realizar la actualización."""
        if not self.model_fields_set:
            raise ValueError(
                "Debes proporcionar al menos un campo para actualizar."
            )

        return self


# ============================================================
# RESPONSE SCHEMA
# ============================================================

class SampleEventResponse(SampleEventBase):
    """Respuesta pública de un evento almacenado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sample_id: int
    occurred_at: datetime
    created_at: datetime


# ============================================================
# LIST RESPONSE SCHEMA
# ============================================================

class SampleEventListResponse(BaseModel):
    """Respuesta paginada para consultar eventos."""

    success: bool = True
    total: int = Field(ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    items: list[SampleEventResponse] = Field(default_factory=list)


# ============================================================
# SUMMARY SCHEMAS
# ============================================================

class SampleEventSummary(BaseModel):
    """Resumen estadístico de los eventos de trazabilidad."""

    total_events: int = Field(default=0, ge=0)
    pending_events: int = Field(default=0, ge=0)
    in_progress_events: int = Field(default=0, ge=0)
    completed_events: int = Field(default=0, ge=0)
    failed_events: int = Field(default=0, ge=0)
    cancelled_events: int = Field(default=0, ge=0)

    informational_events: int = Field(default=0, ge=0)
    warning_events: int = Field(default=0, ge=0)
    critical_events: int = Field(default=0, ge=0)

    last_event_at: datetime | None = None


class SampleEventSummaryResponse(BaseModel):
    """Respuesta que contiene el resumen de eventos."""

    success: bool = True
    sample_id: int
    sample_code: str | None = None
    summary: SampleEventSummary

