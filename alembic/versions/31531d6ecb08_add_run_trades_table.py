"""
Revision ID: 31531d6ecb08
Revises: d9389c27d2be
Create Date: 2026-02-04 12:05:01.085946

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '31531d6ecb08'
down_revision = 'd9389c27d2be'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'run_trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('entry_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),  # LONG/SHORT
        sa.Column('entry_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('exit_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('size', sa.Numeric(precision=30, scale=12), nullable=False),
        sa.Column('pnl', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('pnl_pct', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('mae', sa.Numeric(precision=20, scale=8), nullable=True),  # Maximum Adverse Excursion
        sa.Column('mfe', sa.Numeric(precision=20, scale=8), nullable=True),  # Maximum Favorable Excursion
        sa.Column('commission', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['run_headers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_trades_run_id'), 'run_trades', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_run_trades_run_id'), table_name='run_trades')
    op.drop_table('run_trades')

