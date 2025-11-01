"""create candle materialized views (pure PostgreSQL)

Revision ID: a1b2c3d4e5f6
Revises: 3f4b2a1c0d5e
Create Date: 2025-11-01 00:45:00

"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "3f4b2a1c0d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 5 minutes
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_btc_5m AS
        WITH bucketed AS (
            SELECT (
                date_trunc('hour', ts)
                + (((extract(minute from ts)::int) / 5) * 5) * interval '1 minute'
            ) AS bucket_ts,
            ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'BTC-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'BTC-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_btc_5m_ts
          ON mv_candlesticks_btc_5m (ts);
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_eth_5m AS
        WITH bucketed AS (
            SELECT (
                date_trunc('hour', ts)
                + (((extract(minute from ts)::int) / 5) * 5) * interval '1 minute'
            ) AS bucket_ts,
            ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'ETH-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'ETH-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_eth_5m_ts
          ON mv_candlesticks_eth_5m (ts);
        """
    )

    # 15 minutes
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_btc_15m AS
        WITH bucketed AS (
            SELECT (
                date_trunc('hour', ts)
                + (((extract(minute from ts)::int) / 15) * 15) * interval '1 minute'
            ) AS bucket_ts,
            ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'BTC-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'BTC-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_btc_15m_ts
          ON mv_candlesticks_btc_15m (ts);
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_eth_15m AS
        WITH bucketed AS (
            SELECT (
                date_trunc('hour', ts)
                + (((extract(minute from ts)::int) / 15) * 15) * interval '1 minute'
            ) AS bucket_ts,
            ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'ETH-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'ETH-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_eth_15m_ts
          ON mv_candlesticks_eth_15m (ts);
        """
    )

    # 1 hour
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_btc_1h AS
        WITH bucketed AS (
            SELECT date_trunc('hour', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'BTC-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'BTC-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_btc_1h_ts
          ON mv_candlesticks_btc_1h (ts);
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_eth_1h AS
        WITH bucketed AS (
            SELECT date_trunc('hour', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'ETH-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'ETH-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_eth_1h_ts
          ON mv_candlesticks_eth_1h (ts);
        """
    )

    # 4 hours
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_btc_4h AS
        WITH bucketed AS (
            SELECT (
                date_trunc('day', ts)
                + (((extract(hour from ts)::int) / 4) * 4) * interval '1 hour'
            ) AS bucket_ts,
            ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'BTC-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'BTC-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_btc_4h_ts
          ON mv_candlesticks_btc_4h (ts);
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_eth_4h AS
        WITH bucketed AS (
            SELECT (
                date_trunc('day', ts)
                + (((extract(hour from ts)::int) / 4) * 4) * interval '1 hour'
            ) AS bucket_ts,
            ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'ETH-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'ETH-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_eth_4h_ts
          ON mv_candlesticks_eth_4h (ts);
        """
    )

    # 1 day
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_btc_1d AS
        WITH bucketed AS (
            SELECT date_trunc('day', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'BTC-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'BTC-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_btc_1d_ts
          ON mv_candlesticks_btc_1d (ts);
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_eth_1d AS
        WITH bucketed AS (
            SELECT date_trunc('day', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'ETH-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'ETH-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_eth_1d_ts
          ON mv_candlesticks_eth_1d (ts);
        """
    )

    # 1 week
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_btc_1w AS
        WITH bucketed AS (
            SELECT date_trunc('week', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'BTC-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'BTC-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_btc_1w_ts
          ON mv_candlesticks_btc_1w (ts);
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_eth_1w AS
        WITH bucketed AS (
            SELECT date_trunc('week', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'ETH-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'ETH-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_eth_1w_ts
          ON mv_candlesticks_eth_1w (ts);
        """
    )

    # 1 month
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_btc_1mo AS
        WITH bucketed AS (
            SELECT date_trunc('month', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'BTC-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'BTC-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_btc_1mo_ts
          ON mv_candlesticks_btc_1mo (ts);
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_candlesticks_eth_1mo AS
        WITH bucketed AS (
            SELECT date_trunc('month', ts) AS bucket_ts,
                   ts, open, high, low, close, volume
            FROM candlesticks
            WHERE instrument_id = 'ETH-USDT'
        )
        SELECT
            bucket_ts AS ts,
            'ETH-USDT'::varchar(30)                AS instrument_id,
            (array_agg(open  ORDER BY ts ASC))[1]  AS open,
            max(high)                              AS high,
            min(low)                               AS low,
            (array_agg(close ORDER BY ts DESC))[1] AS close,
            sum(volume)                            AS volume
        FROM bucketed
        GROUP BY bucket_ts
        ORDER BY bucket_ts;

        CREATE UNIQUE INDEX ix_mv_candles_eth_1mo_ts
          ON mv_candlesticks_eth_1mo (ts);
        """
    )


def downgrade() -> None:
    # Drop in reverse order
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_1mo;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_1mo;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_1w;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_1w;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_1d;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_1d;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_4h;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_4h;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_1h;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_1h;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_15m;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_15m;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_5m;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_5m;")

