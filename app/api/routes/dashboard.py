
"""
Dashboard routes for LabGuardian AI.

All dashboard statistics are calculated from PostgreSQL.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sample import Sample
from app.models.sample_event import SampleEvent

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)



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



def get_dashboard_data(db: Session) -> dict[str, Any]:
    """Build a dashboard snapshot from the database."""
    total_samples = db.query(func.count(Sample.id)).scalar() or 0

    risk_counts = get_risk_counts(db)

    average_risk = (
        db.query(func.avg(Sample.risk_score))
        .filter(Sample.risk_score.isnot(None))
        .scalar()
    )

    # Treat HIGH and CRITICAL samples, and samples with detected
    # anomalies, as requiring attention.
    active_alerts = (
        db.query(func.count(Sample.id))
        .filter(
            (func.upper(func.coalesce(Sample.risk_level, "LOW")).in_(
                ["HIGH", "CRITICAL"]
            ))
            | (Sample.anomaly_detected.is_(True))
        )
        .scalar()
        or 0
    )

    area_rows = (
        db.query(
            Sample.laboratory_area,
            func.count(Sample.id).label("total"),
            func.sum(
                case(
                    (
                        func.upper(
                            func.coalesce(Sample.risk_level, "LOW")
                        ).in_(["MEDIUM", "HIGH", "CRITICAL"]),
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
                "risk_percentage": round(
                    (at_risk / area_total) * 100, 2
                ) if area_total else 0.0,
            }
        )

    return {
        "total_samples": int(total_samples),
        "risk_counts": risk_counts,
        "active_alerts": int(active_alerts),
        "average_risk": round(float(average_risk), 2)
        if average_risk is not None
        else 0.0,
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
            "normal_samples": risks["low"],
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
        level: round((count / total) * 100, 2) if total else 0.0
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
    """Return recent events that may require attention."""
    events = (
        db.query(SampleEvent, Sample.code)
        .join(Sample, Sample.id == SampleEvent.sample_id)
        .filter(
            func.upper(SampleEvent.severity).in_(
                ["MEDIUM", "HIGH", "CRITICAL"]
            )
        )
        .order_by(
            desc(SampleEvent.occurred_at),
            desc(SampleEvent.id),
        )
        .limit(10)
        .all()
    )

    alerts = []

    for event, sample_code in events:
        metadata = event.event_metadata or {}
        risk_score = metadata.get("risk_score")

        alerts.append(
            {
                "id": event.id,
                "sample_code": sample_code,
                "severity": event.severity,
                "risk": risk_score,
                "event_type": event.event_type,
                "message": event.description or event.title,
                "timestamp": event.occurred_at.isoformat()
                if event.occurred_at
                else None,
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
                "normal": risks["low"],
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
