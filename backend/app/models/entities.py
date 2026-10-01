"""
SQLAlchemy 2.0 ORM Models for Predict-Ai (PrediCore)
Implements all 16 tables from PRD §13 with full check constraints and partial unique indexes.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


# Ensure SQLite compatibility for test environments
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> uuid.UUID:
    return uuid.uuid4()


# 1. Users
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="engineer", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'engineer')", name="check_user_role"),
    )


# 2. Datasets
class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    # Original filename from uploader, kept for display
    filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Secure staging filename (UUID-based, written by upload service)
    staging_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unit_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Auto-detected column mapping from adapter (canonical -> raw)
    schema_mapping: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    schema_mapping_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    data_origin: Mapped[str] = mapped_column(String(64), default="simulated", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(64), default="cmapss_fd001", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'validating', 'validated', 'compatible', 'rejected_incompatible', 'ingesting', 'ingested', 'failed')",
            name="check_dataset_status",
        ),
    )

    compatibility_checks = relationship("DatasetCompatibilityCheck", back_populates="dataset", cascade="all, delete-orphan")


# 3. Dataset Compatibility Checks (one row per check run with JSONB report)
class DatasetCompatibilityCheck(Base):
    __tablename__ = "dataset_compatibility_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 'passed' | 'failed' | 'warning'
    report: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('passed', 'failed', 'warning')", name="check_compatibility_status"),
    )

    dataset = relationship("Dataset", back_populates="compatibility_checks")


# 4. Machines
class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    machine_code: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    operational_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    health_indicator: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    health_band: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    demo_cluster: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("operational_status IN ('active', 'maintenance', 'archived')", name="check_machine_status"),
    )

    readings = relationship("SensorReading", back_populates="machine", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="machine", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="machine", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceRecord", back_populates="machine", cascade="all, delete-orphan")


# 5. Sensor Readings
class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    cycle_index: Mapped[int] = mapped_column("cycle_index", Integer, nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    @hybrid_property
    def cycle(self) -> int:
        return self.cycle_index

    @cycle.setter
    def cycle(self, val: int) -> None:
        self.cycle_index = val

    op_setting_1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    op_setting_2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    op_setting_3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 21 FD001 sensor channels
    sensor_1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_4: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_5: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_6: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_7: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_8: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_9: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_10: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_11: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_12: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_13: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_14: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_15: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_16: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_17: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_18: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_19: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_20: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensor_21: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    imputed_fields: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    machine = relationship("Machine", back_populates="readings")

    __table_args__ = (
        Index("uq_machine_dataset_cycle", "machine_id", "dataset_id", "cycle_index", unique=True),
    )


# 6. Model Versions
class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    bundle_version: Mapped[str] = mapped_column(String(64), nullable=False)
    task: Mapped[str] = mapped_column(String(32), nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(64), default="cmapss_fd001", nullable=False)
    feature_config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_features: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    horizon: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    horizon_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    decision_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_card_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    python_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("task IN ('failure_risk', 'anomaly')", name="check_model_task"),
        CheckConstraint("NOT (is_active = TRUE AND model_card_complete = FALSE)", name="check_model_card_complete_if_active"),
        Index("uq_active_model_per_task", "adapter_key", "task", unique=True, postgresql_where=(is_active == True)),  # noqa: E712
    )

    evaluation = relationship("ModelEvaluation", back_populates="model_version", uselist=False, cascade="all, delete-orphan")


# 7. Model Evaluations
class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    model_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), unique=True, nullable=False)
    task: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confusion_matrix: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    calibration_curve: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    curves: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    feature_importance: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    methodology: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    model_version = relationship("ModelVersion", back_populates="evaluation")


# 8. Health Indicator Configs
class HealthIndicatorConfig(Base):
    __tablename__ = "health_indicator_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    anomaly_weight: Mapped[float] = mapped_column(Float, default=0.30, nullable=False)
    data_quality_penalty: Mapped[Dict[str, float]] = mapped_column(
        JSONB, default=lambda: {"DATA_OK": 0.0, "DATA_WARNING": 10.0}, nullable=False
    )
    trend_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("anomaly_weight >= 0.0 AND anomaly_weight <= 1.0", name="check_anomaly_weight_range"),
        Index("uq_active_health_config", "is_active", unique=True, postgresql_where=(is_active == True)),  # noqa: E712
    )


# 9. Predictions (with complete Lineage)
class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    as_of_index: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Lineage Fields
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_mapping_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_model_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False)
    anomaly_model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True)
    health_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_indicator_configs.id"), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    horizon_unit: Mapped[str] = mapped_column(String(32), default="cycles", nullable=False)

    # Scored Outcomes
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    health_indicator: Mapped[float] = mapped_column(Float, nullable=False)
    health_band: Mapped[str] = mapped_column(String(32), nullable=False)
    penalty_risk: Mapped[float] = mapped_column(Float, nullable=False)
    penalty_anomaly: Mapped[float] = mapped_column(Float, nullable=False)
    penalty_dq: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    penalty_trend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    clipping_adjustment: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    input_window_start: Mapped[int] = mapped_column(Integer, nullable=False)
    input_window_end: Mapped[int] = mapped_column(Integer, nullable=False)
    reliability_flags: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    machine = relationship("Machine", back_populates="predictions")


# 10. Anomalies
class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prediction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=True)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    episode_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    affected_features: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 11. Alerts
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="check_alert_status"),
        CheckConstraint("severity IN ('warning', 'critical')", name="check_alert_severity"),
        Index("uq_open_alert_per_type", "machine_id", "alert_type", unique=True, postgresql_where=(status.in_(["open", "acknowledged"]))),
    )

    machine = relationship("Machine", back_populates="alerts")


# 12. Maintenance Records
class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    issue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    decision_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), default="inspection", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", nullable=False)
    outcome: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    engineer_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    performed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    @hybrid_property
    def action_status(self) -> str:
        return self.status

    @action_status.setter
    def action_status(self, val: str) -> None:
        self.status = val

    __table_args__ = (
        CheckConstraint("status IN ('recommended', 'in_progress', 'completed', 'cancelled')", name="check_maintenance_status"),
        CheckConstraint("decision IS NULL OR decision IN ('followed_recommendation', 'modified', 'declined')", name="check_maintenance_decision"),
        CheckConstraint("outcome IS NULL OR outcome IN ('resolved', 'no_issue_found', 'unresolved')", name="check_maintenance_outcome"),
    )

    machine = relationship("Machine", back_populates="maintenance_records")


# 13. Alert Rules
class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    rule_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_probability_threshold: Mapped[float] = mapped_column(Float, default=0.70, nullable=False)
    anomaly_severity_threshold: Mapped[str] = mapped_column(String(32), default="high", nullable=False)
    consecutive_cycles: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# 14. Settings (Key-Value)
class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


# 15. Jobs (DB-backed Async Queue)
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    input_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="check_job_status"),
    )


# 16. Audit Log
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
