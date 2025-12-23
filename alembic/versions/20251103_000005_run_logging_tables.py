"""add run logging tables for backtest/opt/wfo results

Revision ID: 7d2c3b4e6f10
Revises: 31558d4
Create Date: 2025-11-03 12:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7d2c3b4e6f10"
down_revision = "31558d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_headers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_type", sa.String(length=20), nullable=False),
        sa.Column("instrument_id", sa.String(length=30), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("cash", sa.Numeric(30, 8), nullable=True),
        sa.Column("commission", sa.Numeric(18, 8), nullable=True),
        sa.Column("slip_perc", sa.Numeric(18, 8), nullable=True),
        sa.Column("slip_fixed", sa.Numeric(18, 8), nullable=True),
        sa.Column("slip_open", sa.Boolean(), nullable=True),
        sa.Column("baseline", sa.Boolean(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )
    op.create_index("ix_run_headers_type_ts", "run_headers", ["run_type", "started_at"])
    op.create_index("ix_run_headers_inst_tf", "run_headers", ["instrument_id", "timeframe"])

    op.create_table(
        "run_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("plot_path", sa.String(), nullable=True),
    )
    op.create_index("ix_run_results_run_label", "run_results", ["run_id", "label"])

    op.create_table(
        "wfo_folds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fold_index", sa.Integer(), nullable=False),
        sa.Column("train_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("test_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("test_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("train_objective", sa.Numeric(30, 8), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
    )
    op.create_index("ix_wfo_folds_run_fold", "wfo_folds", ["run_id", "fold_index"])


def downgrade() -> None:
    op.drop_index("ix_wfo_folds_run_fold", table_name="wfo_folds")
    op.drop_table("wfo_folds")
    op.drop_index("ix_run_results_run_label", table_name="run_results")
    op.drop_table("run_results")
    op.drop_index("ix_run_headers_inst_tf", table_name="run_headers")
    op.drop_index("ix_run_headers_type_ts", table_name="run_headers")
    op.drop_table("run_headers")

