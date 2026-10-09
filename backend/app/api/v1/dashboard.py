"""
Fleet Dashboard API Router.
PRD §14.7: Fleet summary, priority at-risk machines, recent anomalies, alerts, and risk distribution.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_engineer
from app.core.db import get_db
from app.models.entities import Alert, Anomaly, Machine, Prediction, User
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    PriorityMachineItem,
    ProbabilityDistributionBin,
    ProbabilityDistributionResponse,
    RecentAlertItem,
    RecentAnomalyItem,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Returns top-level fleet KPI summary."""
    total_machines = db.scalar(select(func.count(Machine.id))) or 0
    healthy_count = db.scalar(
        select(func.count(Machine.id)).where(Machine.health_band.in_(["Healthy", "Excellent"]))
    ) or 0
    warning_count = db.scalar(
        select(func.count(Machine.id)).where(Machine.health_band.in_(["Warning", "Poor"]))
    ) or 0
    critical_count = db.scalar(
        select(func.count(Machine.id)).where(Machine.health_band == "Critical")
    ) or 0
    avg_hi = db.scalar(select(func.avg(Machine.health_indicator))) or 0.0
    open_alerts = db.scalar(
        select(func.count(Alert.id)).where(Alert.status == "open")
    ) or 0
    active_count = db.scalar(
        select(func.count(Machine.id)).where(Machine.operational_status == "active")
    ) or 0
    maintenance_count = db.scalar(
        select(func.count(Machine.id)).where(Machine.operational_status == "maintenance")
    ) or 0

    # Health band counts for distribution chart
    all_bands = ["Excellent", "Healthy", "Warning", "Poor", "Critical"]
    health_band_counts = {}
    for band in all_bands:
        health_band_counts[band] = db.scalar(
            select(func.count(Machine.id)).where(Machine.health_band == band)
        ) or 0

    operational_counts = {
        "active": active_count,
        "maintenance": maintenance_count,
        "archived": db.scalar(
            select(func.count(Machine.id)).where(Machine.operational_status == "archived")
        ) or 0,
    }

    return DashboardSummaryResponse(
        total_machines=total_machines,
        healthy_count=healthy_count,
        warning_count=warning_count,
        critical_count=critical_count,
        average_health_indicator=round(float(avg_hi), 1),
        open_alerts_count=open_alerts,
        dataset_banner_text="Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data",
        dataset_badge_text="Demo / Simulated Data",
        health_band_counts=health_band_counts,
        operational_counts=operational_counts,
        active_count=active_count,
        maintenance_count=maintenance_count,
        server_time=datetime.now(timezone.utc),
    )


@router.get("/priority-machines", response_model=List[PriorityMachineItem])
def get_priority_machines(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Returns highest risk machines ranked by failure probability with horizon."""
    # Subquery for latest prediction per machine
    latest_pred_subq = (
        select(
            Prediction.machine_id,
            func.max(Prediction.cycle).label("max_cycle"),
        )
        .group_by(Prediction.machine_id)
        .subquery()
    )

    stmt = (
        select(Machine, Prediction)
        .join(latest_pred_subq, Machine.id == latest_pred_subq.c.machine_id)
        .join(
            Prediction,
            (Prediction.machine_id == latest_pred_subq.c.machine_id)
            & (Prediction.cycle == latest_pred_subq.c.max_cycle),
        )
        .order_by(Prediction.failure_probability.desc(), Machine.health_indicator.asc())
        .limit(limit)
    )

    results = db.execute(stmt).all()
    items = []
    for machine, pred in results:
        items.append(
            PriorityMachineItem(
                id=machine.id,
                machine_code=machine.machine_code,
                operational_status=machine.operational_status,
                health_indicator=machine.health_indicator,
                health_band=machine.health_band,
                failure_probability=pred.failure_probability,
                horizon=pred.horizon,
                horizon_unit=pred.horizon_unit,
                risk_level=pred.risk_level,
                as_of_cycle=pred.cycle,
            )
        )
    return items


@router.get("/recent-anomalies", response_model=List[RecentAnomalyItem])
def get_recent_anomalies(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Returns recent anomaly occurrences across the fleet."""
    stmt = (
        select(Anomaly, Machine.machine_code)
        .join(Machine, Anomaly.machine_id == Machine.id)
        .order_by(Anomaly.detected_at.desc())
        .limit(limit)
    )
    results = db.execute(stmt).all()
    return [
        RecentAnomalyItem(
            id=anom.id,
            machine_id=anom.machine_id,
            machine_code=code,
            cycle=anom.cycle,
            severity=anom.severity,
            anomaly_score=anom.anomaly_score,
            is_anomaly=anom.is_anomaly,
            detected_at=anom.detected_at,
        )
        for anom, code in results
    ]


@router.get("/recent-alerts", response_model=List[RecentAlertItem])
def get_recent_alerts(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Returns latest alerts across the fleet."""
    stmt = (
        select(Alert, Machine.machine_code)
        .join(Machine, Alert.machine_id == Machine.id)
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    results = db.execute(stmt).all()
    return [
        RecentAlertItem(
            id=alert.id,
            machine_id=alert.machine_id,
            machine_code=code,
            alert_type=alert.alert_type,
            status=alert.status,
            severity=alert.severity,
            trigger_cycle=alert.trigger_cycle,
            trigger_score=alert.trigger_score,
            recommendation_text=alert.recommendation_text,
            created_at=alert.created_at,
        )
        for alert, code in results
    ]


@router.get("/probability-distribution", response_model=ProbabilityDistributionResponse)
def get_probability_distribution(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Returns histogram bins of failure probabilities across latest machine predictions."""
    latest_pred_subq = (
        select(
            Prediction.machine_id,
            func.max(Prediction.cycle).label("max_cycle"),
        )
        .group_by(Prediction.machine_id)
        .subquery()
    )

    stmt = (
        select(Prediction.failure_probability)
        .join(
            latest_pred_subq,
            (Prediction.machine_id == latest_pred_subq.c.machine_id)
            & (Prediction.cycle == latest_pred_subq.c.max_cycle),
        )
    )
    probs = [row[0] for row in db.execute(stmt).all()]

    bins = [
        {"bin_range": "0.0 - 0.2 (Low)", "min_prob": 0.0, "max_prob": 0.2, "count": 0},
        {"bin_range": "0.2 - 0.4 (Moderate)", "min_prob": 0.2, "max_prob": 0.4, "count": 0},
        {"bin_range": "0.4 - 0.6 (Medium)", "min_prob": 0.4, "max_prob": 0.6, "count": 0},
        {"bin_range": "0.6 - 0.8 (High)", "min_prob": 0.6, "max_prob": 0.8, "count": 0},
        {"bin_range": "0.8 - 1.0 (Critical)", "min_prob": 0.8, "max_prob": 1.0, "count": 0},
    ]

    for p in probs:
        val = float(p)
        if val < 0.2:
            bins[0]["count"] += 1
        elif val < 0.4:
            bins[1]["count"] += 1
        elif val < 0.6:
            bins[2]["count"] += 1
        elif val < 0.8:
            bins[3]["count"] += 1
        else:
            bins[4]["count"] += 1

    return ProbabilityDistributionResponse(
        bins=[ProbabilityDistributionBin(**b) for b in bins],
        total_scored_machines=len(probs),
    )
