```python
"""
Feature engineering for LabGuardian AI.

This module centralizes the transformation of clinical
sample data into numerical features used by Machine
Learning models.

Keeping feature engineering in one place ensures that
RiskPredictor and AnomalyDetector use exactly the same
feature order and preprocessing logic.
"""

from typing import Any

import numpy as np


# ─────────────────────────────────────────────
# Feature configuration
# ─────────────────────────────────────────────

FEATURE_NAMES = [
    "temperature",
    "transport_minutes",
    "processing_minutes",
    "storage_minutes",
]


DEFAULT_FEATURES = {
    "temperature": 5.0,
    "transport_minutes": 0.0,
    "processing_minutes": 0.0,
    "storage_minutes": 0.0,
}


# ─────────────────────────────────────────────
# Feature extraction
# ─────────────────────────────────────────────

def extract_features(
    data: dict[str, Any],
) -> dict[str, float]:
    """
    Extracts and normalizes the numerical features
    required by the ML models.

    Parameters
    ----------
    data:
        Dictionary containing sample information.

    Returns
    -------
    dict[str, float]
        Normalized numerical features.
    """

    features: dict[str, float] = {}

    for feature_name in FEATURE_NAMES:
        value = data.get(
            feature_name,
            DEFAULT_FEATURES[feature_name],
        )

        try:
            features[feature_name] = float(value)
        except (TypeError, ValueError):
            features[feature_name] = DEFAULT_FEATURES[
                feature_name
            ]

    return features


# ─────────────────────────────────────────────
# NumPy conversion
# ─────────────────────────────────────────────

def features_to_numpy(
    data: dict[str, Any],
) -> np.ndarray:
    """
    Converts sample data into the NumPy matrix
    expected by the Machine Learning models.

    Feature order:

    1. temperature
    2. transport_minutes
    3. processing_minutes
    4. storage_minutes
    """

    features = extract_features(data)

    return np.array(
        [[
            features["temperature"],
            features["transport_minutes"],
            features["processing_minutes"],
            features["storage_minutes"],
        ]],
        dtype=float,
    )


# ─────────────────────────────────────────────
# Feature vector
# ─────────────────────────────────────────────

def features_to_list(
    data: dict[str, Any],
) -> list[float]:
    """
    Converts sample data into an ordered list
    of numerical features.

    Useful for debugging, logging and APIs.
    """

    features = extract_features(data)

    return [
        features[name]
        for name in FEATURE_NAMES
    ]


# ─────────────────────────────────────────────
# Feature validation
# ─────────────────────────────────────────────

def validate_features(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Validates the numerical values used by the
    Machine Learning models.

    Returns information about invalid or suspicious
    values without raising exceptions.
    """

    features = extract_features(data)

    warnings: list[str] = []

    temperature = features["temperature"]
    transport_minutes = features["transport_minutes"]
    processing_minutes = features["processing_minutes"]
    storage_minutes = features["storage_minutes"]

    # Temperature validation
    if temperature < -50 or temperature > 100:
        warnings.append(
            "La temperatura está fuera de un rango físico esperado."
        )

    # Time validation
    if transport_minutes < 0:
        warnings.append(
            "El tiempo de transporte no puede ser negativo."
        )

    if processing_minutes < 0:
        warnings.append(
            "El tiempo de procesamiento no puede ser negativo."
        )

    if storage_minutes < 0:
        warnings.append(
            "El tiempo de almacenamiento no puede ser negativo."
        )

    return {
        "valid": len(warnings) == 0,
        "features": features,
        "warnings": warnings,
    }


# ─────────────────────────────────────────────
# Feature normalization
# ─────────────────────────────────────────────

def normalize_features(
    data: dict[str, Any],
) -> dict[str, float]:
    """
    Applies basic normalization to the features.

    This normalization is intended for models that
    require values on a comparable scale.

    The ranges are based on the operational context
    of LabGuardian AI and can later be replaced by
    statistics calculated from the training dataset.
    """

    features = extract_features(data)

    # Expected operational ranges.
    ranges = {
        "temperature": (-10.0, 40.0),
        "transport_minutes": (0.0, 180.0),
        "processing_minutes": (0.0, 360.0),
        "storage_minutes": (0.0, 720.0),
    }

    normalized: dict[str, float] = {}

    for name in FEATURE_NAMES:
        minimum, maximum = ranges[name]
        value = features[name]

        if maximum == minimum:
            normalized[name] = 0.0
            continue

        normalized_value = (
            (value - minimum)
            / (maximum - minimum)
        )

        normalized[name] = max(
            0.0,
            min(normalized_value, 1.0),
        )

    return normalized


def normalized_to_numpy(
    data: dict[str, Any],
) -> np.ndarray:
    """
    Converts normalized features into a NumPy matrix.
    """

    normalized = normalize_features(data)

    return np.array(
        [[
            normalized["temperature"],
            normalized["transport_minutes"],
            normalized["processing_minutes"],
            normalized["storage_minutes"],
        ]],
        dtype=float,
    )


# ─────────────────────────────────────────────
# Derived features
# ─────────────────────────────────────────────

def create_derived_features(
    data: dict[str, Any],
) -> dict[str, float]:
    """
    Creates additional features derived from the
    original sample measurements.

    These features can improve the ML model by
    representing relationships between variables.
    """

    features = extract_features(data)

    temperature = features["temperature"]
    transport_minutes = features["transport_minutes"]
    processing_minutes = features["processing_minutes"]
    storage_minutes = features["storage_minutes"]

    total_time = (
        transport_minutes
        + processing_minutes
        + storage_minutes
    )

    temperature_deviation = 0.0

    if temperature < 2:
        temperature_deviation = 2 - temperature
    elif temperature > 8:
        temperature_deviation = temperature - 8

    return {
        "total_time_minutes": total_time,
        "temperature_deviation": temperature_deviation,
        "transport_processing_ratio": (
            transport_minutes / processing_minutes
            if processing_minutes > 0
            else 0.0
        ),
        "delayed_processing": (
            1.0
            if processing_minutes > 60
            else 0.0
        ),
        "temperature_anomaly": (
            1.0
            if temperature < 2 or temperature > 8
            else 0.0
        ),
    }


# ─────────────────────────────────────────────
# Complete feature vector
# ─────────────────────────────────────────────

def build_feature_vector(
    data: dict[str, Any],
    include_derived: bool = False,
) -> np.ndarray:
    """
    Builds the final feature vector for Machine Learning.

    Parameters
    ----------
    data:
        Sample information.

    include_derived:
        If True, derived features are appended to the
        base feature vector.

    Returns
    -------
    np.ndarray
        Feature matrix ready for a ML model.
    """

    base_features = extract_features(data)

    values = [
        base_features[name]
        for name in FEATURE_NAMES
    ]

    if include_derived:
        derived = create_derived_features(data)

        values.extend(
            derived.values()
        )

    return np.array(
        [values],
        dtype=float,
    )


# ─────────────────────────────────────────────
# Feature metadata
# ─────────────────────────────────────────────

def get_feature_names(
    include_derived: bool = False,
) -> list[str]:
    """
    Returns the ordered feature names used by
    the Machine Learning model.
    """

    names = FEATURE_NAMES.copy()

    if include_derived:
        names.extend(
            [
                "total_time_minutes",
                "temperature_deviation",
                "transport_processing_ratio",
                "delayed_processing",
                "temperature_anomaly",
            ]
        )

    return names
```
