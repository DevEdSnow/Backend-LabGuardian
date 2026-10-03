"""
Event routes for LabGuardian AI.

This module manages the traceability events associated
with clinical samples.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(
prefix="/api/events",
tags=["Events"],
)

# ─────────────────────────────────────────────

# Temporary mock data

# ─────────────────────────────────────────────

events_data: list[dict[str, Any]] = [
{
"id": 1,
"sample_code": "A49281",
"event_type": "RECEPTION",
"status": "COMPLETED",
"description": "Muestra recibida en el laboratorio.",
"location": "Recepción",
"temperature": 5.2,
"performed_by": "Sistema",
"timestamp": "2026-10-03T08:32:00Z",
},
{
"id": 2,
"sample_code": "A49281",
"event_type": "IDENTIFICATION",
"status": "COMPLETED",
"description": "Muestra identificada y registrada.",
"location": "Recepción",
"temperature": 5.4,
"performed_by": "Sistema",
"timestamp": "2026-10-03T08:35:00Z",
},
{
"id": 3,
"sample_code": "A49281",
"event_type": "TRANSPORT",
"status": "COMPLETED",
"description": "Muestra trasladada al área de procesamiento.",
"location": "Transporte interno",
"temperature": 7.8,
"performed_by": "Operador-01",
"timestamp": "2026-10-03T09:02:00Z",
},
{
"id": 4,
"sample_code": "A49281",
"event_type": "STORAGE",
"status": "WARNING",
"description": "Temperatura de almacenamiento fuera del rango recomendado.",
"location": "Refrigerador R-02",
"temperature": 8.7,
"performed_by": "Sistema",
"timestamp": "2026-10-03T09:21:00Z",
},
{
"id": 5,
"sample_code": "A49281",
"event_type": "PROCESSING",
"status": "COMPLETED",
"description": "Muestra enviada a procesamiento.",
"location": "Hematología",
"temperature": 5.1,
"performed_by": "Operador-02",
"timestamp": "2026-10-03T09:47:00Z",
},
{
"id": 6,
"sample_code": "A49281",
"event_type": "RESULT",
"status": "COMPLETED",
"description": "Resultado generado y validado.",
"location": "Hematología",
"temperature": 5.0,
"performed_by": "Sistema",
"timestamp": "2026-10-03T10:03:00Z",
},
]

# ─────────────────────────────────────────────

# GET /api/events

# ─────────────────────────────────────────────

@router.get("/")
async def get_events() -> dict[str, Any]:
"""
Returns all traceability events.
"""

```
return {
    "success": True,
    "total": len(events_data),
    "events": events_data,
}
```

# ─────────────────────────────────────────────

# GET /api/events/{event_id}

# ─────────────────────────────────────────────

@router.get("/{event_id}")
async def get_event(event_id: int) -> dict[str, Any]:
"""
Returns a specific traceability event.
"""

```
event = next(
    (
        item
        for item in events_data
        if item["id"] == event_id
    ),
    None,
)

if event is None:
    raise HTTPException(
        status_code=404,
        detail="Event not found.",
    )

return {
    "success": True,
    "event": event,
}
```

# ─────────────────────────────────────────────

# GET /api/events/sample/{sample_code}

# ─────────────────────────────────────────────

@router.get("/sample/{sample_code}")
async def get_sample_events(
sample_code: str,
) -> dict[str, Any]:
"""
Returns the complete traceability history
of a specific sample.
"""

```
sample_events = [
    event
    for event in events_data
    if event["sample_code"] == sample_code
]

if not sample_events:
    raise HTTPException(
        status_code=404,
        detail="No events found for this sample.",
    )

return {
    "success": True,
    "sample_code": sample_code,
    "total": len(sample_events),
    "events": sample_events,
}
```

# ─────────────────────────────────────────────

# GET /api/events/sample/{sample_code}/timeline

# ─────────────────────────────────────────────

@router.get("/sample/{sample_code}/timeline")
async def get_sample_timeline(
sample_code: str,
) -> dict[str, Any]:
"""
Returns a simplified timeline for a sample.
"""

```
sample_events = [
    event
    for event in events_data
    if event["sample_code"] == sample_code
]

if not sample_events:
    raise HTTPException(
        status_code=404,
        detail="No events found for this sample.",
    )

timeline = [
    {
        "event_type": event["event_type"],
        "status": event["status"],
        "location": event["location"],
        "timestamp": event["timestamp"],
    }
    for event in sample_events
]

return {
    "success": True,
    "sample_code": sample_code,
    "timeline": timeline,
}
```

# ─────────────────────────────────────────────

# POST /api/events

# ─────────────────────────────────────────────

@router.post("/")
async def create_event(
event: dict[str, Any],
) -> dict[str, Any]:
"""
Creates a new traceability event.

```
Data will be persisted in PostgreSQL later.
"""

new_id = (
    max(
        (item["id"] for item in events_data),
        default=0,
    )
    \+ 1
)

new_event = {
    "id": new_id,
    "sample_code": event.get("sample_code"),
    "event_type": event.get("event_type"),
    "status": event.get(
        "status",
        "COMPLETED",
    ),
    "description": event.get(
        "description",
        "",
    ),
    "location": event.get(
        "location",
        "",
    ),
    "temperature": event.get(
        "temperature",
    ),
    "performed_by": event.get(
        "performed_by",
        "System",
    ),
    "timestamp": event.get(
        "timestamp",
        datetime.now(timezone.utc).isoformat(),
    ),
}

events_data.append(new_event)

return {
    "success": True,
    "message": "Event created successfully.",
    "event": new_event,
}
```

# ─────────────────────────────────────────────

# PUT /api/events/{event_id}

# ─────────────────────────────────────────────

@router.put("/{event_id}")
async def update_event(
event_id: int,
event: dict[str, Any],
) -> dict[str, Any]:
"""
Updates an existing traceability event.
"""

```
existing_event = next(
    (
        item
        for item in events_data
        if item["id"] == event_id
    ),
    None,
)

if existing_event is None:
    raise HTTPException(
        status_code=404,
        detail="Event not found.",
    )

existing_event.update(event)

return {
    "success": True,
    "message": "Event updated successfully.",
    "event": existing_event,
}
```

# ─────────────────────────────────────────────

# DELETE /api/events/{event_id}

# ─────────────────────────────────────────────

@router.delete("/{event_id}")
async def delete_event(
event_id: int,
) -> dict[str, Any]:
"""
Deletes a traceability event.
"""

```
event = next(
    (
        item
        for item in events_data
        if item["id"] == event_id
    ),
    None,
)

if event is None:
    raise HTTPException(
        status_code=404,
        detail="Event not found.",
    )

events_data.remove(event)

return {
    "success": True,
    "message": "Event deleted successfully.",
    "event_id": event_id,
}
```
