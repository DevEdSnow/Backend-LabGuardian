```python
"""
Risk routes for LabGuardian AI.

This module provides endpoints for calculating,
consulting and analyzing the risk associated with
clinical samples.

The current implementation uses a rule-based
risk calculation. Later it will be connected
to the Machine Learning risk engine.
"""

from typing import Any

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/api/risk",
    tags=["Risk"],
)


# ─────────────────────────────────────────────
# Temporary mock risk data
# ─────────────────────────────────────────────

risk_data: dict[str, dict[str, Any]] = {
    "A49281": {
        "sample_code": "A49281",
        "score": 78,
        "level": "HIGH",
        "status": "AT_RISK",
        "factors": [
            {
                "name": "Temperatura",
                "value": 8.7,
                "unit": "°C",
                "impact": 35,
                "severity": "HIGH",
            },
            {
                "name": "Tiempo de procesamiento",
                "value": 75,
                "unit": "min",
                "impact": 18,
                "severity": "MEDIUM",
            },
            {
                "name": "Tiempo de transporte",
                "value": 32,
                "unit": "min",
                "impact": 12,
                "severity": "MEDIUM",
            },
        ],
        "recommendation": (
            "Revisar las condiciones de almacenamiento "
            "y validar la integridad de la muestra."
        ),
    },
    "A49292": {
        "sample_code": "A49292",
        "score": 54,
        "level": "MEDIUM",
        "status": "MONITOR",
        "factors": [
            {
                "name": "Temperatura",
                "value": 7.4,
                "unit": "°C",
                "impact": 15,
                "severity": "MEDIUM",
            },
            {
                "name": "Tiempo de transporte",
                "value": 42,
                "unit": "min",
                "impact": 20,
                "severity": "MEDIUM",
            },
        ],
        "recommendation": (
            "Mantener monitoreo de la muestra "
            "y reducir el tiempo antes del procesamiento."
        ),
    },
    "A49301": {
        "sample_code": "A49301",
        "score": 47,
        "level": "MEDIUM",
        "status": "MONITOR",
        "factors": [
            {
                "name": "Tiempo de procesamiento",
                "value": 52,
                "unit": "min",
                "impact": 17,
                "severity": "MEDIUM",
            },
            {
                "name": "Temperatura",
                "value": 6.8,
                "unit": "°C",
                "impact": 10,
                "severity": "LOW",
            },
        ],
        "recommendation": (
            "Continuar monitoreando la muestra "
            "durante el procesamiento."
        ),
    },
}


# ─────────────────────────────────────────────
# Risk calculation helpers
# ─────────────────────────────────────────────

def calculate_temperature_risk(
    temperature: float,
    minimum: float = 2.0,
    maximum: float = 8.0,
) -> int:
    """
    Calculates the risk contribution caused by temperature.

    Returns a value between 0 and 40.
    """

    if minimum <= temperature <= maximum:
        return 0

    difference = min(
        abs(temperature - minimum),
        abs(temperature - maximum),
    )

    risk = int(difference * 10)

    return min(risk, 40)


def calculate_processing_risk(
    processing_minutes: float,
    recommended_minutes: float = 60.0,
) -> int:
    """
    Calculates the risk contribution caused by
    excessive processing time.

    Returns a value between 0 and 30.
    """

    if processing_minutes <= recommended_minutes:
        return 0

    excess = processing_minutes - recommended_minutes

    risk = int(excess * 0.8)

    return min(risk, 30)


def calculate_transport_risk(
    transport_minutes: float,
    recommended_minutes: float = 30.0,
) -> int:
    """
    Calculates the risk contribution caused by
    excessive transport time.

    Returns a value between 0 and 20.
    """

    if transport_minutes <= recommended_minutes:
        return 0

    excess = transport_minutes - recommended_minutes

    risk = int(excess * 0.5)

    return min(risk, 20)


def get_risk_level(score: int) -> str:
    """
    Converts a numerical risk score into a risk level.
    """

    if score >= 70:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"


def get_risk_status(level: str) -> str:
    """
    Returns the recommended status associated
    with the risk level.
    """

    if level == "HIGH":
        return "AT_RISK"

    if level == "MEDIUM":
        return "MONITOR"

    return "NORMAL"


# ─────────────────────────────────────────────
# GET /api/risk
# ─────────────────────────────────────────────

@router.get("/")
async def get_all_risks() -> dict[str, Any]:
    """
    Returns the risk information for all monitored samples.
    """

    return {
        "success": True,
        "total": len(risk_data),
        "risks": list(risk_data.values()),
    }


# ─────────────────────────────────────────────
# POST /api/risk/calculate
# ─────────────────────────────────────────────

@router.post("/calculate")
async def calculate_risk(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculates the risk of a clinical sample.

    Example request:

    {
        "sample_code": "A49281",
        "temperature": 8.7,
        "processing_minutes": 75,
        "transport_minutes": 32
    }
    """

    sample_code = data.get("sample_code")

    if not sample_code:
        raise HTTPException(
            status_code=400,
            detail="sample_code is required.",
        )

    temperature = float(
        data.get("temperature", 5.0)
    )

    processing_minutes = float(
        data.get("processing_minutes", 0)
    )

    transport_minutes = float(
        data.get("transport_minutes", 0)
    )

    temperature_risk = calculate_temperature_risk(
        temperature
    )

    processing_risk = calculate_processing_risk(
        processing_minutes
    )

    transport_risk = calculate_transport_risk(
        transport_minutes
    )

    score = min(
        temperature_risk
        + processing_risk
        + transport_risk,
        100,
    )

    level = get_risk_level(score)
    status = get_risk_status(level)

    factors = []

    if temperature_risk > 0:
        factors.append(
            {
                "name": "Temperatura",
                "value": temperature,
                "unit": "°C",
                "impact": temperature_risk,
                "severity": (
                    "HIGH"
                    if temperature_risk >= 25
                    else "MEDIUM"
                ),
            }
        )

    if processing_risk > 0:
        factors.append(
            {
                "name": "Tiempo de procesamiento",
                "value": processing_minutes,
                "unit": "min",
                "impact": processing_risk,
                "severity": "MEDIUM",
            }
        )

    if transport_risk > 0:
        factors.append(
            {
                "name": "Tiempo de transporte",
                "value": transport_minutes,
                "unit": "min",
                "impact": transport_risk,
                "severity": "MEDIUM",
            }
        )

    if level == "HIGH":
        recommendation = (
            "Revisar inmediatamente las condiciones "
            "de la muestra antes de continuar."
        )
    elif level == "MEDIUM":
        recommendation = (
            "Mantener monitoreo de la muestra y "
            "reducir los factores de riesgo."
        )
    else:
        recommendation = (
            "Las condiciones actuales de la muestra "
            "se encuentran dentro de los parámetros esperados."
        )

    result = {
        "sample_code": sample_code,
        "score": score,
        "level": level,
        "status": status,
        "factors": factors,
        "recommendation": recommendation,
    }

    # Temporary in-memory storage.
    # This will later be handled by risk_service.py
    # and PostgreSQL.
    risk_data[sample_code] = result

    return {
        "success": True,
        "risk": result,
    }


# ─────────────────────────────────────────────
# GET /api/risk/sample/{sample_code}
# ─────────────────────────────────────────────

@router.get("/sample/{sample_code}")
async def get_sample_risk(
    sample_code: str,
) -> dict[str, Any]:
    """
    Returns the current risk analysis of a sample.
    """

    risk = risk_data.get(sample_code)

    if risk is None:
        raise HTTPException(
            status_code=404,
            detail="Risk information not found for this sample.",
        )

    return {
        "success": True,
        "risk": risk,
    }


# ─────────────────────────────────────────────
# GET /api/risk/sample/{sample_code}/factors
# ─────────────────────────────────────────────

@router.get("/sample/{sample_code}/factors")
async def get_risk_factors(
    sample_code: str,
) -> dict[str, Any]:
    """
    Returns only the factors contributing to
    the risk of a sample.
    """

    risk = risk_data.get(sample_code)

    if risk is None:
        raise HTTPException(
            status_code=404,
            detail="Risk information not found for this sample.",
        )

    return {
        "success": True,
        "sample_code": sample_code,
        "score": risk["score"],
        "level": risk["level"],
        "factors": risk["factors"],
    }


# ─────────────────────────────────────────────
# GET /api/risk/high
# ─────────────────────────────────────────────

@router.get("/high")
async def get_high_risk_samples() -> dict[str, Any]:
    """
    Returns all samples currently classified
    as high risk.
    """

    high_risk = [
        risk
        for risk in risk_data.values()
        if risk["level"] == "HIGH"
    ]

    return {
        "success": True,
        "total": len(high_risk),
        "samples": high_risk,
    }


# ─────────────────────────────────────────────
# GET /api/risk/summary
# ─────────────────────────────────────────────

@router.get("/summary")
async def get_risk_summary() -> dict[str, Any]:
    """
    Returns an overview of the current laboratory risk.
    """

    risks = list(risk_data.values())

    low = sum(
        1
        for risk in risks
        if risk["level"] == "LOW"
    )

    medium = sum(
        1
        for risk in risks
        if risk["level"] == "MEDIUM"
    )

    high = sum(
        1
        for risk in risks
        if risk["level"] == "HIGH"
    )

    average_score = (
        sum(risk["score"] for risk in risks) / len(risks)
        if risks
        else 0
    )

    return {
        "success": True,
        "summary": {
            "total_samples": len(risks),
            "low_risk": low,
            "medium_risk": medium,
            "high_risk": high,
            "average_score": round(
                average_score,
                2,
            ),
        },
    }
```

Con esto ya tienes endpoints como:

```text
GET  /api/risk/
POST /api/risk/calculate
GET  /api/risk/sample/A49281
GET  /api/risk/sample/A49281/factors
GET  /api/risk/high
GET  /api/risk/summary
```

Y lo importante para la competencia es que **el riesgo no sea solamente un número**: el endpoint devuelve los factores que provocaron el riesgo, por ejemplo temperatura, transporte y tiempo de procesamiento. Más adelante esos factores alimentarán el modelo de ML real.
