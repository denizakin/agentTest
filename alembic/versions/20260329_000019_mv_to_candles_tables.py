"""Convert mv_candlesticks_* materialized views to candles schema regular tables.

Creates candles schema, refresh_state tracking table, and candles.refresh_incremental()
procedure. Migrates all existing aggregated (coin-only) MVs to regular tables, copies
data, then drops all mv_candlesticks_* materialized views.

Revision ID: b4c5d6e78901
Revises: a3b4c5d67891
Create Date: 2026-03-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'b4c5d6e78901'
down_revision = 'a3b4c5d67891'
branch_labels = None
depends_on = None

_BUCKET_EXPRS = {
    "5m":  "date_trunc('hour', ts) + (((extract(minute from ts)::int) / 5) * 5) * interval '1 minute'",
    "15m": "date_trunc('hour', ts) + (((extract(minute from ts)::int) / 15) * 15) * interval '1 minute'",
    "1h":  "date_trunc('hour', ts)",
    "4h":  "date_trunc('day', ts) + (((extract(hour from ts)::int) / 4) * 4) * interval '1 hour'",
    "1d":  "date_trunc('day', ts)",
    "1w":  "date_trunc('week', ts)",
    "1mo": "date_trunc('month', ts)",
}


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Schema ─────────────────────────────────────────────────────────────
    conn.execute(sa.text("CREATE SCHEMA IF NOT EXISTS candles"))

    # ── 2. Watermark tracking table ───────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS candles.refresh_state (
            table_name    TEXT        PRIMARY KEY,
            instrument_id TEXT        NOT NULL,
            bucket_expr   TEXT        NOT NULL,
            last_source_ts TIMESTAMPTZ
        )
    """))

    # ── 3. Migrate aggregated (coin-only) MVs ─────────────────────────────────
    # Pattern: mv_candlesticks_{coin}_{tf}  (exactly one underscore after prefix)
    mv_rows = conn.execute(sa.text(
        "SELECT matviewname FROM pg_matviews "
        "WHERE matviewname ~ '^mv_candlesticks_[a-z0-9]+_[a-z0-9]+$' "
        "ORDER BY matviewname"
    )).fetchall()

    for row in mv_rows:
        mv_name = row[0]
        suffix = mv_name[len("mv_candlesticks_"):]   # e.g. "btc_5m"
        last_ul = suffix.rfind("_")
        coin = suffix[:last_ul]                       # e.g. "btc"
        tf   = suffix[last_ul + 1:]                   # e.g. "5m"

        bucket_expr = _BUCKET_EXPRS.get(tf)
        if bucket_expr is None:
            continue  # unknown tf, skip

        table_name    = f"candlesticks_{coin}_{tf}"
        instrument_id = f"{coin.upper()}-USDT"

        # Create table
        conn.execute(sa.text(f"""
            CREATE TABLE IF NOT EXISTS candles.{table_name} (
                ts            TIMESTAMPTZ  NOT NULL,
                instrument_id VARCHAR(30)  NOT NULL,
                open          NUMERIC      NOT NULL,
                high          NUMERIC      NOT NULL,
                low           NUMERIC      NOT NULL,
                close         NUMERIC      NOT NULL,
                volume        NUMERIC      NOT NULL
            )
        """))

        # Copy data from MV
        conn.execute(sa.text(f"""
            INSERT INTO candles.{table_name} (ts, instrument_id, open, high, low, close, volume)
            SELECT ts, instrument_id, open, high, low, close, volume
            FROM {mv_name}
            ON CONFLICT DO NOTHING
        """))

        # Unique index required for ON CONFLICT in refresh_incremental
        conn.execute(sa.text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS uix_{table_name}_inst_ts
            ON candles.{table_name} (instrument_id, ts)
        """))

        # Watermark: last ts currently in the table
        max_ts = conn.execute(sa.text(f"SELECT max(ts) FROM candles.{table_name}")).scalar()
        conn.execute(sa.text("""
            INSERT INTO candles.refresh_state (table_name, instrument_id, bucket_expr, last_source_ts)
            VALUES (:table_name, :instrument_id, :bucket_expr, :last_source_ts)
            ON CONFLICT (table_name) DO NOTHING
        """), {
            "table_name":     table_name,
            "instrument_id":  instrument_id,
            "bucket_expr":    bucket_expr,
            "last_source_ts": max_ts,
        })

        print(f"  Migrated {mv_name} → candles.{table_name}")

    # ── 4. Incremental refresh stored procedure ───────────────────────────────
    conn.execute(sa.text(r"""
        CREATE OR REPLACE FUNCTION candles.refresh_incremental(p_table_name TEXT)
        RETURNS void AS $$
        DECLARE
            v_instrument  TEXT;
            v_bucket_expr TEXT;
            v_last_ts     TIMESTAMPTZ;
            v_fence       TIMESTAMPTZ;
            v_max_ts      TIMESTAMPTZ;
        BEGIN
            SELECT instrument_id, bucket_expr, last_source_ts
              INTO v_instrument, v_bucket_expr, v_last_ts
              FROM candles.refresh_state
             WHERE table_name = p_table_name;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'No refresh_state entry for table %', p_table_name;
            END IF;

            IF v_last_ts IS NULL THEN
                -- Full initial load
                EXECUTE format('TRUNCATE candles.%I', p_table_name);
                v_fence := '-infinity'::TIMESTAMPTZ;
            ELSE
                -- Compute the bucket that v_last_ts falls into (the open/last bucket)
                EXECUTE format(
                    'SELECT (%s) FROM (SELECT $1::timestamptz AS ts) _t',
                    v_bucket_expr
                ) INTO v_fence USING v_last_ts;
                -- Delete the open bucket and anything after it, then re-aggregate
                EXECUTE format('DELETE FROM candles.%I WHERE ts >= $1', p_table_name)
                    USING v_fence;
            END IF;

            -- Re-aggregate from fence onwards and upsert
            EXECUTE format(
                $sql$
                INSERT INTO candles.%I (ts, instrument_id, open, high, low, close, volume)
                WITH bucketed AS (
                    SELECT (%s) AS bucket_ts, ts, open, high, low, close, volume
                    FROM candlesticks
                    WHERE instrument_id = %L AND ts >= $1
                )
                SELECT
                    bucket_ts,
                    %L                                          AS instrument_id,
                    (array_agg(open  ORDER BY ts ASC ))[1]     AS open,
                    max(high)                                   AS high,
                    min(low)                                    AS low,
                    (array_agg(close ORDER BY ts DESC))[1]     AS close,
                    sum(volume)                                 AS volume
                FROM bucketed
                GROUP BY bucket_ts
                ON CONFLICT (instrument_id, ts) DO UPDATE
                    SET open   = EXCLUDED.open,
                        high   = EXCLUDED.high,
                        low    = EXCLUDED.low,
                        close  = EXCLUDED.close,
                        volume = EXCLUDED.volume
                $sql$,
                p_table_name, v_bucket_expr, v_instrument, v_instrument
            ) USING v_fence;

            -- Advance watermark
            SELECT max(ts) INTO v_max_ts
              FROM candlesticks
             WHERE instrument_id = v_instrument;
            IF v_max_ts IS NOT NULL THEN
                UPDATE candles.refresh_state
                   SET last_source_ts = v_max_ts
                 WHERE table_name = p_table_name;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """))

    # ── 5. Drop ALL mv_candlesticks_* materialized views ──────────────────────
    all_mvs = conn.execute(sa.text(
        "SELECT matviewname FROM pg_matviews "
        "WHERE matviewname LIKE 'mv_candlesticks_%' "
        "ORDER BY matviewname"
    )).fetchall()

    for row in all_mvs:
        conn.execute(sa.text(f"DROP MATERIALIZED VIEW IF EXISTS {row[0]} CASCADE"))
        print(f"  Dropped {row[0]}")


def downgrade() -> None:
    # Dropping the schema and tables is destructive — require manual intervention.
    raise NotImplementedError(
        "Downgrade not supported: manually recreate mv_candlesticks_* from candles.* tables if needed."
    )
