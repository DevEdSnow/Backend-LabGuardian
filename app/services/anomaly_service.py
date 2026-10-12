
"""
Anomaly service for LabGuardian AI.

Coordina la detección de anomalías en muestras clínicas,
combina reglas operativas con el detector de Machine Learning
y genera alertas cuando corresponde.

Importante:
- No confirma transacciones; el llamador controla el commit.
- Los umbrales son reglas operativas de demostración.
- Los resultados deben revisarse antes de tomar decisiones clínicas.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.ml.anomaly_detector import anomaly_detector
from app.models.sample import Sample
from app.schemas.alert import (
    AlertSeverity,
    AlertSource,
    AlertType,
)
from app.services.alert_service import create_alert


# ============================================================
# CONSTANTS
# ============================================================

MIN_TEMPERATURE = 2.0
MAX_TEMPERATURE = 8.0

MAX_TRANSPORT_MINUTES = 30.0
MAX_PROCESSING_MINUTES = 60.0
MAX_STORAGE_MINUTES = 120.0


# ============================================================
# EXCEPTIONS
# ============================================================

class AnomalyServiceError(Exception):
    """Error base del servicio de anomalías."""


class SampleNotFoundError(AnomalyServiceError):
    """La muestra solicitada no existe."""


class AnomalyDetectionError(AnomalyServiceError):
    """No fue posible completar el análisis de anomalías."""


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> datetime:
    """Devuelve la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


def _sample_features(sample: Sample) -> dict[str, float]:
    """Prepara las variables de entrada del detector."""
    return {
        "temperature": float(
            sample.current_temperature
            if sample.current_temperature is not None
            else 5.0
        ),
        "transport_minutes": float(sample.transport_minutes or 0.0),
        "processing_minutes": float(sample.processing_minutes or 0.0),
        "storage_minutes": float(sample.storage_minutes or 0.0),
    }


def _rule_based_analysis(
    features: dict[str, float],
) -> list[dict[str, str]]:
    """
    Identifica desviaciones mediante reglas operativas.

    Estas reglas sirven como ejemplos de desarrollo. Los límites
    reales dependen del tipo de muestra, método y protocolo validado.
    """
    findings: list[dict[str, str]] = []

    temperature = features["temperature"]
    transport = features["transport_minutes"]
    processing = features["processing_minutes"]
    storage = features["storage_minutes"]

    if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
        findings.append({
            "code": "TEMPERATURE_OUT_OF_RANGE",
            "category": "TEMPERATURE",
            "severity": "HIGH",
            "message": (
                f"Temperatura registrada: {temperature:.1f} °C. "
                f"Está fuera del rango de demostración "
                f"({MIN_TEMPERATURE:.1f}–{MAX_TEMPERATURE:.1f} °C)."
            ),
        })

    if transport > MAX_TRANSPORT_MINUTES:
        findings.append({
            "code": "TRANSPORT_DELAY",
            "category": "TRANSPORT",
            "severity": "MEDIUM",
            "message": (
                f"Tiempo de transporte de {transport:.1f} minutos; "
                f"supera el umbral de demostración de "
                f"{MAX_TRANSPORT_MINUTES:.0f} minutos."
            ),
        })

    if processing > MAX_PROCESSING_MINUTES:
        findings.append({
            "code": "PROCESSING_DELAY",
            "category": "PROCESSING",
            "severity": "MEDIUM",
            "message": (
                f"Tiempo de procesamiento de {processing:.1f} minutos; "
                f"supera el umbral de demostración de "
                f"{MAX_PROCESSING_MINUTES:.0f} minutos."
            ),
        })

    if storage > MAX_STORAGE_MINUTES:
        findings.append({
            "code": "STORAGE_DELAY",
            "category": "STORAGE",
            "severity": "MEDIUM",
            "message": (
                f"Tiempo de almacenamiento de {storage:.1f} minutos; "
                f"supera el umbral de demostración de "
                f"{MAX_STORAGE_MINUTES:.0f} minutos."
            ),
        })

    if (
        temperature > MAX_TEMPERATURE
        and processing > MAX_PROCESSING_MINUTES
    ):
        findings.append({
            "code": "SAMPLE_DEGRADATION_RISK",
            "category": "SAMPLE_DEGRADATION",
            "severity": "CRITICAL",
            "message": (
                "Se combinan una temperatura superior al rango "
                "configurado y un procesamiento prolongado. "
                "Se requiere revisión del personal responsable."
            ),
        })

    return findings


