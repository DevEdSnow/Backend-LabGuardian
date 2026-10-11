
"""
Initial demonstration data for LabGuardian AI.

Todos los registros son ficticios y están destinados únicamente
al desarrollo y las pruebas del sistema.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.alert import Alert
from app.models.equipment import Equipment
from app.models.sample import Sample
from app.models.sample_event import SampleEvent
from app.models.user import User


# ============================================================
# HELPERS
# ============================================================

def utc_now() -> datetime:
    """Devuelve la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


def ensure_user(
    db: Session,
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    department: str,
    password: str,
) -> User:
    """Crea un usuario si todavía no existe."""
    user = db.scalar(
        select(User).where(User.username == username)
    )

    if user is not None:
        return user

    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        hashed_password=hash_password(password),
        role=role,
        department=department,
        is_active=True,
        is_verified=True,
    )

    db.add(user)
    db.flush()

    return user


def ensure_equipment(
    db: Session,
    *,
    code: str,
    name: str,
    equipment_type: str,
    area: str,
    location: str,
    status: str = "OPERATIONAL",
    current_temperature: float | None = None,
    minimum_temperature: float | None = None,
    maximum_temperature: float | None = None,
    anomaly_detected: bool = False,
    anomaly_type: str | None = None,
    anomaly_message: str | None = None,
) -> Equipment:
    """Crea un equipo de demostración si no existe."""
    equipment = db.scalar(
        select(Equipment).where(Equipment.code == code)
    )

    if equipment is not None:
        return equipment

    equipment = Equipment(
        code=code,
        name=name,
        equipment_type=equipment_type,
        area=area,
        location=location,
        status=status,
        current_temperature=current_temperature,
        minimum_temperature=minimum_temperature,
        maximum_temperature=maximum_temperature,
        anomaly_detected=anomaly_detected,
        anomaly_type=anomaly_type,
        anomaly_message=anomaly_message,
        last_seen_at=utc_now(),
        description="Equipo ficticio para pruebas de LabGuardian AI.",
    )

    db.add(equipment)
    db.flush()

    return equipment


def ensure_sample(
    db: Session,
    *,
    code: str,
    sample_type: str,
    laboratory_area: str,
    status: str,
    priority: str,
    collected_at: datetime,
    received_at: datetime,
    transport_minutes: float,
    processing_minutes: float,
    storage_minutes: float,
    current_temperature: float,
    minimum_temperature: float,
    maximum_temperature: float,
    storage_location: str,
    risk_score: float,
    risk_level: str,
    anomaly_detected: bool,
    risk_explanation: str,
    processing_started_at: datetime | None = None,
    processed_at: datetime | None = None,
    result_at: datetime | None = None,
) -> Sample:
    """Crea una muestra de demostración si su código no existe."""
    sample = db.scalar(
        select(Sample).where(Sample.code == code)
    )

    if sample is not None:
        return sample

    sample = Sample(
        code=code,
        sample_type=sample_type,
        laboratory_area=laboratory_area,
        status=status,
        priority=priority,
        collected_at=collected_at,
        received_at=received_at,
        processing_started_at=processing_started_at,
        processed_at=processed_at,
        result_at=result_at,
        transport_minutes=transport_minutes,
        processing_minutes=processing_minutes,
        storage_minutes=storage_minutes,
        current_temperature=current_temperature,
        minimum_temperature=minimum_temperature,
        maximum_temperature=maximum_temperature,
        storage_location=storage_location,
        risk_score=risk_score,
        risk_level=risk_level,
        anomaly_detected=anomaly_detected,
        risk_explanation=risk_explanation,
        notes="Registro ficticio para pruebas y demostraciones.",
    )

    db.add(sample)
    db.flush()

    return sample


def ensure_event(
    db: Session,
    *,
    sample_id: int,
    event_type: str,
    title: str,
    description: str,
    occurred_at: datetime,
    status: str = "COMPLETED",
    severity: str = "INFO",
    temperature: float | None = None,
    duration_minutes: float | None = None,
    location: str | None = None,
    performed_by: str | None = None,
    equipment_id: int | None = None,
) -> SampleEvent:
    """Evita duplicar un evento al ejecutar el seed varias veces."""
    existing = db.scalar(
        select(SampleEvent).where(
            SampleEvent.sample_id == sample_id,
            SampleEvent.event_type == event_type,
            SampleEvent.title == title,
        )
    )

    if existing is not None:
        return existing

    event = SampleEvent(
        sample_id=sample_id,
        event_type=event_type,
        title=title,
        description=description,
        occurred_at=occurred_at,
        status=status,
        severity=severity,
        temperature=temperature,
        duration_minutes=duration_minutes,
        location=location,
        performed_by=performed_by,
        equipment_id=equipment_id,
        event_metadata={"source": "initial_seed"},
    )

    db.add(event)
    db.flush()

    return event


