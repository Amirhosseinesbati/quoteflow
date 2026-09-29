"""outbox_recovery

Revision ID: f111a98e0e1c
Revises: 75a6d9e57e63
Create Date: 2026-09-28 00:31:05.163332
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f111a98e0e1c'
down_revision: Union[str, None] = '75a6d9e57e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('outbox_events', sa.Column('attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('outbox_events', sa.Column('last_error', sa.Text(), server_default='', nullable=False))
    op.add_column('outbox_events', sa.Column('provider_id', sa.String(length=120), nullable=True))
    op.add_column('outbox_events', sa.Column('lease_until', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('outbox_events', 'lease_until')
    op.drop_column('outbox_events', 'provider_id')
    op.drop_column('outbox_events', 'last_error')
    op.drop_column('outbox_events', 'attempts')
