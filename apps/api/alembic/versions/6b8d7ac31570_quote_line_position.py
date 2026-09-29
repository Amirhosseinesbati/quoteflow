"""Persist the approved order of quote line items.

Revision ID: 6b8d7ac31570
Revises: 23d641a63a5f
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6b8d7ac31570"
down_revision: Union[str, None] = "23d641a63a5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quote_lines",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    connection = op.get_bind()
    # Older versions had no stored order; preserve their prior PDF order.
    rows = connection.execute(
        sa.text("SELECT id, version_id FROM quote_lines ORDER BY version_id, service_name, id")
    )
    previous_version = None
    position = 0
    for line_id, version_id in rows:
        if version_id != previous_version:
            previous_version = version_id
            position = 0
        connection.execute(
            sa.text("UPDATE quote_lines SET position = :position WHERE id = :id"),
            {"position": position, "id": line_id},
        )
        position += 1


def downgrade() -> None:
    op.drop_column("quote_lines", "position")
