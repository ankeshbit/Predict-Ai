"""
Settings & Admin API Router (PRD §14.8)
Provides system configurations, alert rules, health indicator tuning, reliability parameters, and audit logging.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_engineer
from app.core.db import get_db
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.entities import (
    AlertRule,
    AuditLog,
    HealthIndicatorConfig,
    Setting,
    User,
)
from app.schemas.health_config import HealthConfigResponse, HealthConfigUpdateRequest
from app.schemas.settings import (
    AlertRuleResponse,
    AlertRuleUpdateRequest,
    AuditLogListResponse,
    AuditLogResponse,
    ReliabilityConfigResponse,
    RiskBandsConfig,
)

settings_router = APIRouter(prefix="/settings", tags=["Settings"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# --- Health Indicator Settings ---

@settings_router.get("/health-indicator", response_model=HealthConfigResponse)
def get_health_indicator_config(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves the active Machine Health Indicator configuration (PRD §14.8)."""
    cfg = db.scalar(
        select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True))
    )
    if not cfg:
        raise NotFoundError(message="Active health indicator configuration not found.")
    return HealthConfigResponse.model_validate(cfg)


@settings_router.put("/health-indicator", response_model=HealthConfigResponse)
def update_health_indicator_config(
    payload: HealthConfigUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates Machine Health Indicator parameters (Admin only)."""
    cfg = db.scalar(
        select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True))
    )
    if not cfg:
        raise NotFoundError(message="Active health indicator configuration not found.")

    if payload.anomaly_weight is not None:
        if not (0.0 <= payload.anomaly_weight <= 1.0):
            raise ValidationError(message="anomaly_weight must be between 0.0 and 1.0")
        cfg.anomaly_weight = payload.anomaly_weight

    if payload.data_quality_penalty is not None:
        cfg.data_quality_penalty = payload.data_quality_penalty
    if payload.trend_enabled is not None:
        cfg.trend_enabled = payload.trend_enabled

    db.commit()
    db.refresh(cfg)
    return HealthConfigResponse.model_validate(cfg)


# --- Risk Bands Settings ---

@settings_router.get("/risk-bands", response_model=RiskBandsConfig)
def get_risk_bands(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves failure risk band thresholds (PRD §14.8)."""
    setting = db.scalar(select(Setting).where(Setting.key == "risk_bands"))
    if setting and setting.value:
        return RiskBandsConfig(**setting.value)
    return RiskBandsConfig(low_max=0.10, medium_max=0.50, high_max=0.80)


@settings_router.put("/risk-bands", response_model=RiskBandsConfig)
def update_risk_bands(
    payload: RiskBandsConfig,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates failure risk band thresholds (Admin only)."""
    if not (0.0 < payload.low_max < payload.medium_max < payload.high_max <= 1.0):
        raise ValidationError(message="Risk bands must satisfy 0 < low_max < medium_max < high_max <= 1.0")

    setting = db.scalar(select(Setting).where(Setting.key == "risk_bands"))
    if not setting:
        setting = Setting(key="risk_bands", value=payload.model_dump(), description="Failure risk thresholds")
        db.add(setting)
    else:
        setting.value = payload.model_dump()
        setting.updated_at = datetime.now(timezone.utc)

    db.commit()
    return payload


# --- Alert Rules Settings ---

@settings_router.get("/alert-rules", response_model=List[AlertRuleResponse])
def get_alert_rules(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves all alert rules and threshold criteria (PRD §14.8)."""
    rules = db.scalars(select(AlertRule).order_by(AlertRule.rule_id)).all()
    if not rules:
        defaults = [
            AlertRule(
                id=uuid.uuid4(),
                rule_id="RULE_HIGH_FAILURE_RISK",
                alert_type="high_failure_risk",
                failure_probability_threshold=0.50,
                anomaly_severity_threshold="critical",
                consecutive_cycles=3,
                is_active=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                rule_id="RULE_SEVERE_ANOMALY",
                alert_type="severe_anomaly",
                failure_probability_threshold=0.50,
                anomaly_severity_threshold="warning",
                consecutive_cycles=2,
                is_active=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                rule_id="RULE_RAPID_DETERIORATION",
                alert_type="rapid_deterioration",
                failure_probability_threshold=0.60,
                anomaly_severity_threshold="critical",
                consecutive_cycles=3,
                is_active=True,
            ),
        ]
        db.add_all(defaults)
        db.commit()
        rules = defaults
    return [AlertRuleResponse.model_validate(r) for r in rules]


@settings_router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: str,
    payload: AlertRuleUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates an alert rule's thresholds or status (Admin only)."""
    rule = db.scalar(select(AlertRule).where(AlertRule.rule_id == rule_id))
    if not rule:
        raise NotFoundError(message=f"Alert rule {rule_id} not found")

    if payload.failure_probability_threshold is not None:
        rule.failure_probability_threshold = payload.failure_probability_threshold
    if payload.anomaly_severity_threshold is not None:
        rule.anomaly_severity_threshold = payload.anomaly_severity_threshold
    if payload.consecutive_cycles is not None:
        rule.consecutive_cycles = payload.consecutive_cycles
    if payload.is_active is not None:
        rule.is_active = payload.is_active

    db.commit()
    db.refresh(rule)
    return AlertRuleResponse.model_validate(rule)


# --- Reliability & Recommendation Rules (Read-Only) ---

@settings_router.get("/reliability", response_model=ReliabilityConfigResponse)
def get_reliability_config(
    current_user: User = Depends(get_current_engineer),
):
    """Retrieves data reliability check criteria (PRD §14.8, FR-15)."""
    return ReliabilityConfigResponse(
        max_missing_fraction=0.10,
        max_out_of_range_fraction=0.05,
        max_z_shift=4.0,
        min_window_length=30,
        description="PRD FR-15 Data Quality & Prediction Reliability Rules",
    )


@settings_router.get("/recommendation-rules")
def get_recommendation_rules(
    current_user: User = Depends(get_current_engineer),
):
    """Retrieves read-only AI recommendation mapping rules (PRD §14.8, FR-12)."""
    return {
        "version": "1.0.0",
        "domain": "NASA C-MAPSS FD001 (Simulated Turbofan Engine)",
        "disclaimer": "AI-generated recommendation, not a confirmed diagnosis. Verify with a qualified engineer.",
        "rules": [
            {
                "rule_id": "RULE_CRITICAL_RISK",
                "condition": "failure_probability >= 0.70",
                "category": "Immediate Inspection",
                "action": "Schedule an immediate visual and borescope inspection of this unit. Review flagged sensors.",
            },
            {
                "rule_id": "RULE_WARNING_ANOMALY",
                "condition": "anomaly_flag == True or anomaly_score >= 0.70",
                "category": "Increased Monitoring",
                "action": "Increase monitoring frequency and review recent operating conditions.",
            },
            {
                "rule_id": "RULE_NOMINAL",
                "condition": "failure_probability < 0.20 and anomaly_score < 0.50",
                "category": "Standard Operation",
                "action": "Continue standard operational schedule.",
            },
        ],
    }


# --- Admin Endpoints ---

@admin_router.get("/audit-log", response_model=AuditLogListResponse)
def get_audit_log(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None, description="Filter by action"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieves audit logs (Admin only, PRD §14.8)."""
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)).all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(a) for a in items],
        total=total,
    )


@admin_router.post("/demo/reset", status_code=202)
def admin_demo_reset(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Alias for demo reset under /admin/demo/reset (PRD §14.8)."""
    from app.api.v1.demo import reset_demo_fleet
    return reset_demo_fleet(current_user=current_user, db=db)
