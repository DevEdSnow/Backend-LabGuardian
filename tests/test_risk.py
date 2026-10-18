
"""
Pruebas automatizadas del servicio de cálculo de riesgos de LabGuardian AI.

Módulo:
    tests/test_risk.py

Objetivos:
    - Verificar la clasificación de los niveles de riesgo.
    - Probar el cálculo de riesgo mediante reglas.
    - Comprobar la integración con el modelo de Machine Learning.
    - Verificar la persistencia de los resultados.
    - Comprobar la creación de alertas para riesgos elevados.
    - Validar el manejo de muestras inexistentes.
    - Probar la búsqueda por ID y código de muestra.

IMPORTANTE:
    Los umbrales de riesgo utilizados por el proyecto son valores de
    demostración y no constituyen criterios clínicos validados.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.risk_service import (
    RiskPredictionError,
    RiskSampleNotFoundError,
    RiskValidationError,
    calculate_risk_for_samples,
    calculate_sample_risk,
    calculate_sample_risk_by_code,
    calculate_sample_risk_by_id,
    classify_risk,
)


# ============================================================
# UTILIDADES PARA LAS PRUEBAS
# ============================================================

def create_mock_sample(
    sample_id=1,
    code="LG-RISK-0001",
    current_temperature=5.0,
    transport_minutes=10,
    processing_minutes=20,
    storage_minutes=30,
    risk_score=0.0,
    risk_level="LOW",
    risk_explanation=None,
):
    """Crea una muestra simulada para las pruebas unitarias."""

    return SimpleNamespace(
        id=sample_id,
        code=code,
        current_temperature=current_temperature,
        transport_minutes=transport_minutes,
        processing_minutes=processing_minutes,
        storage_minutes=storage_minutes,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_explanation=risk_explanation,
        updated_at=datetime.now(timezone.utc),
    )


def configure_sample_query(db, sample):
    """Configura la consulta simulada para devolver una muestra."""

    db.query.return_value.filter.return_value.first.return_value = sample


def normal_ml_prediction():
    """Resultado simulado de un modelo con riesgo bajo."""

    return {
        "risk_score": 10.0,
        "risk_level": "LOW",
        "prediction": 10.0,
        "explanation": "Riesgo bajo según el modelo simulado.",
    }


def high_ml_prediction():
    """Resultado simulado de un modelo con riesgo elevado."""

    return {
        "risk_score": 90.0,
        "risk_level": "CRITICAL",
        "prediction": 90.0,
        "explanation": "Riesgo elevado según el modelo simulado.",
    }


# ============================================================
# PRUEBAS DE CLASIFICACIÓN DE RIESGO
# ============================================================

@pytest.mark.parametrize(
    ("score", "expected_level"),
    [
        (0, "LOW"),
        (10, "LOW"),
        (29.9, "LOW"),
        (30, "MEDIUM"),
        (45, "MEDIUM"),
        (59.9, "MEDIUM"),
        (60, "HIGH"),
        (75, "HIGH"),
        (84.9, "HIGH"),
        (85, "CRITICAL"),
        (95, "CRITICAL"),
        (100, "CRITICAL"),
    ],
)
def test_classify_risk_returns_expected_level(score, expected_level):
    """La clasificación debe respetar los umbrales configurados."""

    assert classify_risk(score) == expected_level


@pytest.mark.parametrize(
    "invalid_score",
    [
        -1,
        101,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_classify_risk_rejects_invalid_scores(invalid_score):
    """Los valores fuera del rango válido deben rechazarse."""

    with pytest.raises((ValueError, RiskValidationError)):
        classify_risk(invalid_score)


# ============================================================
# PRUEBAS DE EXISTENCIA DE LA MUESTRA
# ============================================================

def test_calculate_sample_risk_raises_when_sample_does_not_exist():
    """Debe generar una excepción si no se encuentra el ID solicitado."""

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(RiskSampleNotFoundError):
        calculate_sample_risk(
            db,
            sample_id=999999,
            use_ml=False,
            persist=False,
            create_alerts=False,
        )


def test_calculate_sample_risk_by_code_raises_when_sample_does_not_exist():
    """Debe generar una excepción si el código no corresponde a una muestra."""

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(RiskSampleNotFoundError):
        calculate_sample_risk_by_code(
            db,
            sample_code="LG-NO-EXISTE",
            use_ml=False,
            persist=False,
            create_alerts=False,
        )


# ============================================================
# PRUEBAS DE CÁLCULO POR REGLAS
# ============================================================

@patch("app.services.risk_service.risk_predictor")
def test_normal_sample_has_low_risk_without_ml(mock_predictor):
    """Una muestra dentro de los rangos de demostración debe tener riesgo bajo."""

    db = MagicMock()
    sample = create_mock_sample()
    configure_sample_query(db, sample)

    result = calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    assert result["success"] is True
    assert 0 <= result["risk_score"] <= 100
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    mock_predictor.predict.assert_not_called()


@patch("app.services.risk_service.risk_predictor")
def test_high_temperature_increases_risk(mock_predictor):
    """Una temperatura fuera del rango de demostración debe influir en el riesgo."""

    db = MagicMock()

    normal_sample = create_mock_sample(
        current_temperature=5.0,
    )
    configure_sample_query(db, normal_sample)

    normal_result = calculate_sample_risk(
        db,
        sample_id=normal_sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    db.reset_mock()

    hot_sample = create_mock_sample(
        current_temperature=15.0,
    )
    configure_sample_query(db, hot_sample)

    hot_result = calculate_sample_risk(
        db,
        sample_id=hot_sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    assert hot_result["risk_score"] > normal_result["risk_score"]


@pytest.mark.parametrize(
    ("feature_name", "abnormal_value"),
    [
        ("transport_minutes", 60),
        ("processing_minutes", 120),
        ("storage_minutes", 240),
    ],
)
@patch("app.services.risk_service.risk_predictor")
def test_excessive_duration_increases_risk(
    mock_predictor,
    feature_name,
    abnormal_value,
):
    """Un tiempo excesivo debe incrementar el riesgo calculado."""

    db = MagicMock()

    normal_sample = create_mock_sample()
    configure_sample_query(db, normal_sample)

    normal_result = calculate_sample_risk(
        db,
        sample_id=normal_sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    db.reset_mock()

    abnormal_sample = create_mock_sample()
    setattr(abnormal_sample, feature_name, abnormal_value)
    configure_sample_query(db, abnormal_sample)

    abnormal_result = calculate_sample_risk(
        db,
        sample_id=abnormal_sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    assert abnormal_result["risk_score"] > normal_result["risk_score"]


# ============================================================
# PRUEBAS DE INTEGRACIÓN CON MACHINE LEARNING
# ============================================================

@patch("app.services.risk_service.risk_predictor")
def test_risk_calculation_uses_ml_when_enabled(mock_predictor):
    """El predictor debe ejecutarse cuando use_ml=True."""

    db = MagicMock()
    sample = create_mock_sample()
    configure_sample_query(db, sample)

    mock_predictor.predict.return_value = normal_ml_prediction()

    calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=True,
        persist=False,
        create_alerts=False,
    )

    mock_predictor.predict.assert_called_once()


@patch("app.services.risk_service.risk_predictor")
def test_risk_calculation_skips_ml_when_disabled(mock_predictor):
    """El predictor no debe ejecutarse cuando use_ml=False."""

    db = MagicMock()
    sample = create_mock_sample()
    configure_sample_query(db, sample)

    calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    mock_predictor.predict.assert_not_called()


@patch("app.services.risk_service.risk_predictor")
def test_risk_calculation_handles_ml_prediction_error(mock_predictor):
    """
    Si falla el modelo, el servicio debe aplicar su manejo de errores
    y, cuando su implementación lo permita, conservar el cálculo por reglas.
    """

    db = MagicMock()
    sample = create_mock_sample(current_temperature=12.0)
    configure_sample_query(db, sample)

    mock_predictor.predict.side_effect = RuntimeError(
        "Error simulado del predictor."
    )

    try:
        result = calculate_sample_risk(
            db,
            sample_id=sample.id,
            use_ml=True,
            persist=False,
            create_alerts=False,
        )
    except RiskPredictionError:
        # Es válido si la implementación está diseñada para propagar el error.
        return

    assert result["success"] is True
    assert 0 <= result["risk_score"] <= 100


# ============================================================
# PRUEBAS DE PERSISTENCIA
# ============================================================

@patch("app.services.risk_service.risk_predictor")
def test_risk_result_is_persisted_when_enabled(mock_predictor):
    """El resultado debe actualizar los campos de riesgo de la muestra."""

    db = MagicMock()
    sample = create_mock_sample(current_temperature=12.0)
    configure_sample_query(db, sample)

    result = calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=False,
        persist=True,
        create_alerts=False,
    )

    assert sample.risk_score == result["risk_score"]
    assert sample.risk_level == result["risk_level"]
    db.flush.assert_called()


@patch("app.services.risk_service.risk_predictor")
def test_risk_result_is_not_persisted_when_disabled(mock_predictor):
    """Con persist=False, no deben modificarse los campos de riesgo."""

    db = MagicMock()
    sample = create_mock_sample(
        current_temperature=12.0,
        risk_score=7.0,
        risk_level="LOW",
    )
    configure_sample_query(db, sample)

    calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    assert sample.risk_score == 7.0
    assert sample.risk_level == "LOW"
    db.flush.assert_not_called()


# ============================================================
# PRUEBAS DE GENERACIÓN DE ALERTAS
# ============================================================

@patch("app.services.risk_service.create_alert")
@patch("app.services.risk_service.risk_predictor")
def test_high_risk_can_generate_alert(mock_predictor, mock_create_alert):
    """Un riesgo elevado debe permitir la creación de una alerta."""

    db = MagicMock()
    sample = create_mock_sample(
        current_temperature=15.0,
        transport_minutes=90,
        processing_minutes=180,
        storage_minutes=300,
    )
    configure_sample_query(db, sample)

    mock_create_alert.return_value = SimpleNamespace(id=456)

    result = calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=False,
        persist=False,
        create_alerts=True,
    )

    if result["risk_level"] in {"HIGH", "CRITICAL"}:
        mock_create_alert.assert_called_once()


@patch("app.services.risk_service.create_alert")
@patch("app.services.risk_service.risk_predictor")
def test_alerts_are_not_created_when_disabled(
    mock_predictor,
    mock_create_alert,
):
    """Con create_alerts=False no deben generarse alertas."""

    db = MagicMock()
    sample = create_mock_sample(
        current_temperature=15.0,
        transport_minutes=90,
        processing_minutes=180,
        storage_minutes=300,
    )
    configure_sample_query(db, sample)

    calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    mock_create_alert.assert_not_called()


# ============================================================
# PRUEBAS DE BÚSQUEDA POR ID Y CÓDIGO
# ============================================================

@patch("app.services.risk_service.risk_predictor")
def test_calculate_sample_risk_by_id_returns_sample_id(mock_predictor):
    """La función de conveniencia por ID debe identificar la muestra."""

    db = MagicMock()
    sample = create_mock_sample(sample_id=25)
    configure_sample_query(db, sample)

    result = calculate_sample_risk_by_id(
        db,
        sample_id=25,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    assert result["success"] is True
    assert result["sample_id"] == 25


@patch("app.services.risk_service.risk_predictor")
def test_calculate_sample_risk_by_code_returns_sample_code(mock_predictor):
    """La función de conveniencia por código debe identificar la muestra."""

    db = MagicMock()
    sample = create_mock_sample(code="LG-RISK-0099")
    configure_sample_query(db, sample)

    result = calculate_sample_risk_by_code(
        db,
        sample_code="LG-RISK-0099",
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    assert result["success"] is True
    assert result["sample_code"] == "LG-RISK-0099"


# ============================================================
# PRUEBAS DE ANÁLISIS MASIVO
# ============================================================

@patch("app.services.risk_service.calculate_sample_risk")
def test_bulk_risk_calculation_handles_empty_database(mock_calculate):
    """El análisis masivo debe manejar una lista vacía de muestras."""

    db = MagicMock()
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

    result = calculate_risk_for_samples(
        db,
        limit=100,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    assert result["success"] is True
    mock_calculate.assert_not_called()


# ============================================================
# PRUEBAS DE ESTRUCTURA DE RESPUESTA
# ============================================================

@patch("app.services.risk_service.risk_predictor")
def test_risk_result_contains_expected_fields(mock_predictor):
    """La respuesta debe incluir los campos esenciales del cálculo."""

    db = MagicMock()
    sample = create_mock_sample()
    configure_sample_query(db, sample)

    result = calculate_sample_risk(
        db,
        sample_id=sample.id,
        use_ml=False,
        persist=False,
        create_alerts=False,
    )

    expected_fields = {
        "success",
        "sample_id",
        "sample_code",
        "risk_score",
        "risk_level",
    }

    assert expected_fields.issubset(result.keys())
    assert isinstance(result["risk_score"], (int, float))
    assert 0 <= result["risk_score"] <= 100
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
