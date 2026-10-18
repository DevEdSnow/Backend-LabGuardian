
"""
Risk routes for LabGuardian AI.

Risk assessments are calculated using RiskEngine and persisted
in PostgreSQL together with a sample traceability event.
"""

from datetime import datetime, timezone
from math import isfinite
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sample import Sample
from app.models.sample_event import SampleEvent
from app.services.risk_engine import risk_engine

router = APIRouter(
    prefix="/api/risk",
    tags=["Risk"],
)


def get_sample_or_404(db: Session, sample_code: str) -> Sample:
    """Retrieve a sample using its unique code."""
    sample = db.scalar(
        select(Sample).where(Sample.code == sample_code)
    )

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail=f"Sample '{sample_code}' was not found.",
        )

    return sample


def serialize_risk(sample: Sample) -> dict[str, Any]:
    """Serialize the persisted risk assessment."""
    return {
        "sample_code": sample.code,
        "score": sample.risk_score,
        "level": sample.risk_level,
        "anomaly_detected": sample.anomaly_detected,
        "explanation": sample.risk_explanation,
        "status": (
            "AT_RISK"
            if sample.risk_level in ("HIGH", "CRITICAL")
            else "MONITOR"
            if sample.risk_level == "MEDIUM"
            else "NORMAL"
        ),
    }


def severity_for_level(level: str) -> str:
    """Map a risk level to event severity."""
    return {
        "LOW": "INFO",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "CRITICAL",
    }.get(level, "INFO")


def latest_risk_event(
    db: Session,
    sample_id: int,
) -> SampleEvent | None:
    """Retrieve the latest risk assessment event."""
    return db.scalar(
        select(SampleEvent)
        .where(
            SampleEvent.sample_id == sample_id,
            SampleEvent.event_type == "RISK_ASSESSED",
        )
        .order_by(SampleEvent.occurred_at.desc(), SampleEvent.id.desc())
        .limit(1)
    )


@router.get("/")
def get_all_risks(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List persisted risk assessments for laboratory samples."""
    try:
        samples = db.scalars(
            select(Sample).order_by(Sample.id.desc())
        ).all()

        risks = [
            serialize_risk(sample)
            for sample in samples
            if sample.risk_score is not None
        ]

        return {
            "success": True,
            "total": len(risks),
            "risks": risks,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve risk assessments.",
        ) from exc


@router.post("/calculate")
def calculate_risk(
    data: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Evaluate an existing sample and persist its risk assessment.

    Required request body:
    {
        "sample_code": "YOUR-EXISTING-SAMPLE-CODE"
    }

    The calculation uses database values, not measurements
    supplied by the client.
    """
    sample_code = data.get("sample_code")

    if not isinstance(sample_code, str) or not sample_code.strip():
        raise HTTPException(
            status_code=422,
            detail="sample_code is required.",
        )

    sample_code = sample_code.strip()

    try:
        sample = get_sample_or_404(db, sample_code)

        # Evaluate the actual database model.
        assessment = risk_engine.evaluate(sample)
        result = assessment.to_dict()

        score = result["risk_score"]
        level = result["risk_level"]

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not isfinite(score)
            or not 0 <= score <= 100
        ):
            raise ValueError("Risk engine returned an invalid score.")

        if level not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValueError("Risk engine returned an invalid level.")

        # Persist calculated risk fields.
        sample.risk_score = score
        sample.risk_level = level
        sample.anomaly_detected = result["anomaly_detected"]
        sample.risk_explanation = result["risk_explanation"]
        sample.updated_at = datetime.now(timezone.utc)

        # Store the full assessment in the traceability history.
        event = SampleEvent(
            sample_id=sample.id,
            event_type="RISK_ASSESSED",
            title=f"Evaluación de riesgo: {level}",
            description=result["risk_explanation"],
            status="COMPLETED",
            severity=severity_for_level(level),
            temperature=sample.current_temperature,
            location=sample.storage_location,
            event_metadata={
                "risk_score": score,
                "risk_level": level,
                "anomaly_detected": result["anomaly_detected"],
                "findings": result["findings"],
            },
        )

        db.add(sample)
        db.add(event)
        db.commit()
        db.refresh(sample)
        db.refresh(event)

        return {
            "success": True,
            "message": "Risk assessment calculated and saved.",
            "risk": serialize_risk(sample),
            "assessment": result,
            "event": event.to_dict(),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to calculate or save the risk assessment.",
        ) from exc


@router.get("/sample/{sample_code}/factors")
def get_risk_factors(
    sample_code: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the findings from the latest saved assessment."""
    sample = get_sample_or_404(db, sample_code)
    event = latest_risk_event(db, sample.id)

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="No saved risk assessment exists for this sample.",
        )

    metadata = event.event_metadata or {}

    return {
        "success": True,
        "sample_code": sample.code,
        "score": sample.risk_score,
        "level": sample.risk_level,
        "findings": metadata.get("findings", []),
        "assessed_at": (
            event.occurred_at.isoformat()
            if event.occurred_at
            else None
        ),
    }


@router.get("/sample/{sample_code}")
def get_sample_risk(
    sample_code: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the current persisted risk assessment."""
    sample = get_sample_or_404(db, sample_code)

    if sample.risk_score is None or sample.risk_level is None:
        raise HTTPException(
            status_code=404,
            detail="No risk assessment has been saved for this sample.",
        )

    event = latest_risk_event(db, sample.id)

    return {
        "success": True,
        "risk": serialize_risk(sample),
        "assessment": (
            event.event_metadata
            if event is not None
            else None
        ),
        "assessed_at": (
            event.occurred_at.isoformat()
            if event is not None and event.occurred_at
            else None
        ),
    }


@router.get("/high")
def get_high_risk_samples(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List samples classified as HIGH or CRITICAL."""
    try:
        samples = db.scalars(
            select(Sample)
            .where(Sample.risk_level.in_(("HIGH", "CRITICAL")))
            .order_by(Sample.risk_score.desc())
        ).all()

        return {
            "success": True,
            "total": len(samples),
            "samples": [serialize_risk(sample) for sample in samples],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve high-risk samples.",
        ) from exc


@router.get("/summary")
def get_risk_summary(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Summarize risk assessments currently stored in PostgreSQL."""
    try:
        samples = db.scalars(select(Sample)).all()

        assessed = [
            sample
            for sample in samples
            if sample.risk_score is not None
            and sample.risk_level is not None
        ]

        levels = {
            level: sum(
                1 for sample in assessed
                if sample.risk_level == level
            )
            for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        }

        average_score = (
            sum(float(sample.risk_score) for sample in assessed)
            / len(assessed)
            if assessed
            else 0.0
        )

        return {
            "success": True,
            "summary": {
                "total_samples": len(samples),
                "assessed_samples": len(assessed),
                "unassessed_samples": len(samples) - len(assessed),
                "low_risk": levels["LOW"],
                "medium_risk": levels["MEDIUM"],
                "high_risk": levels["HIGH"],
                "critical_risk": levels["CRITICAL"],
                "average_score": round(average_score, 2),
            },
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to calculate the risk summary.",
        ) from exc
