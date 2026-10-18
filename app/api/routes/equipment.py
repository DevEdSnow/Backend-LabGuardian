"""
Equipment routes for LabGuardian AI.

This module provides endpoints for managing laboratory
equipment and monitoring their status.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/equipment",
    tags=["Equipment"],
)

# Temporary mock data.
equipment_data: list[dict[str, Any]] = [
    {
        "id": 1,
        "code": "REF-001",
        "name": "Refrigerador R-01",
        "type": "Refrigerador",
        "area": "Hematología",
        "status": "OPERATIONAL",
        "temperature": 4.2,
        "min_temperature": 2.0,
        "max_temperature": 8.0,
        "last_maintenance": "2026-09-15",
        "anomaly": False,
    },
    {
        "id": 2,
        "code": "ANA-003",
        "name": "Analizador A-03",
        "type": "Analizador",
        "area": "Química Clínica",
        "status": "OPERATIONAL",
        "temperature": 22.4,
        "min_temperature": 18.0,
        "max_temperature": 25.0,
        "last_maintenance": "2026-09-10",
        "anomaly": False,
    },
    {
        "id": 3,
        "code": "REF-002",
        "name": "Refrigerador R-02",
        "type": "Refrigerador",
        "area": "Microbiología",
        "status": "WARNING",
        "temperature": 8.7,
        "min_temperature": 2.0,
        "max_temperature": 8.0,
        "last_maintenance": "2026-08-21",
        "anomaly": True,
    },
]


@router.get("/")
async def get_equipment() -> dict[str, Any]:
    """Return all laboratory equipment."""
    return {
        "success": True,
        "total": len(equipment_data),
        "equipment": equipment_data,
    }


@router.get("/monitoring/anomalies")
async def get_equipment_anomalies() -> dict[str, Any]:
    """Return equipment currently showing anomalies."""
    anomalies = [
        item
        for item in equipment_data
        if item["anomaly"] is True
    ]

    return {
        "success": True,
        "total": len(anomalies),
        "anomalies": anomalies,
    }


@router.get("/{equipment_id}/status")
async def get_equipment_status(
    equipment_id: int,
) -> dict[str, Any]:
    """Return the current status of laboratory equipment."""
    equipment = next(
        (
            item
            for item in equipment_data
            if item["id"] == equipment_id
        ),
        None,
    )

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found.",
        )

    return {
        "success": True,
        "equipment_code": equipment["code"],
        "status": equipment["status"],
        "temperature": equipment["temperature"],
        "anomaly": equipment["anomaly"],
    }


@router.get("/{equipment_id}")
async def get_equipment_by_id(
    equipment_id: int,
) -> dict[str, Any]:
    """Return a specific piece of laboratory equipment."""
    equipment = next(
        (
            item
            for item in equipment_data
            if item["id"] == equipment_id
        ),
        None,
    )

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found.",
        )

    return {
        "success": True,
        "equipment": equipment,
    }


@router.post("/")
async def create_equipment(
    equipment: dict[str, Any],
) -> dict[str, Any]:
    """Create equipment in temporary in-memory storage."""
    if not equipment.get("code") or not equipment.get("name"):
        raise HTTPException(
            status_code=400,
            detail="Equipment code and name are required.",
        )

    existing_code = next(
        (
            item
            for item in equipment_data
            if item["code"] == equipment["code"]
        ),
        None,
    )

    if existing_code is not None:
        raise HTTPException(
            status_code=409,
            detail="Equipment code already exists.",
        )

    new_id = max(
        (item["id"] for item in equipment_data),
        default=0,
    ) + 1

    new_equipment = {
        "id": new_id,
        "code": equipment["code"],
        "name": equipment["name"],
        "type": equipment.get("type", "Other"),
        "area": equipment.get("area", "Unassigned"),
        "status": equipment.get("status", "OPERATIONAL"),
        "temperature": equipment.get("temperature", 0),
        "min_temperature": equipment.get("min_temperature", 0),
        "max_temperature": equipment.get("max_temperature", 0),
        "last_maintenance": equipment.get("last_maintenance"),
        "anomaly": equipment.get("anomaly", False),
    }

    equipment_data.append(new_equipment)

    return {
        "success": True,
        "message": "Equipment created successfully.",
        "equipment": new_equipment,
    }


@router.put("/{equipment_id}")
async def update_equipment(
    equipment_id: int,
    equipment: dict[str, Any],
) -> dict[str, Any]:
    """Update existing laboratory equipment."""
    existing_equipment = next(
        (
            item
            for item in equipment_data
            if item["id"] == equipment_id
        ),
        None,
    )

    if existing_equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found.",
        )

    if "id" in equipment and equipment["id"] != equipment_id:
        raise HTTPException(
            status_code=400,
            detail="The equipment ID cannot be changed.",
        )

    if "code" in equipment:
        duplicate = any(
            item["code"] == equipment["code"]
            and item["id"] != equipment_id
            for item in equipment_data
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Equipment code already exists.",
            )

    existing_equipment.update(equipment)

    return {
        "success": True,
        "message": "Equipment updated successfully.",
        "equipment": existing_equipment,
    }


@router.delete("/{equipment_id}")
async def delete_equipment(
    equipment_id: int,
) -> dict[str, Any]:
    """Delete laboratory equipment from temporary storage."""
    equipment = next(
        (
            item
            for item in equipment_data
            if item["id"] == equipment_id
        ),
        None,
    )

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found.",
        )

    equipment_data.remove(equipment)

    return {
        "success": True,
        "message": "Equipment deleted successfully.",
        "equipment_id": equipment_id,
    }