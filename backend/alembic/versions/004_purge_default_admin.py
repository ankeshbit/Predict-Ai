"""Purge default admin user with known compromised hash

Revision ID: 004_purge_default_admin
Revises: 003_add_machine_metadata
Create Date: 2026-10-02 18:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_purge_default_admin"
down_revision: Union[str, None] = "003_add_machine_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Known hardcoded hash from previous dev releases
COMPROMISED_ADMIN_HASH = "$argon2id$v=19$m=65536,t=3,p=4$DkFIKQWAUMp5L6XU+p9TCg$eaikMh1M16BLc919oX+s8i2EzWDPOQgsth0202cy4hI"


def upgrade() -> None:
    # Delete or invalidate any admin account still holding the known public hash
    op.execute(
        sa.text(
            f"DELETE FROM users WHERE role = 'admin' AND password_hash = '{COMPROMISED_ADMIN_HASH}'"
        )
    )


def downgrade() -> None:
    # Irreversible security fix; do not restore compromised admin
    pass
