"""
Alert routes for LabGuardian AI.

This module provides endpoints for laboratory alerts.
"""

from typing import Any

from fastapi import APIRouter

router = APIRouter(
prefix="/api/alerts",
tags=["Alerts"],
)

# ─────────────────────────────────────────────

# GET /api/alerts

# ─────────────────────────────────────────────

@router.get("/")
async def get_alerts() -> dict[str, Any]:
"""
Returns the active laboratory alerts.

```
This endpoint currently returns sample data.
It will be connected to the database later.
"""

return {
    "success": True,
    "total": 2,
    "alerts": [
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
    ],
}
```

# ─────────────────────────────────────────────

# GET /api/alerts/active

# ─────────────────────────────────────────────

@router.get("/active")
async def get_active_alerts() -> dict[str, Any]:
"""
Returns only active alerts.

```
Database filtering will be implemented later.
"""

return {
    "success": True,
    "alerts": [
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
    ],
}
```

# ─────────────────────────────────────────────

# GET /api/alerts/{alert_id}

# ─────────────────────────────────────────────

@router.get("/{alert_id}")
async def get_alert(alert_id: int) -> dict[str, Any]:
"""
Returns a specific alert by ID.

```
This is currently a mock response.
"""

return {
    "success": True,
    "alert": {
        "id": alert_id,
        "sample_code": "A49281",
        "type": "TEMPERATURE",
        "severity": "HIGH",
        "message": "Temperatura fuera del rango recomendado.",
        "status": "ACTIVE",
    },
}
```