def _normalize_model_result(result: Any) -> dict[str, Any]:
    """
    Normaliza distintos formatos de salida del detector ML.

    Admite diccionarios, booleanos, etiquetas numéricas y objetos
    con atributos comunes. Ajusta esta función si el detector utiliza
    un contrato de salida específico.
    """
    if isinstance(result, dict):
        detected = result.get(
            "anomaly_detected",
            result.get(
                "is_anomaly",
                result.get("anomaly", False),
            ),
        )

        if isinstance(detected, (int, float)) and not isinstance(
            detected, bool
        ):
            detected = detected == -1

        if isinstance(detected, str):
            detected = detected.strip().lower() in {
                "true", "yes", "anomaly", "anomalous", "-1"
            }

        explanations = result.get(
            "explanations",
            result.get(
                "factors",
                result.get("reasons", []),
            ),
        )

        if isinstance(explanations, str):
            explanations = [explanations]
        elif not isinstance(explanations, list):
            explanations = []

        return {
            "anomaly_detected": bool(detected),
            "score": result.get(
                "anomaly_score",
                result.get("score"),
            ),
            "explanations": [str(item) for item in explanations],
            "raw_result": result,
        }

    if isinstance(result, bool):
        return {
            "anomaly_detected": result,
            "score": None,
            "explanations": [],
            "raw_result": result,
        }

    if isinstance(result, (int, float)):
        # Convención habitual de Isolation Forest:
        # -1 = anomalía, 1 = normal.
        return {
            "anomaly_detected": result == -1,
            "score": None,
            "explanations": [],
            "raw_result": result,
        }

    if result is not None:
        detected = getattr(
            result,
            "anomaly_detected",
            getattr(result, "is_anomaly", None),
        )

        if detected is not None:
            explanations = getattr(
                result,
                "explanations",
                getattr(result, "factors", []),
            )

            if isinstance(explanations, str):
                explanations = [explanations]

            return {
                "anomaly_detected": bool(detected),
                "score": getattr(result, "score", None),
                "explanations": [
                    str(item) for item in explanations
                ],
                "raw_result": result,
            }

    raise AnomalyDetectionError(
        "El detector devolvió un formato de resultado no compatible."
    )


def _run_model(
    features: dict[str, float],
) -> dict[str, Any]:
    """Ejecuta el detector ML y normaliza su resultado."""
    try:
        result = anomaly_detector.predict(features)
        return _normalize_model_result(result)
    except AnomalyDetectionError:
        raise
    except Exception as exc:
        raise AnomalyDetectionError(
            "Falló la ejecución del detector de anomalías."
        ) from exc


