
"""
Alert service for LabGuardian AI.

Centraliza la lógica de negocio relacionada con las alertas:
- Creación y consulta de alertas.
- Filtrado por estado, severidad y tipo.
- Reconocimiento y resolución.
- Estadísticas para el dashboard.
- Detección de alertas activas duplicadas.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.sample import Sample
from app.schemas.alert import (
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertType,
)


# ============================================================
# EXCEPTIONS
# ============================================================

class AlertServiceError(Exception):
    """Error base del servicio de alertas."""


class AlertNotFoundError(AlertServiceError):
    """La alerta solicitada no existe."""


class AlertValidationError(AlertServiceError):
    """Los datos de la alerta no son válidos."""


class AlertStateError(AlertServiceError):
    """La transición de estado solicitada no está permitida."""


# ============================================================
# CONSTANTS
# ============================================================

ACTIVE_STATUSES = (
    AlertStatus.ACTIVE.value,
    AlertStatus.ACKNOWLEDGED.value,
)

SEVERITY_ORDER = {
    AlertSeverity.INFO.value: 0,
    AlertSeverity.LOW.value: 1,
    AlertSeverity.MEDIUM.value: 2,
    AlertSeverity.HIGH.value: 3,
    AlertSeverity.CRITICAL.value: 4,
}


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> datetime:
    """Devuelve la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


def _enum_value(value) -> str:
    """Obtiene el valor textual de un enum o una cadena."""
    return value.value if hasattr(value, "value") else str(value)


def _get_alert_or_raise(db: Session, alert_id: int) -> Alert:
    """Obtiene una alerta por ID o genera una excepción."""
    alert = db.get(Alert, alert_id)

    if alert is None:
        raise AlertNotFoundError(
            f"No existe una alerta con ID {alert_id}."
        )

    return alert


def _validate_risk_score(risk_score: float | None) -> None:
    """Comprueba que el puntaje de riesgo esté entre 0 y 100."""
    if risk_score is not None and not 0 <= risk_score <= 100:
        raise AlertValidationError(
            "El puntaje de riesgo debe estar entre 0 y 100."
        )


def _validate_text(
    value: str | None,
    field_name: str,
    max_length: int,
    required: bool = False,
) -> str | None:
    """Normaliza y valida campos de texto."""
    if value is None:
        if required:
            raise AlertValidationError(
                f"El campo {field_name} es obligatorio."
            )
        return None

    value = value.strip()

    if not value:
        if required:
            raise AlertValidationError(
                f"El campo {field_name} no puede estar vacío."
            )
        return None

    if len(value) > max_length:
        raise AlertValidationError(
            f"El campo {field_name} supera los {max_length} caracteres."
        )

    return value


# ============================================================
# CREATE
# ============================================================

