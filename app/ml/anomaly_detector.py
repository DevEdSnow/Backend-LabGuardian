
"""
Anomaly detector for LabGuardian AI.

This module detects unusual conditions in clinical
samples and laboratory equipment.

The detector supports two modes:

1. Machine Learning mode:
   Uses an Isolation Forest model stored as a .pkl file.

2. Rule-based fallback:
   Detects obvious anomalies when the ML model
   is not available yet.

The goal is to identify abnormal conditions such as:

- Unexpected temperature
- Excessive transport time
- Excessive processing time
- Excessive storage time
- Unusual combinations of conditions
"""

from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import settings


class AnomalyDetector:
    """
    Detects anomalies in laboratory sample conditions.
    """

    def __init__(
        self,
        model_path: str | None = None,
    ) -> None:
        """
        Initializes the anomaly detector.

        Parameters
        ----------
        model_path:
            Optional path to the trained anomaly model.
        """

        self.model_path = Path(
            model_path or settings.anomaly_model_path
        )

        self.model: Any = None
        self.model_loaded = False

        self._load_model()

    # ─────────────────────────────────────────
    # Model loading
    # ─────────────────────────────────────────

    def _load_model(self) -> None:
        """
        Attempts to load the trained anomaly model.

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
        feature vector used by the anomaly model.

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
    # Rule-based detection
    # ─────────────────────────────────────────

    def _detect_rule_based(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Detects obvious anomalies using predefined rules.
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

        anomalies: list[dict[str, Any]] = []

        # ─────────────────────────────────────
        # Temperature anomaly
        # ─────────────────────────────────────

        if temperature < 2 or temperature > 8:

            severity = (
                "HIGH"
                if temperature < 0
                or temperature > 10
                else "MEDIUM"
            )

            anomalies.append(
                {
                    "type": "TEMPERATURE",
                    "severity": severity,
                    "value": temperature,
                    "unit": "°C",
                    "message": (
                        "Temperatura fuera del rango "
                        "recomendado."
                    ),
                }
            )

        # ─────────────────────────────────────
        # Transport anomaly
        # ─────────────────────────────────────

        if transport_minutes > 30:

            severity = (
                "HIGH"
                if transport_minutes > 60
                else "MEDIUM"
            )

            anomalies.append(
                {
                    "type": "TRANSPORT_TIME",
                    "severity": severity,
                    "value": transport_minutes,
                    "unit": "min",
                    "message": (
                        "Tiempo de transporte superior "
                        "al recomendado."
                    ),
                }
            )

        # ─────────────────────────────────────
        # Processing anomaly
        # ─────────────────────────────────────

        if processing_minutes > 60:

            severity = (
                "HIGH"
                if processing_minutes > 120
                else "MEDIUM"
            )

            anomalies.append(
                {
                    "type": "PROCESSING_TIME",
                    "severity": severity,
                    "value": processing_minutes,
                    "unit": "min",
                    "message": (
                        "Tiempo de procesamiento superior "
                        "al recomendado."
                    ),
                }
            )

        # ─────────────────────────────────────
        # Storage anomaly
        # ─────────────────────────────────────

        if storage_minutes > 120:

            severity = (
                "HIGH"
                if storage_minutes > 240
                else "MEDIUM"
            )

            anomalies.append(
                {
                    "type": "STORAGE_TIME",
                    "severity": severity,
                    "value": storage_minutes,
                    "unit": "min",
                    "message": (
                        "Tiempo de almacenamiento "
                        "superior al recomendado."
                    ),
                }
            )

        # ─────────────────────────────────────
        # Combined anomaly
        # ─────────────────────────────────────

        if (
            temperature > 8
            and processing_minutes > 60
        ):
            anomalies.append(
                {
                    "type": "SAMPLE_DEGRADATION_RISK",
                    "severity": "HIGH",
                    "value": None,
                    "unit": None,
                    "message": (
                        "La combinación de temperatura "
                        "elevada y procesamiento tardío "
                        "puede indicar riesgo de "
                        "degradación de la muestra."
                    ),
                }
            )

        is_anomaly = len(anomalies) > 0

        if any(
            anomaly["severity"] == "HIGH"
            for anomaly in anomalies
        ):
            severity = "HIGH"

        elif anomalies:
            severity = "MEDIUM"

        else:
            severity = "NORMAL"

        return {
            "is_anomaly": is_anomaly,
            "severity": severity,
            "anomalies": anomalies,
        }

    # ─────────────────────────────────────────
    # ML detection
    # ─────────────────────────────────────────

    def _detect_ml(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Detects anomalies using the trained
        Machine Learning model.

        Isolation Forest normally returns:

            1  -> normal
           -1  -> anomaly
        """

        features = self._prepare_features(
            data
        )

        prediction = self.model.predict(
            features
        )[0]

        is_anomaly = prediction == -1

        anomaly_score = None

        if hasattr(
            self.model,
            "decision_function",
        ):
            anomaly_score = float(
                self.model.decision_function(
                    features
                )[0]
            )

        if is_anomaly:
            severity = "HIGH"
        else:
            severity = "NORMAL"

        return {
            "is_anomaly": is_anomaly,
            "severity": severity,
            "anomalies": [],
            "anomaly_score": anomaly_score,
        }

    # ─────────────────────────────────────────
    # Main detection method
    # ─────────────────────────────────────────

    def detect(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Detects anomalies in a clinical sample.

        Parameters
        ----------
        data:
            Sample conditions.

        Returns
        -------
        dict
            Anomaly detection result.
        """

        # ─────────────────────────────────────
        # Machine Learning
        # ─────────────────────────────────────

        if (
            self.model_loaded
            and self.model is not None
        ):
            try:
                result = self._detect_ml(
                    data
                )

                result["detection_source"] = (
                    "machine_learning"
                )

                result["model_loaded"] = True

                # Add rule-based explanations when
                # the ML model detects an anomaly.
                if result["is_anomaly"]:
                    rule_result = (
                        self._detect_rule_based(
                            data
                        )
                    )

                    result["anomalies"] = (
                        rule_result["anomalies"]
                    )

                    if rule_result["severity"] == "HIGH":
                        result["severity"] = "HIGH"

                return result

            except Exception:
                pass

        # ─────────────────────────────────────
        # Rule-based fallback
        # ─────────────────────────────────────

        result = self._detect_rule_based(
            data
        )

        result["detection_source"] = (
            "rule_based"
        )

        result["model_loaded"] = False

        return result


# ─────────────────────────────────────────────
# Global detector instance
# ─────────────────────────────────────────────

anomaly_detector = AnomalyDetector()

