
"""
Alert routes for LabGuardian AI.

This module provides endpoints for laboratory alerts.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/alerts",
    tags=["Alerts"],
)

# Temporary demonstration data.
alerts_data: list[dict[str, Any]] = [
    {
        "id": 1,
        "sample_code": "A49281",
        "type": "TEMPERATURE",
        "severity": "HIGH",
        "message": "Temperatura fuera del rango recomendado.",
        "status": "ACTIVE",
    },
    {
        "id": 2,
        "sample_code": "A49292",
        "type": "PROCESSING_DELAY",
        "severity": "MEDIUM",
        "message": "Tiempo de procesamiento superior al esperado.",
        "status": "ACTIVE",
    },
]


@router.get("/")
async def get_alerts() -> dict[str, Any]:
    """Return all demonstration alerts."""
    return {
        "success": True,
        "total": len(alerts_data),
        "alerts": alerts_data,
    }


@router.get("/active")
async def get_active_alerts() -> dict[str, Any]:
    """Return alerts whose status is ACTIVE."""
    active_alerts = [
        alert
        for alert in alerts_data
        if alert["status"] == "ACTIVE"
    ]

    return {
        "success": True,
        "total": len(active_alerts),
        "alerts": active_alerts,
    }


@router.get("/{alert_id}")
async def get_alert(alert_id: int) -> dict[str, Any]:
    """Return a specific alert by ID."""
    alert = next(
        (
            item
            for item in alerts_data
            if item["id"] == alert_id
        ),
        None,
    )

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="Alert not found.",
        )

    return {
        "success": True,
        "alert": alert,
    }
