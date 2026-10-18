
"""
Dashboard routes for LabGuardian AI.

Dashboard statistics are calculated from PostgreSQL.
Alert counts and recent alerts use the persisted Alert records.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.alert import Alert
from app.models.sample import Sample
from app.models.sample_event import SampleEvent

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)

ATTENTION_STATUSES = ("ACTIVE", "ACKNOWLEDGED")
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def normalized_risk_level():
    """Normalize persisted risk levels for SQL comparisons."""
    return func.upper(func.coalesce(Sample.risk_level, "LOW"))



def get_risk_counts(db: Session) -> dict[str, int]:
    """Count samples by persisted risk level."""
    risk_level_expr = func.upper(
        func.coalesce(Sample.risk_level, "LOW")
    )

    rows = (
        db.query(
            risk_level_expr.label("risk_level"),
            func.count(Sample.id).label("total"),
        )
        .group_by(risk_level_expr)
        .all()
    )

    counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    for level, total in rows:
        key = str(level).lower()
        if key in counts:
            counts[key] = int(total)

    return counts



def get_active_alert_count(db: Session) -> int:
    """
    Count persisted alerts that still require attention.

    Acknowledged alerts remain active until they are resolved.
    Resolved alerts are excluded.
    """
    total = (
        db.query(func.count(Alert.id))
        .filter(
            func.upper(Alert.status).in_(ATTENTION_STATUSES)
        )
        .scalar()
    )

    return int(total or 0)


def get_normal_sample_count(db: Session) -> int:
    """
    Count low-risk samples without a detected anomaly.

    Low risk alone does not guarantee that a sample is normal.
    """
    total = (
        db.query(func.count(Sample.id))
        .filter(
            normalized_risk_level() == "LOW",
            Sample.anomaly_detected.is_(False),
        )
        .scalar()
    )

    return int(total or 0)


def get_dashboard_data(db: Session) -> dict[str, Any]:
    """Build a dashboard snapshot from persisted database records."""
    total_samples = (
        db.query(func.count(Sample.id)).scalar() or 0
    )

    risk_counts = get_risk_counts(db)

    average_risk = (
        db.query(func.avg(Sample.risk_score))
        .filter(Sample.risk_score.isnot(None))
        .scalar()
    )

    active_alerts = get_active_alert_count(db)
    normal_samples = get_normal_sample_count(db)

    area_rows = (
        db.query(
            Sample.laboratory_area,
            func.count(Sample.id).label("total"),
            func.sum(
                case(
                    (
                        normalized_risk_level().in_(
                            ["MEDIUM", "HIGH", "CRITICAL"]
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("at_risk"),
        )
        .group_by(Sample.laboratory_area)
        .order_by(Sample.laboratory_area)
        .all()
    )

    areas = []

    for area_name, area_total, at_risk in area_rows:
        area_total = int(area_total or 0)
        at_risk = int(at_risk or 0)

        areas.append(
            {
                "name": area_name or "Sin área asignada",
                "samples": area_total,
                "risk_percentage": (
                    round((at_risk / area_total) * 100, 2)
                    if area_total
                    else 0.0
                ),
            }
        )

    return {
        "total_samples": int(total_samples),
        "normal_samples": normal_samples,
        "risk_counts": risk_counts,
        "active_alerts": active_alerts,
        "average_risk": (
            round(float(average_risk), 2)
            if average_risk is not None
            else 0.0
        ),
        "areas": areas,
    }


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the main laboratory dashboard statistics."""
    data = get_dashboard_data(db)
    risks = data["risk_counts"]

    return {
        "success": True,
        "summary": {
            "total_samples": data["total_samples"],
            "normal_samples": data["normal_samples"],
            "low_risk_samples": risks["low"],
            "medium_risk_samples": risks["medium"],
            "high_risk_samples": risks["high"],
            "critical_risk_samples": risks["critical"],
            "active_alerts": data["active_alerts"],
            "average_risk": data["average_risk"],
        },
    }


@router.get("/risks")
def get_risk_statistics(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return sample risk statistics."""
    data = get_dashboard_data(db)
    counts = data["risk_counts"]
    total = data["total_samples"]

    percentages = {
        level: (
            round((count / total) * 100, 2)
            if total
            else 0.0
        )
        for level, count in counts.items()
    }

    return {
        "success": True,
        "risks": counts,
        "percentage": percentages,
        "total_samples": total,
    }


@router.get("/areas")
def get_area_statistics(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return risk statistics grouped by laboratory area."""
    data = get_dashboard_data(db)

    return {
        "success": True,
        "areas": data["areas"],
    }


@router.get("/recent-alerts")
def get_recent_alerts(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Return recent persisted alerts that still require attention.

    Alert IDs are used here, not SampleEvent IDs.
    Alerts without an associated event are included as well.
    """
    rows = (
        db.query(Alert, Sample, SampleEvent)
        .outerjoin(Sample, Sample.id == Alert.sample_id)
        .outerjoin(
            SampleEvent,
            SampleEvent.id == Alert.event_id,
        )
        .filter(
            func.upper(Alert.status).in_(ATTENTION_STATUSES)
        )
        .order_by(
            desc(Alert.created_at),
            desc(Alert.id),
        )
        .limit(10)
        .all()
    )

    alerts = []

    for alert, sample, event in rows:
        metadata = (
            event.event_metadata
            if event is not None and event.event_metadata
            else {}
        )

        risk_score = alert.risk_score

        if risk_score is None:
            risk_score = metadata.get("risk_score")

        if risk_score is None and sample is not None:
            risk_score = sample.risk_score

        sample_code = alert.sample_code

        if not sample_code and sample is not None:
            sample_code = sample.code

        event_type = (
            event.event_type
            if event is not None
            else alert.alert_type
        )

        message = alert.message or alert.title

        if not message and event is not None:
            message = event.description or event.title

        timestamp = alert.created_at

        alerts.append(
            {
                "id": alert.id,
                "sample_code": sample_code,
                "severity": (
                    str(alert.severity).upper()
                    if alert.severity
                    else "INFO"
                ),
                "risk": (
                    float(risk_score)
                    if risk_score is not None
                    else None
                ),
                "event_type": event_type,
                "status": str(alert.status).upper(),
                "message": message,
                "timestamp": (
                    timestamp.isoformat()
                    if timestamp is not None
                    else None
                ),
            }
        )

    return {
        "success": True,
        "total": len(alerts),
        "alerts": alerts,
    }


@router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return a complete dashboard snapshot."""
    data = get_dashboard_data(db)
    risks = data["risk_counts"]

    return {
        "success": True,
        "dashboard": {
            "samples": {
                "total": data["total_samples"],
                "normal": data["normal_samples"],
                "low_risk": risks["low"],
                "medium_risk": risks["medium"],
                "high_risk": risks["high"],
                "critical_risk": risks["critical"],
            },
            "alerts": {
                "active": data["active_alerts"],
            },
            "risk": {
                "average": data["average_risk"],
            },
            "areas": data["areas"],
        },
    }
