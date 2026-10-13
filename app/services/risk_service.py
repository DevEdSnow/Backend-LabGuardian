"""
Risk Service - LabGuardian AI
=============================

Servicio de evaluación de riesgo para muestras de laboratorio.

Responsabilidades:
- Calcular un riesgo base mediante reglas configurables.
- Consultar opcionalmente el predictor de Machine Learning.
- Combinar las señales disponibles en una puntuación de 0 a 100.
- Clasificar el riesgo como LOW, MEDIUM, HIGH o CRITICAL.
- Guardar la evaluación en el modelo Sample.
- Generar alertas para riesgos elevados.
- Analizar una muestra por ID o código.
- Evaluar múltiples muestras.

IMPORTANTE:
Los umbrales de este archivo son demostrativos. No constituyen
criterios clínicos validados ni deben utilizarse para decidir
la aceptación, el rechazo o el diagnóstico de una muestra.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.sample import Sample
from app.ml.predictor import risk_predictor
from app.services.alert_service import create_alert
from app.schemas.alert import (
    AlertSeverity,
    AlertSource,
    AlertType,
)


# ---------------------------------------------------------------------------
# Configuración demostrativa
# ---------------------------------------------------------------------------

MIN_TEMPERATURE = 2.0
MAX_TEMPERATURE = 8.0

MAX_TRANSPORT_MINUTES = 30.0
MAX_PROCESSING_MINUTES = 60.0
MAX_STORAGE_MINUTES = 120.0

# Pesos de las reglas. No son probabilidades clínicas.
TEMPERATURE_WEIGHT = 35.0
TRANSPORT_WEIGHT = 25.0
PROCESSING_WEIGHT = 25.0
STORAGE_WEIGHT = 15.0
COMBINED_RISK_BONUS = 10.0

# Umbrales internos de clasificación de la puntuación.
MEDIUM_RISK_THRESHOLD = 30.0
HIGH_RISK_THRESHOLD = 60.0
CRITICAL_RISK_THRESHOLD = 85.0

# Si el predictor devuelve una puntuación interpretable, esta proporción
# determina su influencia en el resultado final.
ML_WEIGHT = 0.40
RULE_WEIGHT = 0.60


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class RiskServiceError(Exception):
    """Error general del servicio de riesgo."""


class RiskSampleNotFoundError(RiskServiceError):
    """No se encontró la muestra solicitada."""


class RiskValidationError(RiskServiceError):
    """Los datos proporcionados no son válidos."""


class RiskPredictionError(RiskServiceError):
    """No fue posible interpretar la predicción del modelo."""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    """Devuelve la fecha y hora UTC."""

    return datetime.now(timezone.utc)


def _safe_number(value: Any, default: float = 0.0) -> float:
    """Convierte un valor numérico de forma segura."""

    if value is None:
        return default

    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    # Evita valores NaN e infinitos.
    if number != number or number in (float("inf"), float("-inf")):
        return default

    return number


def _sample_features(sample: Sample) -> dict[str, float]:
    """
    Extrae las variables utilizadas por el predictor existente.

    Los valores por defecto son útiles para muestras con campos
    incompletos, pero los datos faltantes no deben interpretarse
    como evidencia de que la muestra es segura.
    """

    return {
        "temperature": _safe_number(
            sample.current_temperature,
            default=5.0,
        ),
        "transport_minutes": max(
            0.0,
            _safe_number(sample.transport_minutes),
        ),
        "processing_minutes": max(
            0.0,
            _safe_number(sample.processing_minutes),
        ),
        "storage_minutes": max(
            0.0,
            _safe_number(sample.storage_minutes),
        ),
    }


def _get_sample(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
) -> Sample:
    """Busca una muestra por ID o código."""

    if (sample_id is None) == (sample_code is None):
        raise RiskValidationError(
            "Proporciona exactamente un identificador: "
            "sample_id o sample_code."
        )

    query = db.query(Sample)

    if sample_id is not None:
        sample = query.filter(Sample.id == sample_id).first()
    else:
        code = str(sample_code).strip()

        if not code:
            raise RiskValidationError(
                "El código de muestra no puede estar vacío."
            )

        sample = query.filter(Sample.code == code).first()

    if sample is None:
        raise RiskSampleNotFoundError(
            "No se encontró la muestra solicitada."
        )

    return sample


# ---------------------------------------------------------------------------
# Evaluación basada en reglas
# ---------------------------------------------------------------------------

def _evaluate_rules(
    features: dict[str, float],
) -> dict[str, Any]:
    """
    Calcula una puntuación demostrativa a partir de las variables.

    Cada factor aporta puntos cuando supera los límites configurados.
    La puntuación final se limita al intervalo 0-100.
    """

    score = 0.0
    findings: list[dict[str, Any]] = []

    temperature = features["temperature"]
    transport = features["transport_minutes"]
    processing = features["processing_minutes"]
    storage = features["storage_minutes"]

    if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
        score += TEMPERATURE_WEIGHT

        findings.append({
            "code": "TEMPERATURE_OUT_OF_RANGE",
            "factor": "temperature",
            "observed_value": temperature,
            "message": (
                f"La temperatura registrada ({temperature:.1f} °C) "
                "está fuera del intervalo demostrativo configurado."
            ),
        })

    if transport > MAX_TRANSPORT_MINUTES:
        score += TRANSPORT_WEIGHT

        findings.append({
            "code": "TRANSPORT_DELAY",
            "factor": "transport_minutes",
            "observed_value": transport,
            "message": (
                f"El tiempo de transporte ({transport:.1f} min) "
                "supera el límite demostrativo configurado."
            ),
        })

    if processing > MAX_PROCESSING_MINUTES:
        score += PROCESSING_WEIGHT

        findings.append({
            "code": "PROCESSING_DELAY",
            "factor": "processing_minutes",
            "observed_value": processing,
            "message": (
                f"El tiempo de procesamiento ({processing:.1f} min) "
                "supera el límite demostrativo configurado."
            ),
        })

    if storage > MAX_STORAGE_MINUTES:
        score += STORAGE_WEIGHT

        findings.append({
            "code": "STORAGE_DELAY",
            "factor": "storage_minutes",
            "observed_value": storage,
            "message": (
                f"El tiempo de almacenamiento ({storage:.1f} min) "
                "supera el límite demostrativo configurado."
            ),
        })

    combined_risk = (
        temperature > MAX_TEMPERATURE
        and processing > MAX_PROCESSING_MINUTES
    )

    if combined_risk:
        score += COMBINED_RISK_BONUS

        findings.append({
            "code": "COMBINED_TEMPERATURE_PROCESSING_RISK",
            "factor": "combined",
            "observed_value": None,
            "message": (
                "Se detectó una combinación de temperatura elevada "
                "y tiempo de procesamiento prolongado."
            ),
        })

    score = min(100.0, max(0.0, score))

    return {
        "score": round(score, 2),
        "findings": findings,
        "combined_risk": combined_risk,
        "rules_triggered": len(findings),
    }


# ---------------------------------------------------------------------------
# Clasificación del riesgo
# ---------------------------------------------------------------------------

def classify_risk(score: float) -> str:
    """Convierte una puntuación de 0-100 en un nivel de riesgo."""

    score = _safe_number(score)

    if not 0.0 <= score <= 100.0:
        raise RiskValidationError(
            "La puntuación de riesgo debe estar entre 0 y 100."
        )

    if score >= CRITICAL_RISK_THRESHOLD:
        return "CRITICAL"

    if score >= HIGH_RISK_THRESHOLD:
        return "HIGH"

    if score >= MEDIUM_RISK_THRESHOLD:
        return "MEDIUM"

    return "LOW"


def _alert_severity_for_risk(risk_level: str) -> AlertSeverity:
    """Mapea el nivel de riesgo al nivel de severidad de una alerta."""

    mapping = {
        "LOW": AlertSeverity.LOW,
        "MEDIUM": AlertSeverity.MEDIUM,
        "HIGH": AlertSeverity.HIGH,
        "CRITICAL": AlertSeverity.CRITICAL,
    }

    return mapping[risk_level]


def _alert_type_for_findings(
    findings: list[dict[str, Any]],
) -> AlertType:
    """Determina el tipo de alerta según el principal factor detectado."""

    codes = {item.get("code") for item in findings}

    if "TEMPERATURE_OUT_OF_RANGE" in codes:
        return AlertType.TEMPERATURE

    if "TRANSPORT_DELAY" in codes:
        return AlertType.TRANSPORT_DELAY

    if "PROCESSING_DELAY" in codes:
        return AlertType.PROCESSING_DELAY

    if "STORAGE_DELAY" in codes:
        return AlertType.STORAGE_ISSUE

    if "ML_ANOMALY" in codes:
        return AlertType.ML_ANOMALY

    if "COMBINED_TEMPERATURE_PROCESSING_RISK" in codes:
        return AlertType.SAMPLE_DEGRADATION

    return AlertType.OTHER


# ---------------------------------------------------------------------------
# Adaptador del predictor de Machine Learning
# ---------------------------------------------------------------------------

def _normalize_ml_score(result: Any) -> dict[str, Any]:
    """
    Intenta extraer una puntuación de riesgo interpretable.

    Formatos admitidos:
        72
        0.72
        {"risk_score": 72}
        {"score": 72}
        {"risk_probability": 0.72}

    Las salidas que no contienen una puntuación interpretable no se
    utilizan para modificar la puntuación basada en reglas.
    """

    if isinstance(result, dict):
        for key in ("risk_score", "risk_probability", "score"):
            if key in result:
                value = _safe_number(result[key], default=-1.0)

                if 0.0 <= value <= 1.0 and key == "risk_probability":
                    value *= 100.0

                elif 0.0 <= value <= 1.0 and key == "score":
                    # No se presupone que score sea una probabilidad.
                    # Se interpreta 0-1 como una escala normalizada.
                    value *= 100.0

                if 0.0 <= value <= 100.0:
                    return {
                        "available": True,
                        "score": round(value, 2),
                        "raw_result": result,
                    }

    elif isinstance(result, (int, float)) and not isinstance(result, bool):
        value = _safe_number(result, default=-1.0)

        if 0.0 <= value <= 1.0:
            value *= 100.0

        if 0.0 <= value <= 100.0:
            return {
                "available": True,
                "score": round(value, 2),
                "raw_result": result,
            }

    return {
        "available": False,
        "score": None,
        "raw_result": None,
        "message": (
            "El predictor no devolvió una puntuación interpretable; "
            "se conservará la evaluación basada en reglas."
        ),
    }


def _run_ml_prediction(
    features: dict[str, float],
) -> dict[str, Any]:
    """
    Ejecuta el predictor existente.

    Si el modelo no está disponible o falla, la evaluación por reglas
    puede continuar sin interrumpir el análisis.
    """

    try:
        raw_result = risk_predictor.predict(features)
        normalized = _normalize_ml_score(raw_result)

        if normalized["available"]:
            return normalized

        return {
            **normalized,
            "error": None,
        }

    except Exception as exc:
        return {
            "available": False,
            "score": None,
            "error": str(exc),
            "message": (
                "No se pudo ejecutar el predictor; "
                "se utilizará la evaluación basada en reglas."
            ),
        }


# ---------------------------------------------------------------------------
# Persistencia y alertas
# ---------------------------------------------------------------------------

def _build_explanation(
    findings: list[dict[str, Any]],
    ml_result: dict[str, Any],
) -> str:
    """Construye una explicación legible y limitada en longitud."""

    messages = [
        item["message"]
        for item in findings
        if item.get("message")
    ]

    if ml_result.get("available"):
        messages.append(
            "El predictor de ML aportó una puntuación adicional."
        )
    elif ml_result.get("error"):
        messages.append(
            "La predicción de ML no estuvo disponible para este análisis."
        )

    if not messages:
        messages.append(
            "No se activaron las reglas de riesgo configuradas."
        )

    explanation = " ".join(messages)
    return explanation[:2000]


def _create_risk_alert(
    db: Session,
    sample: Sample,
    score: float,
    risk_level: str,
    findings: list[dict[str, Any]],
) -> int | None:
    """Crea una alerta si el riesgo calculado es HIGH o CRITICAL."""

    if risk_level not in {"HIGH", "CRITICAL"}:
        return None

    if not findings:
        return None

    messages = "; ".join(
        item["message"]
        for item in findings
        if item.get("message")
    )

    alert = create_alert(
        db,
        alert_type=_alert_type_for_findings(findings),
        severity=_alert_severity_for_risk(risk_level),
        title=f"Riesgo {risk_level.lower()} en muestra {sample.code}",
        message=(
            f"Evaluación de riesgo: {score:.1f}/100. "
            f"Factores detectados: {messages}"
        )[:4000],
        sample_id=sample.id,
        sample_code=sample.code,
        risk_score=score,
        source=AlertSource.SYSTEM,
        deduplicate=True,
    )

    return alert.id


# ---------------------------------------------------------------------------
# Evaluación principal
# ---------------------------------------------------------------------------

def calculate_sample_risk(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
    use_ml: bool = True,
    persist: bool = True,
    create_alerts: bool = True,
) -> dict[str, Any]:
    """
    Evalúa el riesgo de una muestra existente.

    La función no realiza commit. La transacción corresponde a la capa
    que llama al servicio.

    Devuelve puntuación, nivel, factores, variables, información de ML
    y el identificador de la alerta creada o actualizada, si corresponde.
    """

    sample = _get_sample(
        db,
        sample_id=sample_id,
        sample_code=sample_code,
    )

    features = _sample_features(sample)
    rule_result = _evaluate_rules(features)

    ml_result: dict[str, Any] = {
        "available": False,
        "score": None,
        "message": "La predicción de ML no fue solicitada.",
    }

    final_score = rule_result["score"]
    findings = list(rule_result["findings"])

    if use_ml:
        ml_result = _run_ml_prediction(features)

        if ml_result.get("available"):
            final_score = (
                RULE_WEIGHT * rule_result["score"]
                + ML_WEIGHT * ml_result["score"]
            )

            final_score = round(
                min(100.0, max(0.0, final_score)),
                2,
            )

    risk_level = classify_risk(final_score)
    explanation = _build_explanation(findings, ml_result)

    alert_id = None

    if persist:
        sample.risk_score = final_score
        sample.risk_level = risk_level
        sample.risk_explanation = explanation
        sample.updated_at = _utc_now()

        db.add(sample)
        db.flush()

        if create_alerts:
            alert_id = _create_risk_alert(
                db=db,
                sample=sample,
                score=final_score,
                risk_level=risk_level,
                findings=findings,
            )

    return {
        "success": True,
        "sample_id": sample.id,
        "sample_code": sample.code,
        "risk_score": final_score,
        "risk_level": risk_level,
        "explanation": explanation,
        "features": features,
        "rule_analysis": rule_result,
        "machine_learning": {
            key: value
            for key, value in ml_result.items()
            if key != "raw_result"
        },
        "findings": findings,
        "alert_id": alert_id,
        "persisted": persist,
        "analyzed_at": _utc_now(),
    }


def calculate_sample_risk_by_id(
    db: Session,
    sample_id: int,
    **kwargs: Any,
) -> dict[str, Any]:
    """Evalúa una muestra utilizando su ID."""

    return calculate_sample_risk(
        db,
        sample_id=sample_id,
        **kwargs,
    )


def calculate_sample_risk_by_code(
    db: Session,
    sample_code: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Evalúa una muestra utilizando su código único."""

    return calculate_sample_risk(
        db,
        sample_code=sample_code,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Evaluación por lotes
# ---------------------------------------------------------------------------

def calculate_risk_for_samples(
    db: Session,
    *,
    limit: int = 100,
    use_ml: bool = True,
    persist: bool = True,
    create_alerts: bool = True,
) -> dict[str, Any]:
    """
    Evalúa un lote de muestras.

    Cada resultado contiene su propio estado para permitir que un error
    individual no interrumpa todo el lote.
    """

    if not 1 <= limit <= 1000:
        raise RiskValidationError(
            "El límite debe estar entre 1 y 1000 muestras."
        )

    samples = (
        db.query(Sample)
        .order_by(Sample.id.asc())
        .limit(limit)
        .all()
    )

    results: list[dict[str, Any]] = []

    for sample in samples:
        try:
            result = calculate_sample_risk(
                db,
                sample_id=sample.id,
                use_ml=use_ml,
                persist=persist,
                create_alerts=create_alerts,
            )
            results.append(result)

        except RiskServiceError as exc:
            results.append({
                "success": False,
                "sample_id": sample.id,
                "sample_code": sample.code,
                "error": str(exc),
            })

        except Exception as exc:
            results.append({
                "success": False,
                "sample_id": sample.id,
                "sample_code": sample.code,
                "error": (
                    f"Error inesperado durante la evaluación: {exc}"
                ),
            })

    successful = [
        item for item in results if item.get("success")
    ]

    failed = len(results) - len(successful)

    counts = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }

    for item in successful:
        level = item.get("risk_level")

        if level in counts:
            counts[level] += 1

    return {
        "success": failed == 0,
        "total": len(results),
        "successful": len(successful),
        "failed": failed,
        "risk_distribution": counts,
        "results": results,
        "analyzed_at": _utc_now(),
    }
