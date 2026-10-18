
"""
Sample routes for LabGuardian AI.

Endpoints para registrar, consultar, actualizar y eliminar muestras
utilizando PostgreSQL mediante SQLAlchemy y sample_service.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sample import Sample
from app.services import sample_service
from app.services.sample_service import (
    SampleAlreadyExistsError,
    SampleNotFoundError,
    SampleServiceError,
    SampleStateError,
    SampleValidationError,
)
from app.schemas.sample import (
    SampleCreate,
    SampleStatus,
    SampleStatusUpdate,
    SampleUpdate,
)


router = APIRouter(
    prefix="/api/samples",
    tags=["Samples"],
)


# ---------------------------------------------------------
# Utilidades
# ---------------------------------------------------------

def serialize_sample(sample: Sample) -> dict[str, Any]:
    """Convierte una muestra de SQLAlchemy en una respuesta JSON."""
    return sample.to_dict()


def get_sample_or_404(db: Session, sample_id: int) -> Sample:
    """Busca una muestra o devuelve HTTP 404."""
    try:
        return sample_service.get_sample_by_id(db, sample_id)
    except SampleNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


def handle_service_error(exc: SampleServiceError) -> HTTPException:
    """Traduce los errores del servicio a respuestas HTTP."""
    if isinstance(exc, SampleNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))

    if isinstance(exc, SampleAlreadyExistsError):
        return HTTPException(status_code=409, detail=str(exc))

    if isinstance(exc, SampleStateError):
        return HTTPException(status_code=409, detail=str(exc))

    if isinstance(exc, SampleValidationError):
        return HTTPException(status_code=422, detail=str(exc))

    return HTTPException(
        status_code=400,
        detail="No fue posible completar la operación.",
    )


def commit_or_rollback(db: Session) -> None:
    """Confirma la transacción o revierte la sesión si falla."""
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def database_error() -> HTTPException:
    """Respuesta genérica para errores inesperados de persistencia."""
    return HTTPException(
        status_code=500,
        detail="Ocurrió un error al acceder a la base de datos.",
    )


# ---------------------------------------------------------
# GET /api/samples/
# ---------------------------------------------------------

@router.get("/")
def get_samples(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    status: str | None = None,
    priority: str | None = None,
    sample_type: str | None = None,
    laboratory_area: str | None = None,
    risk_level: str | None = None,
    anomaly_detected: bool | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """Lista muestras almacenadas en PostgreSQL con filtros opcionales."""
    try:
        result = sample_service.list_samples(
            db,
            status=status,
            priority=priority,
            sample_type=sample_type,
            laboratory_area=laboratory_area,
            risk_level=risk_level,
            anomaly_detected=anomaly_detected,
            search=search,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        return {
            "success": True,
            "total": result["total"],
            "page": page,
            "page_size": page_size,
            "samples": [
                serialize_sample(item)
                for item in result["items"]
            ],
        }
    except SampleServiceError as exc:
        raise handle_service_error(exc) from exc
    except Exception as exc:
        raise database_error() from exc


# ---------------------------------------------------------
# GET /api/samples/code/{sample_code}
# Esta ruta específica se declara antes de /{sample_id}.
# ---------------------------------------------------------

@router.get("/code/{sample_code}")
def get_sample_by_code(
    sample_code: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Busca una muestra por su código único."""
    try:
        sample = sample_service.get_sample_by_code(db, sample_code)

        return {
            "success": True,
            "sample": serialize_sample(sample),
        }
    except SampleServiceError as exc:
        raise handle_service_error(exc) from exc
    except Exception as exc:
        raise database_error() from exc


# ---------------------------------------------------------
# GET /api/samples/risk/high
# ---------------------------------------------------------