def ensure_alert(
    db: Session,
    *,
    sample: Sample | None,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    risk_score: float | None,
    source: str = "SYSTEM",
) -> Alert:
    """Crea una alerta si todavía no existe una equivalente."""
    statement = select(Alert).where(
        Alert.title == title,
        Alert.source == source,
    )

    if sample is not None:
        statement = statement.where(Alert.sample_id == sample.id)
    else:
        statement = statement.where(Alert.sample_id.is_(None))

    existing = db.scalar(statement)

    if existing is not None:
        return existing

    alert = Alert(
        sample_id=sample.id if sample else None,
        sample_code=sample.code if sample else None,
        alert_type=alert_type,
        severity=severity,
        status="ACTIVE",
        title=title,
        message=message,
        risk_score=risk_score,
        source=source,
    )

    db.add(alert)
    db.flush()

    return alert


# ============================================================
# INITIAL USERS
# ============================================================

def seed_users(db: Session) -> list[User]:
    """Registra usuarios ficticios para probar los roles."""

    demo_users = [
        {
            "username": "admin_demo",
            "email": "admin.demo@example.com",
            "first_name": "Administrador",
            "last_name": "Demostración",
            "role": "ADMIN",
            "department": "Administración",
            "password": "ChangeMe_Admin_2026!",
        },
        {
            "username": "tecnico_demo",
            "email": "tecnico.demo@example.com",
            "first_name": "Técnico",
            "last_name": "Demostración",
            "role": "LAB_TECHNICIAN",
            "department": "Procesamiento",
            "password": "ChangeMe_Tecnico_2026!",
        },
        {
            "username": "supervisor_demo",
            "email": "supervisor.demo@example.com",
            "first_name": "Supervisor",
            "last_name": "Demostración",
            "role": "LAB_SUPERVISOR",
            "department": "Control de calidad",
            "password": "ChangeMe_Supervisor_2026!",
        },
    ]

    return [
        ensure_user(db, **user_data)
        for user_data in demo_users
    ]


# ============================================================
# INITIAL EQUIPMENT
# ============================================================

def seed_equipment(db: Session) -> list[Equipment]:
    """Registra equipos ficticios del laboratorio."""

    equipment_data = [
        {
            "code": "REF-001",
            "name": "Refrigerador de muestras A",
            "equipment_type": "REFRIGERATOR",
            "area": "Hematología",
            "location": "Sala fría A",
            "current_temperature": 4.5,
            "minimum_temperature": 2.0,
            "maximum_temperature": 8.0,
        },
        {
            "code": "REF-002",
            "name": "Refrigerador de muestras B",
            "equipment_type": "REFRIGERATOR",
            "area": "Bioquímica",
            "location": "Sala fría B",
            "current_temperature": 9.4,
            "minimum_temperature": 2.0,
            "maximum_temperature": 8.0,
            "anomaly_detected": True,
            "anomaly_type": "TEMPERATURE_OUT_OF_RANGE",
            "anomaly_message": (
                "Temperatura superior al rango configurado."
            ),
        },
        {
            "code": "CEN-001",
            "name": "Centrífuga clínica A",
            "equipment_type": "CENTRIFUGE",
            "area": "Hematología",
            "location": "Mesa de procesamiento 1",
        },
        {
            "code": "ANA-001",
            "name": "Analizador bioquímico A",
            "equipment_type": "ANALYZER",
            "area": "Bioquímica",
            "location": "Sala de análisis",
        },
        {
            "code": "INC-001",
            "name": "Incubadora clínica A",
            "equipment_type": "INCUBATOR",
            "area": "Microbiología",
            "location": "Sala de microbiología",
            "current_temperature": 36.5,
            "minimum_temperature": 35.0,
            "maximum_temperature": 37.5,
        },
    ]

    return [
        ensure_equipment(db, **equipment_data_item)
        for equipment_data_item in equipment_data
    ]


# ============================================================
# INITIAL SAMPLES
# ============================================================

