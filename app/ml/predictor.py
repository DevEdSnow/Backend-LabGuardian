
"""
Risk predictor for LabGuardian AI.

This module provides the interface used to calculate
the risk of clinical samples.

The predictor supports two modes:

1. Machine Learning mode:
   Uses a trained model stored as a .pkl file.

2. Rule-based fallback:
   Used when the ML model is not available yet.

This allows the API to work during development
before the final Machine Learning model is trained.
"""

from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import settings


# ─────────────────────────────────────────────
# Risk thresholds
# ─────────────────────────────────────────────

LOW_RISK_THRESHOLD = 40
HIGH_RISK_THRESHOLD = 70


# ─────────────────────────────────────────────
# Predictor
# ─────────────────────────────────────────────

class RiskPredictor:
    """
    Predicts the risk level of a clinical sample.

    The class first attempts to use the trained
    Machine Learning model. If the model is not
    available, it falls back to a deterministic
    rule-based calculation.
    """

    def __init__(
        self,
        model_path: str | None = None,
    ) -> None:
        """
        Initializes the risk predictor.

        Parameters
        ----------
        model_path:
            Optional path to the trained ML model.
        """

        self.model_path = Path(
            model_path or settings.risk_model_path
        )

        self.model: Any = None
        self.model_loaded = False

        self._load_model()

    # ─────────────────────────────────────────
    # Model loading
    # ─────────────────────────────────────────

    def _load_model(self) -> None:
        """
        Attempts to load the trained ML model.

        The model is optional during development.
        """

        if not self.model_path.exists():
            self.model = None
            self.model_loaded = False
            return

        try:
            import joblib

            self.model = joblib.load(
                self.model_path
            )

            self.model_loaded = True

        except Exception:
            self.model = None
            self.model_loaded = False

    # ─────────────────────────────────────────
    # Feature preparation
    # ─────────────────────────────────────────

    def _prepare_features(
        self,
        data: dict[str, Any],
    ) -> np.ndarray:
        """
        Converts sample information into the numerical
        feature vector expected by the ML model.

        Feature order:

        1. temperature
        2. transport_minutes
        3. processing_minutes
        4. storage_minutes
        """

        temperature = float(
            data.get("temperature", 5.0)
        )

        transport_minutes = float(
            data.get("transport_minutes", 0.0)
        )

        processing_minutes = float(
            data.get("processing_minutes", 0.0)
        )

        storage_minutes = float(
            data.get("storage_minutes", 0.0)
        )

        return np.array(
            [[
                temperature,
                transport_minutes,
                processing_minutes,
                storage_minutes,
            ]],
            dtype=float,
        )

    # ─────────────────────────────────────────
    # Rule-based prediction
    # ─────────────────────────────────────────

    def _calculate_rule_based_score(
        self,
        data: dict[str, Any],
    ) -> float:
        """
        Calculates a risk score using predefined rules.

        This acts as a fallback until the real ML model
        is trained and available.
        """

        temperature = float(
            data.get("temperature", 5.0)
        )

        transport_minutes = float(
            data.get("transport_minutes", 0.0)
        )

        processing_minutes = float(
            data.get("processing_minutes", 0.0)
        )

        storage_minutes = float(
            data.get("storage_minutes", 0.0)
        )

        score = 0.0

        # ─────────────────────────────────────
        # Temperature
        # ─────────────────────────────────────

        if temperature < 2:
            score += min(
                abs(temperature - 2) * 10,
                25,
            )

        elif temperature > 8:
            score += min(
                (temperature - 8) * 12,
                40,
            )

        # ─────────────────────────────────────
        # Transport time
        # ─────────────────────────────────────

        if transport_minutes > 30:
            score += min(
                (transport_minutes - 30) * 0.5,
                20,
            )

        # ─────────────────────────────────────
        # Processing time
        # ─────────────────────────────────────

        if processing_minutes > 60:
            score += min(
                (processing_minutes - 60) * 0.8,
                25,
            )

        # ─────────────────────────────────────
        # Storage time
        # ─────────────────────────────────────

        if storage_minutes > 120:
            score += min(
                (storage_minutes - 120) * 0.15,
                15,
            )

        return round(
            min(score, 100),
            2,
        )

    # ─────────────────────────────────────────
    # Risk level
    # ─────────────────────────────────────────

    @staticmethod
    def _get_risk_level(
        score: float,
    ) -> str:
        """
        Converts a numerical score into a risk level.
        """

        if score >= HIGH_RISK_THRESHOLD:
            return "HIGH"

        if score >= LOW_RISK_THRESHOLD:
            return "MEDIUM"

        return "LOW"

    # ─────────────────────────────────────────
    # Risk status
    # ─────────────────────────────────────────

    @staticmethod
    def _get_status(
        level: str,
    ) -> str:
        """
        Converts the risk level into a sample status.
        """

        if level == "HIGH":
            return "AT_RISK"

        if level == "MEDIUM":
            return "MONITOR"

        return "NORMAL"

    # ─────────────────────────────────────────
    # Factor analysis
    # ─────────────────────────────────────────

    def _analyze_factors(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Identifies the factors contributing to the
        sample's risk.

        This information is useful for explainable AI
        and for displaying the reason behind a risk score.
        """

        factors: list[dict[str, Any]] = []

        temperature = float(
            data.get("temperature", 5.0)
        )

        transport_minutes = float(
            data.get("transport_minutes", 0.0)
        )

        processing_minutes = float(
            data.get("processing_minutes", 0.0)
        )

        storage_minutes = float(
            data.get("storage_minutes", 0.0)
        )

        # Temperature factor

        if temperature < 2 or temperature > 8:

            difference = min(
                abs(temperature - 2),
                abs(temperature - 8),
            )

            impact = min(
                round(difference * 12, 2),
                40,
            )

            factors.append(
                {
                    "name": "Temperatura",
                    "value": temperature,
                    "unit": "°C",
                    "impact": impact,
                    "severity": (
                        "HIGH"
                        if impact >= 25
                        else "MEDIUM"
                    ),
                }
            )

        # Transport factor

        if transport_minutes > 30:

            impact = min(
                round(
                    (transport_minutes - 30) * 0.5,
                    2,
                ),
                20,
            )

            factors.append(
                {
                    "name": "Tiempo de transporte",
                    "value": transport_minutes,
                    "unit": "min",
                    "impact": impact,
                    "severity": (
                        "HIGH"
                        if impact >= 15
                        else "MEDIUM"
                    ),
                }
            )

        # Processing factor

        if processing_minutes > 60:

            impact = min(
                round(
                    (processing_minutes - 60) * 0.8,
                    2,
                ),
                25,
            )

            factors.append(
                {
                    "name": "Tiempo de procesamiento",
                    "value": processing_minutes,
                    "unit": "min",
                    "impact": impact,
                    "severity": (
                        "HIGH"
                        if impact >= 20
                        else "MEDIUM"
                    ),
                }
            )

        # Storage factor

        if storage_minutes > 120:

            impact = min(
                round(
                    (storage_minutes - 120) * 0.15,
                    2,
                ),
                15,
            )

            factors.append(
                {
                    "name": "Tiempo de almacenamiento",
                    "value": storage_minutes,
                    "unit": "min",
                    "impact": impact,
                    "severity": (
                        "HIGH"
                        if impact >= 10
                        else "MEDIUM"
                    ),
                }
            )

        return factors

    # ─────────────────────────────────────────
    # Prediction
    # ─────────────────────────────────────────

    def predict(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Calculates the risk of a clinical sample.

        Parameters
        ----------
        data:
            Sample characteristics.

        Returns
        -------
        dict
            Risk prediction and explainability data.
        """

        # ─────────────────────────────────────
        # ML prediction
        # ─────────────────────────────────────

        if self.model_loaded and self.model is not None:

            try:
                features = self._prepare_features(
                    data
                )

                prediction = self.model.predict(
                    features
                )[0]

                score = float(prediction)

                score = max(
                    0.0,
                    min(score, 100.0),
                )

                prediction_source = "machine_learning"

            except Exception:
                score = self._calculate_rule_based_score(
                    data
                )

                prediction_source = "rule_based_fallback"

        # ─────────────────────────────────────
        # Rule-based fallback
        # ─────────────────────────────────────

        else:

            score = self._calculate_rule_based_score(
                data
            )

            prediction_source = "rule_based"

        level = self._get_risk_level(
            score
        )

        status = self._get_status(
            level
        )

        factors = self._analyze_factors(
            data
        )

        return {
            "score": score,
            "level": level,
            "status": status,
            "prediction_source": prediction_source,
            "model_loaded": self.model_loaded,
            "factors": factors,
        }


# ─────────────────────────────────────────────
# Global predictor instance
# ─────────────────────────────────────────────

risk_predictor = RiskPredictor()

