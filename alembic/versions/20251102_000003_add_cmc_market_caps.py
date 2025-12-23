"""add cmc market caps table

Revision ID: b7c9d0e1f2a3
Revises: a1b2c3d4e5f6
Create Date: 2025-11-02 12:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c9d0e1f2a3"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cmc_market_caps",
        sa.Column("snapshot_ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(length=30), primary_key=True, nullable=False),
        sa.Column("market_cap_usd", sa.Numeric(30, 4), nullable=False),
    )
    op.create_index("ix_cmc_market_caps_symbol", "cmc_market_caps", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_cmc_market_caps_symbol", table_name="cmc_market_caps")
    op.drop_table("cmc_market_caps")
