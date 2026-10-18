from dataclasses import dataclass, field
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class RiskSettings:
    """
    Configuración del motor de riesgo.

    Los umbrales de tiempo son valores iniciales de demostración.
    Los límites de plausibilidad de temperatura sirven para detectar
    lecturas sospechosas; NO son límites clínicos universales.

    Ajustar los valores según los sensores y protocolos del laboratorio.
    """

    # Plausibilidad de la lectura del sensor, en grados Celsius.
    temperature_sanity_min_c: float = -80.0
    temperature_sanity_max_c: float = 100.0

    # Tiempo de transporte, en minutos.
    transport_warning_minutes: float = 60.0
    transport_critical_minutes: float = 120.0

    # Tiempo de procesamiento, en minutos.
    processing_warning_minutes: float = 60.0
    processing_critical_minutes: float = 120.0

    # Tiempo de almacenamiento, en minutos.
    storage_warning_minutes: float = 240.0
    storage_critical_minutes: float = 480.0


@dataclass
class RiskFinding:
    code: str
    factor: str
    message: str
    points: int


@dataclass
class RiskAssessment:
    score: int
    level: str
    anomaly_detected: bool
    explanation: str
    findings: list[RiskFinding] = field(default_factory=list)
    assessment_status: str = "ASSESSED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.score,
            "risk_level": self.level,
            "anomaly_detected": self.anomaly_detected,
            "risk_explanation": self.explanation,
            "assessment_status": self.assessment_status,
            "findings": [
                {
                    "code": finding.code,
                    "factor": finding.factor,
                    "message": finding.message,
                    "points": finding.points,
                }
                for finding in self.findings
            ],
        }


