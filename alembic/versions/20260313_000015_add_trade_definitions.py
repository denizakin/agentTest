"""Add trade_definitions table

Revision ID: d7f9a0b12456
Revises: c4e6f8a01345
Create Date: 2026-03-13

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'd7f9a0b12456'
down_revision = 'c4e6f8a01345'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trade_definitions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('strategy_id', sa.Integer(), sa.ForeignKey('strategies.strategy_id', ondelete='SET NULL'), nullable=True),
        sa.Column('strategy_name', sa.String(200), nullable=False),
        sa.Column('instrument_id', sa.String(30), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='paused'),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active','paused','stopped')", name='ck_trade_def_status'),
    )


def downgrade() -> None:
    op.drop_table('trade_definitions')