def create_alert(
    db: Session,
    *,
    alert_type: AlertType | str,
    severity: AlertSeverity | str,
    title: str,
    message: str,
    sample_id: int | None = None,
    sample_code: str | None = None,
    risk_score: float | None = None,
    source: AlertSource | str = AlertSource.SYSTEM,
    deduplicate: bool = True,
) -> Alert:
    """
    Crea una alerta.

    Si deduplicate=True, reutiliza una alerta activa equivalente
    para evitar crear repetidamente la misma alerta.

    La función no confirma la transacción: el llamador debe ejecutar
    db.commit() cuando corresponda.
    """

    title = _validate_text(
        title,
        "title",
        max_length=200,
        required=True,
    )
    message = _validate_text(
        message,
        "message",
        max_length=5000,
        required=True,
    )

    alert_type_value = _enum_value(alert_type)
    severity_value = _enum_value(severity)
    source_value = _enum_value(source)

    if severity_value not in SEVERITY_ORDER:
        raise AlertValidationError(
            f"Severidad no válida: {severity_value}."
        )

    _validate_risk_score(risk_score)

    # Si se proporciona un ID de muestra, se comprueba su existencia.
    sample = None

    if sample_id is not None:
        sample = db.get(Sample, sample_id)

        if sample is None:
            raise AlertValidationError(
                f"No existe una muestra con ID {sample_id}."
            )

        if sample_code is not None:
            if sample.code != sample_code.strip().upper():
                raise AlertValidationError(
                    "El código de muestra no coincide con el ID proporcionado."
                )

        sample_code = sample.code

    elif sample_code is not None:
        sample_code = sample_code.strip().upper()

        sample = db.scalar(
            select(Sample).where(Sample.code == sample_code)
        )

        if sample is not None:
            sample_id = sample.id

    if deduplicate:
        statement = select(Alert).where(
            Alert.title == title,
            Alert.alert_type == alert_type_value,
            Alert.source == source_value,
            Alert.status.in_(ACTIVE_STATUSES),
        )

        if sample_id is not None:
            statement = statement.where(
                Alert.sample_id == sample_id
            )
        else:
            statement = statement.where(
                Alert.sample_id.is_(None),
                Alert.sample_code == sample_code,
            )

        existing = db.scalar(
            statement.order_by(Alert.created_at.desc())
        )

        if existing is not None:
            # Actualiza la información si la alerta sigue activa.
            existing.severity = severity_value
            existing.message = message
            existing.risk_score = risk_score
            existing.updated_at = _utc_now()

            db.flush()
            return existing

    alert = Alert(
        sample_id=sample_id,
        sample_code=sample_code,
        alert_type=alert_type_value,
        severity=severity_value,
        status=AlertStatus.ACTIVE.value,
        title=title,
        message=message,
        risk_score=risk_score,
        source=source_value,
    )

    db.add(alert)
    db.flush()

    return alert


# ============================================================
# READ
# ============================================================

def get_alert(db: Session, alert_id: int) -> Alert:
    """Obtiene una alerta por su identificador."""
    if alert_id <= 0:
        raise AlertValidationError(
            "El ID de la alerta debe ser mayor que cero."
        )

    return _get_alert_or_raise(db, alert_id)


def list_alerts(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: AlertStatus | str | None = None,
    severity: AlertSeverity | str | None = None,
    alert_type: AlertType | str | None = None,
    source: AlertSource | str | None = None,
    sample_code: str | None = None,
    active_only: bool = False,
    order_by_severity: bool = False,
) -> dict:
    """
    Devuelve alertas paginadas con filtros opcionales.

    El resultado contiene total, page, page_size e items.
    """

    if page < 1:
        raise AlertValidationError(
            "La página debe ser mayor o igual a uno."
        )

    if not 1 <= page_size <= 100:
        raise AlertValidationError(
            "page_size debe estar entre 1 y 100."
        )

    statement = select(Alert)
    count_statement = select(func.count(Alert.id))

    filters = []

    if active_only:
        filters.append(Alert.status.in_(ACTIVE_STATUSES))

    if status is not None:
        filters.append(Alert.status == _enum_value(status))

    if severity is not None:
        filters.append(Alert.severity == _enum_value(severity))

    if alert_type is not None:
        filters.append(Alert.alert_type == _enum_value(alert_type))

    if source is not None:
        filters.append(Alert.source == _enum_value(source))

    if sample_code is not None:
        filters.append(
            Alert.sample_code == sample_code.strip().upper()
        )

    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    total = db.scalar(count_statement) or 0

    if order_by_severity:
        # La prioridad clínica se ordena explícitamente para evitar
        # depender del orden alfabético de las severidades.
        alerts = list(
            db.scalars(
                statement.order_by(
                    Alert.created_at.desc(),
                    Alert.id.desc(),
                ).offset((page - 1) * page_size).limit(page_size)
            ).all()
        )

        alerts.sort(
            key=lambda alert: (
                -SEVERITY_ORDER.get(alert.severity, -1),
                -(
                    alert.created_at.timestamp()
                    if alert.created_at
                    else 0
                ),
            )
        )
    else:
        alerts = list(
            db.scalars(
                statement.order_by(
                    Alert.created_at.desc(),
                    Alert.id.desc(),
                ).offset((page - 1) * page_size).limit(page_size)
            ).all()
        )

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": alerts,
    }


