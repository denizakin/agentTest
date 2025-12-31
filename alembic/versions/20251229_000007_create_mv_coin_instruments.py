"""create mv for coin instruments from candlesticks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e6f7
Create Date: 2025-12-29 11:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_coin_instruments AS
        SELECT instrument_id
        FROM candlesticks
        GROUP BY instrument_id
        """
    )
    op.create_index(
        "ix_mv_coin_instruments_inst",
        "mv_coin_instruments",
        ["instrument_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_mv_coin_instruments_inst", table_name="mv_coin_instruments")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_coin_instruments")
