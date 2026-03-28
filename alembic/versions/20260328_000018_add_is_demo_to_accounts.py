"""Add is_demo to accounts

Revision ID: a3b4c5d67891
Revises: f2a3b4567890
Create Date: 2026-03-28

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'a3b4c5d67891'
down_revision = 'f2a3b4567890'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'is_demo')
