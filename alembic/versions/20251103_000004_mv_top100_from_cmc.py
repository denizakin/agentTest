"""create materialized views for top CMC symbols (excluding stables)

Revision ID: 6c7f9c1d2e3f
Revises: b7c9d0e1f2a3
Create Date: 2025-11-03 00:00:00
"""
from __future__ import annotations

from typing import Dict

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6c7f9c1d2e3f"
down_revision = "b7c9d0e1f2a3"
branch_labels = None
depends_on = None


def _time_buckets() -> Dict[str, str]:
    return {
        "5m": "date_trunc('hour', ts) + (((extract(minute from ts)::int) / 5) * 5) * interval '1 minute'",
        "15m": "date_trunc('hour', ts) + (((extract(minute from ts)::int) / 15) * 15) * interval '1 minute'",
        "1h": "date_trunc('hour', ts)",
        "4h": "date_trunc('day', ts) + (((extract(hour from ts)::int) / 4) * 4) * interval '1 hour'",
        "1d": "date_trunc('day', ts)",
        "1w": "date_trunc('week', ts)",
        "1mo": "date_trunc('month', ts)",
    }


def _stable_symbols() -> set[str]:
    # Common stables to exclude
    return {
        "USDT",
        "USDC",
        "BUSD",
        "DAI",
        "TUSD",
        "USDP",
        "PAX",
        "GUSD",
        "LUSD",
        "FRAX",
        "USDD",
        "FDUSD",
        "USDJ",
    }


def upgrade() -> None:
    conn = op.get_bind()
    stable = _stable_symbols()

    # Get latest snapshot_ts and top 100 symbols by market cap
    latest_ts = conn.execute(sa.text("SELECT max(snapshot_ts) FROM cmc_market_caps")).scalar()
    if latest_ts is None:
        print("No market_caps data found; skipping MV creation.")
        return

    rows = conn.execute(
        sa.text(
            """
            SELECT symbol
            FROM cmc_market_caps
            WHERE snapshot_ts = :ts
            ORDER BY market_cap_usd DESC
            LIMIT 100
            """
        ),
        {"ts": latest_ts},
    ).fetchall()

    symbols = [r[0] for r in rows if r and r[0]]
    tf_buckets = _time_buckets()

    for sym in symbols:
        sym_up = str(sym).upper()
        if sym_up in stable:
            continue
        sym_low = sym_up.lower()
        inst_id = f"{sym_up}-USDT"

        inst_lit = inst_id.replace("'", "''")  # simple escape for literal insertion
        for tf, bucket_expr in tf_buckets.items():
            view_name = f"mv_candlesticks_{sym_low}_{tf}"
            idx_name = f"ix_mv_candles_{sym_low}_{tf}_ts"
            create_sql = f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name} AS
            WITH bucketed AS (
                SELECT
                    ({bucket_expr}) AS bucket_ts,
                    ts,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM candlesticks
                WHERE instrument_id = '{inst_lit}'
            )
            SELECT
                bucket_ts AS ts,
                '{inst_lit}'::varchar(30)                AS instrument_id,
                (array_agg(open  ORDER BY ts ASC))[1]  AS open,
                max(high)                              AS high,
                min(low)                               AS low,
                (array_agg(close ORDER BY ts DESC))[1] AS close,
                sum(volume)                            AS volume
            FROM bucketed
            GROUP BY bucket_ts
            ORDER BY bucket_ts;
            """
            conn.execute(sa.text(create_sql))
            conn.execute(sa.text(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {view_name} (ts);"))


def downgrade() -> None:
    conn = op.get_bind()
    # Drop any mv_candlesticks_<sym>_<tf> created from market_caps top 100 snapshot
    tf_buckets = _time_buckets()
    latest_ts = conn.execute(sa.text("SELECT max(snapshot_ts) FROM cmc_market_caps")).scalar()
    if latest_ts is None:
        return
    rows = conn.execute(
        sa.text(
            """
            SELECT symbol
            FROM cmc_market_caps
            WHERE snapshot_ts = :ts
            ORDER BY market_cap_usd DESC
            LIMIT 100
            """
        ),
        {"ts": latest_ts},
    ).fetchall()
    symbols = [str(r[0]).lower() for r in rows if r and r[0]]
    for sym in symbols:
        for tf in tf_buckets.keys():
            view_name = f"mv_candlesticks_{sym}_{tf}"
            conn.execute(sa.text(f"DROP MATERIALIZED VIEW IF EXISTS {view_name} CASCADE;"))
