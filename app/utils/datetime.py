
"""
Utilidades para el manejo de fechas y horas de LabGuardian AI.

Proporciona funciones para trabajar con fechas UTC, normalizar fechas
con zona horaria y calcular diferencias de tiempo.

Se recomienda almacenar y comparar fechas usando UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Devuelve la fecha y hora actuales con zona horaria UTC.

    Returns:
        datetime: Fecha y hora actual en UTC.
    """
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """
    Convierte una fecha a UTC.

    Si la fecha no contiene zona horaria, se interpreta como UTC.
    Si ya contiene una zona horaria, se convierte a UTC.

    Args:
        value: Fecha y hora que se desea normalizar.

    Returns:
        datetime: Fecha con zona horaria UTC.

    Raises:
        TypeError: Si el valor no es un datetime.
    """
    if not isinstance(value, datetime):
        raise TypeError("El valor debe ser una instancia de datetime.")

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def to_iso_string(value: Optional[datetime]) -> Optional[str]:
    """
    Convierte una fecha a formato ISO 8601.

    Las fechas se normalizan a UTC antes de serializarlas.

    Args:
        value: Fecha que se desea convertir.

    Returns:
        str | None: Fecha en ISO 8601 o None si no se proporciona fecha.
    """
    if value is None:
        return None

    return ensure_utc(value).isoformat()


def from_iso_string(value: str) -> datetime:
    """
    Convierte una cadena ISO 8601 en un datetime UTC.

    Acepta cadenas con zona horaria y cadenas sin zona horaria.
    Las cadenas sin zona horaria se interpretan como UTC.

    Args:
        value: Fecha en formato ISO 8601.

    Returns:
        datetime: Fecha normalizada a UTC.

    Raises:
        TypeError: Si el valor no es una cadena.
        ValueError: Si la cadena no contiene una fecha válida.
    """
    if not isinstance(value, str):
        raise TypeError("La fecha debe proporcionarse como una cadena.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError("La fecha no puede estar vacía.")

    try:
        parsed_value = datetime.fromisoformat(
            normalized_value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError(
            f"Formato de fecha ISO 8601 inválido: {value}"
        ) from exc

    return ensure_utc(parsed_value)


def minutes_between(
    start: datetime,
    end: datetime,
    *,
    absolute: bool = False,
) -> float:
    """
    Calcula los minutos transcurridos entre dos fechas.

    Args:
        start: Fecha inicial.
        end: Fecha final.
        absolute: Si es True, devuelve el valor absoluto de la diferencia.

    Returns:
        float: Minutos transcurridos.
    """
    start_utc = ensure_utc(start)
    end_utc = ensure_utc(end)

    difference = (end_utc - start_utc).total_seconds() / 60

    return abs(difference) if absolute else difference


def is_future(value: datetime, *, reference: Optional[datetime] = None) -> bool:
    """
    Indica si una fecha es posterior a una fecha de referencia.

    Si no se proporciona referencia, se utiliza la hora actual UTC.

    Args:
        value: Fecha que se desea comprobar.
        reference: Fecha de referencia opcional.

    Returns:
        bool: True si la fecha es futura.
    """
    value_utc = ensure_utc(value)
    reference_utc = ensure_utc(reference) if reference else utc_now()

    return value_utc > reference_utc


def format_datetime(
    value: Optional[datetime],
    fmt: str = "%d/%m/%Y %H:%M:%S",
) -> Optional[str]:
    """
    Formatea una fecha para mostrarla en la interfaz o en reportes.

    La hora se convierte a UTC antes de formatearse.

    Args:
        value: Fecha que se desea mostrar.
        fmt: Formato compatible con datetime.strftime.

    Returns:
        str | None: Fecha formateada o None si no hay fecha.
    """
    if value is None:
        return None

    return ensure_utc(value).strftime(fmt)


__all__ = [
    "utc_now",
    "ensure_utc",
    "to_iso_string",
    "from_iso_string",
    "minutes_between",
    "is_future",
    "format_datetime",
]
