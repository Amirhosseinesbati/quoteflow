"""Allow every workflow waiting state in jobs.status.

Revision ID: a4b1c9d2e3f4
Revises: 6b8d7ac31570
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4b1c9d2e3f4"
down_revision: str | None = "6b8d7ac31570"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Native ALTER on PostgreSQL; batch recreation is required by SQLite.
    with op.batch_alter_table("jobs") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.String(length=20),
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    too_long = op.get_bind().execute(
        sa.text("SELECT 1 FROM jobs WHERE length(status) > 20 LIMIT 1")
    ).first()
    if too_long:
        raise RuntimeError("Cannot narrow jobs.status while longer workflow states exist")
    with op.batch_alter_table("jobs") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.String(length=64),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
