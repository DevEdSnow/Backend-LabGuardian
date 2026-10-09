
"""
Dashboard schemas for LabGuardian AI.

Defines Pydantic schemas for laboratory statistics,
sample risk distribution, equipment monitoring and
recent alerts displayed on the dashboard.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────
# Base response
# ─────────────────────────────────────────────

class DashboardBaseResponse(BaseModel):
    """Base schema for dashboard API responses."""

    success: bool = True


# ─────────────────────────────────────────────
# Sample statistics
# ─────────────────────────────────────────────

class SampleStatistics(BaseModel):
    """Summary of clinical sample statistics."""

    total: int = Field(default=0, ge=0)
    received: int = Field(default=0, ge=0)
    processing: int = Field(default=0, ge=0)
    processed: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)


# ─────────────────────────────────────────────
# Risk statistics
# ─────────────────────────────────────────────

class RiskStatistics(BaseModel):
    """Distribution of samples by risk level."""

    low: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    high: int = Field(default=0, ge=0)
    critical: int = Field(default=0, ge=0)

    average_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
    )


class RiskPercentages(BaseModel):
    """Percentage distribution of sample risk levels."""

    low: float = Field(default=0.0, ge=0, le=100)
    medium: float = Field(default=0.0, ge=0, le=100)
    high: float = Field(default=0.0, ge=0, le=100)
    critical: float = Field(default=0.0, ge=0, le=100)


class RiskDistributionResponse(DashboardBaseResponse):
    """Risk counts and percentages."""

    total_samples: int = Field(default=0, ge=0)
    counts: RiskStatistics
    percentages: RiskPercentages


# ─────────────────────────────────────────────
# Alert statistics
# ─────────────────────────────────────────────

class AlertStatistics(BaseModel):
    """Summary of laboratory alerts."""

    total: int = Field(default=0, ge=0)
    active: int = Field(default=0, ge=0)
    acknowledged: int = Field(default=0, ge=0)
    resolved: int = Field(default=0, ge=0)
    critical: int = Field(default=0, ge=0)


# ─────────────────────────────────────────────
# Equipment statistics
# ─────────────────────────────────────────────

class EquipmentStatistics(BaseModel):
    """Summary of laboratory equipment status."""

    total: int = Field(default=0, ge=0)
    operational: int = Field(default=0, ge=0)
    maintenance: int = Field(default=0, ge=0)
    offline: int = Field(default=0, ge=0)
    with_anomalies: int = Field(default=0, ge=0)


# ─────────────────────────────────────────────
# Laboratory area statistics
# ─────────────────────────────────────────────

class AreaStatistics(BaseModel):
    """Statistics for an individual laboratory area."""

    name: str = Field(min_length=1, max_length=100)
    total_samples: int = Field(default=0, ge=0)
    high_risk_samples: int = Field(default=0, ge=0)
    risk_percentage: float = Field(
        default=0.0,
        ge=0,
        le=100,
    )


class AreaStatisticsResponse(DashboardBaseResponse):
    """Statistics grouped by laboratory area."""

    areas: list[AreaStatistics] = Field(default_factory=list)


# ─────────────────────────────────────────────
# Recent alert item
# ─────────────────────────────────────────────

class RecentAlert(BaseModel):
    """Compact alert information for dashboard widgets."""

    id: int
    sample_code: str | None = None
    alert_type: str
    title: str
    message: str
    severity: str
    status: str
    risk_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    created_at: datetime | None = None


class RecentAlertsResponse(DashboardBaseResponse):
    """Recent alerts displayed on the dashboard."""

    total: int = Field(default=0, ge=0)
    alerts: list[RecentAlert] = Field(default_factory=list)


# ─────────────────────────────────────────────
# Equipment monitoring item
# ─────────────────────────────────────────────

class EquipmentMonitoringItem(BaseModel):
    """Compact monitoring information for one device."""

    id: int
    code: str
    name: str
    equipment_type: str
    area: str
    status: str
    current_temperature: float | None = None
    anomaly_detected: bool = False
    last_seen_at: datetime | None = None


class EquipmentMonitoringResponse(DashboardBaseResponse):
    """Equipment monitoring summary for the dashboard."""

    total: int = Field(default=0, ge=0)
    equipment: list[EquipmentMonitoringItem] = Field(
        default_factory=list
    )


# ─────────────────────────────────────────────
# Complete dashboard summary
# ─────────────────────────────────────────────

class DashboardSummary(BaseModel):
    """Combined summary of laboratory activity."""

    samples: SampleStatistics = Field(
        default_factory=SampleStatistics
    )

    risks: RiskStatistics = Field(
        default_factory=RiskStatistics
    )

    alerts: AlertStatistics = Field(
        default_factory=AlertStatistics
    )

    equipment: EquipmentStatistics = Field(
        default_factory=EquipmentStatistics
    )

    last_updated: datetime | None = None


class DashboardSummaryResponse(DashboardBaseResponse):
    """Complete dashboard summary response."""

    summary: DashboardSummary


# ─────────────────────────────────────────────
# Full dashboard response
# ─────────────────────────────────────────────

class DashboardResponse(DashboardBaseResponse):
    """Aggregated data for the main dashboard."""

    summary: DashboardSummary
    areas: list[AreaStatistics] = Field(default_factory=list)
    recent_alerts: list[RecentAlert] = Field(
        default_factory=list
    )
    equipment_monitoring: list[EquipmentMonitoringItem] = Field(
        default_factory=list
    )


# ─────────────────────────────────────────────
# Dashboard query filters
# ─────────────────────────────────────────────

class DashboardFilters(BaseModel):
    """Optional filters for dashboard queries."""

    laboratory_area: str | None = Field(
        default=None,
        max_length=100,
    )

    risk_level: str | None = Field(
        default=None,
        max_length=20,
    )

    start_date: datetime | None = None
    end_date: datetime | None = None

    model_config = ConfigDict(extra="forbid")

