"""
Servicio de códigos QR para LabGuardian AI.

Responsabilidades:
- Construir el contenido QR de una muestra.
- Generar imágenes QR en formato PNG.
- Devolver la imagen codificada en Base64.
- Localizar una muestra a partir del contenido de su QR.
- Evitar incluir información clínica sensible en el código.

Dependencias:
    pip install "qrcode[pil]"
"""

from __future__ import annotations

import base64
import io
import re
from typing import Any
from urllib.parse import quote, unquote, urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sample import Sample


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DEFAULT_FRONTEND_URL = "http://localhost:5173"
QR_ROUTE_PREFIX = "/samples"

DEFAULT_QR_SIZE = 8
DEFAULT_QR_BORDER = 4
MAX_QR_SIZE = 20
MAX_QR_BORDER = 10

SAMPLE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class QRServiceError(Exception):
    """Error general del servicio QR."""


class QRValidationError(QRServiceError):
    """El contenido QR no es válido o no está permitido."""


class QRDependencyError(QRServiceError):
    """Falta una dependencia necesaria para generar imágenes QR."""


class SampleNotFoundError(QRServiceError):
    """No se encontró la muestra solicitada."""


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _get_base_url() -> str:
    """
    Obtiene la URL base del frontend.

    Se recomienda definir QR_BASE_URL en la configuración del proyecto.
    Si no existe, se intenta utilizar FRONTEND_URL.
    """

    configured_url = (
        getattr(settings, "qr_base_url", None)
        or getattr(settings, "frontend_url", None)
        or DEFAULT_FRONTEND_URL
    )

    base_url = str(configured_url).strip().rstrip("/")
    parsed = urlparse(base_url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise QRServiceError(
            "La URL base para códigos QR debe ser una URL HTTP o HTTPS válida."
        )

    if parsed.username or parsed.password:
        raise QRServiceError(
            "La URL base del QR no debe contener credenciales."
        )

    return base_url


def _validate_sample_code(sample_code: str) -> str:
    """Valida el formato del código único de una muestra."""

    if not isinstance(sample_code, str):
        raise QRValidationError("El código de muestra debe ser texto.")

    code = sample_code.strip()

    if not SAMPLE_CODE_PATTERN.fullmatch(code):
        raise QRValidationError(
            "El código de muestra contiene caracteres no permitidos."
        )

    return code


def _get_qrcode_module() -> Any:
    """Importa la biblioteca QR de forma diferida."""

    try:
        import qrcode
    except ImportError as exc:
        raise QRDependencyError(
            'Instala la dependencia con: pip install "qrcode[pil]"'
        ) from exc

    return qrcode


def _get_sample(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
) -> Sample:
    """Busca una muestra por ID o por código."""

    if (sample_id is None) == (sample_code is None):
        raise QRValidationError(
            "Debes proporcionar exactamente un identificador: "
            "sample_id o sample_code."
        )

    query = db.query(Sample)

    if sample_id is not None:
        sample = query.filter(Sample.id == sample_id).first()
    else:
        code = _validate_sample_code(sample_code or "")
        sample = query.filter(Sample.code == code).first()

    if sample is None:
        raise SampleNotFoundError("No se encontró la muestra solicitada.")

    return sample


# ---------------------------------------------------------------------------
# Construcción del contenido QR
# ---------------------------------------------------------------------------

def build_sample_qr_payload(sample: Sample) -> str:
    """
    Construye la URL que se almacenará dentro del QR.

    Ejemplo:
        http://localhost:5173/samples/LG-2026-0001

    La página del frontend debe implementar la ruta correspondiente.
    """

    if sample is None:
        raise QRValidationError("Debes proporcionar una muestra válida.")

    sample_code = _validate_sample_code(sample.code)
    base_url = _get_base_url()

    return f"{base_url}{QR_ROUTE_PREFIX}/{quote(sample_code, safe='')}"


# ---------------------------------------------------------------------------
# Generación de imagen
# ---------------------------------------------------------------------------

def generate_qr_png(
    payload: str,
    *,
    box_size: int = DEFAULT_QR_SIZE,
    border: int = DEFAULT_QR_BORDER,
) -> bytes:
    """
    Genera una imagen QR PNG y devuelve sus bytes.

    Esta función no guarda archivos en el disco.
    """

    if not isinstance(payload, str) or not payload.strip():
        raise QRValidationError("El contenido del QR no puede estar vacío.")

    if not 1 <= box_size <= MAX_QR_SIZE:
        raise QRValidationError(
            f"box_size debe estar entre 1 y {MAX_QR_SIZE}."
        )

    if not 1 <= border <= MAX_QR_BORDER:
        raise QRValidationError(
            f"border debe estar entre 1 y {MAX_QR_BORDER}."
        )

    qrcode = _get_qrcode_module()

    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )

        qr.add_data(payload)
        qr.make(fit=True)

        image = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        return buffer.getvalue()

    except QRServiceError:
        raise
    except Exception as exc:
        raise QRServiceError(
            "No fue posible generar la imagen QR."
        ) from exc


