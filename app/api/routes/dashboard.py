"""
Dashboard routes for LabGuardian AI.

This module provides endpoints for laboratory dashboard
statistics and monitoring information.
"""

from typing import Any

from fastapi import APIRouter

router = APIRouter(
prefix="/api/dashboard",
tags=["Dashboard"],
)

# ─────────────────────────────────────────────

# GET /api/dashboard/summary

# ─────────────────────────────────────────────

@router.get("/summary")
async def get_dashboard_summary() -> dict[str, Any]:
"""
Returns the main laboratory dashboard statistics.

```
This endpoint currently returns mock data.
It will be connected to PostgreSQL and the
ML risk engine later.
"""

return {
    "success": True,
    "summary": {
        "total_samples": 1284,
        "normal_samples": 1173,
        "medium_risk_samples": 83,
        "high_risk_samples": 28,
        "active_alerts": 12,
        "average_risk": 8.4,
    },
}
```

# ─────────────────────────────────────────────

# GET /api/dashboard/risks

# ─────────────────────────────────────────────

@router.get("/risks")
async def get_risk_statistics() -> dict[str, Any]:
"""
Returns sample risk statistics.
"""

```
return {
    "success": True,
    "risks": {
        "low": 1173,
        "medium": 83,
        "high": 28,
    },
    "percentage": {
        "low": 91.4,
        "medium": 6.5,
        "high": 2.1,
    },
}
```

# ─────────────────────────────────────────────

# GET /api/dashboard/areas

# ─────────────────────────────────────────────

@router.get("/areas")
async def get_area_statistics() -> dict[str, Any]:
"""
Returns risk statistics grouped by laboratory area.
"""

```
return {
    "success": True,
    "areas": [
        {
            "name": "Hematología",
            "samples": 420,
            "risk_percentage": 12.0,
        },
        {
            "name": "Química Clínica",
            "samples": 356,
            "risk_percentage": 6.0,
        },
        {
            "name": "Microbiología",
            "samples": 218,
            "risk_percentage": 15.0,
        },
        {
            "name": "Uroanálisis",
            "samples": 290,
            "risk_percentage": 4.0,
        },
    ],
}
```

# ─────────────────────────────────────────────

# GET /api/dashboard/recent-alerts

# ─────────────────────────────────────────────

@router.get("/recent-alerts")
async def get_recent_alerts() -> dict[str, Any]:
"""
Returns the most recent laboratory alerts.
"""

```
return {
    "success": True,
    "alerts": [
        {
            "id": 1,
            "sample_code": "A49281",
            "severity": "HIGH",
            "risk": 78,
            "message": "Temperatura fuera del rango recomendado.",
        },
        {
            "id": 2,
            "sample_code": "A49292",
            "severity": "MEDIUM",
            "risk": 54,
            "message": "Tiempo de procesamiento elevado.",
        },
        {
            "id": 3,
            "sample_code": "A49301",
            "severity": "MEDIUM",
            "risk": 47,
            "message": "Anomalía detectada durante el transporte.",
        },
    ],
}
```

# ─────────────────────────────────────────────

# GET /api/dashboard

# ─────────────────────────────────────────────

@router.get("/")
async def get_dashboard() -> dict[str, Any]:
"""
Returns a complete dashboard snapshot.
"""

```
return {
    "success": True,
    "dashboard": {
        "samples": {
            "total": 1284,
            "normal": 1173,
            "medium_risk": 83,
            "high_risk": 28,
        },
        "alerts": {
            "active": 12,
        },
        "risk": {
            "average": 8.4,
        },
        "areas": [
            {
                "name": "Hematología",
                "risk_percentage": 12.0,
            },
            {
                "name": "Química Clínica",
                "risk_percentage": 6.0,
            },
            {
                "name": "Microbiología",
                "risk_percentage": 15.0,
            },
            {
                "name": "Uroanálisis",
                "risk_percentage": 4.0,
            },
        ],
    },
}
```