def seed_samples(db: Session) -> list[Sample]:
    """Registra muestras ficticias con diferentes niveles de riesgo."""

    now = utc_now()

    samples_data = [
        {
            "code": "LG-2026-0001",
            "sample_type": "BLOOD",
            "laboratory_area": "Hematología",
            "status": "RECEIVED",
            "priority": "NORMAL",
            "collected_at": now - timedelta(hours=1, minutes=20),
            "received_at": now - timedelta(minutes=40),
            "transport_minutes": 40,
            "processing_minutes": 0,
            "storage_minutes": 20,
            "current_temperature": 4.5,
            "minimum_temperature": 2.0,
            "maximum_temperature": 8.0,
            "storage_location": "REF-001 / Estante A",
            "risk_score": 12.0,
            "risk_level": "LOW",
            "anomaly_detected": False,
            "risk_explanation": "Sin anomalías importantes en los datos de demostración.",
        },
        {
            "code": "LG-2026-0002",
            "sample_type": "SERUM",
            "laboratory_area": "Bioquímica",
            "status": "PROCESSING",
            "priority": "HIGH",
            "collected_at": now - timedelta(hours=2),
            "received_at": now - timedelta(hours=1, minutes=35),
            "processing_started_at": now - timedelta(minutes=25),
            "transport_minutes": 25,
            "processing_minutes": 25,
            "storage_minutes": 45,
            "current_temperature": 5.2,
            "minimum_temperature": 2.0,
            "maximum_temperature": 8.0,
            "storage_location": "Área de procesamiento",
            "risk_score": 38.0,
            "risk_level": "MEDIUM",
            "anomaly_detected": False,
            "risk_explanation": "Muestra prioritaria en procesamiento.",
        },
        {
            "code": "LG-2026-0003",
            "sample_type": "PLASMA",
            "laboratory_area": "Bioquímica",
            "status": "IN_STORAGE",
            "priority": "HIGH",
            "collected_at": now - timedelta(hours=3),
            "received_at": now - timedelta(hours=2, minutes=20),
            "transport_minutes": 40,
            "processing_minutes": 0,
            "storage_minutes": 140,
            "current_temperature": 9.4,
            "minimum_temperature": 2.0,
            "maximum_temperature": 8.0,
            "storage_location": "REF-002 / Estante B",
            "risk_score": 82.0,
            "risk_level": "HIGH",
            "anomaly_detected": True,
            "risk_explanation": (
                "Temperatura por encima del máximo configurado "
                "y tiempo de almacenamiento prolongado."
            ),
        },
        {
            "code": "LG-2026-0004",
            "sample_type": "URINE",
            "laboratory_area": "Uroanálisis",
            "status": "COMPLETED",
            "priority": "NORMAL",
            "collected_at": now - timedelta(hours=4),
            "received_at": now - timedelta(hours=3, minutes=40),
            "processing_started_at": now - timedelta(hours=3),
            "processed_at": now - timedelta(hours=2, minutes=30),
            "result_at": now - timedelta(hours=2),
            "transport_minutes": 20,
            "processing_minutes": 30,
            "storage_minutes": 10,
            "current_temperature": 5.0,
            "minimum_temperature": 2.0,
            "maximum_temperature": 8.0,
            "storage_location": "Área de uroanálisis",
            "risk_score": 8.0,
            "risk_level": "LOW",
            "anomaly_detected": False,
            "risk_explanation": "Proceso de demostración completado sin anomalías registradas.",
        },
        {
            "code": "LG-2026-0005",
            "sample_type": "SWAB",
            "laboratory_area": "Microbiología",
            "status": "RECEIVED",
            "priority": "STAT",
            "collected_at": now - timedelta(hours=2, minutes=30),
            "received_at": now - timedelta(minutes=15),
            "transport_minutes": 135,
            "processing_minutes": 0,
            "storage_minutes": 0,
            "current_temperature": 10.5,
            "minimum_temperature": 2.0,
            "maximum_temperature": 8.0,
            "storage_location": "Recepción de microbiología",
            "risk_score": 91.0,
            "risk_level": "CRITICAL",
            "anomaly_detected": True,
            "risk_explanation": (
                "Tiempo de transporte prolongado y temperatura "
                "fuera del rango configurado para esta demostración."
            ),
        },
    ]

    return [
        ensure_sample(db, **sample_data)
        for sample_data in samples_data
    ]


# ============================================================
# INITIAL TRACEABILITY EVENTS
# ============================================================

