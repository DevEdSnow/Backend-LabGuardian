
"""
Model loader for LabGuardian AI.

This module centralizes the loading and management of
Machine Learning models used by the application.

Supported models:

- Risk prediction model
- Anomaly detection model

Models are loaded from .pkl files using joblib.

The loader is designed to fail safely: if a model does
not exist or cannot be loaded, the application continues
working and the corresponding ML component can use its
rule-based fallback.
"""

from pathlib import Path
from typing import Any

import joblib


# ─────────────────────────────────────────────
# Model Loader
# ─────────────────────────────────────────────

class ModelLoader:
    """
    Utility class responsible for loading Machine
    Learning models from disk.
    """

    def __init__(
        self,
        model_path: str | Path,
    ) -> None:
        self.model_path = Path(model_path)

        self.model: Any = None
        self.loaded: bool = False
        self.error: str | None = None

    # ─────────────────────────────────────────
    # Load model
    # ─────────────────────────────────────────

    def load(self) -> Any | None:
        """
        Loads the model from the configured path.

        Returns
        -------
        Any | None
            Loaded model or None if loading fails.
        """

        self.error = None

        if not self.model_path.exists():
            self.loaded = False
            self.model = None
            self.error = (
                f"Modelo no encontrado: "
                f"{self.model_path}"
            )
            return None

        if not self.model_path.is_file():
            self.loaded = False
            self.model = None
            self.error = (
                f"La ruta del modelo no es un archivo: "
                f"{self.model_path}"
            )
            return None

        try:
            self.model = joblib.load(
                self.model_path
            )

            self.loaded = True

            return self.model

        except Exception as exc:
            self.model = None
            self.loaded = False
            self.error = (
                f"No se pudo cargar el modelo: {exc}"
            )

            return None

    # ─────────────────────────────────────────
    # Reload model
    # ─────────────────────────────────────────

    def reload(self) -> Any | None:
        """
        Forces the model to be loaded again.
        """

        self.model = None
        self.loaded = False

        return self.load()

    # ─────────────────────────────────────────
    # Get model
    # ─────────────────────────────────────────

    def get_model(self) -> Any | None:
        """
        Returns the currently loaded model.

        If the model has not been loaded yet,
        it attempts to load it.
        """

        if self.model is None:
            return self.load()

        return self.model

    # ─────────────────────────────────────────
    # Model status
    # ─────────────────────────────────────────

    def is_loaded(self) -> bool:
        """
        Returns True if the model was loaded successfully.
        """

        return self.loaded

    # ─────────────────────────────────────────
    # Model information
    # ─────────────────────────────────────────

    def get_info(self) -> dict[str, Any]:
        """
        Returns information about the model.
        """

        return {
            "path": str(self.model_path),
            "exists": self.model_path.exists(),
            "loaded": self.loaded,
            "model_type": (
                type(self.model).__name__
                if self.model is not None
                else None
            ),
            "error": self.error,
        }


# ─────────────────────────────────────────────
# Model manager
# ─────────────────────────────────────────────

class MLModelManager:
    """
    Manages the Machine Learning models used by
    LabGuardian AI.

    The manager provides a centralized interface for:

    - Risk model
    - Anomaly detection model
    """

    def __init__(
        self,
        risk_model_path: str | Path,
        anomaly_model_path: str | Path,
    ) -> None:

        self.risk_model = ModelLoader(
            risk_model_path
        )

        self.anomaly_model = ModelLoader(
            anomaly_model_path
        )

    # ─────────────────────────────────────────
    # Load all models
    # ─────────────────────────────────────────

    def load_all(self) -> dict[str, bool]:
        """
        Loads all configured Machine Learning models.

        Returns
        -------
        dict[str, bool]
            Loading status for each model.
        """

        risk = self.risk_model.load()
        anomaly = self.anomaly_model.load()

        return {
            "risk_model": risk is not None,
            "anomaly_model": anomaly is not None,
        }

    # ─────────────────────────────────────────
    # Risk model
    # ─────────────────────────────────────────

    def get_risk_model(self) -> Any | None:
        """
        Returns the risk prediction model.
        """

        return self.risk_model.get_model()

    # ─────────────────────────────────────────
    # Anomaly model
    # ─────────────────────────────────────────

    def get_anomaly_model(self) -> Any | None:
        """
        Returns the anomaly detection model.
        """

        return self.anomaly_model.get_model()

    # ─────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """
        Returns the loading status of all models.
        """

        return {
            "risk_model": self.risk_model.get_info(),
            "anomaly_model": self.anomaly_model.get_info(),
        }

    # ─────────────────────────────────────────
    # Reload all
    # ─────────────────────────────────────────

    def reload_all(self) -> dict[str, bool]:
        """
        Reloads all Machine Learning models.
        """

        risk = self.risk_model.reload()
        anomaly = self.anomaly_model.reload()

        return {
            "risk_model": risk is not None,
            "anomaly_model": anomaly is not None,
        }


# ─────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────

def create_model_manager(
    risk_model_path: str,
    anomaly_model_path: str,
) -> MLModelManager:
    """
    Creates a configured MLModelManager instance.
    """

    return MLModelManager(
        risk_model_path=risk_model_path,
        anomaly_model_path=anomaly_model_path,
    )

