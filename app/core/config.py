
"""
Application configuration for LabGuardian AI.

This module centralizes environment variables and
application settings.

Configuration values are loaded from the .env file
when available.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application settings.
    """

    # ─────────────────────────────────────────────
    # Application
    # ─────────────────────────────────────────────

    app_name: str = Field(
        default="LabGuardian AI",
        description="Application name.",
    )

    app_version: str = Field(
        default="1.0.0",
        description="Application version.",
    )

    app_description: str = Field(
        default=(
            "API para control inteligente, "
            "trazabilidad y análisis de riesgo "
            "de muestras clínicas."
        ),
        description="Application description.",
    )

    environment: str = Field(
        default="development",
        description="Application environment.",
    )

    debug: bool = Field(
        default=True,
        description="Enable debug mode.",
    )

    # ─────────────────────────────────────────────
    # API
    # ─────────────────────────────────────────────

    api_prefix: str = Field(
        default="/api",
        description="Base API prefix.",
    )

    host: str = Field(
        default="0.0.0.0",
        description="API host.",
    )

    port: int = Field(
        default=8000,
        description="API port.",
    )

    # ─────────────────────────────────────────────
    # CORS
    # ─────────────────────────────────────────────

    frontend_url: str = Field(
        default="http://localhost:5173",
        description="Frontend URL.",
    )

    # ─────────────────────────────────────────────
    # PostgreSQL
    # ─────────────────────────────────────────────

    database_url: str = Field(
        default=(
            "postgresql+psycopg://"
            "postgres:postgres@localhost:5432/"
            "labguardian"
        ),
        description="PostgreSQL database URL.",
    )

    database_echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy SQL logging.",
    )

    # ─────────────────────────────────────────────
    # Security
    # ─────────────────────────────────────────────

    secret_key: str = Field(
        default="change-this-secret-key",
        description="Secret key used by the application.",
    )

    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm.",
    )

    access_token_expire_minutes: int = Field(
        default=60,
        description="JWT expiration time in minutes.",
    )

    # ─────────────────────────────────────────────
    # Machine Learning
    # ─────────────────────────────────────────────

    risk_model_path: str = Field(
        default="ml_models/risk_model.pkl",
        description="Path to the risk prediction model.",
    )

    anomaly_model_path: str = Field(
        default="ml_models/anomaly_model.pkl",
        description="Path to the anomaly detection model.",
    )

    ml_enabled: bool = Field(
        default=False,
        description=(
            "Enable Machine Learning functionality."
        ),
    )

    # ─────────────────────────────────────────────
    # QR
    # ─────────────────────────────────────────────

    qr_base_url: str = Field(
        default="http://localhost:5173/sample",
        description="Base URL used by sample QR codes.",
    )

    # ─────────────────────────────────────────────
    # Pydantic Settings
    # ─────────────────────────────────────────────

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns the application settings.

    The result is cached so the configuration is
    loaded only once during the application lifecycle.
    """

    return Settings()


# Global settings instance.
settings = get_settings()

