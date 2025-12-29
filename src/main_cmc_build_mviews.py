"""CLI: Build materialized views for the latest top-N CMC symbols.

Workflow:
- Assumes `cmc_market_caps` already populated (e.g., via main_cmc_market_caps.py).
- Reads the latest snapshot, takes top-N by market cap, drops stablecoins,
  and creates mv_candlesticks_<symbol>_<tf> for each timeframe bucket.

Example:
    python src/main_cmc_build_mviews.py --limit 100 --tfs 5m,15m,1h,4h,1d,1w,1mo
"""
from __future__ import annotations

import argparse
from typing import Dict, Sequence, Tuple
import re

from sqlalchemy import text

from config import load_env_file
from db.db_conn import DbConn
from main_cmc_market_caps import _is_stablecoin


SUPPORTED_TFS: Tuple[str, ...] = ("5m", "15m", "1h", "4h", "1d", "1w", "1mo")


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create materialized views for top CMC symbols")
    p.add_argument("--limit", type=int, default=100, help="How many symbols to use from latest CMC snapshot")
    p.add_argument(
        "--tfs",
        default=",".join(SUPPORTED_TFS),
        help=f"Comma-separated timeframes to build. Supported: {','.join(SUPPORTED_TFS)}",
    )
    p.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    return p.parse_args()


def _validate_tfs(tf_list: Sequence[str]) -> Tuple[str, ...]:
    unknown = [tf for tf in tf_list if tf not in SUPPORTED_TFS]
    if unknown:
        print(f"Warning: dropping unsupported timeframes: {unknown}. Supported: {list(SUPPORTED_TFS)}")
    # Preserve canonical order and drop unknowns
    ordered = tuple(tf for tf in SUPPORTED_TFS if tf in tf_list)
    if not ordered:
        raise ValueError(f"No valid timeframes provided. Supported: {list(SUPPORTED_TFS)}")
    return ordered


def build_mviews(limit: int, tfs: Sequence[str], echo: bool = False) -> int:
    load_env_file()
    db = DbConn(echo=echo)
    buckets = _time_buckets()
    selected_tfs = _validate_tfs(tfs)

    with db.engine.begin() as conn:
        latest_ts = conn.execute(text("SELECT max(snapshot_ts) FROM cmc_market_caps")).scalar_one_or_none()
        if latest_ts is None:
            print("No cmc_market_caps snapshot found; aborting.")
            return 2

        rows = conn.execute(
            text(
                """
                SELECT symbol
                FROM cmc_market_caps
                WHERE snapshot_ts = :ts
                ORDER BY market_cap_usd DESC
                LIMIT :limit
                """
            ),
            {"ts": latest_ts, "limit": int(limit)},
        ).fetchall()

        symbols = [r[0] for r in rows if r and r[0]]
        filtered = [sym for sym in symbols if not _is_stablecoin({"symbol": sym, "tags": []})]
        skipped = len(symbols) - len(filtered)
        if skipped:
            print(f"Skipped {skipped} stablecoins from top list.")

        if not filtered:
            print("No symbols to process after filtering; aborting.")
            return 2

        for sym in filtered:
            sym_up = str(sym).upper()
            sym_low = sym_up.lower()
            inst_id = f"{sym_up}-USDT"
            inst_lit = inst_id.replace("'", "''")

            for tf in selected_tfs:
                bucket_expr = buckets[tf]
                view_name = f"mv_candlesticks_{sym_low}_{tf}"
                idx_name = f"ix_mv_candles_{sym_low}_{tf}_ts"
                sql = f"""
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
                conn.execute(text(sql))
                conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {view_name} (ts);"))
                print(f"Created {view_name}")

    return 0


def main() -> int:
    args = parse_args()
    # Normalize timeframes: split on comma or whitespace, strip, lowercase, drop empties
    parts = re.split(r"[,\s]+", args.tfs or "")
    tfs = [s.strip().lower() for s in parts if s and s.strip()]
    return build_mviews(limit=args.limit, tfs=tfs, echo=args.echo)


if __name__ == "__main__":
    raise SystemExit(main())