def seed_sample_events(
    db: Session,
    samples: list[Sample],
    equipment: list[Equipment],
    users: list[User],
) -> list[SampleEvent]:
    """Registra eventos de trazabilidad para las muestras de ejemplo."""

    if not samples:
        return []

    now = utc_now()
    technician = next(
        (
            user
            for user in users
            if user.username == "tecnico_demo"
        ),
        None,
    )
    technician_name = technician.full_name if technician else "Técnico de demostración"

    equipment_by_code = {
        item.code: item
        for item in equipment
    }

    events = []

    event_definitions = [
        {
            "sample_code": "LG-2026-0001",
            "event_type": "RECEIVED",
            "title": "Muestra recibida",
            "description": "Registro de recepción en el laboratorio.",
            "occurred_at": now - timedelta(minutes=40),
            "temperature": 4.5,
            "location": "Recepción de hematología",
            "equipment_code": "REF-001",
        },
        {
            "sample_code": "LG-2026-0002",
            "event_type": "PROCESSING_STARTED",
            "title": "Procesamiento iniciado",
            "description": "La muestra entró en procesamiento.",
            "occurred_at": now - timedelta(minutes=25),
            "temperature": 5.2,
            "location": "Área de bioquímica",
            "equipment_code": "ANA-001",
        },
        {
            "sample_code": "LG-2026-0003",
            "event_type": "ANOMALY_DETECTED",
            "title": "Temperatura fuera de rango",
            "description": (
                "Se detectó una temperatura superior al máximo "
                "configurado en el almacenamiento."
            ),
            "occurred_at": now - timedelta(minutes=10),
            "status": "COMPLETED",
            "severity": "HIGH",
            "temperature": 9.4,
            "location": "Sala fría B",
            "equipment_code": "REF-002",
        },
        {
            "sample_code": "LG-2026-0004",
            "event_type": "RESULT_RELEASED",
            "title": "Resultado liberado",
            "description": "Finalización del flujo de demostración.",
            "occurred_at": now - timedelta(hours=2),
            "temperature": 5.0,
            "location": "Área de uroanálisis",
            "equipment_code": "ANA-001",
        },
        {
            "sample_code": "LG-2026-0005",
            "event_type": "ANOMALY_DETECTED",
            "title": "Riesgo de degradación de muestra",
            "description": (
                "El transporte prolongado y la temperatura registrada "
                "requieren revisión por personal autorizado."
            ),
            "occurred_at": now - timedelta(minutes=5),
            "status": "COMPLETED",
            "severity": "CRITICAL",
            "temperature": 10.5,
            "location": "Recepción de microbiología",
            "equipment_code": None,
        },
    ]

    samples_by_code = {
        sample.code: sample
        for sample in samples
    }

    for definition in event_definitions:
        sample = samples_by_code.get(definition["sample_code"])

        if sample is None:
            continue

        equipment_item = equipment_by_code.get(
            definition.get("equipment_code")
        )

        event = ensure_event(
            db,
            sample_id=sample.id,
            event_type=definition["event_type"],
            title=definition["title"],
            description=definition["description"],
            occurred_at=definition["occurred_at"],
            status=definition.get("status", "COMPLETED"),
            severity=definition.get("severity", "INFO"),
            temperature=definition.get("temperature"),
            location=definition.get("location"),
            performed_by=technician_name,
            equipment_id=(
                equipment_item.id
                if equipment_item is not None
                else None
            ),
        )

        events.append(event)

    return events


# ============================================================
# INITIAL ALERTS
# ============================================================

def seed_alerts(db: Session, samples: list[Sample]) -> list[Alert]:
    """Genera alertas ficticias para los escenarios de riesgo."""

    samples_by_code = {
        sample.code: sample
        for sample in samples
    }

    alerts = []

    high_risk_sample = samples_by_code.get("LG-2026-0003")

    if high_risk_sample is not None:
        alerts.append(
            ensure_alert(
                db,
                sample=high_risk_sample,
                alert_type="TEMPERATURE",
                severity="HIGH",
                title="Temperatura de almacenamiento fuera de rango",
                message=(
                    "La muestra presenta una temperatura superior "
                    "al máximo configurado. Requiere revisión."
                ),
                risk_score=high_risk_sample.risk_score,
            )
        )

    critical_sample = samples_by_code.get("LG-2026-0005")

    if critical_sample is not None:
        alerts.append(
            ensure_alert(
                db,
                sample=critical_sample,
                alert_type="SAMPLE_DEGRADATION",
                severity="CRITICAL",
                title="Riesgo crítico de degradación",
                message=(
                    "Revisar el tiempo de transporte y la temperatura "
                    "registrada antes de continuar con el procesamiento."
                ),
                risk_score=critical_sample.risk_score,
                source="ANOMALY_DETECTION",
            )
        )

    alerts.append(
        ensure_alert(
            db,
            sample=None,
            alert_type="EQUIPMENT_ANOMALY",
            severity="HIGH",
            title="Anomalía en refrigerador REF-002",
            message=(
                "El refrigerador de demostración presenta una "
                "temperatura superior al límite configurado."
            ),
            risk_score=None,
        )
    )

    return alerts


# ============================================================
# MAIN SEED FUNCTION
# ============================================================

def seed_initial_data(db: Session) -> dict[str, int]:
    """
    Carga todos los datos iniciales de forma idempotente.

    No elimina registros existentes. Los registros de ejemplo
    identificados por sus códigos o claves naturales se reutilizan.

    El llamador es responsable de confirmar o revertir la transacción.
    """

    try:
        users = seed_users(db)
        equipment = seed_equipment(db)
        samples = seed_samples(db)

        events = seed_sample_events(
            db,
            samples=samples,
            equipment=equipment,
            users=users,
        )

        alerts = seed_alerts(db, samples)

        db.flush()

        return {
            "users": len(users),
            "equipment": len(equipment),
            "samples": len(samples),
            "events": len(events),
            "alerts": len(alerts),
        }

    except Exception:
        db.rollback()
        raise