class RiskEngine:
    """
    Motor de evaluación de riesgos basado en reglas explícitas.

    Distingue entre:
    - Desviaciones operativas que suman puntos de riesgo.
    - Problemas de calidad de datos que requieren revisión.
    - Ausencia de información.

    No sustituye los protocolos clínicos ni un modelo de ML validado.
    """

    def __init__(self, settings: RiskSettings | None = None):
        self.settings = settings or RiskSettings()

    @staticmethod
    def _number(value: Any) -> float | None:
        """
        Convierte un valor a float si es numérico y finito.
        Rechaza None, booleanos, NaN e infinitos.
        """
        if value is None or isinstance(value, bool):
            return None

        try:
            result = float(value)
        except (TypeError, ValueError):
            return None

        if not isfinite(result):
            return None

        return result

    def evaluate(self, sample: Any) -> RiskAssessment:
        findings: list[RiskFinding] = []

        def add(
            code: str,
            factor: str,
            message: str,
            points: int,
        ) -> None:
            findings.append(
                RiskFinding(
                    code=code,
                    factor=factor,
                    message=message,
                    points=points,
                )
            )

        data_quality_issue = False

        # ---------------------------------------------------------
        # 1. Temperatura
        # ---------------------------------------------------------
        raw_temperature = getattr(
            sample,
            "current_temperature",
            None,
        )

        temperature = self._number(raw_temperature)

        minimum = self._number(
            getattr(sample, "minimum_temperature", None)
        )

        maximum = self._number(
            getattr(sample, "maximum_temperature", None)
        )

        if raw_temperature is not None and temperature is None:
            data_quality_issue = True

            add(
                "INVALID_TEMPERATURE_READING",
                "data_quality",
                (
                    "La temperatura registrada no es válida: "
                    "debe ser un número finito."
                ),
                0,
            )

        elif temperature is None:
            data_quality_issue = True

            add(
                "TEMPERATURE_NOT_RECORDED",
                "data_quality",
                (
                    "No hay una temperatura actual válida registrada. "
                    "Se requiere revisar la información."
                ),
                0,
            )

        else:
            # Primero comprobar si la lectura es plausible para el sensor.
            sanity_min = self.settings.temperature_sanity_min_c
            sanity_max = self.settings.temperature_sanity_max_c

            if temperature < sanity_min or temperature > sanity_max:
                data_quality_issue = True

                add(
                    "TEMPERATURE_MEASUREMENT_IMPLAUSIBLE",
                    "data_quality",
                    (
                        f"La lectura de temperatura ({temperature:g} °C) "
                        f"está fuera del intervalo de plausibilidad "
                        f"configurado ({sanity_min:g} a "
                        f"{sanity_max:g} °C). Verifica el sensor, "
                        "las unidades y el dato registrado. "
                        "Esto no confirma por sí solo que la muestra "
                        "esté dañada."
                    ),
                    0,
                )

            else:
                # Solo evaluar los límites específicos de la muestra
                # cuando la lectura supera la comprobación de plausibilidad.
                if minimum is not None and maximum is not None:
                    if minimum > maximum:
                        data_quality_issue = True

                        add(
                            "INVALID_TEMPERATURE_LIMITS",
                            "data_quality",
                            (
                                "Los límites mínimo y máximo de "
                                "temperatura están invertidos. "
                                "Revisa la configuración de la muestra."
                            ),
                            0,
                        )

                    elif temperature < minimum or temperature > maximum:
                        add(
                            "TEMPERATURE_OUT_OF_RANGE",
                            "temperature",
                            (
                                f"Temperatura {temperature:g} °C fuera "
                                f"del rango configurado para la muestra "
                                f"({minimum:g} a {maximum:g} °C)."
                            ),
                            40,
                        )

                elif minimum is not None and temperature < minimum:
                    add(
                        "TEMPERATURE_BELOW_MINIMUM",
                        "temperature",
                        (
                            f"La temperatura ({temperature:g} °C) "
                            f"está por debajo del mínimo configurado "
                            f"({minimum:g} °C)."
                        ),
                        40,
                    )

                elif maximum is not None and temperature > maximum:
                    add(
                        "TEMPERATURE_ABOVE_MAXIMUM",
                        "temperature",
                        (
                            f"La temperatura ({temperature:g} °C) "
                            f"supera el máximo configurado "
                            f"({maximum:g} °C)."
                        ),
                        40,
                    )

        # ---------------------------------------------------------
        # 2. Tiempo de transporte
        # ---------------------------------------------------------
        transport = self._number(
            getattr(sample, "transport_minutes", None)
        )

        if transport is not None:
            if transport < 0:
                data_quality_issue = True

                add(
                    "INVALID_TRANSPORT_DURATION",
                    "data_quality",
                    "El tiempo de transporte no puede ser negativo.",
                    0,
                )

            elif transport >= self.settings.transport_critical_minutes:
                add(
                    "TRANSPORT_TIME_CRITICAL",
                    "transport",
                    f"Transporte prolongado: {transport:g} minutos.",
                    35,
                )

            elif transport >= self.settings.transport_warning_minutes:
                add(
                    "TRANSPORT_TIME_WARNING",
                    "transport",
                    f"Tiempo de transporte elevado: {transport:g} minutos.",
                    20,
                )

        # ---------------------------------------------------------
        # 3. Tiempo de procesamiento
        # ---------------------------------------------------------
        processing = self._number(
            getattr(sample, "processing_minutes", None)
        )

        if processing is not None:
            if processing < 0:
                data_quality_issue = True

                add(
                    "INVALID_PROCESSING_DURATION",
                    "data_quality",
                    "El tiempo de procesamiento no puede ser negativo.",
                    0,
                )

            elif processing >= self.settings.processing_critical_minutes:
                add(
                    "PROCESSING_TIME_CRITICAL",
                    "processing",
                    f"Procesamiento prolongado: {processing:g} minutos.",
                    35,
                )

            elif processing >= self.settings.processing_warning_minutes:
                add(
                    "PROCESSING_TIME_WARNING",
                    "processing",
                    f"Tiempo de procesamiento elevado: {processing:g} minutos.",
                    20,
                )

        # ---------------------------------------------------------
        # 4. Tiempo de almacenamiento
        # ---------------------------------------------------------
        storage = self._number(
            getattr(sample, "storage_minutes", None)
        )

        if storage is not None:
            if storage < 0:
                data_quality_issue = True

                add(
                    "INVALID_STORAGE_DURATION",
                    "data_quality",
                    "El tiempo de almacenamiento no puede ser negativo.",
                    0,
                )

            elif storage >= self.settings.storage_critical_minutes:
                add(
                    "STORAGE_TIME_CRITICAL",
                    "storage",
                    f"Almacenamiento prolongado: {storage:g} minutos.",
                    35,
                )

            elif storage >= self.settings.storage_warning_minutes:
                add(
                    "STORAGE_TIME_WARNING",
                    "storage",
                    f"Tiempo de almacenamiento elevado: {storage:g} minutos.",
                    20,
                )

        # ---------------------------------------------------------
        # 5. Calcular puntuación
        # ---------------------------------------------------------
        score = min(
            100,
            sum(finding.points for finding in findings),
        )

        if score >= 75:
            level = "CRITICAL"
        elif score >= 50:
            level = "HIGH"
        elif score >= 20:
            level = "MEDIUM"
        else:
            level = "LOW"

        # Una lectura inválida puede requerir revisión aunque no sume
        # puntos al riesgo de la muestra.
        anomaly_detected = (
            data_quality_issue
            or any(finding.points > 0 for finding in findings)
        )

        if data_quality_issue:
            assessment_status = "REVIEW_REQUIRED"

        else:
            assessment_status = "ASSESSED"

        if findings:
            explanation = " ".join(
                finding.message for finding in findings
            )
        else:
            explanation = (
                "No se detectaron desviaciones con las reglas "
                "disponibles. Esto no garantiza que la muestra "
                "sea clínicamente segura."
            )

        if data_quality_issue:
            explanation += (
                " La calidad de uno o más datos requiere revisión; "
                "no debe interpretarse esta evaluación como una "
                "confirmación de que la muestra sea segura."
            )

        return RiskAssessment(
            score=score,
            level=level,
            anomaly_detected=anomaly_detected,
            explanation=explanation,
            findings=findings,
            assessment_status=assessment_status,
        )


risk_engine = RiskEngine()