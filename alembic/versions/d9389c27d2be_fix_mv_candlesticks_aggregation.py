"""fix mv_candlesticks aggregation

Revision ID: d9389c27d2be
Revises: be5b03f1f761
Create Date: 2026-01-26 23:16:11.505365

"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'd9389c27d2be'
down_revision = 'be5b03f1f761'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop all existing incorrectly created MVs
    op.execute("""
        DO $$
        DECLARE
            mv_name text;
        BEGIN
            FOR mv_name IN
                SELECT matviewname
                FROM pg_matviews
                WHERE schemaname = 'public'
                AND matviewname LIKE 'mv_candlesticks_%'
            LOOP
                EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS ' || mv_name || ' CASCADE';
            END LOOP;
        END $$;
    """)

    # Get all distinct instruments
    instruments = op.get_bind().execute(
        text("SELECT DISTINCT instrument_id FROM candlesticks ORDER BY instrument_id")
    ).fetchall()

    # Timeframes with their aggregation logic
    timeframes = {
        '5m': {
            'bucket': """
                date_trunc('hour', ts)
                + (((extract(minute from ts)::int) / 5) * 5) * interval '1 minute'
            """,
        },
        '15m': {
            'bucket': """
                date_trunc('hour', ts)
                + (((extract(minute from ts)::int) / 15) * 15) * interval '1 minute'
            """,
        },
        '1h': {
            'bucket': "date_trunc('hour', ts)",
        },
        '4h': {
            'bucket': """
                date_trunc('day', ts)
                + (((extract(hour from ts)::int) / 4) * 4) * interval '1 hour'
            """,
        },
        '1d': {
            'bucket': "date_trunc('day', ts)",
        },
        '1w': {
            'bucket': "date_trunc('week', ts)",
        },
        '1mo': {
            'bucket': "date_trunc('month', ts)",
        },
    }

    # Create MVs for each instrument and timeframe
    for inst_row in instruments:
        instrument_id = inst_row[0]
        # Extract coin symbol (e.g., BTC-USDT -> btc)
        coin = instrument_id.lower().split('-')[0] if '-' in instrument_id else instrument_id.lower()

        for tf, config in timeframes.items():
            mv_name = f"mv_candlesticks_{coin}_{tf}"
            bucket_expr = config['bucket']

            sql = f"""
                CREATE MATERIALIZED VIEW {mv_name} AS
                WITH bucketed AS (
                    SELECT ({bucket_expr}) AS bucket_ts,
                           ts, open, high, low, close, volume
                    FROM candlesticks
                    WHERE instrument_id = '{instrument_id}'
                )
                SELECT
                    bucket_ts AS ts,
                    '{instrument_id}'::varchar(30) AS instrument_id,
                    (array_agg(open  ORDER BY ts ASC))[1]  AS open,
                    max(high)                              AS high,
                    min(low)                               AS low,
                    (array_agg(close ORDER BY ts DESC))[1] AS close,
                    sum(volume)                            AS volume
                FROM bucketed
                GROUP BY bucket_ts
                ORDER BY bucket_ts;

                CREATE UNIQUE INDEX ix_{mv_name}_ts ON {mv_name} (ts);
            """
            op.execute(sql)


def downgrade() -> None:
    # Drop all MVs created by this migration
    op.execute("""
        DO $$
        DECLARE
            mv_name text;
        BEGIN
            FOR mv_name IN
                SELECT matviewname
                FROM pg_matviews
                WHERE schemaname = 'public'
                AND matviewname LIKE 'mv_candlesticks_%'
            LOOP
                EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS ' || mv_name || ' CASCADE';
            END LOOP;
        END $$;
    """)
