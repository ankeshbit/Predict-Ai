"""Add machine metadata fields per PRD Section 13

Revision ID: 003_add_machine_metadata
Revises: 002_conform_prd_and_health
Create Date: 2026-10-02 01:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003_add_machine_metadata"
down_revision: Union[str, None] = "002_conform_prd_and_health"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("machines", sa.Column("name", sa.String(length=128), nullable=True))
    op.add_column("machines", sa.Column("machine_type", sa.String(length=64), nullable=True))
    op.add_column("machines", sa.Column("location", sa.String(length=128), nullable=True))
    op.add_column("machines", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("machines", sa.Column("install_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("machines", sa.Column("source_unit_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("machines", "source_unit_id")
    op.drop_column("machines", "install_date")
    op.drop_column("machines", "notes")
    op.drop_column("machines", "location")
    op.drop_column("machines", "machine_type")
    op.drop_column("machines", "name")
