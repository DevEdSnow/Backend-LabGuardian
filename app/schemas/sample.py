
"""
Pydantic schemas for clinical samples.

LabGuardian AI
--------------
Validación de datos y respuestas para el registro,
seguimiento y evaluación de riesgos de muestras clínicas.
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

class SampleStatus(str, Enum):
    """Estados posibles de una muestra clínica."""

    RECEIVED = "RECEIVED"
    IDENTIFIED = "IDENTIFIED"
    IN_TRANSPORT = "IN_TRANSPORT"
    IN_STORAGE = "IN_STORAGE"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    DISCARDED = "DISCARDED"


class SamplePriority(str, Enum):
    """Prioridad de procesamiento de la muestra."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    STAT = "STAT"


class SampleRiskLevel(str, Enum):
    """Clasificación del riesgo estimado de la muestra."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SampleType(str, Enum):
    """Tipos frecuentes de muestras clínicas."""

    BLOOD = "BLOOD"
    SERUM = "SERUM"
    PLASMA = "PLASMA"
    URINE = "URINE"
    STOOL = "STOOL"
    SALIVA = "SALIVA"
    SWAB = "SWAB"
    SPUTUM = "SPUTUM"
    CEREBROSPINAL_FLUID = "CEREBROSPINAL_FLUID"
    TISSUE = "TISSUE"
    OTHER = "OTHER"


# ============================================================
# BASE SCHEMA
# ============================================================

class SampleBase(BaseModel):
    """Campos compartidos de una muestra clínica."""

    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Código único de identificación de la muestra.",
    )

    sample_type: SampleType = Field(
        ...,
        description="Tipo de muestra clínica.",
    )

    laboratory_area: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Área del laboratorio responsable.",
    )

    priority: SamplePriority = Field(
        default=SamplePriority.NORMAL,
        description="Prioridad de procesamiento.",
    )

    status: SampleStatus = Field(
        default=SampleStatus.RECEIVED,
        description="Estado actual de la muestra.",
    )

    collected_at: datetime | None = Field(
        default=None,
        description="Fecha y hora de recolección.",
    )

    received_at: datetime | None = Field(
        default=None,
        description="Fecha y hora de recepción en el laboratorio.",
    )

    processing_started_at: datetime | None = Field(
        default=None,
        description="Fecha y hora de inicio del procesamiento.",
    )

    processed_at: datetime | None = Field(
        default=None,
        description="Fecha y hora de finalización del procesamiento.",
    )

    result_at: datetime | None = Field(
        default=None,
        description="Fecha y hora de disponibilidad del resultado.",
    )

    transport_minutes: float = Field(
        default=0,
        ge=0,
        le=525600,
        description="Tiempo de transporte en minutos.",
    )

    processing_minutes: float = Field(
        default=0,
        ge=0,
        le=525600,
        description="Tiempo de procesamiento en minutos.",
    )

    storage_minutes: float = Field(
        default=0,
        ge=0,
        le=525600,
        description="Tiempo acumulado de almacenamiento en minutos.",
    )

    current_temperature: float | None = Field(
        default=None,
        ge=-100,
        le=150,
        description="Temperatura actual en grados Celsius.",
    )

    minimum_temperature: float | None = Field(
        default=None,
        ge=-100,
        le=150,
        description="Temperatura mínima registrada en grados Celsius.",
    )

    maximum_temperature: float | None = Field(
        default=None,
        ge=-100,
        le=150,
        description="Temperatura máxima registrada en grados Celsius.",
    )

    storage_location: str | None = Field(
        default=None,
        max_length=200,
        description="Ubicación física de almacenamiento.",
    )

    notes: str | None = Field(
        default=None,
        max_length=3000,
        description="Observaciones sobre la muestra.",
    )

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        """Normaliza el código de identificación."""
        value = value.strip().upper()

        if not value:
            raise ValueError("El código de la muestra es obligatorio.")

        return value

    @field_validator("laboratory_area")
    @classmethod
    def normalize_area(cls, value: str) -> str:
        """Elimina espacios innecesarios del área."""
        value = value.strip()

        if not value:
            raise ValueError("El área del laboratorio es obligatoria.")

        return value

    @field_validator("storage_location", "notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        """Normaliza los textos opcionales."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value

    @model_validator(mode="after")
    def validate_temperatures(self):
        """Comprueba que el rango térmico sea coherente."""
        minimum = self.minimum_temperature
        maximum = self.maximum_temperature
        current = self.current_temperature

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                raise ValueError(
                    "La temperatura mínima no puede superar la máxima."
                )

        if current is not None:
            if minimum is not None and current < minimum:
                raise ValueError(
                    "La temperatura actual está por debajo del mínimo registrado."
                )

            if maximum is not None and current > maximum:
                raise ValueError(
                    "La temperatura actual supera el máximo registrado."
                )

        return self

    @model_validator(mode="after")
    def validate_timeline(self):
        """Comprueba el orden cronológico de las fechas disponibles."""
        timeline = [
            ("collected_at", self.collected_at),
            ("received_at", self.received_at),
            ("processing_started_at", self.processing_started_at),
            ("processed_at", self.processed_at),
            ("result_at", self.result_at),
        ]

        previous_name = None
        previous_value = None

        for current_name, current_value in timeline:
            if current_value is None:
                continue

            if (
                current_value.tzinfo is None
                or current_value.utcoffset() is None
            ):
                raise ValueError(
                    f"{current_name} debe incluir una zona horaria."
                )

            if previous_value is not None and current_value < previous_value:
                raise ValueError(
                    f"{current_name} no puede ser anterior a {previous_name}."
                )

            previous_name = current_name
            previous_value = current_value

        return self


