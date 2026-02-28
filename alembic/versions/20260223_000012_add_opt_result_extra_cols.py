"""Add extra metric columns to optimization_results

Revision ID: a2c4e6f80123
Revises: f8a9b0c1d2e3
Create Date: 2026-02-23

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2c4e6f80123'
down_revision = 'f8a9b0c1d2e3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('optimization_results', sa.Column('long_count', sa.Integer(), nullable=True))
    op.add_column('optimization_results', sa.Column('short_count', sa.Integer(), nullable=True))
    op.add_column('optimization_results', sa.Column('best_pnl', sa.Numeric(precision=30, scale=8), nullable=True))
    op.add_column('optimization_results', sa.Column('worst_pnl', sa.Numeric(precision=30, scale=8), nullable=True))
    op.add_column('optimization_results', sa.Column('avg_pnl', sa.Numeric(precision=30, scale=8), nullable=True))


def downgrade() -> None:
    op.drop_column('optimization_results', 'avg_pnl')
    op.drop_column('optimization_results', 'worst_pnl')
    op.drop_column('optimization_results', 'best_pnl')
    op.drop_column('optimization_results', 'short_count')
    op.drop_column('optimization_results', 'long_count')
