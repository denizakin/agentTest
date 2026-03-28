"""Add account_id to trade_definitions

Revision ID: f2a3b4567890
Revises: e1f2a3b45678
Create Date: 2026-03-28

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'f2a3b4567890'
down_revision = 'e1f2a3b45678'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'trade_definitions',
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('trade_definitions', 'account_id')
