"""
Traceability Service - LabGuardian AI
=====================================

Servicio de trazabilidad y auditoría de muestras de laboratorio.

Responsabilidades:
- Registrar eventos en el historial de una muestra.
- Consultar la línea de tiempo de trazabilidad.
- Filtrar eventos por tipo, estado y rango de fechas.
- Generar resúmenes del recorrido de una muestra.
- Detectar inconsistencias cronológicas.
- Consultar eventos relacionados con equipos.
- Proporcionar información para auditorías.

Este servicio no realiza commit() ni rollback().
La gestión de transacciones corresponde a la capa llamadora.

NOTA:
La detección de inconsistencias es una ayuda técnica y no sustituye
los procedimientos de calidad y auditoría del laboratorio.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.sample import Sample
from app.models.sample_event import SampleEvent
from app.schemas.sample_event import (
    SampleEventCreate,
    SampleEventSeverity,
    SampleEventStatus,
    SampleEventType,
)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class TraceabilityServiceError(Exception):
    """Error general del servicio de trazabilidad."""


class TraceabilitySampleNotFoundError(TraceabilityServiceError):
    """La muestra solicitada no existe."""


class TraceabilityEventNotFoundError(TraceabilityServiceError):
    """El evento solicitado no existe."""


class TraceabilityValidationError(TraceabilityServiceError):
    """Los datos del evento no son válidos."""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    """Obtiene la fecha y hora UTC."""

    return datetime.now(timezone.utc)


def _enum_value(value: Any) -> Any:
    """Devuelve el valor de un enum o el valor original."""

    return getattr(value, "value", value)


def _serialize_datetime(value: datetime | None) -> str | None:
    """Convierte una fecha en una cadena ISO 8601."""

    if value is None:
        return None

    return value.isoformat()


def _model_data(data: Any) -> dict[str, Any]:
    """Convierte un esquema Pydantic o diccionario a un diccionario."""

    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)

    if hasattr(data, "dict"):
        return data.dict(exclude_unset=True)

    if isinstance(data, dict):
        return dict(data)

    raise TraceabilityValidationError(
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
        raise TraceabilityValidationError(
            "Proporciona exactamente un identificador: "
            "sample_id o sample_code."
        )

    query = db.query(Sample)

    if sample_id is not None:
        sample = query.filter(Sample.id == sample_id).first()
    else:
        code = str(sample_code).strip()

        if not code:
            raise TraceabilityValidationError(
                "El código de la muestra no puede estar vacío."
            )

        sample = query.filter(Sample.code == code).first()

    if sample is None:
        raise TraceabilitySampleNotFoundError(
            "No se encontró la muestra solicitada."
        )

    return sample


def _get_event(
    db: Session,
    event_id: int,
) -> SampleEvent:
    """Busca un evento por su ID."""

    event = (
        db.query(SampleEvent)
        .filter(SampleEvent.id == event_id)
        .first()
    )

    if event is None:
        raise TraceabilityEventNotFoundError(
            f"No se encontró el evento con ID {event_id}."
        )

    return event


def _validate_datetime(
    value: datetime | None,
    field_name: str,
) -> datetime | None:
    """Valida y normaliza una fecha a UTC."""

    if value is None:
        return None

    if not isinstance(value, datetime):
        raise TraceabilityValidationError(
            f"{field_name} debe ser una fecha válida."
        )

    if value.tzinfo is None:
        # Los valores sin zona horaria se interpretan como UTC.
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _event_to_dict(event: SampleEvent) -> dict[str, Any]:
    """Serializa un evento sin exponer objetos SQLAlchemy."""

    return {
        "id": event.id,
        "sample_id": event.sample_id,
        "event_type": _enum_value(event.event_type),
        "title": event.title,
        "description": event.description,
        "status": _enum_value(event.status),
        "severity": _enum_value(event.severity),
        "temperature": event.temperature,
        "duration_minutes": event.duration_minutes,
        "location": event.location,
        "performed_by": event.performed_by,
        "equipment_id": event.equipment_id,
        "metadata": event.event_metadata or {},
        "occurred_at": _serialize_datetime(event.occurred_at),
        "created_at": _serialize_datetime(event.created_at),
    }


# ---------------------------------------------------------------------------
# Registro de eventos
# ---------------------------------------------------------------------------

def record_traceability_event(
    db: Session,
    data: SampleEventCreate | dict[str, Any],
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
) -> SampleEvent:
    """
    Registra un evento de trazabilidad para una muestra existente.

    El identificador de la muestra puede proporcionarse en data
    o mediante sample_id/sample_code.

    Si se especifica más de una fuente de identificación, deben
    referirse a la misma muestra.
    """

    values = _model_data(data)

    payload_sample_id = values.pop("sample_id", None)

    if sample_id is not None and payload_sample_id is not None:
        if sample_id != payload_sample_id:
            raise TraceabilityValidationError(
                "Los identificadores de muestra no coinciden."
            )

    resolved_sample_id = (
        sample_id
        if sample_id is not None
        else payload_sample_id
    )

    if sample_code is not None:
        sample = _get_sample(db, sample_code=sample_code)

        if resolved_sample_id is not None:
            if sample.id != resolved_sample_id:
                raise TraceabilityValidationError(
                    "El ID y el código corresponden a muestras distintas."
                )
    elif resolved_sample_id is not None:
        sample = _get_sample(db, sample_id=resolved_sample_id)
    else:
        raise TraceabilityValidationError(
            "Debes indicar el ID o código de la muestra."
        )

    allowed_fields = {
        "event_type",
        "title",
        "description",
        "status",
        "severity",
        "temperature",
        "duration_minutes",
        "location",
        "performed_by",
        "equipment_id",
        "metadata",
        "occurred_at",
    }

    unexpected = set(values) - allowed_fields

    if unexpected:
        raise TraceabilityValidationError(
            "Campos no permitidos para un evento: "
            + ", ".join(sorted(unexpected))
        )

    event_type = values.get("event_type")

    if event_type is None:
        raise TraceabilityValidationError(
            "El tipo de evento es obligatorio."
        )

    allowed_types = {
        _enum_value(item)
        for item in SampleEventType
    }

    normalized_type = str(_enum_value(event_type)).upper()

    if normalized_type not in allowed_types:
        raise TraceabilityValidationError(
            f"Tipo de evento no válido: {normalized_type}."
        )

    title = str(values.get("title", "")).strip()

    if not title:
        raise TraceabilityValidationError(
            "El título del evento es obligatorio."
        )

    description = str(values.get("description", "")).strip()

    status = str(
        _enum_value(
            values.get("status", SampleEventStatus.COMPLETED)
        )
    ).upper()

    allowed_statuses = {
        _enum_value(item)
        for item in SampleEventStatus
    }

    if status not in allowed_statuses:
        raise TraceabilityValidationError(
            f"Estado de evento no válido: {status}."
        )

    severity = str(
        _enum_value(
            values.get("severity", SampleEventSeverity.INFO)
        )
    ).upper()

    allowed_severities = {
        _enum_value(item)
        for item in SampleEventSeverity
    }

    if severity not in allowed_severities:
        raise TraceabilityValidationError(
            f"Severidad no válida: {severity}."
        )

    temperature = values.get("temperature")
    if temperature is not None:
        try:
            temperature = float(temperature)
        except (TypeError, ValueError) as exc:
            raise TraceabilityValidationError(
                "La temperatura debe ser numérica."
            ) from exc

        if not -100.0 <= temperature <= 200.0:
            raise TraceabilityValidationError(
                "La temperatura está fuera del rango técnico permitido."
            )

    duration = values.get("duration_minutes")
    if duration is not None:
        try:
            duration = float(duration)
        except (TypeError, ValueError) as exc:
            raise TraceabilityValidationError(
                "La duración debe ser numérica."
            ) from exc

        if duration < 0:
            raise TraceabilityValidationError(
                "La duración no puede ser negativa."
            )

    occurred_at = _validate_datetime(
        values.get("occurred_at"),
        "occurred_at",
    ) or _utc_now()

    metadata = values.get("metadata") or {}

    if not isinstance(metadata, dict):
        raise TraceabilityValidationError(
            "Los metadatos del evento deben ser un objeto."
        )

    event = SampleEvent(
        sample_id=sample.id,
        event_type=normalized_type,
        title=title,
        description=description,
        status=status,
        severity=severity,
        temperature=temperature,
        duration_minutes=duration,
        location=values.get("location") or sample.storage_location,
        performed_by=values.get("performed_by"),
        equipment_id=values.get("equipment_id"),
        event_metadata=metadata,
        occurred_at=occurred_at,
    )

    db.add(event)

    try:
        db.flush()
    except IntegrityError as exc:
        raise TraceabilityValidationError(
            "No fue posible registrar el evento. "
            "Verifica las referencias a la muestra y al equipo."
        ) from exc

    return event


# ---------------------------------------------------------------------------
# Consulta del historial
# ---------------------------------------------------------------------------

def get_traceability_timeline(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
    event_type: str | SampleEventType | None = None,
    status: str | SampleEventStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Obtiene la línea de tiempo de una muestra.

    Los eventos se devuelven del más reciente al más antiguo.
    """

    sample = _get_sample(
        db,
        sample_id=sample_id,
        sample_code=sample_code,
    )

    if not 1 <= limit <= 1000:
        raise TraceabilityValidationError(
            "El límite debe estar entre 1 y 1000."
        )

    if offset < 0:
        raise TraceabilityValidationError(
            "El desplazamiento no puede ser negativo."
        )

    start = _validate_datetime(start_date, "start_date")
    end = _validate_datetime(end_date, "end_date")

    if start and end and start > end:
        raise TraceabilityValidationError(
            "La fecha inicial no puede ser posterior a la fecha final."
        )

    query = db.query(SampleEvent).filter(
        SampleEvent.sample_id == sample.id
    )

    if event_type is not None:
        normalized_type = str(_enum_value(event_type)).upper()

        allowed_types = {
            _enum_value(item)
            for item in SampleEventType
        }

        if normalized_type not in allowed_types:
            raise TraceabilityValidationError(
                f"Tipo de evento no válido: {normalized_type}."
            )

        query = query.filter(
            SampleEvent.event_type == normalized_type
        )

    if status is not None:
        normalized_status = str(_enum_value(status)).upper()

        allowed_statuses = {
            _enum_value(item)
            for item in SampleEventStatus
        }

        if normalized_status not in allowed_statuses:
            raise TraceabilityValidationError(
                f"Estado de evento no válido: {normalized_status}."
            )

        query = query.filter(
            SampleEvent.status == normalized_status
        )

    if start is not None:
        query = query.filter(SampleEvent.occurred_at >= start)

    if end is not None:
        query = query.filter(SampleEvent.occurred_at <= end)

    total = query.order_by(None).count()

    events = (
        query
        .order_by(
            SampleEvent.occurred_at.desc(),
            SampleEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "sample_id": sample.id,
        "sample_code": sample.code,
        "current_status": _enum_value(sample.status),
        "total_events": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(events) < total,
        "events": [_event_to_dict(event) for event in events],
    }


# ---------------------------------------------------------------------------
# Resumen de trazabilidad
# ---------------------------------------------------------------------------

def get_traceability_summary(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
) -> dict[str, Any]:
    """Genera un resumen del recorrido registrado de una muestra."""

    sample = _get_sample(
        db,
        sample_id=sample_id,
        sample_code=sample_code,
    )

    events = (
        db.query(SampleEvent)
        .filter(SampleEvent.sample_id == sample.id)
        .order_by(
            SampleEvent.occurred_at.asc(),
            SampleEvent.id.asc(),
        )
        .all()
    )

    event_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}

    for event in events:
        event_type = str(_enum_value(event.event_type))
        event_status = str(_enum_value(event.status))
        severity = str(_enum_value(event.severity))

        event_counts[event_type] = (
            event_counts.get(event_type, 0) + 1
        )

        status_counts[event_status] = (
            status_counts.get(event_status, 0) + 1
        )

        severity_counts[severity] = (
            severity_counts.get(severity, 0) + 1
        )

    first_event = events[0] if events else None
    last_event = events[-1] if events else None

    elapsed_minutes = None

    if (
        first_event is not None
        and last_event is not None
        and first_event.occurred_at is not None
        and last_event.occurred_at is not None
    ):
        first_time = _validate_datetime(
            first_event.occurred_at,
            "first_event.occurred_at",
        )
        last_time = _validate_datetime(
            last_event.occurred_at,
            "last_event.occurred_at",
        )

        elapsed_minutes = round(
            max(
                0.0,
                (last_time - first_time).total_seconds() / 60.0,
            ),
            2,
        )

    return {
        "sample_id": sample.id,
        "sample_code": sample.code,
        "sample_status": _enum_value(sample.status),
        "risk_level": _enum_value(sample.risk_level),
        "anomaly_detected": sample.anomaly_detected,
        "total_events": len(events),
        "event_counts": event_counts,
        "status_counts": status_counts,
        "severity_counts": severity_counts,
        "first_event_at": (
            _serialize_datetime(first_event.occurred_at)
            if first_event else None
        ),
        "last_event_at": (
            _serialize_datetime(last_event.occurred_at)
            if last_event else None
        ),
        "elapsed_minutes_between_recorded_events": elapsed_minutes,
        "generated_at": _serialize_datetime(_utc_now()),
    }


