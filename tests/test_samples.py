
"""
Pruebas automatizadas del servicio de gestión de muestras.

Módulo:
    tests/test_samples.py

Objetivos:
    - Comprobar la creación de muestras.
    - Validar la búsqueda por ID y código.
    - Probar el listado y filtrado de muestras.
    - Verificar la actualización de información.
    - Comprobar los cambios de estado.
    - Probar el rechazo y descarte de muestras.
    - Validar la generación de eventos de trazabilidad.
    - Comprobar las estadísticas de muestras.

Las pruebas utilizan una base de datos simulada mediante unittest.mock.
No se necesita una conexión real con PostgreSQL.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.sample_service import (
    SampleAlreadyExistsError,
    SampleNotFoundError,
    SampleStateError,
    SampleValidationError,
    create_sample,
    discard_sample,
    get_sample_by_code,
    get_sample_by_id,
    get_sample_events,
    get_sample_statistics,
    list_samples,
    reject_sample,
    update_sample,
    update_sample_status,
)

from app.schemas.sample import (
    SampleCreate,
    SampleStatus,
    SampleStatusUpdate,
    SampleUpdate,
)


# ============================================================
# UTILIDADES DE PRUEBA
# ============================================================

def create_mock_sample(
    sample_id=1,
    code="LG-TEST-0001",
    sample_type="BLOOD",
    laboratory_area="HEMATOLOGY",
    status="RECEIVED",
    priority="NORMAL",
    risk_score=0.0,
    risk_level="LOW",
    anomaly_detected=False,
):
    """Crea una muestra simulada para las pruebas."""

    return SimpleNamespace(
        id=sample_id,
        code=code,
        sample_type=sample_type,
        laboratory_area=laboratory_area,
        status=status,
        priority=priority,
        risk_score=risk_score,
        risk_level=risk_level,
        anomaly_detected=anomaly_detected,
        collected_at=None,
        received_at=datetime.now(timezone.utc),
        processing_started_at=None,
        processed_at=None,
        result_at=None,
        transport_minutes=0,
        processing_minutes=0,
        storage_minutes=0,
        current_temperature=5.0,
        minimum_temperature=2.0,
        maximum_temperature=8.0,
        storage_location="REF-001",
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def configure_sample_query(db, sample):
    """Configura una consulta simulada para devolver una muestra."""

    db.query.return_value.filter.return_value.first.return_value = sample


def valid_sample_data(**overrides):
    """Genera los datos mínimos de creación de una muestra."""

    data = {
        "code": "LG-TEST-0001",
        "sample_type": "BLOOD",
        "laboratory_area": "HEMATOLOGY",
        "priority": "NORMAL",
        "current_temperature": 5.0,
        "minimum_temperature": 2.0,
        "maximum_temperature": 8.0,
        "storage_location": "REF-001",
        "notes": "Muestra de prueba.",
    }
    data.update(overrides)
    return data


# ============================================================
# PRUEBAS DE CREACIÓN
# ============================================================

@patch("app.services.sample_service._record_event")
def test_create_sample_success(mock_record_event):
    """Debe crear una muestra cuando los datos son válidos."""

    db = MagicMock()

    # Primera consulta: comprobar que el código no exista.
    # La siguiente consulta no es necesaria para este escenario.
    db.query.return_value.filter.return_value.first.return_value = None

    data = SampleCreate(**valid_sample_data())

    result = create_sample(
        db,
        data,
        performed_by="tecnico_demo",
    )

    assert result is not None
    db.add.assert_called()
    db.flush.assert_called()


@patch("app.services.sample_service._record_event")
def test_create_sample_rejects_duplicate_code(mock_record_event):
    """No debe permitir dos muestras con el mismo código."""

    db = MagicMock()
    existing_sample = create_mock_sample(code="LG-TEST-0001")

    configure_sample_query(db, existing_sample)

    data = SampleCreate(**valid_sample_data())

    with pytest.raises(SampleAlreadyExistsError):
        create_sample(
            db,
            data,
            performed_by="tecnico_demo",
        )


# ============================================================
# PRUEBAS DE CONSULTA
# ============================================================

def test_get_sample_by_id_returns_sample():
    """Debe devolver una muestra existente a partir de su ID."""

    db = MagicMock()
    sample = create_mock_sample(sample_id=15)

    configure_sample_query(db, sample)

    result = get_sample_by_id(db, 15)

    assert result is sample
    assert result.id == 15


def test_get_sample_by_id_raises_when_missing():
    """Debe generar SampleNotFoundError cuando el ID no existe."""

    db = MagicMock()
    configure_sample_query(db, None)

    with pytest.raises(SampleNotFoundError):
        get_sample_by_id(db, 999999)


def test_get_sample_by_code_returns_sample():
    """Debe encontrar una muestra por su código único."""

    db = MagicMock()
    sample = create_mock_sample(code="LG-TEST-0042")

    configure_sample_query(db, sample)

    result = get_sample_by_code(db, "LG-TEST-0042")

    assert result is sample
    assert result.code == "LG-TEST-0042"


def test_get_sample_by_code_raises_when_missing():
    """Debe generar SampleNotFoundError si el código no existe."""

    db = MagicMock()
    configure_sample_query(db, None)

    with pytest.raises(SampleNotFoundError):
        get_sample_by_code(db, "LG-NOT-FOUND")


# ============================================================
# PRUEBAS DE LISTADO
# ============================================================

def test_list_samples_returns_pagination_structure():
    """El listado debe devolver una estructura con resultados y paginación."""

    db = MagicMock()
    samples = [
        create_mock_sample(sample_id=1, code="LG-TEST-0001"),
        create_mock_sample(sample_id=2, code="LG-TEST-0002"),
    ]

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = len(samples)
    query.all.return_value = samples

    result = list_samples(
        db,
        page=1,
        page_size=10,
    )

    assert result is not None


def test_list_samples_supports_search_filter():
    """El servicio debe aceptar un término de búsqueda."""

    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = 0
    query.all.return_value = []

    result = list_samples(
        db,
        search="LG-TEST",
        page=1,
        page_size=10,
    )

    assert result is not None


# ============================================================
# PRUEBAS DE ACTUALIZACIÓN
# ============================================================

def test_update_sample_changes_notes():
    """Debe actualizar los campos permitidos de una muestra."""

    db = MagicMock()
    sample = create_mock_sample()

    configure_sample_query(db, sample)

    update_data = SampleUpdate(
        notes="Muestra revisada durante las pruebas."
    )

    result = update_sample(
        db,
        sample_id=sample.id,
        data=update_data,
        performed_by="tecnico_demo",
    )

    assert result is sample
    assert sample.notes == "Muestra revisada durante las pruebas."
    db.flush.assert_called()


def test_update_sample_raises_when_missing():
    """No debe actualizar una muestra inexistente."""

    db = MagicMock()
    configure_sample_query(db, None)

    update_data = SampleUpdate(
        notes="Actualización de prueba."
    )

    with pytest.raises(SampleNotFoundError):
        update_sample(
            db,
            sample_id=999999,
            data=update_data,
            performed_by="tecnico_demo",
        )


# ============================================================
# PRUEBAS DE CAMBIO DE ESTADO
# ============================================================

@patch("app.services.sample_service._record_event")
def test_update_sample_status_changes_status(mock_record_event):
    """Debe actualizar el estado cuando la transición es válida."""

    db = MagicMock()
    sample = create_mock_sample(status="RECEIVED")

    configure_sample_query(db, sample)

    status_data = SampleStatusUpdate(
        status=SampleStatus.IDENTIFIED
    )

    result = update_sample_status(
        db,
        sample_id=sample.id,
        data=status_data,
        performed_by="tecnico_demo",
    )

    assert result is sample
    assert str(sample.status).upper().endswith("IDENTIFIED")
    db.flush.assert_called()


def test_update_sample_status_raises_when_missing():
    """No debe cambiar el estado de una muestra inexistente."""

    db = MagicMock()
    configure_sample_query(db, None)

    status_data = SampleStatusUpdate(
        status=SampleStatus.IDENTIFIED
    )

    with pytest.raises(SampleNotFoundError):
        update_sample_status(
            db,
            sample_id=999999,
            data=status_data,
            performed_by="tecnico_demo",
        )


def test_completed_sample_cannot_be_moved_back_automatically():
    """Una muestra completada no debe regresar a un estado anterior."""

    db = MagicMock()
    sample = create_mock_sample(status="COMPLETED")

    configure_sample_query(db, sample)

    status_data = SampleStatusUpdate(
        status=SampleStatus.PROCESSING
    )

    with pytest.raises(SampleStateError):
        update_sample_status(
            db,
            sample_id=sample.id,
            data=status_data,
            performed_by="tecnico_demo",
        )


# ============================================================
# PRUEBAS DE RECHAZO
# ============================================================

@patch("app.services.sample_service._record_event")
def test_reject_sample_changes_status(mock_record_event):
    """Debe marcar la muestra como rechazada."""

    db = MagicMock()
    sample = create_mock_sample(status="RECEIVED")

    configure_sample_query(db, sample)

    result = reject_sample(
        db,
        sample_id=sample.id,
        reason="Identificación de prueba incorrecta.",
        performed_by="supervisor_demo",
    )

    assert result is sample
    assert str(sample.status).upper().endswith("REJECTED")
    db.flush.assert_called()


def test_reject_sample_raises_when_missing():
    """Debe rechazar la operación si la muestra no existe."""

    db = MagicMock()
    configure_sample_query(db, None)

    with pytest.raises(SampleNotFoundError):
        reject_sample(
            db,
            sample_id=999999,
            reason="Motivo de prueba.",
            performed_by="supervisor_demo",
        )


# ============================================================
# PRUEBAS DE DESCARTE
# ============================================================

@patch("app.services.sample_service._record_event")
def test_discard_sample_changes_status(mock_record_event):
    """Debe marcar la muestra como descartada."""

    db = MagicMock()
    sample = create_mock_sample(status="RECEIVED")

    configure_sample_query(db, sample)

    result = discard_sample(
        db,
        sample_id=sample.id,
        reason="Descarte de prueba.",
        performed_by="supervisor_demo",
    )

    assert result is sample
    assert str(sample.status).upper().endswith("DISCARDED")
    db.flush.assert_called()


def test_discard_sample_raises_when_missing():
    """Debe generar una excepción cuando la muestra no existe."""

    db = MagicMock()
    configure_sample_query(db, None)

    with pytest.raises(SampleNotFoundError):
        discard_sample(
            db,
            sample_id=999999,
            reason="Motivo de prueba.",
            performed_by="supervisor_demo",
        )


# ============================================================
# PRUEBAS DE EVENTOS DE TRAZABILIDAD
# ============================================================

def test_get_sample_events_returns_events():
    """Debe devolver los eventos asociados a una muestra."""

    db = MagicMock()
    sample = create_mock_sample(sample_id=7)

    event = SimpleNamespace(
        id=1,
        sample_id=7,
        event_type="RECEIVED",
        title="Recepción de muestra",
    )

    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        event
    ]

    result = get_sample_events(
        db,
        sample_id=sample.id,
    )

    assert result is not None
    assert len(result) == 1


# ============================================================
# PRUEBAS DE ESTADÍSTICAS
# ============================================================

def test_get_sample_statistics_returns_result():
    """El servicio de estadísticas debe producir un resultado."""

    db = MagicMock()

    result = get_sample_statistics(db)

    assert result is not None


# ============================================================
# PRUEBAS DE VALIDACIÓN DEL ESQUEMA
# ============================================================

def test_sample_create_requires_code():
    """La creación debe exigir un código de muestra."""

    data = valid_sample_data()
    data.pop("code")

    with pytest.raises(Exception):
        SampleCreate(**data)


def test_sample_create_rejects_invalid_temperature_range():
    """El esquema debe rechazar un rango de temperatura invertido."""

    data = valid_sample_data(
        minimum_temperature=10.0,
        maximum_temperature=2.0,
    )

    with pytest.raises(Exception):
        SampleCreate(**data)


def test_sample_update_does_not_accept_protected_risk_fields():
    """El esquema de actualización no debe aceptar campos protegidos."""

    with pytest.raises(Exception):
        SampleUpdate(
            risk_score=95.0
        )


# ============================================================
# PRUEBAS DE ESTRUCTURA
# ============================================================

def test_sample_service_exports_expected_functions():
    """Las funciones principales del servicio deben estar disponibles."""

    from app.services import sample_service

    assert callable(sample_service.create_sample)
    assert callable(sample_service.get_sample_by_id)
    assert callable(sample_service.get_sample_by_code)
    assert callable(sample_service.list_samples)
    assert callable(sample_service.update_sample)
    assert callable(sample_service.update_sample_status)
    assert callable(sample_service.reject_sample)
    assert callable(sample_service.discard_sample)
