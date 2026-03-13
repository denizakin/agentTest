"""Add backtest_run_id to optimization_results

Revision ID: c4e6f8a01345
Revises: b3d5e7f90234
Create Date: 2026-02-28

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e6f8a01345'
down_revision = 'b3d5e7f90234'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('optimization_results', sa.Column('backtest_run_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_opt_result_backtest_run',
        'optimization_results',
        'run_headers',
        ['backtest_run_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_opt_result_backtest_run', 'optimization_results', type_='foreignkey')
    op.drop_column('optimization_results', 'backtest_run_id')