# ---------------------------------------------------------------------------
# Auditoría cronológica
# ---------------------------------------------------------------------------

def audit_traceability(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
) -> dict[str, Any]:
    """
    Busca señales de inconsistencia en las marcas temporales.

    Detecta:
    - Eventos cuya fecha es anterior al evento registrado previamente.
    - Eventos con fecha futura respecto al momento de auditoría.
    - Eventos sin fecha de ocurrencia.

    Una anomalía cronológica es una señal para revisión, no una prueba
    automática de manipulación o incumplimiento.
    """

    sample = _get_sample(
        db,
        sample_id=sample_id,
        sample_code=sample_code,
    )

    events = (
        db.query(SampleEvent)
        .filter(SampleEvent.sample_id == sample.id)
        .order_by(
            SampleEvent.occurred_at.asc(),
            SampleEvent.id.asc(),
        )
        .all()
    )

    now = _utc_now()
    findings: list[dict[str, Any]] = []
    previous_event: SampleEvent | None = None

    for event in events:
        occurred_at = event.occurred_at

        if occurred_at is None:
            findings.append({
                "code": "MISSING_OCCURRED_AT",
                "event_id": event.id,
                "message": "El evento no tiene fecha de ocurrencia.",
            })
            continue

        normalized_time = _validate_datetime(
            occurred_at,
            "occurred_at",
        )

        if normalized_time > now:
            findings.append({
                "code": "FUTURE_EVENT",
                "event_id": event.id,
                "occurred_at": normalized_time.isoformat(),
                "message": (
                    "El evento tiene una fecha posterior al momento "
                    "de la auditoría."
                ),
            })

        if previous_event is not None:
            previous_time = _validate_datetime(
                previous_event.occurred_at,
                "previous_event.occurred_at",
            )

            if normalized_time < previous_time:
                findings.append({
                    "code": "NON_MONOTONIC_TIMELINE",
                    "event_id": event.id,
                    "previous_event_id": previous_event.id,
                    "occurred_at": normalized_time.isoformat(),
                    "previous_occurred_at": previous_time.isoformat(),
                    "message": (
                        "La secuencia cronológica de los eventos "
                        "requiere revisión."
                    ),
                })

        if (
            previous_event is None
            or normalized_time >= _validate_datetime(
                previous_event.occurred_at,
                "previous_event.occurred_at",
            )
        ):
            previous_event = event

    return {
        "sample_id": sample.id,
        "sample_code": sample.code,
        "events_audited": len(events),
        "has_findings": bool(findings),
        "findings_count": len(findings),
        "findings": findings,
        "audited_at": _serialize_datetime(now),
    }


