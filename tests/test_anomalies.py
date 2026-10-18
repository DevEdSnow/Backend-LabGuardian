```python
"""
Pruebas automatizadas del servicio de detección de anomalías.

Módulo:
    tests/test_anomalies.py

Objetivos:
    - Verificar la detección de anomalías en muestras.
    - Comprobar la detección de temperaturas fuera del rango configurado.
    - Detectar retrasos de transporte, procesamiento y almacenamiento.
    - Comprobar anomalías combinadas.
    - Validar el manejo de muestras inexistentes.
    - Verificar que los errores del modelo de ML no impidan
      ejecutar las reglas de detección.

IMPORTANTE:
    Los umbrales utilizados son valores de demostración del proyecto.
    Deben validarse con los protocolos del laboratorio antes de
    utilizarse en un entorno clínico real.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.anomaly_service import (
    AnomalyDetectionError,
    SampleNotFoundError,
    analyze_sample,
    analyze_sample_by_code,
    analyze_samples,
)


# ============================================================
# UTILIDADES PARA LAS PRUEBAS
# ============================================================

def create_mock_sample(
    sample_id=1,
    code="LG-TEST-0001",
    current_temperature=5.0,
    transport_minutes=10,
    processing_minutes=20,
    storage_minutes=30,
    risk_score=0.0,
    risk_level="LOW",
    anomaly_detected=False,
):
    """
    Construye una muestra simulada sin requerir una base de datos real.
    """

    return SimpleNamespace(
        id=sample_id,
        code=code,
        current_temperature=current_temperature,
        transport_minutes=transport_minutes,
        processing_minutes=processing_minutes,
        storage_minutes=storage_minutes,
        risk_score=risk_score,
        risk_level=risk_level,
        anomaly_detected=anomaly_detected,
        updated_at=datetime.now(timezone.utc),
    )


def mock_normal_model_result():
    """Resultado simulado del modelo: no se detecta anomalía."""
    return {
        "anomaly_detected": False,
        "is_anomaly": False,
        "prediction": 1,
        "score": 0.0,
        "message": "No se detectaron anomalías mediante el modelo.",
    }


def mock_anomaly_model_result():
    """Resultado simulado del modelo: se detecta una anomalía."""
    return {
        "anomaly_detected": True,
        "is_anomaly": True,
        "prediction": -1,
        "score": 0.9,
        "message": "El modelo detectó un comportamiento atípico.",
    }


# ============================================================
# PRUEBAS DE CONFIGURACIÓN
# ============================================================

def test_anomaly_service_can_be_imported():
    """El servicio de anomalías debe poder importarse."""
    from app.services import anomaly_service

    assert anomaly_service is not None
    assert callable(anomaly_service.analyze_sample)


# ============================================================
# PRUEBAS DE EXISTENCIA DE LA MUESTRA
# ============================================================

def test_analyze_sample_raises_when_sample_does_not_exist():
    """Debe generar SampleNotFoundError si el ID no existe."""

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(SampleNotFoundError):
        analyze_sample(
            db,
            sample_id=999999,
            create_alerts=False,
            use_ml=False,
        )


def test_analyze_sample_by_code_raises_when_sample_does_not_exist():
    """Debe generar SampleNotFoundError si el código no existe."""

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(SampleNotFoundError):
        analyze_sample_by_code(
            db,
            sample_code="LG-NO-EXISTE",
            create_alerts=False,
            use_ml=False,
        )


# ============================================================
# PRUEBAS DE TEMPERATURA
# ============================================================

def test_temperature_outside_demo_range_is_detected():
    """
    Una temperatura superior al rango de demostración debe generar
    un hallazgo relacionado con la temperatura.
    """

    from app.services.anomaly_service import _rule_based_analysis

    features = {
        "temperature": 12.0,
        "transport_minutes": 10,
        "processing_minutes": 20,
        "storage_minutes": 30,
    }

    findings = _rule_based_analysis(features)

    assert any(
        "TEMPERATURE" in str(finding.get("code", "")).upper()
        or "TEMPERATURE" in str(finding.get("category", "")).upper()
        for finding in findings
    )


def test_temperature_below_demo_range_is_detected():
    """Una temperatura inferior al rango de demostración debe detectarse."""

    from app.services.anomaly_service import _rule_based_analysis

    features = {
        "temperature": -2.0,
        "transport_minutes": 10,
        "processing_minutes": 20,
        "storage_minutes": 30,
    }

    findings = _rule_based_analysis(features)

    assert any(
        "TEMPERATURE" in str(finding.get("code", "")).upper()
        or "TEMPERATURE" in str(finding.get("category", "")).upper()
        for finding in findings
    )


def test_temperature_inside_demo_range_does_not_generate_temperature_finding():
    """Una temperatura de 5 °C no debe generar una alerta térmica."""

    from app.services.anomaly_service import _rule_based_analysis

    features = {
        "temperature": 5.0,
        "transport_minutes": 10,
        "processing_minutes": 20,
        "storage_minutes": 30,
    }

    findings = _rule_based_analysis(features)

    temperature_findings = [
        finding
        for finding in findings
        if (
            "TEMPERATURE" in str(finding.get("code", "")).upper()
            or "TEMPERATURE" in str(finding.get("category", "")).upper()
        )
    ]

    assert temperature_findings == []


# ============================================================
# PRUEBAS DE RETRASOS
# ============================================================

@pytest.mark.parametrize(
    ("feature_name", "value"),
    [
        ("transport_minutes", 45),
        ("processing_minutes", 90),
        ("storage_minutes", 180),
    ],
)
def test_excessive_duration_is_detected(feature_name, value):
    """Los tiempos superiores a los umbrales de demostración se detectan."""

    from app.services.anomaly_service import _rule_based_analysis

    features = {
        "temperature": 5.0,
        "transport_minutes": 10,
        "processing_minutes": 20,
        "storage_minutes": 30,
    }

    features[feature_name] = value

    findings = _rule_based_analysis(features)

    assert findings, (
        f"Se esperaba detectar una anomalía para {feature_name}={value}."
    )


# ============================================================
# PRUEBAS DE ANOMALÍAS COMBINADAS
# ============================================================

def test_combined_high_temperature_and_long_processing_is_detected():
    """
    Una temperatura elevada junto con un procesamiento prolongado
    debe producir un hallazgo combinado cuando se cumplen las reglas.
    """

    from app.services.anomaly_service import _rule_based_analysis
