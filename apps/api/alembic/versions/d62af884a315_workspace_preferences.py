"""Persist workspace studio defaults without rewriting historical quotes."""

import sqlalchemy as sa
from alembic import op

revision = "d62af884a315"
down_revision = "a4b1c9d2e3f4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workspace_preferences",
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("workspace_preferences")
