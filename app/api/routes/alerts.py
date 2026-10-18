
"""
Persistent alert management for LabGuardian AI.

Features:
- PostgreSQL-backed alert management.
- Idempotent synchronization with SampleEvent.
- Descriptive alert titles and types.
- Persistent acknowledgment and resolution metadata.
- Safe serialization for alerts without related samples or events.
"""

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.alert import Alert
from app.models.sample import Sample
from app.models.sample_event import SampleEvent


router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

ATTENTION_SEVERITIES = ("MEDIUM", "HIGH", "CRITICAL")
VALID_STATUSES = ("ACTIVE", "ACKNOWLEDGED", "RESOLVED")


class AlertActionRequest(BaseModel):
    performed_by: str = Field(
        min_length=1,
        max_length=100,
        description="Nombre o identificador del responsable.",
    )


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def normalize_text(value: Any, default: str = "") -> str:
    """Normalize a nullable value to a safe string."""
    if value is None:
        return default

    result = str(value).strip()
    return result or default


def get_event_metadata(event: SampleEvent) -> dict[str, Any]:
    """Return event metadata only when it is a dictionary."""
    metadata = event.event_metadata
    return metadata if isinstance(metadata, dict) else {}


def get_event_alert_type(
    event: SampleEvent,
    sample: Sample | None,
    metadata: dict[str, Any],
) -> str:
    """Determine a meaningful alert type from the event."""

    event_type = normalize_text(
        event.event_type,
        "LABORATORY_ALERT",
    ).upper()

    # A risk assessment can identify an implausible reading or
    # another data-quality issue without proving sample degradation.
    if event_type == "RISK_ASSESSED":
        data_quality_issue = (
            metadata.get("data_quality_issue") is True
            or metadata.get("data_quality_warning") is True
            or metadata.get("temperature_implausible") is True
        )

        explanation = normalize_text(
            metadata.get("risk_explanation")
            or metadata.get("explanation")
        ).lower()

        if (
            sample is not None
            and sample.anomaly_detected
        ):
            data_quality_issue = True

        if any(
            term in explanation
            for term in (
                "plausibilidad",
                "dato registrado",
                "calidad de datos",
                "data quality",
                "implausible",
            )
        ):
            data_quality_issue = True

        if data_quality_issue:
            return "DATA_QUALITY"

        return "RISK_ASSESSMENT"

    return event_type


def get_event_alert_title(
    event: SampleEvent,
    sample: Sample | None,
    alert_type: str,
) -> str:
    """Build a descriptive Spanish title for an event alert."""

    sample_code = (
        normalize_text(sample.code)
        if sample is not None
        else ""
    )
    suffix = f" — {sample_code}" if sample_code else ""

    titles = {
        "RISK_ASSESSED": "Evaluación de riesgo: requiere revisión",
        "RISK_ASSESSMENT": "Evaluación de riesgo: requiere revisión",
        "DATA_QUALITY": "Anomalía en los datos de la muestra",
        "ANOMALY_DETECTED": "Anomalía detectada en la muestra",
        "SAMPLE_DEGRADATION": "Riesgo de degradación de la muestra",
        "TEMPERATURE": "Temperatura fuera del rango permitido",
        "TEMPERATURE_ANOMALY": "Anomalía de temperatura detectada",
        "EQUIPMENT_ANOMALY": "Anomalía detectada en el equipo",
        "TRANSPORT_DELAY": "Retraso en el transporte de la muestra",
        "PROCESSING_DELAY": "Retraso en el procesamiento de la muestra",
        "STORAGE_ANOMALY": "Anomalía en el almacenamiento",
    }

    title = titles.get(
        alert_type,
        normalize_text(event.title, "Alerta de laboratorio"),
    )

    # Keep a useful original event title when it is already specific.
    original_title = normalize_text(event.title)
    if (
        original_title
        and original_title.lower() not in {
            "laboratory alert",
            "laboratory event",
            "alerta de laboratorio",
        }
        and alert_type not in {
            "RISK_ASSESSED",
            "RISK_ASSESSMENT",
            "DATA_QUALITY",
        }
    ):
        title = original_title

    return f"{title}{suffix}"


def serialize_alert(alert: Alert) -> dict[str, Any]:
    """Serialize an alert safely, even without a related event."""

    sample = alert.sample
    event = alert.event

    metadata = get_event_metadata(event) if event is not None else {}

    risk_score = metadata.get("risk_score")
    if risk_score is None:
        risk_score = alert.risk_score
    if risk_score is None and sample is not None:
        risk_score = sample.risk_score

    risk_level = metadata.get("risk_level")
    if risk_level is None and sample is not None:
        risk_level = sample.risk_level

    event_type = (
        normalize_text(event.event_type, alert.alert_type)
        if event is not None
        else alert.alert_type
    )

    message = alert.message
    if not message and event is not None:
        message = event.description or event.title
    if not message:
        message = alert.title

    sample_code = (
        sample.code
        if sample is not None
        else alert.sample_code
    )

    return {
        "id": alert.id,
        "sample_id": alert.sample_id,
        "sample_code": sample_code,
        "event_id": alert.event_id,
        "type": event_type,
        "event_type": event_type,
        "alert_type": alert.alert_type,
        "title": alert.title,
        "severity": alert.severity,
        "message": message,
        "status": alert.status,
        "requires_attention": alert.status != "RESOLVED",
        "risk_score": (
            float(risk_score)
            if risk_score is not None
            else None
        ),
        "risk_level": (
            str(risk_level).upper()
            if risk_level is not None
            else None
        ),
        "created_at": (
            alert.created_at.isoformat()
            if alert.created_at
            else None
        ),
        "acknowledged_at": (
            alert.acknowledged_at.isoformat()
            if alert.acknowledged_at
            else None
        ),
        "acknowledged_by": alert.acknowledged_by,
        "resolved_at": (
            alert.resolved_at.isoformat()
            if alert.resolved_at
            else None
        ),
        "resolved_by": alert.resolved_by,
        "updated_at": (
            alert.updated_at.isoformat()
            if alert.updated_at
            else None
        ),
    }


