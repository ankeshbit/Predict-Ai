"""Conform schema to PRD v3.0 sections 13/14 and notebook health configuration

Revision ID: 002_conform_prd_and_notebook_health
Revises: 001_initial_schema
Create Date: 2026-10-01 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_conform_prd_and_health"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update machines.operational_status check constraint to strictly ('active', 'maintenance', 'archived')
    op.drop_constraint("check_machine_status", "machines", type_="check")
    op.execute(
        "UPDATE machines SET operational_status = 'active' WHERE operational_status NOT IN ('active', 'maintenance', 'archived')"
    )
    op.create_check_constraint(
        "check_machine_status",
        "machines",
        "operational_status IN ('active', 'maintenance', 'archived')",
    )

    # 2. Drop unique index (machine_id, cycle_index) on sensor_readings
    op.drop_index("uq_machine_cycle", table_name="sensor_readings")

    # 3. Replace weights-sum-100 health configuration with notebook-driven config
    op.drop_constraint("check_health_weights_sum_100", "health_indicator_configs", type_="check")
    op.add_column(
        "health_indicator_configs",
        sa.Column("anomaly_weight", sa.Float(), nullable=False, server_default="0.30"),
    )
    op.add_column(
        "health_indicator_configs",
        sa.Column(
            "data_quality_penalty",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{"DATA_OK": 0.0, "DATA_WARNING": 10.0}',
        ),
    )
    op.add_column(
        "health_indicator_configs",
        sa.Column("trend_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_check_constraint(
        "check_anomaly_weight_range",
        "health_indicator_configs",
        "anomaly_weight >= 0.0 AND anomaly_weight <= 1.0",
    )
    op.drop_column("health_indicator_configs", "weight_risk")
    op.drop_column("health_indicator_configs", "weight_anomaly")
    op.drop_column("health_indicator_configs", "weight_trend")
    op.drop_column("health_indicator_configs", "trend_window")

    # 4. Store breakdown points on predictions
    op.add_column(
        "predictions",
        sa.Column("penalty_dq", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "predictions",
        sa.Column("clipping_adjustment", sa.Float(), nullable=False, server_default="0.0"),
    )

    # 5. Recreate dataset_compatibility_checks as 1 row per check run with JSONB report
    op.drop_table("dataset_compatibility_checks")
    op.create_table(
        "dataset_compatibility_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'warning')",
            name="check_compatibility_status",
        ),
    )
    op.create_index("ix_compatibility_checks_dataset_id", "dataset_compatibility_checks", ["dataset_id"])

    # 6. Conform maintenance_records with decision fields and status enum
    op.add_column("maintenance_records", sa.Column("issue", sa.Text(), nullable=True))
    op.add_column("maintenance_records", sa.Column("recommended_action", sa.Text(), nullable=True))
    op.add_column("maintenance_records", sa.Column("decision", sa.String(32), nullable=True))
    op.create_check_constraint(
        "check_maintenance_decision",
        "maintenance_records",
        "decision IS NULL OR decision IN ('followed_recommendation', 'modified', 'declined')",
    )
    op.add_column("maintenance_records", sa.Column("decision_rationale", sa.Text(), nullable=True))
    op.add_column("maintenance_records", sa.Column("action_taken", sa.Text(), nullable=True))
    op.add_column(
        "maintenance_records",
        sa.Column("status", sa.String(32), nullable=False, server_default="in_progress"),
    )
    op.drop_constraint("check_maintenance_status", "maintenance_records", type_="check")
    op.create_check_constraint(
        "check_maintenance_status",
        "maintenance_records",
        "status IN ('recommended', 'in_progress', 'completed', 'cancelled')",
    )


def downgrade() -> None:
    # 6. Revert maintenance_records
    op.drop_constraint("check_maintenance_status", "maintenance_records", type_="check")
    op.create_check_constraint(
        "check_maintenance_status",
        "maintenance_records",
        "action_status IN ('in_progress', 'completed')",
    )
    op.drop_column("maintenance_records", "status")
    op.drop_column("maintenance_records", "action_taken")
    op.drop_column("maintenance_records", "decision_rationale")
    op.drop_constraint("check_maintenance_decision", "maintenance_records", type_="check")
    op.drop_column("maintenance_records", "decision")
    op.drop_column("maintenance_records", "recommended_action")
    op.drop_column("maintenance_records", "issue")

    # 5. Revert dataset_compatibility_checks
    op.drop_table("dataset_compatibility_checks")
    op.create_table(
        "dataset_compatibility_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("check_number", sa.Integer(), nullable=False),
        sa.Column("check_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("found_value", sa.Text(), nullable=True),
        sa.Column("how_to_fix", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 4. Revert predictions
    op.drop_column("predictions", "clipping_adjustment")
    op.drop_column("predictions", "penalty_dq")

    # 3. Revert health_indicator_configs
    op.drop_constraint("check_anomaly_weight_range", "health_indicator_configs", type_="check")
    op.drop_column("health_indicator_configs", "trend_enabled")
    op.drop_column("health_indicator_configs", "data_quality_penalty")
    op.drop_column("health_indicator_configs", "anomaly_weight")
    op.add_column(
        "health_indicator_configs",
        sa.Column("trend_window", sa.Integer(), nullable=False, server_default="20"),
    )
    op.add_column(
        "health_indicator_configs",
        sa.Column("weight_trend", sa.Float(), nullable=False, server_default="20.0"),
    )
    op.add_column(
        "health_indicator_configs",
        sa.Column("weight_anomaly", sa.Float(), nullable=False, server_default="30.0"),
    )
    op.add_column(
        "health_indicator_configs",
        sa.Column("weight_risk", sa.Float(), nullable=False, server_default="50.0"),
    )
    op.create_check_constraint(
        "check_health_weights_sum_100",
        "health_indicator_configs",
        "(weight_risk + weight_anomaly + weight_trend) = 100.0",
    )

    # 2. Recreate uq_machine_cycle
    op.create_index(
        "uq_machine_cycle",
        "sensor_readings",
        ["machine_id", "cycle_index"],
        unique=True,
    )

    # 1. Revert operational_status check constraint
    op.drop_constraint("check_machine_status", "machines", type_="check")
    op.create_check_constraint(
        "check_machine_status",
        "machines",
        "operational_status IN ('active', 'warning', 'critical', 'maintenance', 'degraded', 'offline')",
    )
