"""Create optimization_results table

Revision ID: f8a9b0c1d2e3
Revises: 31531d6ecb08
Create Date: 2026-02-14

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8a9b0c1d2e3'
down_revision = '31531d6ecb08'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'optimization_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('variant_params', sa.JSON(), nullable=False),
        sa.Column('final_value', sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column('sharpe', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('maxdd', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('winrate', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('profit_factor', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('sqn', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['run_headers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_optimization_results_run_id', 'optimization_results', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_optimization_results_run_id', table_name='optimization_results')
    op.drop_table('optimization_results')
