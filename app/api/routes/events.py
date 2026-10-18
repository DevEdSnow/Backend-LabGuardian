
"""
Event routes for LabGuardian AI.

Traceability events are persisted in PostgreSQL through SQLAlchemy.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sample import Sample
from app.models.sample_event import SampleEvent
from app.schemas.sample_event import (
    SampleEventSeverity,
    SampleEventStatus,
    SampleEventType,
)

router = APIRouter(
    prefix="/api/events",
    tags=["Events"],
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def enum_values(enum_class) -> set[str]:
    """Return the accepted values of an enum."""
    return {item.value for item in enum_class}


def normalize_event_type(value: str) -> str:
    """Translate legacy event names into supported event types."""
    aliases = {
        "RECEPTION": "RECEIVED",
        "IDENTIFICATION": "IDENTIFIED",
        "TRANSPORT": "TRANSPORT_COMPLETED",
        "STORAGE": "STORAGE_STARTED",
        "RESULT": "RESULT_RELEASED",
    }

    normalized = str(value).strip().upper()
    normalized = aliases.get(normalized, normalized)

    if normalized not in enum_values(SampleEventType):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported event_type: {value}",
        )

    return normalized


def normalize_status(value: str) -> str:
    """Validate an event status."""
    normalized = str(value).strip().upper()

    if normalized == "WARNING":
        normalized = "COMPLETED"

    if normalized not in enum_values(SampleEventStatus):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported event status: {value}",
        )

    return normalized


def normalize_severity(value: str | None) -> str:
    """Validate event severity."""
    normalized = str(value or "INFO").strip().upper()

    if normalized == "WARNING":
        normalized = "MEDIUM"

    if normalized not in enum_values(SampleEventSeverity):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported event severity: {value}",
        )

    return normalized


def parse_timestamp(value: Any) -> datetime:
    """Parse an ISO timestamp or use the current UTC time."""
    if value is None:
        return datetime.now(timezone.utc)

    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="timestamp must be a valid ISO 8601 date.",
            ) from exc
    else:
        raise HTTPException(
            status_code=422,
            detail="timestamp must be an ISO 8601 string.",
        )

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result


def serialize_event(
    event: SampleEvent,
    sample_code: str,
) -> dict[str, Any]:
    """Serialize a database event using the existing API response shape."""
    occurred_at = event.occurred_at

    return {
        "id": event.id,
        "sample_id": event.sample_id,
        "sample_code": sample_code,
        "event_type": event.event_type,
        "title": event.title,
        "status": event.status,
        "severity": event.severity,
        "description": event.description,
        "location": event.location,
        "temperature": event.temperature,
        "duration_minutes": event.duration_minutes,
        "performed_by": event.performed_by,
        "timestamp": (
            occurred_at.isoformat()
            if occurred_at is not None
            else None
        ),
        "created_at": (
            event.created_at.isoformat()
            if event.created_at is not None
            else None
        ),
    }


def get_event_or_404(
    db: Session,
    event_id: int,
) -> tuple[SampleEvent, Sample]:
    """Retrieve an event and its sample."""
    row = db.execute(
        select(SampleEvent, Sample)
        .join(Sample, Sample.id == SampleEvent.sample_id)
        .where(SampleEvent.id == event_id)
    ).first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found.",
        )

    return row[0], row[1]


def get_sample_or_404(
    db: Session,
    sample_code: str,
) -> Sample:
    """Retrieve a sample by its unique code."""
    sample = db.scalar(
        select(Sample).where(Sample.code == sample_code)
    )

    if sample is None:
        raise HTTPException(
            status_code=404,
            detail="Sample not found.",
        )

    return sample


def get_events_for_sample(
    db: Session,
    sample_code: str,
) -> tuple[Sample, list[SampleEvent]]:
    """Retrieve a sample and its persisted events in chronological order."""
    sample = get_sample_or_404(db, sample_code)

    events = list(
        db.scalars(
            select(SampleEvent)
            .where(SampleEvent.sample_id == sample.id)
            .order_by(
                SampleEvent.occurred_at.asc(),
                SampleEvent.id.asc(),
            )
        ).all()
    )

    return sample, events


# ---------------------------------------------------------
# GET /api/events/
# ---------------------------------------------------------

@router.get("/")
def get_events(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return all persisted traceability events."""
    try:
        rows = db.execute(
            select(SampleEvent, Sample)
            .join(Sample, Sample.id == SampleEvent.sample_id)
            .order_by(
                SampleEvent.occurred_at.desc(),
                SampleEvent.id.desc(),
            )
        ).all()

        events = [
            serialize_event(event, sample.code)
            for event, sample in rows
        ]

        return {
            "success": True,
            "total": len(events),
            "events": events,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve traceability events.",
        ) from exc


# ---------------------------------------------------------
# GET /api/events/sample/{sample_code}/timeline
# ---------------------------------------------------------

