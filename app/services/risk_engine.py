
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RiskSettings:
    """
    Umbrales operativos configurables.

    Los tiempos son valores iniciales de demostración, no límites
    clínicos universales. Deben ajustarse al protocolo del laboratorio.
    """
    transport_warning_minutes: float = 60.0
    transport_critical_minutes: float = 120.0

    processing_warning_minutes: float = 60.0
    processing_critical_minutes: float = 120.0

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.score,
            "risk_level": self.level,
            "anomaly_detected": self.anomaly_detected,
            "risk_explanation": self.explanation,
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
    Motor inicial basado en reglas explícitas.

    No sustituye los protocolos clínicos ni un modelo ML validado.
    La temperatura solo se evalúa cuando existen límites configurados
    para esa muestra.
    """

    def __init__(self, settings: RiskSettings | None = None):
        self.settings = settings or RiskSettings()

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None

        try:
            result = float(value)
        except (TypeError, ValueError):
            return None

        # Rechazar NaN e infinitos.
        if result != result or result in (float("inf"), float("-inf")):
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

        # 1. Temperatura: únicamente contra límites de la muestra.
        temperature = self._number(
            getattr(sample, "current_temperature", None)
        )
        minimum = self._number(
            getattr(sample, "minimum_temperature", None)
        )
        maximum = self._number(
            getattr(sample, "maximum_temperature", None)
        )

        if temperature is not None:
            if minimum is not None and maximum is not None:
                if minimum > maximum:
                    add(
                        "INVALID_TEMPERATURE_LIMITS",
                        "temperature",
                        "Los límites mínimo y máximo están invertidos.",
                        30,
                    )
                elif temperature < minimum or temperature > maximum:
                    add(
                        "TEMPERATURE_OUT_OF_RANGE",
                        "temperature",
                        (
                            f"Temperatura {temperature:g} fuera del rango "
                            f"configurado ({minimum:g} a {maximum:g})."
                        ),
                        40,
                    )
            elif minimum is not None and temperature < minimum:
                add(
                    "TEMPERATURE_BELOW_MINIMUM",
                    "temperature",
                    f"Temperatura inferior al mínimo configurado ({minimum:g}).",
                    40,
                )
            elif maximum is not None and temperature > maximum:
                add(
                    "TEMPERATURE_ABOVE_MAXIMUM",
                    "temperature",
                    f"Temperatura superior al máximo configurado ({maximum:g}).",
                    40,
                )

        # 2. Tiempo de transporte.
        transport = self._number(
            getattr(sample, "transport_minutes", None)
        )

        if transport is not None:
            if transport < 0:
                add(
                    "INVALID_TRANSPORT_DURATION",
                    "transport",
                    "El tiempo de transporte no puede ser negativo.",
                    30,
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

        # 3. Tiempo de procesamiento.
        processing = self._number(
            getattr(sample, "processing_minutes", None)
        )

        if processing is not None:
            if processing < 0:
                add(
                    "INVALID_PROCESSING_DURATION",
                    "processing",
                    "El tiempo de procesamiento no puede ser negativo.",
                    30,
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

        # 4. Tiempo de almacenamiento.
        storage = self._number(
            getattr(sample, "storage_minutes", None)
        )

        if storage is not None:
            if storage < 0:
                add(
                    "INVALID_STORAGE_DURATION",
                    "storage",
                    "El tiempo de almacenamiento no puede ser negativo.",
                    30,
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

        # 5. Datos incompletos: se informa, pero no se inventan valores.
        if temperature is None:
            add(
                "TEMPERATURE_NOT_RECORDED",
                "data_quality",
                "No hay una temperatura actual válida registrada.",
                0,
            )

        if not findings:
            score = 0
            level = "LOW"
            explanation = (
                "No se detectaron desviaciones con las reglas disponibles. "
                "Esto no garantiza que la muestra sea clínicamente segura."
            )
        else:
            score = min(100, sum(item.points for item in findings))

            if score >= 75:
                level = "CRITICAL"
            elif score >= 50:
                level = "HIGH"
            elif score >= 20:
                level = "MEDIUM"
            else:
                level = "LOW"

            explanation = " ".join(item.message for item in findings)

        return RiskAssessment(
            score=score,
            level=level,
            anomaly_detected=any(
                item.points > 0 for item in findings
            ),
            explanation=explanation,
            findings=findings,
        )


risk_engine = RiskEngine()
