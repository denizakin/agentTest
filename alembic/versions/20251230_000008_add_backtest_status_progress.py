"""add status/progress to run_headers

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-12-30 12:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_headers", sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"))
    op.add_column("run_headers", sa.Column("progress", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("run_headers", sa.Column("error", sa.Text(), nullable=True))
    op.alter_column("run_headers", "status", server_default=None)
    op.alter_column("run_headers", "progress", server_default=None)
    op.create_index("ix_run_headers_status", "run_headers", ["status"])


def downgrade() -> None:
    op.drop_index("ix_run_headers_status", table_name="run_headers")
    op.drop_column("run_headers", "error")
    op.drop_column("run_headers", "progress")
    op.drop_column("run_headers", "status")
