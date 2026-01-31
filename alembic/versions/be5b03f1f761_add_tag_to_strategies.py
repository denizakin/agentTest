"""Add tag column to strategies

Revision ID: be5b03f1f761
Revises: e5f6a7b8c9d0
Create Date: 2026-01-26 22:11:05.163223

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'be5b03f1f761'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategies', sa.Column('tag', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('strategies', 'tag')
