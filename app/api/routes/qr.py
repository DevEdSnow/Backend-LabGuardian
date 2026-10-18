"""
QR routes for LabGuardian AI.

This module provides endpoints for generating and
consulting QR codes associated with clinical samples.
"""

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/qr",
    tags=["QR"],
)

# Temporary mock sample data.
samples_qr_data: dict[str, dict[str, Any]] = {
    "A49281": {
        "sample_code": "A49281",
        "sample_type": "Sangre",
        "patient_reference": "PAT-001",
        "status": "PROCESSING",
        "risk": 78,
        "risk_level": "HIGH",
    },
    "A49292": {
        "sample_code": "A49292",
        "sample_type": "Orina",
        "patient_reference": "PAT-002",
        "status": "RECEIVED",
        "risk": 54,
        "risk_level": "MEDIUM",
    },
    "A49301": {
        "sample_code": "A49301",
        "sample_type": "Suero",
        "patient_reference": "PAT-003",
        "status": "PROCESSING",
        "risk": 47,
        "risk_level": "MEDIUM",
    },
}

# Frontend URL for sample traceability.
QR_BASE_URL = "http://localhost:5173/sample"


@router.post("/generate")
async def generate_qr(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Generate a QR URL for a registered sample."""
    sample_code = data.get("sample_code")

    if not isinstance(sample_code, str) or not sample_code.strip():
        raise HTTPException(
            status_code=400,
            detail="sample_code is required.",
        )

    sample_code = sample_code.strip()
    sample = samples_qr_data.get(sample_code)

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    encoded_sample_code = quote(sample_code, safe="")
    qr_url = f"{QR_BASE_URL}/{encoded_sample_code}"

    return {
        "success": True,
        "message": "QR information generated successfully.",
        "qr": {
            "sample_code": sample_code,
            "url": qr_url,
            "format": "QR_CODE",
        },
    }


@router.get("/{sample_code}/data")
async def get_qr_data(
    sample_code: str,
) -> dict[str, Any]:
    """Return the data represented by a sample QR code."""
    sample = samples_qr_data.get(sample_code)

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    return {
        "success": True,
        "qr_data": {
            "sample_code": sample_code,
            "url": (
                f"{QR_BASE_URL}/"
                f"{quote(sample_code, safe='')}"
            ),
        },
    }


@router.get("/{sample_code}/passport")
async def get_sample_passport(
    sample_code: str,
) -> dict[str, Any]:
    """Return the digital passport for a clinical sample."""
    sample = samples_qr_data.get(sample_code)

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    return {
        "success": True,
        "passport": {
            "sample_code": sample["sample_code"],
            "sample_type": sample["sample_type"],
            "status": sample["status"],
            "risk": {
                "score": sample["risk"],
                "level": sample["risk_level"],
            },
            "traceability_url": (
                f"{QR_BASE_URL}/"
                f"{quote(sample_code, safe='')}"
            ),
        },
    }


@router.get("/{sample_code}/verify")
async def verify_qr(
    sample_code: str,
) -> dict[str, Any]:
    """Verify whether a QR code belongs to a registered sample."""
    sample = samples_qr_data.get(sample_code)

    if sample is None:
        return {
            "success": True,
            "valid": False,
            "sample_code": sample_code,
            "message": (
                "QR code is not associated "
                "with a registered sample."
            ),
        }

    return {
        "success": True,
        "valid": True,
        "sample_code": sample_code,
        "message": "QR code verified successfully.",
        "sample_status": sample["status"],
        "risk_level": sample["risk_level"],
    }


@router.get("/{sample_code}")
async def get_qr_information(
    sample_code: str,
) -> dict[str, Any]:
    """Return QR URL and basic sample information."""
    sample = samples_qr_data.get(sample_code)

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    encoded_sample_code = quote(sample_code, safe="")
    qr_url = f"{QR_BASE_URL}/{encoded_sample_code}"

    return {
        "success": True,
        "sample_code": sample_code,
        "qr": {
            "url": qr_url,
            "format": "QR_CODE",
        },
        "sample": sample,
    }