def generate_sample_qr(
    db: Session,
    *,
    sample_id: int | None = None,
    sample_code: str | None = None,
    box_size: int = DEFAULT_QR_SIZE,
    border: int = DEFAULT_QR_BORDER,
) -> dict[str, Any]:
    """
    Genera un QR para una muestra registrada.

    Devuelve:
        {
            "sample_id": ...,
            "sample_code": ...,
            "payload": ...,
            "image_format": "PNG",
            "image_base64": ...,
            "image_data_uri": ...
        }
    """

    sample = _get_sample(
        db,
        sample_id=sample_id,
        sample_code=sample_code,
    )

    payload = build_sample_qr_payload(sample)
    image_bytes = generate_qr_png(
        payload,
        box_size=box_size,
        border=border,
    )

    image_base64 = base64.b64encode(image_bytes).decode("ascii")

    return {
        "sample_id": sample.id,
        "sample_code": sample.code,
        "payload": payload,
        "image_format": "PNG",
        "image_base64": image_base64,
        "image_data_uri": f"data:image/png;base64,{image_base64}",
    }


# ---------------------------------------------------------------------------
# Validación y lectura del contenido QR
# ---------------------------------------------------------------------------

def extract_sample_code_from_qr(qr_content: str) -> str:
    """
    Extrae el código de muestra de una URL QR generada por este servicio.

    Acepta únicamente:
        <URL_BASE>/samples/<codigo>

    Rechaza esquemas distintos de HTTP/HTTPS, credenciales, rutas
    inesperadas y códigos con caracteres no permitidos.
    """

    if not isinstance(qr_content, str) or not qr_content.strip():
        raise QRValidationError("El contenido del QR está vacío.")

    content = qr_content.strip()

    if len(content) > 2048:
        raise QRValidationError("El contenido del QR es demasiado largo.")

    parsed = urlparse(content)
    base_url = urlparse(_get_base_url())

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise QRValidationError("El QR no contiene una URL válida.")

    if parsed.username or parsed.password:
        raise QRValidationError("La URL QR no debe contener credenciales.")

    if parsed.scheme.lower() != base_url.scheme.lower():
        raise QRValidationError("El esquema de la URL QR no coincide.")

    if parsed.netloc.lower() != base_url.netloc.lower():
        raise QRValidationError("El dominio del QR no está autorizado.")

    expected_prefix = f"{base_url.path.rstrip('/')}{QR_ROUTE_PREFIX}"
    path = parsed.path

    if not path.startswith(expected_prefix + "/"):
        raise QRValidationError("El QR no corresponde a una ruta de muestra.")

    encoded_code = path[len(expected_prefix) + 1:]

    # No se permiten rutas adicionales ni segmentos vacíos.
    if not encoded_code or "/" in encoded_code:
        raise QRValidationError("La ruta del QR no contiene un código válido.")

    code = unquote(encoded_code)

    # Exige una codificación URL canónica para evitar rutas ambiguas.
    if quote(code, safe="") != encoded_code:
        raise QRValidationError("La codificación del código QR no es válida.")

    return _validate_sample_code(code)


def get_sample_from_qr(
    db: Session,
    qr_content: str,
) -> Sample:
    """
    Localiza una muestra a partir del contenido de su QR.

    La muestra se consulta en la base de datos; el QR por sí solo
    no demuestra que la muestra sea auténtica ni que esté autorizada.
    """

    sample_code = extract_sample_code_from_qr(qr_content)

    sample = (
        db.query(Sample)
        .filter(Sample.code == sample_code)
        .first()
    )

    if sample is None:
        raise SampleNotFoundError(
            f"No se encontró una muestra con código {sample_code}."
        )

    return sample


def get_sample_qr_data(
    db: Session,
    qr_content: str,
) -> dict[str, Any]:
    """
    Obtiene los datos operativos básicos de una muestra mediante su QR.

    No devuelve notas ni información clínica adicional.
    """

    sample = get_sample_from_qr(db, qr_content)

    return {
        "sample_id": sample.id,
        "sample_code": sample.code,
        "sample_type": sample.sample_type,
        "laboratory_area": sample.laboratory_area,
        "status": sample.status,
        "priority": sample.priority,
        "risk_level": sample.risk_level,
        "anomaly_detected": sample.anomaly_detected,
        "storage_location": sample.storage_location,
        "created_at": sample.created_at,
        "updated_at": sample.updated_at,
    }


# ---------------------------------------------------------------------------
# Comprobación de disponibilidad
# ---------------------------------------------------------------------------

def qr_service_status() -> dict[str, Any]:
    """Indica si la biblioteca QR está instalada."""

    try:
        _get_qrcode_module()
        available = True
        message = "La biblioteca QR está disponible."
    except QRDependencyError:
        available = False
        message = 'Instala la dependencia con: pip install "qrcode[pil]"'

    return {
        "available": available,
        "image_format": "PNG",
        "message": message,
    }
