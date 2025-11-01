-- Materialized view: 1 month ETH-USDT OHLCV (pure PostgreSQL)

DROP MATERIALIZED VIEW IF EXISTS mv_candlesticks_eth_1mo;

CREATE MATERIALIZED VIEW mv_candlesticks_eth_1mo AS
WITH bucketed AS (
    SELECT
        date_trunc('month', ts) AS bucket_ts,
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

CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_candles_eth_1mo_ts
  ON mv_candlesticks_eth_1mo (ts);

