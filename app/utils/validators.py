
"""
Validadores compartidos de LabGuardian AI.

Este módulo contiene funciones de validación independientes de la base
de datos y de los endpoints de FastAPI.

Las validaciones de este archivo verifican el formato y la coherencia
básica de los datos; no sustituyen los protocolos clínicos del laboratorio.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


# Límites técnicos y de demostración.
MIN_TEMPERATURE_C = -100.0
MAX_TEMPERATURE_C = 200.0

MAX_DURATION_MINUTES = 10_000_000.0

MIN_RISK_SCORE = 0.0
MAX_RISK_SCORE = 100.0

MAX_CODE_LENGTH = 100
MAX_NAME_LENGTH = 150
MAX_TEXT_LENGTH = 5000

# Ejemplo: LG-2026-0001, SAMPLE-001, LAB_001.
SAMPLE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Validación práctica de formato, no verificación de existencia del correo.
EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


class ValidationError(ValueError):
    """Error base para validaciones de datos."""


def validate_required_string(
    value: Any,
    field_name: str,
    *,
    max_length: int = MAX_TEXT_LENGTH,
    min_length: int = 1,
    strip: bool = True,
) -> str:
    """
    Comprueba que un valor sea una cadena no vacía y dentro de los límites.

    Args:
        value: Valor que se desea validar.
        field_name: Nombre del campo para los mensajes de error.
        max_length: Longitud máxima permitida.
        min_length: Longitud mínima permitida.
        strip: Si es True, elimina espacios al inicio y al final.

    Returns:
        str: Cadena validada.

    Raises:
        ValidationError: Si el valor no cumple las reglas.
    """
    if not isinstance(value, str):
        raise ValidationError(f"El campo '{field_name}' debe ser texto.")

    result = value.strip() if strip else value

    if len(result) < min_length:
        raise ValidationError(
            f"El campo '{field_name}' debe tener al menos "
            f"{min_length} caracteres."
        )

    if len(result) > max_length:
        raise ValidationError(
            f"El campo '{field_name}' no puede superar "
            f"{max_length} caracteres."
        )

    return result


def validate_sample_code(value: Any) -> str:
    """
    Valida el formato de un código de muestra.

    Acepta letras, números, puntos, guiones y guiones bajos.
    No comprueba si el código ya existe en la base de datos.

    Examples:
        LG-2026-0001
        SAMPLE_001
        LAB.001

    Returns:
        str: Código validado.
    """
    code = validate_required_string(
        value,
        "code",
        max_length=MAX_CODE_LENGTH,
    )

    if not SAMPLE_CODE_PATTERN.fullmatch(code):
        raise ValidationError(
            "El código de muestra solo puede contener letras, números, "
            "puntos, guiones y guiones bajos; debe comenzar con una letra "
            "o un número."
        )

    return code


def validate_email(value: Any) -> str:
    """
    Valida el formato básico de una dirección de correo electrónico.

    No comprueba si el buzón existe ni si puede recibir mensajes.
    """
    email = validate_required_string(
        value,
        "email",
        max_length=254,
    )

    if not EMAIL_PATTERN.fullmatch(email):
        raise ValidationError("La dirección de correo no tiene un formato válido.")

    return email.lower()


def validate_temperature(
    value: Any,
    *,
    minimum: float = MIN_TEMPERATURE_C,
    maximum: float = MAX_TEMPERATURE_C,
) -> float:
    """
    Valida una temperatura numérica expresada en grados Celsius.

    Los límites predeterminados son límites técnicos amplios, no límites
    de conservación clínicamente aprobados.
    """
    temperature = _to_finite_float(value, "temperature")

    if minimum > maximum:
        raise ValidationError("El límite mínimo no puede superar al máximo.")

    if not minimum <= temperature <= maximum:
        raise ValidationError(
            f"La temperatura debe estar entre {minimum} y {maximum} °C."
        )

    return temperature


def validate_duration(
    value: Any,
    field_name: str = "duration_minutes",
    *,
    maximum: float = MAX_DURATION_MINUTES,
) -> float:
    """
    Valida una duración expresada en minutos.

    No acepta valores negativos, infinitos ni NaN.
    """
    duration = _to_finite_float(value, field_name)

    if duration < 0:
        raise ValidationError(
            f"El campo '{field_name}' no puede ser negativo."
        )

    if duration > maximum:
        raise ValidationError(
            f"El campo '{field_name}' supera el máximo permitido "
            f"de {maximum} minutos."
        )

    return duration


def validate_risk_score(value: Any) -> float:
    """
    Valida una puntuación de riesgo en la escala de 0 a 100.

    No convierte automáticamente valores de 0 a 1 a porcentajes.
    """
    score = _to_finite_float(value, "risk_score")

    if not MIN_RISK_SCORE <= score <= MAX_RISK_SCORE:
        raise ValidationError(
            f"La puntuación de riesgo debe estar entre "
            f"{MIN_RISK_SCORE} y {MAX_RISK_SCORE}."
        )

    return round(score, 2)


def validate_percentage(value: Any, field_name: str = "percentage") -> float:
    """Valida un porcentaje numérico entre 0 y 100."""
    percentage = _to_finite_float(value, field_name)

    if not 0 <= percentage <= 100:
        raise ValidationError(
            f"El campo '{field_name}' debe estar entre 0 y 100."
        )

    return percentage


def validate_positive_integer(
    value: Any,
    field_name: str,
    *,
    allow_zero: bool = False,
    maximum: Optional[int] = None,
) -> int:
    """
    Valida un entero positivo o, opcionalmente, cero.

    Rechaza booleanos aunque Python los considere un subtipo de int.
    """
    if isinstance(value, bool):
        raise ValidationError(f"El campo '{field_name}' debe ser un entero.")

    if isinstance(value, float) and not value.is_integer():
        raise ValidationError(f"El campo '{field_name}' debe ser un entero.")

    if isinstance(value, str):
        if not re.fullmatch(r"-?\d+", value.strip()):
            raise ValidationError(
                f"El campo '{field_name}' debe ser un entero."
            )

    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError(
            f"El campo '{field_name}' debe ser un entero."
        ) from exc

    lower_bound = 0 if allow_zero else 1

    if number < lower_bound:
        condition = "cero o mayor" if allow_zero else "mayor que cero"
        raise ValidationError(
            f"El campo '{field_name}' debe ser {condition}."
        )

    if maximum is not None and number > maximum:
        raise ValidationError(
            f"El campo '{field_name}' no puede superar {maximum}."
        )

    return number


def validate_datetime(value: Any, field_name: str = "datetime") -> datetime:
    """
    Comprueba que el valor sea un datetime.

    La normalización de zona horaria debe realizarse por separado con
    app.utils.datetime.ensure_utc.
    """
    if not isinstance(value, datetime):
        raise ValidationError(
            f"El campo '{field_name}' debe ser una fecha y hora válida."
        )

    return value


def validate_datetime_order(
    start: datetime,
    end: datetime,
    *,
    start_name: str = "start",
    end_name: str = "end",
) -> tuple[datetime, datetime]:
    """
    Valida que dos fechas estén ordenadas cronológicamente.

    Las fechas deben tener ambas zona horaria o ambas carecer de ella.
    Para evitar ambigüedades, se recomienda usar fechas UTC con zona horaria.
    """
    validate_datetime(start, start_name)
    validate_datetime(end, end_name)

    start_aware = start.utcoffset() is not None
    end_aware = end.utcoffset() is not None

    if start_aware != end_aware:
        raise ValidationError(
            f"Los campos '{start_name}' y '{end_name}' deben usar "
            "el mismo criterio de zona horaria."
        )

    if start > end:
        raise ValidationError(
            f"El campo '{start_name}' no puede ser posterior "
            f"al campo '{end_name}'."
        )

    return start, end


def validate_uuid(value: Any, field_name: str = "id") -> UUID:
    """Valida y devuelve un identificador UUID."""
    if isinstance(value, UUID):
        return value

    if not isinstance(value, str):
        raise ValidationError(
            f"El campo '{field_name}' debe ser un UUID válido."
        )

    try:
        return UUID(value.strip())
    except (ValueError, AttributeError) as exc:
        raise ValidationError(
            f"El campo '{field_name}' debe ser un UUID válido."
        ) from exc


def validate_allowed_value(
    value: Any,
    allowed_values: set[str] | list[str] | tuple[str, ...],
    field_name: str,
    *,
    case_insensitive: bool = True,
) -> str:
    """
    Comprueba que un valor pertenezca a una lista de valores permitidos.

    Si case_insensitive es True, devuelve el valor canónico de la lista.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"El campo '{field_name}' debe ser texto."
        )

    candidate = value.strip()
    allowed = list(allowed_values)

    if case_insensitive:
        lookup = {item.casefold(): item for item in allowed}
        result = lookup.get(candidate.casefold())
    else:
        result = candidate if candidate in allowed else None

    if result is None:
        options = ", ".join(sorted(allowed))
        raise ValidationError(
            f"Valor inválido para '{field_name}'. "
            f"Valores permitidos: {options}."
        )

    return result


def _to_finite_float(value: Any, field_name: str) -> float:
    """Convierte un valor a float y rechaza booleanos y números no finitos."""
    if isinstance(value, bool):
        raise ValidationError(
            f"El campo '{field_name}' debe ser numérico."
        )

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError(
            f"El campo '{field_name}' debe ser numérico."
        ) from exc

    if not math.isfinite(number):
        raise ValidationError(
            f"El campo '{field_name}' debe ser un número finito."
        )

    return number


__all__ = [
    "ValidationError",
    "validate_required_string",
    "validate_sample_code",
    "validate_email",
    "validate_temperature",
    "validate_duration",
    "validate_risk_score",
    "validate_percentage",
    "validate_positive_integer",
    "validate_datetime",
    "validate_datetime_order",
    "validate_uuid",
    "validate_allowed_value",
]
