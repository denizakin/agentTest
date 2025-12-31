"""create strategies table

Revision ID: a1b2c3d4e6f7
Revises: 7d2c3b4e6f10
Create Date: 2025-12-29 10:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e6f7"
down_revision = "7d2c3b4e6f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategies",
        sa.Column("strategy_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("code", sa.Text(), nullable=True),
        sa.UniqueConstraint("name", name="uq_strategy_name"),
        sa.CheckConstraint("status IN ('draft','prod','archived')", name="ck_strategy_status"),
    )


def downgrade() -> None:
    op.drop_table("strategies")