@router.get("/risk/high")
def get_high_risk_samples(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Obtiene las muestras con riesgo alto o crítico."""
    try:
        result = sample_service.list_samples(
            db,
            risk_level="HIGH",
            limit=1000,
        )
        critical = sample_service.list_samples(
            db,
            risk_level="CRITICAL",
            limit=1000,
        )

        samples = result["items"] + critical["items"]

        return {
            "success": True,
            "total": len(samples),
            "samples": [serialize_sample(item) for item in samples],
        }
    except SampleServiceError as exc:
        raise handle_service_error(exc) from exc
    except Exception as exc:
        raise database_error() from exc


# ---------------------------------------------------------
# GET /api/samples/status/{status}
# ---------------------------------------------------------

@router.get("/status/{status}")
def get_samples_by_status(
    status: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Filtra las muestras por su estado actual."""
    try:
        result = sample_service.list_samples(
            db,
            status=status,
            limit=1000,
        )

        return {
            "success": True,
            "status": status.upper(),
            "total": result["total"],
            "samples": [
                serialize_sample(item)
                for item in result["items"]
            ],
        }
    except SampleServiceError as exc:
        raise handle_service_error(exc) from exc
    except Exception as exc:
        raise database_error() from exc


# ---------------------------------------------------------
# POST /api/samples/
# ---------------------------------------------------------

@router.post("/", status_code=201)
def create_sample(
    data: SampleCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Registra una muestra y su primer evento de trazabilidad."""
    try:
        sample = sample_service.create_sample(db, data)
        commit_or_rollback(db)
        db.refresh(sample)

        return {
            "success": True,
            "message": "Sample registered successfully.",
            "sample": serialize_sample(sample),
        }
    except SampleServiceError as exc:
        db.rollback()
        raise handle_service_error(exc) from exc
    except Exception as exc:
        db.rollback()
        raise database_error() from exc


# ---------------------------------------------------------
# GET /api/samples/{sample_id}/status
# ---------------------------------------------------------

@router.get("/{sample_id}/status")
def get_sample_status(
    sample_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Consulta el estado y el riesgo actual de una muestra."""
    sample = get_sample_or_404(db, sample_id)

    return {
        "success": True,
        "sample_code": sample.code,
        "status": sample.status,
        "priority": sample.priority,
        "risk_level": sample.risk_level,
        "risk_score": sample.risk_score,
        "anomaly": sample.anomaly_detected,
    }


# ---------------------------------------------------------
# GET /api/samples/{sample_id}/passport
# ---------------------------------------------------------

@router.get("/{sample_id}/passport")
def get_sample_passport(
    sample_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Devuelve el pasaporte digital de la muestra."""
    sample = get_sample_or_404(db, sample_id)

    return {
        "success": True,
        "passport": {
            "id": sample.id,
            "sample_code": sample.code,
            "sample_type": sample.sample_type,
            "area": sample.laboratory_area,
            "status": sample.status,
            "priority": sample.priority,
            "risk": {
                "score": sample.risk_score,
                "level": sample.risk_level,
                "explanation": sample.risk_explanation,
            },
            "temperature": sample.current_temperature,
            "anomaly": sample.anomaly_detected,
            "collection_date": (
                sample.collected_at.isoformat()
                if sample.collected_at else None
            ),
            "reception_date": (
                sample.received_at.isoformat()
                if sample.received_at else None
            ),
            "processing_date": (
                sample.processed_at.isoformat()
                if sample.processed_at else None
            ),
            "storage_location": sample.storage_location,
            "notes": sample.notes,
        },
    }


# ---------------------------------------------------------
# GET /api/samples/{sample_id}
# ---------------------------------------------------------

@router.get("/{sample_id}")
def get_sample(
    sample_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Busca una muestra por su ID."""
    sample = get_sample_or_404(db, sample_id)

    return {
        "success": True,
        "sample": serialize_sample(sample),
    }


# ---------------------------------------------------------
# PUT /api/samples/{sample_id}
# ---------------------------------------------------------

@router.put("/{sample_id}")
def update_sample(
    sample_id: int,
    data: SampleUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Actualiza los campos editables y registra el evento."""
    try:
        sample = sample_service.update_sample(db, sample_id, data)
        commit_or_rollback(db)
        db.refresh(sample)

        return {
            "success": True,
            "message": "Sample updated successfully.",
            "sample": serialize_sample(sample),
        }
    except SampleServiceError as exc:
        db.rollback()
        raise handle_service_error(exc) from exc
    except Exception as exc:
        db.rollback()
        raise database_error() from exc


# ---------------------------------------------------------
# PATCH /api/samples/{sample_id}/status
# ---------------------------------------------------------

@router.patch("/{sample_id}/status")
def update_sample_status(
    sample_id: int,
    data: SampleStatusUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Actualiza el estado y registra la trazabilidad."""
    try:
        sample = sample_service.update_sample_status(
            db,
            sample_id,
            data,
        )
        commit_or_rollback(db)
        db.refresh(sample)

        return {
            "success": True,
            "message": "Sample status updated successfully.",
            "sample_code": sample.code,
            "status": sample.status,
        }
    except SampleServiceError as exc:
        db.rollback()
        raise handle_service_error(exc) from exc
    except Exception as exc:
        db.rollback()
        raise database_error() from exc


# ---------------------------------------------------------
# PATCH /api/samples/{sample_id}/risk
# ---------------------------------------------------------

@router.patch("/{sample_id}/risk")
def update_sample_risk(
    sample_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Actualiza los datos de riesgo de una muestra.

    Este endpoint actualiza los campos de riesgo almacenados.
    La predicción real debe proceder del motor de riesgo de LabGuardian.
    """
    sample = get_sample_or_404(db, sample_id)

    score = data.get("risk_score")

    if score is None:
        raise HTTPException(
            status_code=422,
            detail="risk_score is required.",
        )

    try:
        score = float(score)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="risk_score must be a number.",
        ) from exc

    if not 0 <= score <= 100:
        raise HTTPException(
            status_code=422,
            detail="risk_score must be between 0 and 100.",
        )

    level = (
        "CRITICAL" if score >= 85
        else "HIGH" if score >= 70
        else "MEDIUM" if score >= 40
        else "LOW"
    )

    try:
        sample.risk_score = score
        sample.risk_level = level
        sample.anomaly_detected = bool(data.get("anomaly_detected", False))

        if "risk_explanation" in data:
            sample.risk_explanation = data["risk_explanation"]

        sample.updated_at = datetime.now(timezone.utc)

        db.add(sample)
        commit_or_rollback(db)
        db.refresh(sample)

        return {
            "success": True,
            "message": "Sample risk updated successfully.",
            "sample_code": sample.code,
            "risk_score": sample.risk_score,
            "risk_level": sample.risk_level,
            "anomaly_detected": sample.anomaly_detected,
        }
    except Exception as exc:
        db.rollback()
        raise database_error() from exc


# ---------------------------------------------------------
# DELETE /api/samples/{sample_id}
# ---------------------------------------------------------

@router.delete("/{sample_id}")
def delete_sample(
    sample_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Elimina una muestra de PostgreSQL.

    Nota: el modelo define ON DELETE CASCADE para sus eventos.
    Si el laboratorio necesita conservar permanentemente el historial,
    conviene sustituir esta operación por rechazo o descarte.
    """
    sample = get_sample_or_404(db, sample_id)
    sample_id_value = sample.id
    code = sample.code

    try:
        db.delete(sample)
        commit_or_rollback(db)

        return {
            "success": True,
            "message": "Sample deleted successfully.",
            "sample_id": sample_id_value,
            "sample_code": code,
        }
    except Exception as exc:
        db.rollback()
        raise database_error() from exc
