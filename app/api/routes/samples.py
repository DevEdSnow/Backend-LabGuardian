```python
"""
Sample routes for LabGuardian AI.

This module provides endpoints for registering,
consulting, updating and deleting clinical samples.

The current implementation uses temporary in-memory
data. It will later be connected to PostgreSQL
through the sample service and SQLAlchemy models.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/api/samples",
    tags=["Samples"],
)


# ─────────────────────────────────────────────
# Temporary mock data
# ─────────────────────────────────────────────

samples_data: list[dict[str, Any]] = [
    {
        "id": 1,
        "code": "A49281",
        "sample_type": "Sangre",
        "patient_reference": "PAT-001",
        "area": "Hematología",
        "status": "PROCESSING",
        "priority": "NORMAL",
        "collection_date": "2026-10-03T08:10:00Z",
        "reception_date": "2026-10-03T08:32:00Z",
        "processing_date": "2026-10-03T09:47:00Z",
        "temperature": 8.7,
        "risk_score": 78,
        "risk_level": "HIGH",
        "anomaly": True,
        "notes": "Temperatura de almacenamiento fuera del rango recomendado.",
    },
    {
        "id": 2,
        "code": "A49292",
        "sample_type": "Orina",
        "patient_reference": "PAT-002",
        "area": "Uroanálisis",
        "status": "RECEIVED",
        "priority": "NORMAL",
        "collection_date": "2026-10-03T09:00:00Z",
        "reception_date": "2026-10-03T09:42:00Z",
        "processing_date": None,
        "temperature": 7.4,
        "risk_score": 54,
        "risk_level": "MEDIUM",
        "anomaly": False,
        "notes": "Pendiente de procesamiento.",
    },
    {
        "id": 3,
        "code": "A49301",
        "sample_type": "Suero",
        "patient_reference": "PAT-003",
        "area": "Química Clínica",
        "status": "PROCESSING",
        "priority": "URGENT",
        "collection_date": "2026-10-03T08:40:00Z",
        "reception_date": "2026-10-03T09:12:00Z",
        "processing_date": "2026-10-03T10:04:00Z",
        "temperature": 6.8,
        "risk_score": 47,
        "risk_level": "MEDIUM",
        "anomaly": False,
        "notes": "Procesamiento prioritario.",
    },
]


# ─────────────────────────────────────────────
# GET /api/samples
# ─────────────────────────────────────────────

@router.get("/")
async def get_samples() -> dict[str, Any]:
    """
    Returns all registered clinical samples.
    """

    return {
        "success": True,
        "total": len(samples_data),
        "samples": samples_data,
    }


# ─────────────────────────────────────────────
# GET /api/samples/{sample_id}
# ─────────────────────────────────────────────

@router.get("/{sample_id}")
async def get_sample(
    sample_id: int,
) -> dict[str, Any]:
    """
    Returns a specific sample by ID.
    """

    sample = next(
        (
            item
            for item in samples_data
            if item["id"] == sample_id
        ),
        None,
    )

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    return {
        "success": True,
        "sample": sample,
    }


# ─────────────────────────────────────────────
# GET /api/samples/code/{sample_code}
# ─────────────────────────────────────────────

@router.get("/code/{sample_code}")
async def get_sample_by_code(
    sample_code: str,
) -> dict[str, Any]:
    """
    Returns a sample using its unique sample code.
    """

    sample = next(
        (
            item
            for item in samples_data
            if item["code"] == sample_code
        ),
        None,
    )

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    return {
        "success": True,
        "sample": sample,
    }


# ─────────────────────────────────────────────
# GET /api/samples/{sample_id}/status
# ─────────────────────────────────────────────

@router.get("/{sample_id}/status")
async def get_sample_status(
    sample_id: int,
) -> dict[str, Any]:
    """
    Returns the current status of a clinical sample.
    """

    sample = next(
        (
            item
            for item in samples_data
            if item["id"] == sample_id
        ),
        None,
    )

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    return {
        "success": True,
        "sample_code": sample["code"],
        "status": sample["status"],
        "priority": sample["priority"],
        "risk_level": sample["risk_level"],
        "risk_score": sample["risk_score"],
        "anomaly": sample["anomaly"],
    }


# ─────────────────────────────────────────────
# GET /api/samples/{sample_id}/passport
# ─────────────────────────────────────────────

@router.get("/{sample_id}/passport")
async def get_sample_passport(
    sample_id: int,
) -> dict[str, Any]:
    """
    Returns the digital passport of a sample.

    The passport provides the main information required
    to visualize the complete state of a sample.
    """

    sample = next(
        (
            item
            for item in samples_data
            if item["id"] == sample_id
        ),
        None,
    )

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    return {
        "success": True,
        "passport": {
            "sample_code": sample["code"],
            "sample_type": sample["sample_type"],
            "area": sample["area"],
            "status": sample["status"],
            "priority": sample["priority"],
            "risk": {
                "score": sample["risk_score"],
                "level": sample["risk_level"],
            },
            "temperature": sample["temperature"],
            "anomaly": sample["anomaly"],
            "collection_date": sample["collection_date"],
            "reception_date": sample["reception_date"],
            "processing_date": sample["processing_date"],
        },
    }


# ─────────────────────────────────────────────
# GET /api/samples/risk/high
# ─────────────────────────────────────────────

@router.get("/risk/high")
async def get_high_risk_samples() -> dict[str, Any]:
    """
    Returns samples classified as high risk.
    """

    high_risk_samples = [
        sample
        for sample in samples_data
        if sample["risk_level"] == "HIGH"
    ]

    return {
        "success": True,
        "total": len(high_risk_samples),
        "samples": high_risk_samples,
    }


# ─────────────────────────────────────────────
# GET /api/samples/status/{status}
# ─────────────────────────────────────────────

@router.get("/status/{status}")
async def get_samples_by_status(
    status: str,
) -> dict[str, Any]:
    """
    Returns samples filtered by their current status.

    Example:
        /api/samples/status/PROCESSING
    """

    normalized_status = status.upper()

    filtered_samples = [
        sample
        for sample in samples_data
        if sample["status"] == normalized_status
    ]

    return {
        "success": True,
        "status": normalized_status,
        "total": len(filtered_samples),
        "samples": filtered_samples,
    }


# ─────────────────────────────────────────────
# POST /api/samples
# ─────────────────────────────────────────────

@router.post("/")
async def create_sample(
    sample: dict[str, Any],
) -> dict[str, Any]:
    """
    Registers a new clinical sample.

    Example request:

    {
        "code": "A49350",
        "sample_type": "Sangre",
        "patient_reference": "PAT-010",
        "area": "Hematología",
        "priority": "NORMAL",
        "temperature": 5.2
    }

    PostgreSQL persistence will be implemented later.
    """

    code = sample.get("code")

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Sample code is required.",
        )

    existing_sample = next(
        (
            item
            for item in samples_data
            if item["code"] == code
        ),
        None,
    )

    if existing_sample is not None:
        raise HTTPException(
            status_code=409,
            detail="A sample with this code already exists.",
        )

    now = datetime.now(
        timezone.utc
    ).isoformat()

    new_id = (
        max(
            (
                item["id"]
                for item in samples_data
            ),
            default=0,
        )
        + 1
    )

    new_sample = {
        "id": new_id,
        "code": code,
        "sample_type": sample.get(
            "sample_type",
            "Unknown",
        ),
        "patient_reference": sample.get(
            "patient_reference",
        ),
        "area": sample.get(
            "area",
            "General",
        ),
        "status": sample.get(
            "status",
            "RECEIVED",
        ),
        "priority": sample.get(
            "priority",
            "NORMAL",
        ),
        "collection_date": sample.get(
            "collection_date",
            now,
        ),
        "reception_date": sample.get(
            "reception_date",
            now,
        ),
        "processing_date": sample.get(
            "processing_date",
        ),
        "temperature": sample.get(
            "temperature",
        ),
        "risk_score": sample.get(
            "risk_score",
            0,
        ),
        "risk_level": sample.get(
            "risk_level",
            "LOW",
        ),
        "anomaly": sample.get(
            "anomaly",
            False,
        ),
        "notes": sample.get(
            "notes",
            "",
        ),
    }

    samples_data.append(new_sample)

    return {
        "success": True,
        "message": "Sample registered successfully.",
        "sample": new_sample,
    }


# ─────────────────────────────────────────────
# PUT /api/samples/{sample_id}
# ─────────────────────────────────────────────

@router.put("/{sample_id}")
async def update_sample(
    sample_id: int,
    sample: dict[str, Any],
) -> dict[str, Any]:
    """
    Updates an existing clinical sample.
    """

    existing_sample = next(
        (
            item
            for item in samples_data
            if item["id"] == sample_id
        ),
        None,
    )

    if existing_sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    if "code" in sample:
        duplicated_code = next(
            (
                item
                for item in samples_data
                if item["code"] == sample["code"]
                and item["id"] != sample_id
            ),
            None,
        )

        if duplicated_code is not None:
            raise HTTPException(
                status_code=409,
                detail="A sample with this code already exists.",
            )

    existing_sample.update(sample)

    return {
        "success": True,
        "message": "Sample updated successfully.",
        "sample": existing_sample,
    }


# ─────────────────────────────────────────────
# PATCH /api/samples/{sample_id}/status
# ─────────────────────────────────────────────

@router.patch("/{sample_id}/status")
async def update_sample_status(
    sample_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Updates only the status of a clinical sample.

    Example request:

    {
        "status": "PROCESSING"
    }
    """

    existing_sample = next(
        (
            item
            for item in samples_data
            if item["id"] == sample_id
        ),
        None,
    )

    if existing_sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    status = data.get("status")

    if not status:
        raise HTTPException(
            status_code=400,
            detail="status is required.",
        )

    existing_sample["status"] = status.upper()

    return {
        "success": True,
        "message": "Sample status updated successfully.",
        "sample_code": existing_sample["code"],
        "status": existing_sample["status"],
    }


# ─────────────────────────────────────────────
# PATCH /api/samples/{sample_id}/risk
# ─────────────────────────────────────────────

@router.patch("/{sample_id}/risk")
async def update_sample_risk(
    sample_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Updates the risk information of a sample.

    This endpoint will later be called by the
    Machine Learning risk engine.
    """

    existing_sample = next(
        (
            item
            for item in samples_data
            if item["id"] == sample_id
        ),
        None,
    )

    if existing_sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    score = data.get("risk_score")

    if score is None:
        raise HTTPException(
            status_code=400,
            detail="risk_score is required.",
        )

    try:
        score = float(score)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="risk_score must be a number.",
        )

    if not 0 <= score <= 100:
        raise HTTPException(
            status_code=400,
            detail="risk_score must be between 0 and 100.",
        )

    if score >= 70:
        risk_level = "HIGH"
    elif score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    existing_sample["risk_score"] = score
    existing_sample["risk_level"] = risk_level

    return {
        "success": True,
        "message": "Sample risk updated successfully.",
        "sample_code": existing_sample["code"],
        "risk_score": score,
        "risk_level": risk_level,
    }


# ─────────────────────────────────────────────
# DELETE /api/samples/{sample_id}
# ─────────────────────────────────────────────

@router.delete("/{sample_id}")
async def delete_sample(
    sample_id: int,
) -> dict[str, Any]:
    """
    Deletes a clinical sample.
    """

    sample = next(
        (
            item
            for item in samples_data
            if item["id"] == sample_id
        ),
        None,
    )

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    samples_data.remove(sample)

    return {
        "success": True,
        "message": "Sample deleted successfully.",
        "sample_id": sample_id,
        "sample_code": sample["code"],
    }
```

Con este archivo ya tienes la base para:

```text
GET    /api/samples/
GET    /api/samples/{id}
GET    /api/samples/code/{code}
GET    /api/samples/{id}/status
GET    /api/samples/{id}/passport
GET    /api/samples/risk/high
GET    /api/samples/status/{status}

POST   /api/samples/

PUT    /api/samples/{id}
PATCH  /api/samples/{id}/status
PATCH  /api/samples/{id}/risk

DELETE /api/samples/{id}
```

**Ojo con el orden:** en FastAPI las rutas específicas como `/code/{sample_code}`, `/risk/high` y `/status/{status}` deben estar antes de `/{sample_id}`. En el archivo anterior están colocadas así para evitar que `"code"`, `"risk"` o `"status"` se intenten convertir en `int`.
