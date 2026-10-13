"""
Sample Service - LabGuardian AI
===============================

Servicio de gestión de muestras de laboratorio.

Responsabilidades:
- Registrar muestras.
- Consultar muestras por ID o código.
- Listar y filtrar muestras.
- Actualizar información de las muestras.
- Gestionar cambios de estado.
- Registrar eventos de trazabilidad.
- Obtener estadísticas de las muestras.
- Conservar la trazabilidad de las muestras rechazadas o descartadas.

Las transacciones se administran desde la capa que invoca el servicio.
Este módulo no ejecuta commit() ni rollback() automáticamente.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.sample import Sample
from app.models.sample_event import SampleEvent
from app.schemas.sample import (
    SampleCreate,
    SampleStatus,
    SampleStatusUpdate,
    SampleUpdate,
)
from app.schemas.sample_event import (
    SampleEventSeverity,
    SampleEventStatus,
    SampleEventType,
)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class SampleServiceError(Exception):
    """Error general del servicio de muestras."""


class SampleNotFoundError(SampleServiceError):
    """No se encontró la muestra solicitada."""


class SampleAlreadyExistsError(SampleServiceError):
    """Ya existe una muestra con el código proporcionado."""


class SampleValidationError(SampleServiceError):
    """Los datos proporcionados no son válidos."""


class SampleStateError(SampleServiceError):
    """La operación no está permitida para el estado actual."""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    """Devuelve la fecha y hora UTC."""

    return datetime.now(timezone.utc)


def _enum_value(value: Any) -> Any:
    """Obtiene el valor de un enum o devuelve el valor original."""

    return getattr(value, "value", value)


def _model_data(data: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    """Convierte un esquema Pydantic o diccionario en datos utilizables."""

    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=exclude_unset)

    if hasattr(data, "dict"):
        return data.dict(exclude_unset=exclude_unset)

    if isinstance(data, dict):
        return dict(data)

    raise SampleValidationError(
        "Los datos deben ser un esquema compatible o un diccionario."
    )


def _get_sample(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
) -> Sample:
    """Busca una muestra por ID o código."""

    if (sample_id is None) == (sample_code is None):
        raise SampleValidationError(
            "Proporciona exactamente un identificador: "
            "sample_id o sample_code."
        )

    query = db.query(Sample)

    if sample_id is not None:
        sample = query.filter(Sample.id == sample_id).first()
    else:
        code = str(sample_code).strip()

        if not code:
            raise SampleValidationError(
                "El código de la muestra no puede estar vacío."
            )

        sample = query.filter(Sample.code == code).first()

    if sample is None:
        raise SampleNotFoundError(
            "No se encontró la muestra solicitada."
        )

    return sample


def _record_event(
    db: Session,
    *,
    sample: Sample,
    event_type: SampleEventType,
    title: str,
    description: str,
    performed_by: str | None = None,
    severity: SampleEventSeverity = SampleEventSeverity.INFO,
    event_metadata: dict[str, Any] | None = None,
) -> SampleEvent:
    """Crea un evento de trazabilidad asociado a una muestra."""

    event = SampleEvent(
        sample_id=sample.id,
        event_type=_enum_value(event_type),
        title=title,
        description=description,
        status=_enum_value(SampleEventStatus.COMPLETED),
        severity=_enum_value(severity),
        location=sample.storage_location,
        performed_by=performed_by,
        event_metadata=event_metadata or {},
        occurred_at=_utc_now(),
    )

    db.add(event)
    db.flush()

    return event


def _normalize_status(status: Any) -> str:
    """Normaliza y valida un estado de muestra."""

    value = str(_enum_value(status)).strip().upper()

    allowed = {
        _enum_value(item)
        for item in SampleStatus
    }

    if value not in allowed:
        raise SampleValidationError(
            f"Estado de muestra no válido: {value}."
        )

    return value


def _set_status_timestamp(sample: Sample, status: str) -> None:
    """Actualiza las marcas temporales relacionadas con el estado."""

    now = _utc_now()

    if status == "RECEIVED" and sample.received_at is None:
        sample.received_at = now

    elif status == "PROCESSING":
        if sample.processing_started_at is None:
            sample.processing_started_at = now

    elif status == "PROCESSED":
        if sample.processed_at is None:
            sample.processed_at = now

    elif status == "COMPLETED":
        if sample.result_at is None:
            sample.result_at = now

    sample.updated_at = now


def _status_event_type(status: str) -> SampleEventType:
    """Mapea el estado nuevo al tipo de evento más apropiado."""

    mapping = {
        "RECEIVED": SampleEventType.RECEIVED,
        "IDENTIFIED": SampleEventType.IDENTIFIED,
        "IN_TRANSPORT": SampleEventType.TRANSPORT_STARTED,
        "IN_STORAGE": SampleEventType.STORAGE_STARTED,
        "PROCESSING": SampleEventType.PROCESSING_STARTED,
        "PROCESSED": SampleEventType.PROCESSING_COMPLETED,
        "ANALYZING": SampleEventType.ANALYSIS_STARTED,
        "COMPLETED": SampleEventType.RESULT_RELEASED,
        "REJECTED": SampleEventType.SAMPLE_REJECTED,
        "DISCARDED": SampleEventType.SAMPLE_DISCARDED,
    }

    return mapping.get(status, SampleEventType.MANUAL_UPDATE)


# ---------------------------------------------------------------------------
# Creación
# ---------------------------------------------------------------------------

def create_sample(
    db: Session,
    data: SampleCreate | dict[str, Any],
    *,
    performed_by: str | None = None,
) -> Sample:
    """
    Registra una muestra nueva y crea su primer evento de trazabilidad.

    El código de muestra debe ser único.
    """

    values = _model_data(data)

    code = str(values.get("code", "")).strip()

    if not code:
        raise SampleValidationError(
            "El código de la muestra es obligatorio."
        )

    existing = (
        db.query(Sample.id)
        .filter(Sample.code == code)
        .first()
    )

    if existing is not None:
        raise SampleAlreadyExistsError(
            f"Ya existe una muestra con el código {code}."
        )

    values["code"] = code

    # El riesgo se calcula por el servicio especializado, no se acepta
    # desde el formulario de registro de una muestra.
    protected_fields = {
        "id",
        "risk_score",
        "risk_level",
        "risk_explanation",
        "anomaly_detected",
        "created_at",
        "updated_at",
    }

    for field in protected_fields:
        values.pop(field, None)

    if "status" in values:
        values["status"] = _normalize_status(values["status"])

    if "priority" in values:
        values["priority"] = _enum_value(values["priority"])

    if "sample_type" in values:
        values["sample_type"] = _enum_value(values["sample_type"])

    now = _utc_now()

    values.setdefault("status", "RECEIVED")
    values.setdefault("priority", "NORMAL")
    values.setdefault("received_at", now)

    sample = Sample(**values)
    db.add(sample)

    try:
        db.flush()

        _record_event(
            db,
            sample=sample,
            event_type=SampleEventType.RECEIVED,
            title="Muestra registrada",
            description=(
                f"La muestra {sample.code} fue registrada en el sistema."
            ),
            performed_by=performed_by,
            event_metadata={
                "initial_status": _enum_value(sample.status),
            },
        )

        return sample

    except IntegrityError as exc:
        # La capa llamadora debe hacer rollback antes de reutilizar
        # la sesión después de un error de integridad.
        raise SampleAlreadyExistsError(
            "No fue posible registrar la muestra. "
            "Comprueba que el código sea único y que los datos "
            "cumplan las restricciones de la base de datos."
        ) from exc


# ---------------------------------------------------------------------------
# Consultas individuales
# ---------------------------------------------------------------------------

def get_sample_by_id(db: Session, sample_id: int) -> Sample:
    """Obtiene una muestra mediante su ID."""

    return _get_sample(db, sample_id=sample_id)


def get_sample_by_code(db: Session, sample_code: str) -> Sample:
    """Obtiene una muestra mediante su código único."""

    return _get_sample(db, sample_code=sample_code)


def get_sample_events(
    db: Session,
    sample_id: int,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[SampleEvent]:
    """Obtiene el historial cronológico de una muestra."""

    _get_sample(db, sample_id=sample_id)

    if not 1 <= limit <= 1000:
        raise SampleValidationError(
            "El límite debe estar entre 1 y 1000."
        )

    if offset < 0:
        raise SampleValidationError(
            "El desplazamiento no puede ser negativo."
        )

    return (
        db.query(SampleEvent)
        .filter(SampleEvent.sample_id == sample_id)
        .order_by(
            SampleEvent.occurred_at.desc(),
            SampleEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Listado y filtros
# ---------------------------------------------------------------------------

def list_samples(
    db: Session,
    *,
    status: str | SampleStatus | None = None,
    priority: str | None = None,
    sample_type: str | None = None,
    laboratory_area: str | None = None,
    risk_level: str | None = None,
    anomaly_detected: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Devuelve muestras paginadas y permite aplicar filtros combinados.

    La búsqueda de texto contempla código, tipo de muestra,
    área de laboratorio y ubicación de almacenamiento.
    """

    if not 1 <= limit <= 1000:
        raise SampleValidationError(
            "El límite debe estar entre 1 y 1000."
        )

    if offset < 0:
        raise SampleValidationError(
            "El desplazamiento no puede ser negativo."
        )

    query = db.query(Sample)

    if status is not None:
        query = query.filter(
            Sample.status == _normalize_status(status)
        )

    if priority is not None:
        query = query.filter(
            Sample.priority == str(_enum_value(priority)).upper()
        )

    if sample_type is not None:
        query = query.filter(
            Sample.sample_type == str(_enum_value(sample_type)).upper()
        )

    if laboratory_area:
        query = query.filter(
            Sample.laboratory_area.ilike(
                f"%{laboratory_area.strip()}%"
            )
        )

    if risk_level is not None:
        level = str(_enum_value(risk_level)).upper()

        if level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise SampleValidationError(
                "El nivel de riesgo no es válido."
            )

        query = query.filter(Sample.risk_level == level)

    if anomaly_detected is not None:
        query = query.filter(
            Sample.anomaly_detected == anomaly_detected
        )

    if search and search.strip():
        term = f"%{search.strip()}%"

        query = query.filter(
            or_(
                Sample.code.ilike(term),
                Sample.sample_type.ilike(term),
                Sample.laboratory_area.ilike(term),
                Sample.storage_location.ilike(term),
            )
        )

    total = query.order_by(None).count()

    items = (
        query
        .order_by(Sample.created_at.desc(), Sample.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


# ---------------------------------------------------------------------------
# Actualización de información
# ---------------------------------------------------------------------------

def update_sample(
    db: Session,
    sample_id: int,
    data: SampleUpdate | dict[str, Any],
    *,
    performed_by: str | None = None,
) -> Sample:
    """
    Actualiza los datos editables de una muestra.

    El cambio de estado se realiza mediante update_sample_status().
    El riesgo y los campos de auditoría no pueden modificarse aquí.
    """

    sample = _get_sample(db, sample_id=sample_id)
    values = _model_data(data, exclude_unset=True)

    protected_fields = {
        "id",
        "code",
        "status",
        "risk_score",
        "risk_level",
        "risk_explanation",
        "anomaly_detected",
        "created_at",
        "updated_at",
    }

    forbidden = protected_fields.intersection(values)

    if forbidden:
        raise SampleValidationError(
            "Estos campos no pueden actualizarse desde este método: "
            + ", ".join(sorted(forbidden))
        )

    if not values:
        return sample

    for field in values:
        if not hasattr(sample, field):
            raise SampleValidationError(
                f"Campo no reconocido para una muestra: {field}."
            )

    for field in ("priority", "sample_type"):
        if field in values:
            values[field] = _enum_value(values[field])

    for field, value in values.items():
        setattr(sample, field, value)

    sample.updated_at = _utc_now()

    db.add(sample)

    try:
        db.flush()

        _record_event(
            db,
            sample=sample,
            event_type=SampleEventType.MANUAL_UPDATE,
            title="Datos de la muestra actualizados",
            description=(
                f"Se actualizaron datos de la muestra {sample.code}."
            ),
            performed_by=performed_by,
            event_metadata={
                "updated_fields": sorted(values.keys()),
            },
        )

        return sample

    except IntegrityError as exc:
        raise SampleValidationError(
            "La actualización incumple una restricción de la base de datos."
        ) from exc


# ---------------------------------------------------------------------------
# Cambio de estado
# ---------------------------------------------------------------------------

def update_sample_status(
    db: Session,
    sample_id: int,
    data: SampleStatusUpdate | dict[str, Any] | SampleStatus | str,
    *,
    performed_by: str | None = None,
    description: str | None = None,
) -> Sample:
    """
    Cambia el estado de una muestra y registra el cambio en el historial.

    Este método valida que el estado exista, pero no impone un flujo
    clínico universal: las transiciones permitidas deben definirse
    conforme al protocolo de cada laboratorio.
    """

    sample = _get_sample(db, sample_id=sample_id)

    if isinstance(data, (str, SampleStatus)):
        new_status = _normalize_status(data)
        notes = description
    else:
        values = _model_data(data, exclude_unset=True)

        if "status" not in values:
            raise SampleValidationError(
                "Debes especificar el nuevo estado de la muestra."
            )

        new_status = _normalize_status(values["status"])
        notes = (
            values.get("notes")
            or values.get("description")
            or description
        )

    current_status = str(_enum_value(sample.status)).upper()

    if current_status == new_status:
        return sample

    # Un estado terminal no se revierte automáticamente. Si se necesita
    # una corrección, debe implementarse un flujo explícito y auditable.
    terminal_states = {"COMPLETED", "REJECTED", "DISCARDED"}

    if current_status in terminal_states:
        raise SampleStateError(
            f"No se permite cambiar automáticamente una muestra "
            f"desde el estado terminal {current_status}."
        )

    sample.status = new_status
    _set_status_timestamp(sample, new_status)

    db.add(sample)

    try:
        db.flush()

        _record_event(
            db,
            sample=sample,
            event_type=_status_event_type(new_status),
            title=f"Estado actualizado: {new_status}",
            description=(
                str(notes).strip()
                if notes
                else (
                    f"La muestra {sample.code} cambió de "
                    f"{current_status} a {new_status}."
                )
            ),
            performed_by=performed_by,
            event_metadata={
                "previous_status": current_status,
                "new_status": new_status,
            },
        )

        return sample

    except IntegrityError as exc:
        raise SampleValidationError(
            "No fue posible actualizar el estado de la muestra."
        ) from exc


# ---------------------------------------------------------------------------
# Rechazo y descarte
# ---------------------------------------------------------------------------

def reject_sample(
    db: Session,
    sample_id: int,
    *,
    reason: str,
    performed_by: str | None = None,
) -> Sample:
    """Rechaza una muestra conservando su historial."""

    if not reason or not reason.strip():
        raise SampleValidationError(
            "Debes indicar el motivo del rechazo."
        )

    return update_sample_status(
        db,
        sample_id,
        SampleStatus.REJECTED,
        performed_by=performed_by,
        description=f"Muestra rechazada. Motivo: {reason.strip()}",
    )


def discard_sample(
    db: Session,
    sample_id: int,
    *,
    reason: str,
    performed_by: str | None = None,
) -> Sample:
    """Marca una muestra como descartada sin borrar su trazabilidad."""

    if not reason or not reason.strip():
        raise SampleValidationError(
            "Debes indicar el motivo del descarte."
        )

    return update_sample_status(
        db,
        sample_id,
        SampleStatus.DISCARDED,
        performed_by=performed_by,
        description=f"Muestra descartada. Motivo: {reason.strip()}",
    )


# ---------------------------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------------------------

def get_sample_statistics(db: Session) -> dict[str, Any]:
    """Calcula estadísticas generales para el panel de control."""

    total = db.query(func.count(Sample.id)).scalar() or 0

    status_rows = (
        db.query(Sample.status, func.count(Sample.id))
        .group_by(Sample.status)
        .all()
    )

    risk_rows = (
        db.query(Sample.risk_level, func.count(Sample.id))
        .group_by(Sample.risk_level)
        .all()
    )

    priority_rows = (
        db.query(Sample.priority, func.count(Sample.id))
        .group_by(Sample.priority)
        .all()
    )

    anomalies = (
        db.query(func.count(Sample.id))
        .filter(Sample.anomaly_detected.is_(True))
        .scalar()
        or 0
    )

    return {
        "total_samples": total,
        "by_status": {
            str(_enum_value(key)): count
            for key, count in status_rows
        },
        "by_risk_level": {
            str(_enum_value(key)): count
            for key, count in risk_rows
        },
        "by_priority": {
            str(_enum_value(key)): count
            for key, count in priority_rows
        },
        "anomalies_detected": anomalies,
        "generated_at": _utc_now(),
    }