def _highest_severity(
    findings: list[dict[str, str]],
) -> AlertSeverity:
    """Selecciona la severidad más alta entre los hallazgos."""
    severity_rank = {
        "INFO": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    highest = max(
        findings,
        key=lambda item: severity_rank.get(
            item.get("severity", "INFO"), 0
        ),
        default={"severity": "MEDIUM"},
    )

    return AlertSeverity(highest["severity"])


def _alert_type_for_findings(
    findings: list[dict[str, str]],
) -> AlertType:
    """Determina el tipo principal de alerta."""
    categories = {
        item.get("category")
        for item in findings
    }

    if "SAMPLE_DEGRADATION" in categories:
        return AlertType.SAMPLE_DEGRADATION

    if "TEMPERATURE" in categories:
        return AlertType.TEMPERATURE

    if "TRANSPORT" in categories:
        return AlertType.TRANSPORT_DELAY

    if "PROCESSING" in categories:
        return AlertType.PROCESSING_DELAY

    if "STORAGE" in categories:
        return AlertType.STORAGE_ISSUE

    return AlertType.ML_ANOMALY


# ============================================================
# ANALYZE SAMPLE
# ============================================================

def analyze_sample(
    db: Session,
    sample_id: int,
    *,
    create_alerts: bool = True,
    use_ml: bool = True,
) -> dict[str, Any]:
    """
    Analiza una muestra existente.

    Combina reglas operativas y, opcionalmente, el detector ML.
    Si create_alerts=True, registra una alerta consolidada cuando
    encuentra hallazgos.

    No modifica el risk_score de la muestra: la evaluación de riesgo
    corresponde al predictor de riesgo, no al detector de anomalías.
    """
    if sample_id <= 0:
        raise SampleNotFoundError(
            "El identificador de muestra debe ser mayor que cero."
        )

    sample = db.get(Sample, sample_id)

    if sample is None:
        raise SampleNotFoundError(
            f"No existe una muestra con ID {sample_id}."
        )

    features = _sample_features(sample)
    findings = _rule_based_analysis(features)

    model_result: dict[str, Any] = {
        "anomaly_detected": False,
        "score": None,
        "explanations": [],
        "raw_result": None,
        "executed": False,
        "error": None,
    }

    if use_ml:
        try:
            normalized = _run_model(features)
            model_result.update(normalized)
            model_result["executed"] = True

            if model_result["anomaly_detected"]:
                findings.append({
                    "code": "ML_ANOMALY",
                    "category": "MACHINE_LEARNING",
                    "severity": "HIGH",
                    "message": (
                        "El detector de Machine Learning clasificó "
                        "la muestra como potencial anomalía."
                    ),
                })

                for explanation in model_result["explanations"]:
                    findings.append({
                        "code": "ML_EXPLANATION",
                        "category": "MACHINE_LEARNING",
                        "severity": "MEDIUM",
                        "message": explanation,
                    })

        except AnomalyDetectionError as exc:
            # Las reglas siguen funcionando aunque falle el modelo.
            model_result["error"] = str(exc)

    anomaly_detected = bool(findings)

    # Deduplicación de alertas: el servicio de alertas reutiliza
    # una alerta activa equivalente para evitar duplicados comunes.
    alert = None

    if anomaly_detected and create_alerts:
        primary_type = _alert_type_for_findings(findings)
        severity = _highest_severity(findings)

        messages = [
            item["message"]
            for item in findings
            if item.get("message")
        ]

        alert = create_alert(
            db,
            sample_id=sample.id,
            alert_type=primary_type,
            severity=severity,
            title=f"Anomalía detectada en {sample.code}",
            message=" ".join(messages)[:5000],
            risk_score=(
                float(sample.risk_score)
                if sample.risk_score is not None
                else None
            ),
            source=AlertSource.ANOMALY_DETECTION,
            deduplicate=True,
        )

    return {
        "success": True,
        "sample_id": sample.id,
        "sample_code": sample.code,
        "anomaly_detected": anomaly_detected,
        "findings": findings,
        "features": features,
        "machine_learning": {
            "enabled_for_request": use_ml,
            "executed": model_result["executed"],
            "anomaly_detected": model_result["anomaly_detected"],
            "score": model_result["score"],
            "explanations": model_result["explanations"],
            "error": model_result["error"],
        },
        "alert_id": alert.id if alert is not None else None,
        "analyzed_at": _utc_now(),
    }


# ============================================================
# ANALYZE BY SAMPLE CODE
# ============================================================

def analyze_sample_by_code(
    db: Session,
    sample_code: str,
    *,
    create_alerts: bool = True,
    use_ml: bool = True,
) -> dict[str, Any]:
    """Busca una muestra por código y analiza sus anomalías."""
    normalized_code = sample_code.strip().upper()

    if not normalized_code:
        raise SampleNotFoundError(
            "El código de la muestra es obligatorio."
        )

    sample = db.query(Sample).filter(
        Sample.code == normalized_code
    ).first()

    if sample is None:
        raise SampleNotFoundError(
            f"No existe una muestra con código {normalized_code}."
        )

    return analyze_sample(
        db,
        sample.id,
        create_alerts=create_alerts,
        use_ml=use_ml,
    )


# ============================================================
# BATCH ANALYSIS
# ============================================================

def analyze_samples(
    db: Session,
    *,
    limit: int = 100,
    create_alerts: bool = True,
    use_ml: bool = True,
) -> dict[str, Any]:
    """
    Analiza un lote de muestras.

    Útil para tareas programadas y paneles de supervisión.
    El límite evita analizar accidentalmente toda la base de datos.
    """
    if not 1 <= limit <= 1000:
        raise ValueError("limit debe estar entre 1 y 1000.")

    samples = (
        db.query(Sample)
        .order_by(Sample.id.asc())
        .limit(limit)
        .all()
    )

    results = []
    errors = []

    for sample in samples:
        try:
            result = analyze_sample(
                db,
                sample.id,
                create_alerts=create_alerts,
                use_ml=use_ml,
            )
            results.append(result)
        except AnomalyServiceError as exc:
            errors.append({
                "sample_id": sample.id,
                "sample_code": sample.code,
                "error": str(exc),
            })

    anomalies = sum(
        1 for result in results
        if result["anomaly_detected"]
    )

    return {
        "success": len(errors) == 0,
        "total_analyzed": len(results),
        "anomalies_detected": anomalies,
        "without_anomalies": len(results) - anomalies,
        "errors_count": len(errors),
        "results": results,
        "errors": errors,
        "analyzed_at": _utc_now(),
    }