def get_alert_or_404(db: Session, alert_id: int) -> Alert:
    """Get an alert or raise HTTP 404."""
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id)
        .first()
    )

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="Alert not found.",
        )

    return alert


@router.post("/sync")
def sync_alerts(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Synchronize attention-worthy events with persisted alerts.

    Existing linked alerts are updated with descriptive fields.
    Their status and acknowledgment/resolution history are preserved.
    Repeated calls do not create duplicate alerts.
    """

    events = (
        db.query(SampleEvent)
        .filter(
            func.upper(
                func.coalesce(SampleEvent.severity, "INFO")
            ).in_(ATTENTION_SEVERITIES)
        )
        .order_by(SampleEvent.id.asc())
        .all()
    )

    linked_alerts = (
        db.query(Alert)
        .filter(Alert.event_id.is_not(None))
        .all()
    )
    alerts_by_event_id = {
        alert.event_id: alert
        for alert in linked_alerts
    }

    created = 0
    updated = 0

    try:
        for event in events:
            sample = (
                db.query(Sample)
                .filter(Sample.id == event.sample_id)
                .first()
                if event.sample_id is not None
                else None
            )

            metadata = get_event_metadata(event)

            severity = normalize_text(
                event.severity,
                "MEDIUM",
            ).upper()

            alert_type = get_event_alert_type(
                event,
                sample,
                metadata,
            )

            title = get_event_alert_title(
                event,
                sample,
                alert_type,
            )

            message = normalize_text(
                event.description or event.title,
                title,
            )

            risk_score = metadata.get("risk_score")
            if risk_score is None and sample is not None:
                risk_score = sample.risk_score

            alert = alerts_by_event_id.get(event.id)

            if alert is None:
                alert = Alert(
                    sample_id=event.sample_id,
                    event_id=event.id,
                    sample_code=sample.code if sample else None,
                    alert_type=alert_type,
                    severity=severity,
                    title=title,
                    message=message,
                    risk_score=risk_score,
                    source="SAMPLE_EVENT",
                    status="ACTIVE",
                )
                db.add(alert)
                alerts_by_event_id[event.id] = alert
                created += 1

            else:
                # Update descriptive fields, not the alert's
                # workflow status or acknowledgment/resolution history.
                alert.sample_id = event.sample_id
                alert.sample_code = (
                    sample.code if sample else alert.sample_code
                )
                alert.alert_type = alert_type
                alert.severity = severity
                alert.title = title
                alert.message = message
                alert.risk_score = risk_score
                if not alert.source:
                    alert.source = "SAMPLE_EVENT"

                updated += 1

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "An alert was created concurrently. "
                "Retry synchronization."
            ),
        )

    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "created": created,
        "updated": updated,
        "message": (
            f"Synchronization complete: "
            f"{created} created, {updated} updated."
        ),
    }


@router.get("/")
def get_alerts(
    status: Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"] | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List persisted alerts, optionally filtered by status."""

    query = db.query(Alert)

    if status is not None:
        query = query.filter(Alert.status == status)

    total = query.count()

    alerts = (
        query.order_by(desc(Alert.created_at), desc(Alert.id))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "alerts": [serialize_alert(alert) for alert in alerts],
    }


@router.get("/active")
def get_active_alerts(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List alerts that have not been resolved."""

    alerts = (
        db.query(Alert)
        .filter(
            Alert.status.in_(("ACTIVE", "ACKNOWLEDGED"))
        )
        .order_by(desc(Alert.created_at), desc(Alert.id))
        .limit(100)
        .all()
    )

    return {
        "success": True,
        "total": len(alerts),
        "alerts": [serialize_alert(alert) for alert in alerts],
    }


@router.get("/{alert_id}")
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get one persisted alert."""

    alert = get_alert_or_404(db, alert_id)

    return {
        "success": True,
        "alert": serialize_alert(alert),
    }


@router.patch("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    payload: AlertActionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Acknowledge an alert and persist the responsible person."""

    alert = get_alert_or_404(db, alert_id)
    performed_by = payload.performed_by.strip()

    if not performed_by:
        raise HTTPException(
            status_code=422,
            detail="performed_by cannot be blank.",
        )

    if alert.status == "RESOLVED":
        raise HTTPException(
            status_code=409,
            detail="A resolved alert cannot be acknowledged.",
        )

    if alert.status == "ACTIVE":
        alert.status = "ACKNOWLEDGED"

    if alert.acknowledged_at is None:
        alert.acknowledged_at = utc_now()

    if not alert.acknowledged_by:
        alert.acknowledged_by = performed_by

    try:
        db.commit()
        db.refresh(alert)
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "message": "Alert acknowledged.",
        "alert": serialize_alert(alert),
    }


@router.patch("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    payload: AlertActionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Resolve an alert and persist who resolved it."""

    alert = get_alert_or_404(db, alert_id)
    resolved_by = payload.performed_by.strip()

    if not resolved_by:
        raise HTTPException(
            status_code=422,
            detail="performed_by cannot be blank.",
        )

    if alert.status == "RESOLVED":
        raise HTTPException(
            status_code=409,
            detail="Alert is already resolved.",
        )

    alert.status = "RESOLVED"
    alert.resolved_at = utc_now()
    alert.resolved_by = resolved_by

    try:
        db.commit()
        db.refresh(alert)
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "message": "Alert resolved.",
        "alert": serialize_alert(alert),
    }
