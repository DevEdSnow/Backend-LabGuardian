
"""
Utilidades para la clasificación y presentación de riesgos de LabGuardian AI.

Este módulo proporciona funciones auxiliares para normalizar puntuaciones,
clasificar niveles de riesgo y generar etiquetas consistentes.

IMPORTANTE:
Los niveles y umbrales incluidos son valores de demostración.
Deben validarse con especialistas y protocolos del laboratorio antes
de utilizarlos en un entorno clínico real.
"""

from __future__ import annotations

import math
from typing import Any, Optional


# Umbrales de demostración para puntuaciones de 0 a 100.
RISK_THRESHOLDS: dict[str, float] = {
    "LOW": 30.0,
    "MEDIUM": 60.0,
    "HIGH": 85.0,
    "CRITICAL": 100.0,
}

RISK_LABELS: dict[str, str] = {
    "LOW": "Bajo",
    "MEDIUM": "Medio",
    "HIGH": "Alto",
    "CRITICAL": "Crítico",
}

RISK_DESCRIPTIONS: dict[str, str] = {
    "LOW": "No se identificaron factores importantes de riesgo según las reglas configuradas.",
    "MEDIUM": "Se identificaron factores que requieren revisión.",
    "HIGH": "Se identificaron factores importantes que requieren atención prioritaria.",
    "CRITICAL": "Se identificaron factores de riesgo de máxima prioridad según las reglas configuradas.",
}


class RiskUtilityError(ValueError):
    """Error al procesar una puntuación o nivel de riesgo."""


def normalize_risk_score(score: Any) -> float:
    """
    Valida y normaliza una puntuación de riesgo al rango de 0 a 100.

    No convierte automáticamente valores entre 0 y 1 a porcentajes,
    porque la escala de salida del modelo debe conocerse explícitamente.

    Args:
        score: Puntuación numérica de riesgo.

    Returns:
        float: Puntuación válida entre 0 y 100.

    Raises:
        RiskUtilityError: Si la puntuación no es válida.
    """
    if isinstance(score, bool):
        raise RiskUtilityError("La puntuación de riesgo debe ser numérica.")

    try:
        normalized = float(score)
    except (TypeError, ValueError) as exc:
        raise RiskUtilityError(
            "La puntuación de riesgo debe ser un número."
        ) from exc

    if not math.isfinite(normalized):
        raise RiskUtilityError(
            "La puntuación de riesgo debe ser un número finito."
        )

    if not 0.0 <= normalized <= 100.0:
        raise RiskUtilityError(
            "La puntuación de riesgo debe estar entre 0 y 100."
        )

    return round(normalized, 2)


def classify_risk(score: Any) -> str:
    """
    Clasifica una puntuación numérica de riesgo.

    Clasificación de demostración:
        0 a menos de 30: LOW
        30 a menos de 60: MEDIUM
        60 a menos de 85: HIGH
        85 a 100: CRITICAL

    Args:
        score: Puntuación entre 0 y 100.

    Returns:
        str: LOW, MEDIUM, HIGH o CRITICAL.
    """
    value = normalize_risk_score(score)

    if value >= RISK_THRESHOLDS["HIGH"]:
        return "CRITICAL"

    if value >= RISK_THRESHOLDS["MEDIUM"]:
        return "HIGH"

    if value >= RISK_THRESHOLDS["LOW"]:
        return "MEDIUM"

    return "LOW"


def get_risk_label(level: str) -> str:
    """
    Devuelve el nombre legible de un nivel de riesgo.

    Args:
        level: Nivel de riesgo, como LOW o CRITICAL.

    Returns:
        str: Etiqueta en español.
    """
    normalized = _normalize_level(level)
    return RISK_LABELS[normalized]


def get_risk_description(level: str) -> str:
    """
    Devuelve una descripción del nivel de riesgo.

    Args:
        level: Nivel de riesgo.

    Returns:
        str: Descripción en español.
    """
    normalized = _normalize_level(level)
    return RISK_DESCRIPTIONS[normalized]


def get_risk_color(level: str) -> str:
    """
    Devuelve un color hexadecimal sugerido para representar el riesgo
    en dashboards y reportes.

    Args:
        level: Nivel de riesgo.

    Returns:
        str: Color hexadecimal.
    """
    colors = {
        "LOW": "#16A34A",
        "MEDIUM": "#D97706",
        "HIGH": "#EA580C",
        "CRITICAL": "#DC2626",
    }

    normalized = _normalize_level(level)
    return colors[normalized]


def get_risk_priority(level: str) -> int:
    """
    Convierte el nivel de riesgo en una prioridad numérica.

    Un valor mayor indica mayor prioridad.

    Returns:
        int: Prioridad de 1 a 4.
    """
    priorities = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    normalized = _normalize_level(level)
    return priorities[normalized]


def is_high_risk(level: str) -> bool:
    """
    Indica si un nivel se considera alto o crítico.

    Returns:
        bool: True para HIGH o CRITICAL.
    """
    normalized = _normalize_level(level)
    return normalized in {"HIGH", "CRITICAL"}


def build_risk_summary(
    score: Any,
    level: Optional[str] = None,
) -> dict[str, Any]:
    """
    Construye un resumen estructurado para la API o el dashboard.

    Si se proporciona un nivel, se valida y se conserva. Si no,
    se clasifica la puntuación con los umbrales de demostración.

    Args:
        score: Puntuación entre 0 y 100.
        level: Nivel opcional previamente calculado.

    Returns:
        dict: Puntuación, nivel, etiqueta, descripción, color y prioridad.
    """
    normalized_score = normalize_risk_score(score)
    normalized_level = (
        _normalize_level(level)
        if level is not None
        else classify_risk(normalized_score)
    )

    return {
        "score": normalized_score,
        "level": normalized_level,
        "label": get_risk_label(normalized_level),
        "description": get_risk_description(normalized_level),
        "color": get_risk_color(normalized_level),
        "priority": get_risk_priority(normalized_level),
        "is_high_risk": is_high_risk(normalized_level),
    }


def _normalize_level(level: str) -> str:
    """Valida y normaliza el nombre de un nivel de riesgo."""
    if not isinstance(level, str):
        raise RiskUtilityError("El nivel de riesgo debe ser una cadena.")

    normalized = level.strip().upper()

    if normalized not in RISK_LABELS:
        allowed = ", ".join(RISK_LABELS.keys())
        raise RiskUtilityError(
            f"Nivel de riesgo inválido: {level!r}. Valores permitidos: {allowed}."
        )

    return normalized


__all__ = [
    "RISK_THRESHOLDS",
    "RISK_LABELS",
    "RISK_DESCRIPTIONS",
    "RiskUtilityError",
    "normalize_risk_score",
    "classify_risk",
    "get_risk_label",
    "get_risk_description",
    "get_risk_color",
    "get_risk_priority",
    "is_high_risk",
    "build_risk_summary",
]
