"""add strategy_id FK to run_headers

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-12-30 15:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_headers", sa.Column("strategy_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_run_headers_strategy",
        "run_headers",
        "strategies",
        ["strategy_id"],
        ["strategy_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_run_headers_strategy_id", "run_headers", ["strategy_id"])


def downgrade() -> None:
    op.drop_index("ix_run_headers_strategy_id", table_name="run_headers")
    op.drop_constraint("fk_run_headers_strategy", "run_headers", type_="foreignkey")
    op.drop_column("run_headers", "strategy_id")
