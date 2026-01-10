"""create run_logs table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2025-12-30 14:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("level", sa.String(length=10), nullable=False, server_default="INFO"),
        sa.Column("message", sa.Text(), nullable=False),
    )
    op.create_index("ix_run_logs_run_ts", "run_logs", ["run_id", "ts"])
    op.alter_column("run_logs", "ts", server_default=None)
    op.alter_column("run_logs", "level", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_run_logs_run_ts", table_name="run_logs")
    op.drop_table("run_logs")
