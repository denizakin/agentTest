"""init schema

Revision ID: 3f4b2a1c0d5e
Revises: 
Create Date: 2025-10-19 17:15:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f4b2a1c0d5e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candlesticks",
        sa.Column("instrument_id", sa.String(length=30), primary_key=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(30, 12), nullable=False),
        sa.UniqueConstraint("instrument_id", "ts", name="uq_candles_inst_ts"),
    )
    op.create_index(
        "ix_candles_inst_ts",
        "candlesticks",
        ["instrument_id", "ts"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_candles_inst_ts", table_name="candlesticks")
    op.drop_table("candlesticks")

