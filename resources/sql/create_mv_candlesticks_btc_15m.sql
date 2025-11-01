-- Materialized view: 15m BTC-USDT OHLCV aggregated from 1m candlesticks
-- Pure PostgreSQL (no TimescaleDB/time_bucket)
--
-- Aggregation rules:
--  - ts:        15-minute bucket start
--  - open:      first open by time within bucket
--  - high:      max(high)
--  - low:       min(low)
--  - close:     last close by time within bucket
--  - volume:    sum(volume)
--
-- Recreate safely if needed:
--   DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_15m;

DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_btc_15m;

CREATE MATERIALIZED VIEW mv_candlesticks_btc_15m AS
WITH bucketed AS (
    SELECT
        -- Compute 15-minute bucket start without TimescaleDB
        (
            date_trunc('hour', ts)
            + (((extract(minute from ts)::int) / 15) * 15) * interval '1 minute'
        ) AS bucket_ts,
        ts,
        open,
        high,
        low,
        close,
        volume
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

-- Unique by bucket since instrument_id is constant
CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_candles_btc_15m_ts
  ON mv_candlesticks_btc_15m (ts);

-- Refresh commands:
--   REFRESH MATERIALIZED VIEW mv_candlesticks_btc_15m;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_candlesticks_btc_15m; -- requires the unique index and outside a TX

