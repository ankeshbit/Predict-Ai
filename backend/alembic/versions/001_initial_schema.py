"""Initial schema with 16 PRD tables and seed defaults

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-01 00:00:00.000000
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="engineer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('admin', 'engineer')", name="check_user_role"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # 2. datasets
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(32), nullable=False, server_default="1.0"),
        sa.Column("filename", sa.String(512), nullable=True),
        sa.Column("staging_filename", sa.String(512), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("unit_count", sa.Integer(), nullable=True),
        sa.Column("schema_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("schema_mapping_hash", sa.String(64), nullable=True),
        sa.Column("data_origin", sa.String(64), nullable=False, server_default="simulated"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("adapter_key", sa.String(64), nullable=False, server_default="cmapss_fd001"),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('uploaded', 'valid', 'invalid', 'compatible', 'rejected_incompatible', 'ingesting', 'ingested', 'failed')",
            name="check_dataset_status",
        ),
    )
    op.create_index("ix_datasets_slug", "datasets", ["slug"])

    # 3. dataset_compatibility_checks
    op.create_table(
        "dataset_compatibility_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_number", sa.Integer(), nullable=False),
        sa.Column("check_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("found_value", sa.Text(), nullable=True),
        sa.Column("how_to_fix", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 4. machines
    op.create_table(
        "machines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("machine_code", sa.String(128), unique=True, nullable=False),
        sa.Column("operational_status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("health_indicator", sa.Float(), nullable=True),
        sa.Column("health_band", sa.String(32), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("demo_cluster", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("operational_status IN ('active', 'warning', 'critical', 'maintenance', 'degraded', 'offline')", name="check_machine_status"),
    )
    op.create_index("ix_machines_machine_code", "machines", ["machine_code"])

    # 5. sensor_readings
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("cycle_index", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("op_setting_1", sa.Float(), nullable=True),
        sa.Column("op_setting_2", sa.Float(), nullable=True),
        sa.Column("op_setting_3", sa.Float(), nullable=True),
        *[sa.Column(f"sensor_{i}", sa.Float(), nullable=True) for i in range(1, 22)],
        sa.Column("imputed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_sensor_readings_machine_id", "sensor_readings", ["machine_id"])
    op.create_index("ix_sensor_readings_cycle_index", "sensor_readings", ["cycle_index"])
    op.create_index("uq_machine_dataset_cycle", "sensor_readings", ["machine_id", "dataset_id", "cycle_index"], unique=True)
    op.create_index("uq_machine_cycle", "sensor_readings", ["machine_id", "cycle_index"], unique=True)

    # 6. model_versions
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bundle_version", sa.String(64), nullable=False),
        sa.Column("task", sa.String(32), nullable=False),
        sa.Column("model_type", sa.String(64), nullable=False),
        sa.Column("adapter_key", sa.String(64), nullable=False, server_default="cmapss_fd001"),
        sa.Column("feature_config_version", sa.String(64), nullable=False),
        sa.Column("preprocessing_version", sa.String(64), nullable=False),
        sa.Column("input_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=True),
        sa.Column("horizon_unit", sa.String(32), nullable=True),
        sa.Column("decision_threshold", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("model_card_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("artifact_path", sa.String(512), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("python_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("task IN ('failure_risk', 'anomaly')", name="check_model_task"),
        sa.CheckConstraint("NOT (is_active = TRUE AND model_card_complete = FALSE)", name="check_model_card_complete_if_active"),
    )
    # Partial unique index for active model per task
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_active_model_per_task",
            "model_versions",
            ["adapter_key", "task"],
            unique=True,
            postgresql_where=sa.text("is_active = TRUE"),
        )

    # 7. model_evaluations
    op.create_table(
        "model_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_versions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("task", sa.String(32), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confusion_matrix", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calibration_curve", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("curves", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feature_importance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("methodology", sa.Text(), nullable=False),
        sa.Column("limitations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 8. health_indicator_configs
    op.create_table(
        "health_indicator_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(64), unique=True, nullable=False),
        sa.Column("weight_risk", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("weight_anomaly", sa.Float(), nullable=False, server_default="30.0"),
        sa.Column("weight_trend", sa.Float(), nullable=False, server_default="20.0"),
        sa.Column("trend_window", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(weight_risk + weight_anomaly + weight_trend) = 100.0", name="check_health_weights_sum_100"),
    )
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_active_health_config",
            "health_indicator_configs",
            ["is_active"],
            unique=True,
            postgresql_where=sa.text("is_active = TRUE"),
        )

    # 9. predictions
    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("as_of_index", sa.Integer(), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dataset_version", sa.String(64), nullable=False),
        sa.Column("schema_mapping_hash", sa.String(64), nullable=False),
        sa.Column("feature_config_version", sa.String(64), nullable=False),
        sa.Column("preprocessing_version", sa.String(64), nullable=False),
        sa.Column("failure_model_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("anomaly_model_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_versions.id"), nullable=True),
        sa.Column("health_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("health_indicator_configs.id"), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("horizon_unit", sa.String(32), nullable=False, server_default="cycles"),
        sa.Column("failure_probability", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(32), nullable=False),
        sa.Column("health_indicator", sa.Float(), nullable=False),
        sa.Column("health_band", sa.String(32), nullable=False),
        sa.Column("penalty_risk", sa.Float(), nullable=False),
        sa.Column("penalty_anomaly", sa.Float(), nullable=False),
        sa.Column("penalty_trend", sa.Float(), nullable=False),
        sa.Column("input_window_start", sa.Integer(), nullable=False),
        sa.Column("input_window_end", sa.Integer(), nullable=False),
        sa.Column("reliability_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_predictions_machine_id", "predictions", ["machine_id"])
    op.create_index("ix_predictions_cycle", "predictions", ["cycle"])

    # 10. anomalies
    op.create_table(
        "anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("predictions.id"), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("affected_features", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_anomalies_machine_id", "anomalies", ["machine_id"])
    op.create_index("ix_anomalies_cycle", "anomalies", ["cycle"])

    # 11. alerts
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("trigger_cycle", sa.Integer(), nullable=False),
        sa.Column("trigger_score", sa.Float(), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("recommendation_rule_id", sa.String(64), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="check_alert_status"),
        sa.CheckConstraint("severity IN ('warning', 'critical')", name="check_alert_severity"),
    )
    op.create_index("ix_alerts_machine_id", "alerts", ["machine_id"])
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_open_alert_per_type",
            "alerts",
            ["machine_id", "alert_type"],
            unique=True,
            postgresql_where=sa.text("status IN ('open', 'acknowledged')"),
        )

    # 12. maintenance_records
    op.create_table(
        "maintenance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id"), nullable=True),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("action_status", sa.String(32), nullable=False, server_default="in_progress"),
        sa.Column("outcome", sa.String(32), nullable=True),
        sa.Column("engineer_notes", sa.Text(), nullable=False),
        sa.Column("performed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("action_status IN ('in_progress', 'completed')", name="check_maintenance_status"),
        sa.CheckConstraint("outcome IS NULL OR outcome IN ('resolved', 'no_issue_found', 'unresolved')", name="check_maintenance_outcome"),
    )
    op.create_index("ix_maintenance_records_machine_id", "maintenance_records", ["machine_id"])

    # 13. alert_rules
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", sa.String(64), unique=True, nullable=False),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("failure_probability_threshold", sa.Float(), nullable=False, server_default="0.50"),
        sa.Column("anomaly_severity_threshold", sa.String(32), nullable=False, server_default="high"),
        sa.Column("consecutive_cycles", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # 14. settings
    op.create_table(
        "settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 15. jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("progress_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("input_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="check_job_status"),
    )

    # 16. audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # --- SEED DEFAULTS ---
    # Seed initial Health Indicator Config v1.0
    op.execute(
        sa.text(
            f"INSERT INTO health_indicator_configs (id, version, weight_risk, weight_anomaly, weight_trend, trend_window, is_active) "
            f"VALUES ('{uuid.uuid4()}', 'v1.0', 50.0, 30.0, 20.0, 20, TRUE)"
        )
    )

    # Seed default Alert Rules
    rules = [
        (uuid.uuid4(), "REC_HIGH_RISK_01", "high_failure_risk", 0.50, "high", 3),
        (uuid.uuid4(), "REC_SEVERE_ANOM_01", "severe_anomaly", 0.60, "critical", 2),
        (uuid.uuid4(), "REC_RAPID_DETER_01", "rapid_deterioration", 0.50, "high", 3),
    ]
    for rid, rule_code, atype, prob_thresh, anom_sev, consec in rules:
        op.execute(
            sa.text(
                f"INSERT INTO alert_rules (id, rule_id, alert_type, failure_probability_threshold, anomaly_severity_threshold, consecutive_cycles, is_active) "
                f"VALUES ('{rid}', '{rule_code}', '{atype}', {prob_thresh}, '{anom_sev}', {consec}, TRUE)"
            )
        )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("jobs")
    op.drop_table("settings")
    op.drop_table("alert_rules")
    op.drop_table("maintenance_records")
    op.drop_table("alerts")
    op.drop_table("anomalies")
    op.drop_table("predictions")
    op.drop_table("health_indicator_configs")
    op.drop_table("model_evaluations")
    op.drop_table("model_versions")
    op.drop_table("sensor_readings")
    op.drop_table("machines")
    op.drop_table("dataset_compatibility_checks")
    op.drop_table("datasets")
    op.drop_table("users")