# ---------------------------------------------------------------------------
# Consulta de eventos relacionados con equipos
# ---------------------------------------------------------------------------

def get_equipment_traceability(
    db: Session,
    equipment_id: int,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Consulta los eventos vinculados a un equipo.

    Permite revisar cuándo se utilizó un equipo en eventos de muestras.
    """

    if equipment_id <= 0:
        raise TraceabilityValidationError(
            "El ID del equipo debe ser positivo."
        )

    if not 1 <= limit <= 1000:
        raise TraceabilityValidationError(
            "El límite debe estar entre 1 y 1000."
        )

    if offset < 0:
        raise TraceabilityValidationError(
            "El desplazamiento no puede ser negativo."
        )

    start = _validate_datetime(start_date, "start_date")
    end = _validate_datetime(end_date, "end_date")

    if start and end and start > end:
        raise TraceabilityValidationError(
            "La fecha inicial no puede ser posterior a la fecha final."
        )

    query = db.query(SampleEvent).filter(
        SampleEvent.equipment_id == equipment_id
    )

    if start:
        query = query.filter(
            SampleEvent.occurred_at >= start
        )

    if end:
        query = query.filter(
            SampleEvent.occurred_at <= end
        )

    total = query.order_by(None).count()

    events = (
        query
        .order_by(
            SampleEvent.occurred_at.desc(),
            SampleEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "equipment_id": equipment_id,
        "total_events": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(events) < total,
        "events": [_event_to_dict(event) for event in events],
    }


# ---------------------------------------------------------------------------
# Eliminación controlada
# ---------------------------------------------------------------------------

def delete_traceability_event(
    db: Session,
    event_id: int,
    *,
    reason: str,
) -> dict[str, Any]:
    """
    Bloquea la eliminación ordinaria de eventos de trazabilidad.

    Para conservar una auditoría confiable, los eventos no deberían
    borrarse físicamente. Las correcciones deben implementarse mediante
    un nuevo evento que documente la rectificación.

    La función se mantiene explícita para impedir que una ruta elimine
    eventos accidentalmente.
    """

    _get_event(db, event_id)

    if not reason or not reason.strip():
        raise TraceabilityValidationError(
            "Debes indicar el motivo de la solicitud."
        )

    raise TraceabilityValidationError(
        "No se permite eliminar físicamente eventos de trazabilidad. "
        "Registra un nuevo evento de corrección con el motivo y el "
        "usuario responsable."
    )
