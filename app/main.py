
"""
LabGuardian AI — Aplicación principal de FastAPI.

Punto de entrada del backend:
- Configuración de FastAPI.
- Middleware CORS.
- Registro de rutas disponibles.
- Endpoints de estado y diagnóstico básico.
- Manejo general de errores.
- Metadatos de la API.

La inicialización de la base de datos y la carga de modelos ML se mantienen
separadas para evitar efectos secundarios al importar este módulo.
"""

from __future__ import annotations

import importlib
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __project_name__, __version__
from app.core.config import settings


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

logger = logging.getLogger("labguardian")

API_PREFIX = getattr(settings, "api_prefix", "/api/v1")
APP_NAME = getattr(settings, "app_name", __project_name__)
APP_VERSION = __version__
DEBUG = bool(getattr(settings, "debug", False))

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

configured_origins = getattr(settings, "cors_origins", DEFAULT_CORS_ORIGINS)

if isinstance(configured_origins, str):
    CORS_ORIGINS = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
else:
    CORS_ORIGINS = list(configured_origins or DEFAULT_CORS_ORIGINS)


# ---------------------------------------------------------------------------
# Ciclo de vida de la aplicación
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Gestiona el inicio y cierre de la aplicación."""
    logger.info(
        "Iniciando %s versión %s",
        APP_NAME,
        APP_VERSION,
    )

    yield

    logger.info("Cerrando %s", APP_NAME)


# ---------------------------------------------------------------------------
# Aplicación FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    description=(
        "API para la trazabilidad de muestras, monitorización de equipos, "
        "gestión de alertas y análisis de riesgos de laboratorio."
    ),
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Middleware CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)


# ---------------------------------------------------------------------------
# Manejo de errores
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Devuelve errores de entrada con un formato consistente."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Los datos enviados no son válidos.",
                "details": exc.errors(),
            },
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Registra errores inesperados sin exponer detalles internos."""
    logger.exception(
        "Error inesperado en %s %s",
        request.method,
        request.url.path,
    )

    response: dict[str, Any] = {
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Ocurrió un error interno en el servidor.",
        },
    }

    if DEBUG:
        response["error"]["details"] = str(exc)

    return JSONResponse(
        status_code=500,
        content=response,
    )


# ---------------------------------------------------------------------------
# Endpoints generales
# ---------------------------------------------------------------------------

@app.get("/", tags=["Sistema"])
async def root() -> dict[str, Any]:
    """Presenta información general del backend."""
    return {
        "success": True,
        "name": APP_NAME,
        "version": APP_VERSION,
        "message": "API de LabGuardian AI en funcionamiento.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Sistema"])
async def health_check() -> dict[str, Any]:
    """
    Comprueba que el proceso de la API responde.

    Este endpoint no comprueba la conexión a PostgreSQL ni la disponibilidad
    de los modelos de Machine Learning.
    """
    return {
        "success": True,
        "status": "healthy",
        "service": "labguardian-api",
        "version": APP_VERSION,
    }


@app.get(f"{API_PREFIX}/health", tags=["Sistema"])
async def api_health_check() -> dict[str, Any]:
    """Comprueba que el prefijo principal de la API responde."""
    return {
        "success": True,
        "status": "healthy",
        "api_prefix": API_PREFIX,
        "version": APP_VERSION,
    }


# ---------------------------------------------------------------------------
# Registro de routers
# ---------------------------------------------------------------------------

ROUTE_MODULES = (
    "samples",
    "events",
    "equipment",
    "alerts",
    "dashboard",
    "risk",
    "qr",
)


def register_routers() -> None:
    """
    Registra los routers de app.api.routes.

    Cada módulo debe exponer una variable llamada `router` de tipo APIRouter.
    Los módulos que todavía no existan se omiten durante el desarrollo.
    Los demás errores de importación se propagan para no ocultar fallos.
    """
    for module_name in ROUTE_MODULES:
        module_path = f"app.api.routes.{module_name}"

        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            # Solo se omite si el módulo de ruta solicitado es el que falta.
            if exc.name == module_path:
                logger.warning(
                    "Ruta todavía no disponible: %s",
                    module_path,
                )
                continue
            raise

        router = getattr(module, "router", None)

        if router is None:
            logger.warning(
                "El módulo %s no exporta una variable 'router'.",
                module_path,
            )
            continue

        app.include_router(
            router,
            prefix=API_PREFIX,
        )

        logger.info("Ruta registrada: %s", module_path)


register_routers()


# ---------------------------------------------------------------------------
# Ejecución directa
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=DEBUG,
    )
