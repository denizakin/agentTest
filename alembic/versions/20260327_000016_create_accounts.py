"""Create accounts table

Revision ID: e1f2a3b45678
Revises: d7f9a0b12456
Create Date: 2026-03-27

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b45678'
down_revision = 'd7f9a0b12456'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('api_key', sa.String(500), nullable=True),
        sa.Column('secret_key', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("platform IN ('binance','okx')", name='ck_account_platform'),
    )


def downgrade() -> None:
    op.drop_table('accounts')
