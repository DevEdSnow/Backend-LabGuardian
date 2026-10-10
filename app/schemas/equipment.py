
"""
Equipment schemas for LabGuardian AI.

Defines request and response schemas for registering,
updating and monitoring laboratory equipment.

Features:
- Equipment registration and identification
- Laboratory area and location
- Operational status
- Temperature monitoring
- Anomaly tracking
- Maintenance scheduling
- IoT sensor information
"""

from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class EquipmentStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    OFFLINE = "OFFLINE"


class EquipmentType(str, Enum):
    REFRIGERATOR = "REFRIGERATOR"
    FREEZER = "FREEZER"
    CENTRIFUGE = "CENTRIFUGE"
    ANALYZER = "ANALYZER"
    MICROSCOPE = "MICROSCOPE"
    INCUBATOR = "INCUBATOR"
    SENSOR = "SENSOR"
    OTHER = "OTHER"


class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ─────────────────────────────────────────────
# Base schema
# ─────────────────────────────────────────────

class EquipmentBase(BaseModel):
    """Shared equipment fields."""

    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    equipment_type: EquipmentType

    manufacturer: str | None = Field(
        default=None,
        max_length=100,
    )

    model: str | None = Field(
        default=None,
        max_length=100,
    )

    serial_number: str | None = Field(
        default=None,
        max_length=100,
    )

    area: str = Field(min_length=2, max_length=100)

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    status: EquipmentStatus = EquipmentStatus.OPERATIONAL

    description: str | None = None
    notes: str | None = None

    @field_validator(
        "code",
        "name",
        "area",
        "manufacturer",
        "model",
        "serial_number",
        "location",
        "description",
        "notes",
    )
    @classmethod
    def normalize_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        return value


# ─────────────────────────────────────────────
# Create schema
# ─────────────────────────────────────────────

class EquipmentCreate(EquipmentBase):
    """Fields required or accepted when registering equipment."""

    minimum_temperature: float | None = Field(
        default=None,
        ge=-100,
        le=200,
    )

    maximum_temperature: float | None = Field(
        default=None,
        ge=-100,
        le=200,
    )

    sensor_id: str | None = Field(
        default=None,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_temperature_range(self):
        minimum = self.minimum_temperature
        maximum = self.maximum_temperature

        if (
            minimum is not None
            and maximum is not None
            and minimum > maximum
        ):
            raise ValueError(
                "La temperatura mínima no puede superar "
                "la temperatura máxima."
            )

        return self


# ─────────────────────────────────────────────
# Update schema
# ─────────────────────────────────────────────

class EquipmentUpdate(BaseModel):
    """Optional fields for updating existing equipment."""

    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    equipment_type: EquipmentType | None = None

    manufacturer: str | None = Field(
        default=None,
        max_length=100,
    )

    model: str | None = Field(
        default=None,
        max_length=100,
    )

    serial_number: str | None = Field(
        default=None,
        max_length=100,
    )

    area: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    status: EquipmentStatus | None = None

    minimum_temperature: float | None = Field(
        default=None,
        ge=-100,
        le=200,
    )

    maximum_temperature: float | None = Field(
        default=None,
        ge=-100,
        le=200,
    )

    sensor_id: str | None = Field(
        default=None,
        max_length=100,
    )

    description: str | None = None
    notes: str | None = None

    @field_validator(
        "code",
        "name",
        "manufacturer",
        "model",
        "serial_number",
        "area",
        "location",
        "sensor_id",
        "description",
        "notes",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        return value

    @model_validator(mode="after")
    def validate_temperature_range(self):
        minimum = self.minimum_temperature
        maximum = self.maximum_temperature

        if (
            minimum is not None
            and maximum is not None
            and minimum > maximum
        ):
            raise ValueError(
                "La temperatura mínima no puede superar "
                "la temperatura máxima."
            )

        return self


# ─────────────────────────────────────────────
# Temperature monitoring
# ─────────────────────────────────────────────

class EquipmentTemperatureUpdate(BaseModel):
    """Temperature measurement reported by an operator or sensor."""

    temperature: float = Field(
        ge=-100,
        le=200,
    )

    recorded_at: datetime | None = None

    sensor_id: str | None = Field(
        default=None,
        max_length=100,
    )


class EquipmentTemperatureResponse(BaseModel):
    """Temperature monitoring result."""

    equipment_id: int
    code: str
    temperature: float

    minimum_temperature: float | None = None
    maximum_temperature: float | None = None

    within_range: bool
    anomaly_detected: bool

    message: str


# ─────────────────────────────────────────────
# Anomaly information
# ─────────────────────────────────────────────

class EquipmentAnomaly(BaseModel):
    """An anomaly detected on a piece of equipment."""

    equipment_id: int
    code: str
    name: str

    severity: AnomalySeverity

    anomaly_type: str = Field(
        min_length=2,
        max_length=80,
    )

    message: str = Field(
        min_length=3,
        max_length=2000,
    )

    current_temperature: float | None = None
    detected_at: datetime | None = None


class EquipmentAnomalyResponse(BaseModel):
    """List of equipment anomalies."""

    success: bool = True
    total: int = Field(ge=0)

    anomalies: list[EquipmentAnomaly] = Field(
        default_factory=list,
    )


# ─────────────────────────────────────────────
# Maintenance
# ─────────────────────────────────────────────

class EquipmentMaintenanceUpdate(BaseModel):
    """Maintenance information for laboratory equipment."""

    last_maintenance_at: datetime | None = None
    next_maintenance_at: datetime | None = None

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @model_validator(mode="after")
    def validate_maintenance_dates(self):
        last_date = self.last_maintenance_at
        next_date = self.next_maintenance_at

        if (
            last_date is not None
            and next_date is not None
            and last_date > next_date
        ):
            raise ValueError(
                "La siguiente fecha de mantenimiento debe ser "
                "posterior a la última fecha de mantenimiento."
            )

        return self


# ─────────────────────────────────────────────
# Equipment response
# ─────────────────────────────────────────────

class EquipmentResponse(EquipmentBase):
    """Equipment information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int

    current_temperature: float | None = None
    minimum_temperature: float | None = None
    maximum_temperature: float | None = None

    anomaly_detected: bool = False
    anomaly_type: str | None = None
    anomaly_message: str | None = None

    last_maintenance_at: datetime | None = None
    next_maintenance_at: datetime | None = None

    last_seen_at: datetime | None = None
    sensor_id: str | None = None

    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────
# List response
# ─────────────────────────────────────────────

class EquipmentListResponse(BaseModel):
    """List of registered laboratory equipment."""

    success: bool = True
    total: int = Field(ge=0)

    equipment: list[EquipmentResponse] = Field(
        default_factory=list,
    )


# ─────────────────────────────────────────────
# Monitoring summary
# ─────────────────────────────────────────────

class EquipmentSummary(BaseModel):
    """Aggregated equipment statistics."""

    total: int = Field(default=0, ge=0)
    operational: int = Field(default=0, ge=0)
    maintenance: int = Field(default=0, ge=0)
    out_of_service: int = Field(default=0, ge=0)
    offline: int = Field(default=0, ge=0)
    with_anomalies: int = Field(default=0, ge=0)


class EquipmentSummaryResponse(BaseModel):
    """Equipment statistics response."""

    success: bool = True
    summary: EquipmentSummary