@router.get("/sample/{sample_code}/timeline")
def get_sample_timeline(
    sample_code: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the chronological timeline of a sample."""
    try:
        sample, events = get_events_for_sample(db, sample_code)

        timeline = [
            {
                "event_type": event.event_type,
                "title": event.title,
                "status": event.status,
                "severity": event.severity,
                "location": event.location,
                "timestamp": (
                    event.occurred_at.isoformat()
                    if event.occurred_at else None
                ),
            }
            for event in events
        ]

        return {
            "success": True,
            "sample_code": sample.code,
            "total": len(timeline),
            "timeline": timeline,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve the sample timeline.",
        ) from exc


# ---------------------------------------------------------
# GET /api/events/sample/{sample_code}
# ---------------------------------------------------------

@router.get("/sample/{sample_code}")
def get_sample_events(
    sample_code: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return all persisted events associated with a sample."""
    try:
        sample, events = get_events_for_sample(db, sample_code)

        serialized = [
            serialize_event(event, sample.code)
            for event in events
        ]

        return {
            "success": True,
            "sample_code": sample.code,
            "total": len(serialized),
            "events": serialized,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve the sample events.",
        ) from exc


# ---------------------------------------------------------
# POST /api/events/
# ---------------------------------------------------------

@router.post("/", status_code=201)
def create_event(
    data: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a traceability event in PostgreSQL."""
    sample_code = data.get("sample_code")
    event_type = data.get("event_type")

    if not sample_code or not event_type:
        raise HTTPException(
            status_code=422,
            detail="sample_code and event_type are required.",
        )

    try:
        sample = get_sample_or_404(db, str(sample_code))

        normalized_type = normalize_event_type(str(event_type))
        status = normalize_status(data.get("status", "COMPLETED"))
        severity = normalize_severity(data.get("severity"))

        temperature = data.get("temperature")
        if temperature is not None:
            temperature = float(temperature)

        duration = data.get("duration_minutes")
        if duration is not None:
            duration = float(duration)

        event = SampleEvent(
            sample_id=sample.id,
            event_type=normalized_type,
            title=str(data.get("title") or normalized_type.replace("_", " ").title()),
            description=str(data.get("description") or ""),
            status=status,
            severity=severity,
            temperature=temperature,
            duration_minutes=duration,
            location=data.get("location"),
            performed_by=data.get("performed_by", "Sistema"),
            equipment_id=data.get("equipment_id"),
            event_metadata=data.get("event_metadata"),
            occurred_at=parse_timestamp(
                data.get("timestamp", data.get("occurred_at"))
            ),
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        return {
            "success": True,
            "message": "Event created successfully.",
            "event": serialize_event(event, sample.code),
        }
    except HTTPException:
        db.rollback()
        raise
    except (TypeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="One or more event fields have invalid values.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the traceability event.",
        ) from exc


# ---------------------------------------------------------
# GET /api/events/{event_id}
# ---------------------------------------------------------

@router.get("/{event_id}")
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return a persisted event."""
    try:
        event, sample = get_event_or_404(db, event_id)

        return {
            "success": True,
            "event": serialize_event(event, sample.code),
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve the event.",
        ) from exc


# ---------------------------------------------------------
# PUT /api/events/{event_id}
# ---------------------------------------------------------

@router.put("/{event_id}")
def update_event(
    event_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update editable fields of a persisted event."""
    try:
        event, sample = get_event_or_404(db, event_id)

        if "id" in data and data["id"] != event_id:
            raise HTTPException(
                status_code=400,
                detail="The event ID cannot be changed.",
            )

        if "sample_code" in data and data["sample_code"] != sample.code:
            raise HTTPException(
                status_code=400,
                detail="The event cannot be reassigned to another sample.",
            )

        if "sample_id" in data and data["sample_id"] != sample.id:
            raise HTTPException(
                status_code=400,
                detail="The event cannot be reassigned to another sample.",
            )

        if "event_type" in data:
            event.event_type = normalize_event_type(data["event_type"])

        if "status" in data:
            event.status = normalize_status(data["status"])

        if "severity" in data:
            event.severity = normalize_severity(data["severity"])

        if "timestamp" in data or "occurred_at" in data:
            event.occurred_at = parse_timestamp(
                data.get("timestamp", data.get("occurred_at"))
            )

        for field in (
            "title",
            "description",
            "location",
            "performed_by",
            "temperature",
            "duration_minutes",
            "equipment_id",
            "event_metadata",
        ):
            if field in data:
                setattr(event, field, data[field])

        db.commit()
        db.refresh(event)

        return {
            "success": True,
            "message": "Event updated successfully.",
            "event": serialize_event(event, sample.code),
        }
    except HTTPException:
        db.rollback()
        raise
    except (TypeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="One or more event fields have invalid values.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update the event.",
        ) from exc


# ---------------------------------------------------------
# DELETE /api/events/{event_id}
# ---------------------------------------------------------

@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a persisted event."""
    try:
        event, _sample = get_event_or_404(db, event_id)

        db.delete(event)
        db.commit()

        return {
            "success": True,
            "message": "Event deleted successfully.",
            "event_id": event_id,
        }
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not delete the event.",
        ) from exc
