"""Add won_count and lost_count to optimization_results

Revision ID: b3d5e7f90234
Revises: a2c4e6f80123
Create Date: 2026-02-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3d5e7f90234'
down_revision = 'a2c4e6f80123'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('optimization_results', sa.Column('won_count', sa.Integer(), nullable=True))
    op.add_column('optimization_results', sa.Column('lost_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('optimization_results', 'lost_count')
    op.drop_column('optimization_results', 'won_count')