# ============================================================
# CREATE SCHEMA
# ============================================================

class SampleCreate(SampleBase):
    """Datos para registrar una nueva muestra."""

    # Los campos de riesgo no se aceptan aquí: los calcula el backend.
    # El identificador interno y las fechas de auditoría también
    # los administra la base de datos.


# ============================================================
# UPDATE SCHEMA
# ============================================================

class SampleUpdate(BaseModel):
    """Campos que pueden modificarse en una muestra existente."""

    model_config = ConfigDict(extra="forbid")

    sample_type: SampleType | None = None
    laboratory_area: str | None = Field(default=None, max_length=100)
    priority: SamplePriority | None = None
    status: SampleStatus | None = None

    collected_at: datetime | None = None
    received_at: datetime | None = None
    processing_started_at: datetime | None = None
    processed_at: datetime | None = None
    result_at: datetime | None = None

    transport_minutes: float | None = Field(
        default=None, ge=0, le=525600
    )
    processing_minutes: float | None = Field(
        default=None, ge=0, le=525600
    )
    storage_minutes: float | None = Field(
        default=None, ge=0, le=525600
    )

    current_temperature: float | None = Field(
        default=None, ge=-100, le=150
    )
    minimum_temperature: float | None = Field(
        default=None, ge=-100, le=150
    )
    maximum_temperature: float | None = Field(
        default=None, ge=-100, le=150
    )

    storage_location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=3000)

    @field_validator("laboratory_area")
    @classmethod
    def normalize_area(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("El área del laboratorio no puede estar vacía.")

        return value

    @field_validator("storage_location", "notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value

    @field_validator(
        "collected_at",
        "received_at",
        "processing_started_at",
        "processed_at",
        "result_at",
    )
    @classmethod
    def validate_datetime_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError(
                "Las fechas deben incluir una zona horaria."
            )

        return value

    @model_validator(mode="after")
    def validate_update(self):
        """Comprueba los datos enviados en la actualización."""
        if not self.model_fields_set:
            raise ValueError(
                "Debes proporcionar al menos un campo para actualizar."
            )

        minimum = self.minimum_temperature
        maximum = self.maximum_temperature
        current = self.current_temperature

        if (
            minimum is not None
            and maximum is not None
            and minimum > maximum
        ):
            raise ValueError(
                "La temperatura mínima no puede superar la máxima."
            )

        if (
            current is not None
            and minimum is not None
            and current < minimum
        ):
            raise ValueError(
                "La temperatura actual está por debajo del mínimo."
            )

        if (
            current is not None
            and maximum is not None
            and current > maximum
        ):
            raise ValueError(
                "La temperatura actual supera el máximo."
            )

        timeline = [
            ("collected_at", self.collected_at),
            ("received_at", self.received_at),
            ("processing_started_at", self.processing_started_at),
            ("processed_at", self.processed_at),
            ("result_at", self.result_at),
        ]

        previous_name = None
        previous_value = None

        for current_name, current_value in timeline:
            if current_name not in self.model_fields_set:
                continue

            if current_value is None:
                continue

            if (
                previous_value is not None
                and current_value < previous_value
            ):
                raise ValueError(
                    f"{current_name} no puede ser anterior a {previous_name}."
                )

            previous_name = current_name
            previous_value = current_value

        return self


# ============================================================
# STATUS UPDATE SCHEMA
# ============================================================

class SampleStatusUpdate(BaseModel):
    """Solicitud específica para cambiar el estado de una muestra."""

    status: SampleStatus
    notes: str | None = Field(default=None, max_length=1000)


# ============================================================
# RISK SCHEMA
# ============================================================

class SampleRiskResponse(BaseModel):
    """Resultado del análisis de riesgo de una muestra."""

    model_config = ConfigDict(from_attributes=True)

    sample_id: int
    sample_code: str
    risk_score: float = Field(ge=0, le=100)
    risk_level: SampleRiskLevel
    anomaly_detected: bool
    risk_explanation: str | None = None
    factors: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============================================================
# RESPONSE SCHEMA
# ============================================================

class SampleResponse(SampleBase):
    """Representación de una muestra almacenada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_score: float = Field(ge=0, le=100)
    risk_level: SampleRiskLevel
    anomaly_detected: bool
    risk_explanation: str | None = None
    created_at: datetime
    updated_at: datetime


# ============================================================
# LIST RESPONSE SCHEMA
# ============================================================

class SampleListResponse(BaseModel):
    """Respuesta paginada para el listado de muestras."""

    success: bool = True
    total: int = Field(ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    items: list[SampleResponse] = Field(default_factory=list)


# ============================================================
# SUMMARY SCHEMA
# ============================================================

class SampleSummary(BaseModel):
    """Estadísticas generales de las muestras."""

    total: int = Field(default=0, ge=0)

    received: int = Field(default=0, ge=0)
    processing: int = Field(default=0, ge=0)
    processed: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    discarded: int = Field(default=0, ge=0)

    low_risk: int = Field(default=0, ge=0)
    medium_risk: int = Field(default=0, ge=0)
    high_risk: int = Field(default=0, ge=0)
    critical_risk: int = Field(default=0, ge=0)

    anomalies_detected: int = Field(default=0, ge=0)
    average_risk_score: float = Field(default=0, ge=0, le=100)


class SampleSummaryResponse(BaseModel):
    """Respuesta para las estadísticas de muestras."""

    success: bool = True
    summary: SampleSummary