def get_active_alerts(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Obtiene las alertas activas o reconocidas."""
    return list_alerts(
        db,
        page=page,
        page_size=page_size,
        active_only=True,
        order_by_severity=True,
    )


def get_alerts_by_sample(
    db: Session,
    sample_code: str,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Consulta el historial de alertas de una muestra."""
    sample_code = _validate_text(
        sample_code,
        "sample_code",
        max_length=50,
        required=True,
    )

    return list_alerts(
        db,
        page=page,
        page_size=page_size,
        sample_code=sample_code.upper(),
    )


# ============================================================
# ACKNOWLEDGE
# ============================================================

def acknowledge_alert(
    db: Session,
    alert_id: int,
    *,
    acknowledged_by: str,
) -> Alert:
    """
    Marca una alerta activa como reconocida.

    El nombre del responsable se registra en resolved_by únicamente
    si tu modelo no dispone de un campo acknowledged_by; para evitar
    confundir reconocimiento con resolución, este servicio no
    reutiliza resolved_by y exige agregar un campo propio si necesitas
    auditar el responsable del reconocimiento.

    Por ahora, esta función cambia el estado, pero no registra
    acknowledged_by en la tabla.
    """

    alert = _get_alert_or_raise(db, alert_id)

    acknowledged_by = _validate_text(
        acknowledged_by,
        "acknowledged_by",
        max_length=150,
        required=True,
    )

    if alert.status == AlertStatus.ACKNOWLEDGED.value:
        return alert

    if alert.status != AlertStatus.ACTIVE.value:
        raise AlertStateError(
            "Solo se pueden reconocer alertas activas."
        )

    alert.status = AlertStatus.ACKNOWLEDGED.value
    alert.updated_at = _utc_now()

    db.flush()

    return alert


# ============================================================
# UPDATE
# ============================================================

def update_alert(
    db: Session,
    alert_id: int,
    *,
    changes: dict,
) -> Alert:
    """Actualiza los campos permitidos de una alerta."""

    alert = _get_alert_or_raise(db, alert_id)

    allowed_fields = {
        "severity",
        "title",
        "message",
        "risk_score",
    }

    unknown_fields = set(changes) - allowed_fields

    if unknown_fields:
        raise AlertValidationError(
            "Campos no permitidos: "
            + ", ".join(sorted(unknown_fields))
        )

    if "severity" in changes:
        severity = _enum_value(changes["severity"])

        if severity not in SEVERITY_ORDER:
            raise AlertValidationError(
                f"Severidad no válida: {severity}."
            )

        alert.severity = severity

    if "title" in changes:
        alert.title = _validate_text(
            changes["title"],
            "title",
            max_length=200,
            required=True,
        )

    if "message" in changes:
        alert.message = _validate_text(
            changes["message"],
            "message",
            max_length=5000,
            required=True,
        )

    if "risk_score" in changes:
        _validate_risk_score(changes["risk_score"])
        alert.risk_score = changes["risk_score"]

    alert.updated_at = _utc_now()

    db.flush()

    return alert


# ============================================================
# RESOLVE
# ============================================================

def resolve_alert(
    db: Session,
    alert_id: int,
    *,
    resolved_by: str,
    resolution_notes: str | None = None,
) -> Alert:
    """Resuelve una alerta activa o reconocida."""

    alert = _get_alert_or_raise(db, alert_id)

    resolved_by = _validate_text(
        resolved_by,
        "resolved_by",
        max_length=150,
        required=True,
    )

    resolution_notes = _validate_text(
        resolution_notes,
        "resolution_notes",
        max_length=2000,
    )

    if alert.status == AlertStatus.RESOLVED.value:
        raise AlertStateError(
            "La alerta ya se encuentra resuelta."
        )

    if alert.status == "DISMISSED":
        raise AlertStateError(
            "No se puede resolver una alerta descartada."
        )

    if alert.status not in ACTIVE_STATUSES:
        raise AlertStateError(
            f"No se puede resolver una alerta con estado {alert.status}."
        )

    now = _utc_now()

    alert.status = AlertStatus.RESOLVED.value
    alert.resolved_by = resolved_by
    alert.resolution_notes = resolution_notes
    alert.resolved_at = now
    alert.updated_at = now

    db.flush()

    return alert


# ============================================================
# DISMISS
# ============================================================

def dismiss_alert(
    db: Session,
    alert_id: int,
    *,
    dismissed_by: str,
    reason: str,
) -> Alert:
    """Descarta una alerta que se determinó que no requiere acción."""

    alert = _get_alert_or_raise(db, alert_id)

    dismissed_by = _validate_text(
        dismissed_by,
        "dismissed_by",
        max_length=150,
        required=True,
    )

    reason = _validate_text(
        reason,
        "reason",
        max_length=2000,
        required=True,
    )

    if alert.status not in ACTIVE_STATUSES:
        raise AlertStateError(
            "Solo se pueden descartar alertas activas o reconocidas."
        )

    now = _utc_now()

    alert.status = AlertStatus.DISMISSED.value
    alert.resolved_by = dismissed_by
    alert.resolution_notes = reason
    alert.resolved_at = now
    alert.updated_at = now

    db.flush()

    return alert


# ============================================================
# STATISTICS
# ============================================================

def get_alert_statistics(db: Session) -> dict:
    """Calcula estadísticas generales de alertas."""

    total = db.scalar(
        select(func.count(Alert.id))
    ) or 0

    status_counts = db.execute(
        select(
            Alert.status,
            func.count(Alert.id),
        ).group_by(Alert.status)
    ).all()

    severity_counts = db.execute(
        select(
            Alert.severity,
            func.count(Alert.id),
        ).group_by(Alert.severity)
    ).all()

    statuses = {
        str(status): count
        for status, count in status_counts
    }

    severities = {
        str(severity): count
        for severity, count in severity_counts
    }

    active = statuses.get(AlertStatus.ACTIVE.value, 0)
    acknowledged = statuses.get(
        AlertStatus.ACKNOWLEDGED.value, 0
    )
    resolved = statuses.get(AlertStatus.RESOLVED.value, 0)

    critical = severities.get(
        AlertSeverity.CRITICAL.value, 0
    )

    return {
        "total": total,
        "active": active,
        "acknowledged": acknowledged,
        "resolved": resolved,
        "dismissed": statuses.get(
            AlertStatus.DISMISSED.value, 0
        ),
        "open": active + acknowledged,
        "critical": critical,
        "by_status": statuses,
        "by_severity": severities,
    }


def get_critical_alerts(
    db: Session,
    *,
    limit: int = 10,
) -> list[Alert]:
    """Devuelve las alertas críticas que siguen abiertas."""

    if not 1 <= limit <= 100:
        raise AlertValidationError(
            "El límite debe estar entre 1 y 100."
        )

    return list(
        db.scalars(
            select(Alert)
            .where(
                Alert.severity == AlertSeverity.CRITICAL.value,
                Alert.status.in_(ACTIVE_STATUSES),
            )
            .order_by(
                Alert.created_at.desc(),
                Alert.id.desc(),
            )
            .limit(limit)
        ).all()
    )


# ============================================================
# DELETE
# ============================================================

def delete_alert(db: Session, alert_id: int) -> None:
    """
    Elimina una alerta.

    En producción suele ser preferible conservar el historial
    y resolver o descartar la alerta en lugar de eliminarla.
    """

    alert = _get_alert_or_raise(db, alert_id)

    db.delete(alert)
    db.flush()
