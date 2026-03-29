"""CLI: Ingest OKX candlesticks into PostgreSQL.

Fetches latest kline data via OkxMarketDataClient and upserts rows
into the `candlesticks` table using SQLAlchemy.
"""
from __future__ import annotations

import argparse
import time
import re
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import text

from config import load_env_file
from db.db_conn import DbConn
from db.candles_repo import CandlesRepo, parse_okx_candle_row
from api.okx_market_data_client import OkxMarketDataClient, OkxApiError


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest OKX candlesticks into DB")
    p.add_argument("--inst", dest="instrument_id", default="BTC-USDT", help="Instrument ID, e.g. BTC-USDT")
    p.add_argument("--bar", dest="bar", default="1m", help="Candle granularity, e.g. 1m, 5m, 1h")
    p.add_argument("--limit", dest="limit", type=int, default=300, help="Per-request rows (<=300)")
    p.add_argument("--max-rows", dest="max_rows", type=int, default=1000, help="Total rows to ingest via pagination")
    p.add_argument(
        "--since",
        dest="since",
        default=None,
        help=(
            "Only ingest candles with ts >= time. Accepts: "
            "ISO8601 (e.g. 2024-01-01T00:00:00Z), "
            "date 'YYYY-MM-DD' (assumes 00:00:00Z), "
            "'YYYY-MM-DD HH:MM[:SS]' (assumes UTC), or epoch (s/ms)."
        ),
    )
    p.add_argument(
        "--until",
        dest="until",
        default=None,
        help=(
            "Only ingest candles with ts <= time. Accepts: "
            "ISO8601 (e.g. 2024-02-01T00:00:00Z), "
            "date 'YYYY-MM-DD' (assumes 00:00:00Z), "
            "'YYYY-MM-DD HH:MM[:SS]' (assumes UTC), or epoch (s/ms)."
        ),
    )
    p.add_argument("--sleep", dest="sleep_sec", type=float, default=0.2, help="Sleep seconds between requests")
    p.add_argument("--retries", dest="retries", type=int, default=3, help="Max retries on transient API errors")
    p.add_argument("--backoff", dest="backoff", type=float, default=0.5, help="Initial backoff seconds for retries")
    p.add_argument("--backoff-mult", dest="backoff_mult", type=float, default=2.0, help="Backoff multiplier")
    p.add_argument(
        "--use-history-first",
        dest="use_history_first",
        action="store_true",
        help="Start pagination with OKX history candles endpoint instead of standard candles",
    )
    p.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    p.add_argument("--refresh-mv", action="store_true", help="Create/refresh per-instrument MV after ingest")
    return p.parse_args()


def _parse_time_to_ms(value: Optional[str]) -> Optional[int]:
    """Parse time string to epoch milliseconds.

    Supported formats:
    - Epoch seconds or milliseconds (digits)
    - ISO8601 (e.g., 2024-01-01T00:00:00Z or with offset)
    - Date only 'YYYY-MM-DD' (assumes 00:00:00 UTC)
    - 'YYYY-MM-DD HH:MM[:SS]' (assumes UTC)
    """
    if not value:
        return None

    txt = value.strip()
    if txt.isdigit():
        # Numeric epoch; decide seconds vs milliseconds by length
        val = int(txt)
        return val if len(txt) > 10 else val * 1000

    # Date-only: YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", txt):
        dt = datetime.strptime(txt, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

    # Datetime without TZ: YYYY-MM-DD HH:MM[:SS]
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?::\d{2})?)", txt)
    if m:
        fmt = "%Y-%m-%d %H:%M:%S" if ":" in m.group(2) and len(m.group(2).split(":")) == 3 else "%Y-%m-%d %H:%M"
        dt = datetime.strptime(txt, fmt).replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

    # ISO8601; support trailing Z
    iso = txt.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


_BUCKET_EXPRS = {
    "5m":  "date_trunc('hour', ts) + (((extract(minute from ts)::int) / 5) * 5) * interval '1 minute'",
    "15m": "date_trunc('hour', ts) + (((extract(minute from ts)::int) / 15) * 15) * interval '1 minute'",
    "1h":  "date_trunc('hour', ts)",
    "4h":  "date_trunc('day', ts) + (((extract(hour from ts)::int) / 4) * 4) * interval '1 hour'",
    "1d":  "date_trunc('day', ts)",
    "1w":  "date_trunc('week', ts)",
    "1mo": "date_trunc('month', ts)",
}


def _candles_table_name(inst: str, bar: str) -> Optional[str]:
    """Return candles schema table name for the given instrument/bar, or None for 1m."""
    bar_slug = bar.lower()
    if bar_slug == "1m":
        return None
    # Extract coin symbol: BTC-USDT → btc
    coin = inst.split("-")[0].lower()
    return f"candlesticks_{coin}_{bar_slug}"


def _ensure_candles_table(conn, table_name: str, inst: str, bar: str) -> None:
    """Create candles table and refresh_state entry if they don't exist yet."""
    bucket_expr = _BUCKET_EXPRS.get(bar.lower())
    if bucket_expr is None:
        return
    conn.execute(text(f"""
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
    conn.execute(text(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS uix_{table_name}_inst_ts
        ON candles.{table_name} (instrument_id, ts)
    """))
    conn.execute(text("""
        INSERT INTO candles.refresh_state (table_name, instrument_id, bucket_expr, last_source_ts)
        VALUES (:table_name, :instrument_id, :bucket_expr, NULL)
        ON CONFLICT (table_name) DO NOTHING
    """), {"table_name": table_name, "instrument_id": inst, "bucket_expr": bucket_expr})


def ensure_and_refresh_mv(db: DbConn, inst: str, bar: str) -> None:
    """Create (if needed) and incrementally refresh the candles schema table."""
    table_name = _candles_table_name(inst, bar)
    if table_name is None:
        return  # 1m uses raw candlesticks, no aggregation table

    with db.engine.connect() as conn:
        try:
            _ensure_candles_table(conn, table_name, inst, bar)
            conn.execute(text("SELECT candles.refresh_incremental(:t)"), {"t": table_name})
            conn.commit()
            print(f"Candles table refreshed: candles.{table_name}")
        except Exception as exc:
            conn.rollback()
            print(f"Candles refresh failed for {table_name}: {exc}")


DEFAULT_MV_BARS = ["5m", "15m", "1h", "4h", "1d", "1w", "1mo"]


def ensure_and_refresh_mv_multi(db: DbConn, inst: str, bars: Optional[list[str]] = None) -> None:
    """Refresh candles tables for a predefined set of bars for an instrument."""
    targets = bars or DEFAULT_MV_BARS
    for b in targets:
        ensure_and_refresh_mv(db, inst, b)


def main() -> int:
    load_env_file()
    args = parse_args()

    client = OkxMarketDataClient()
    db = DbConn(echo=args.echo)
    repo = CandlesRepo()

    since_ms = _parse_time_to_ms(args.since)
    until_ms = _parse_time_to_ms(args.until)
    if since_ms is not None:
        print(f"Ingesting since >= {since_ms} (epoch ms)")
    if until_ms is not None:
        print(f"Ingesting until <= {until_ms} (epoch ms)")

    total_upserted = 0
    # Start cursor: if an upper bound (until) is provided, begin paging from there.
    after_cursor: Optional[str] = str(until_ms) if until_ms is not None else None  # OKX 'after' pages to older data
    last_oldest_ts: Optional[int] = None

    # Start from history endpoint if requested
    use_history = bool(getattr(args, "use_history_first", False))
    if use_history:
        print("Using history endpoint first as requested.")
    if after_cursor is not None:
        from_ts = datetime.fromtimestamp(int(after_cursor) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        print(f"Starting pagination from after={after_cursor} ({from_ts}) due to --until")
    while total_upserted < args.max_rows:
        remain = args.max_rows - total_upserted
        per_request = max(1, min(int(args.limit), 300, remain))

        # Fetch with simple retry + exponential backoff on transient errors
        attempt = 0
        while True:
            try:
                if not use_history:
                    resp = client.get_candlesticks(
                        instrument_id=args.instrument_id,
                        bar=args.bar,
                        limit=per_request,
                        after=after_cursor,
                    )
                else:
                    resp = client.get_history_candlesticks(
                        instrument_id=args.instrument_id,
                        bar=args.bar,
                        limit=per_request,
                        after=after_cursor,
                    )
                break
            except OkxApiError as exc:
                # Do not retry on specific non-transient code 51001
                if str(getattr(exc, "code", "")).strip() == "51001":
                    print(f"Failed with non-retryable OKX error 51001: {exc}")
                    return 2
                attempt += 1
                if attempt > max(0, int(args.retries)):
                    print(f"Failed after retries: {exc}")
                    return 2
                delay = max(0.0, float(args.backoff)) * (float(args.backoff_mult) ** (attempt - 1))
                print(f"Transient error: {exc}; retrying in {delay:.2f}s (attempt {attempt}/{args.retries})")
                time.sleep(delay)
            except Exception as exc:
                attempt += 1
                if attempt > max(0, int(args.retries)):
                    print(f"Failed after retries: {exc}")
                    return 2
                delay = max(0.0, float(args.backoff)) * (float(args.backoff_mult) ** (attempt - 1))
                print(f"Transient error: {exc}; retrying in {delay:.2f}s (attempt {attempt}/{args.retries})")
                time.sleep(delay)
        data = resp.get("data") or []
        if not data:
            if not use_history:
                # Switch to history endpoint and retry this page once
                print("Standard candles returned no data; switching to history endpoint...")
                use_history = True
                continue
            print("No more data from OKX history; stopping.")
            break

        # Determine pagination cursor (oldest ts in this batch)
        try:
            batch_ts = [int(r[0]) for r in data]
        except Exception:
            print("Unexpected data format from OKX; stopping.")
            break
        oldest_ts = min(batch_ts)

        # Apply until (upper bound) then since (lower bound)
        data_to_use = data
        if until_ms is not None:
            data_to_use = [r for r in data_to_use if int(r[0]) <= until_ms]
            if not data_to_use and min(batch_ts) > until_ms:
                # Haven't reached 'until' yet; keep paginating
                pass
        if since_ms is not None:
            filtered = [r for r in data_to_use if int(r[0]) >= since_ms]
            if not filtered:
                # If even the newest in batch is older than since, stop
                if max(batch_ts) < since_ms:
                    print("Reached target 'since' boundary; stopping.")
                    break
                # Otherwise, proceed with next page
                data_to_use = []
            else:
                data_to_use = filtered

        # Parse and upsert
        rows = [parse_okx_candle_row(args.instrument_id, r) for r in data_to_use]
        with db.session_scope() as s:
            affected = repo.upsert_many(s, rows)
            total_upserted += affected

        # Compute next cursor and human-readable timestamps for logging
        next_after = oldest_ts - 1  # exclusive to avoid repeating the boundary candle
        def _fmt_ms(val) -> str:
            try:
                return datetime.fromtimestamp(int(val) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
            except Exception:
                return "n/a"

        after_human = _fmt_ms(after_cursor) if after_cursor is not None else "n/a"
        next_after_human = _fmt_ms(next_after)

        print(
            f"Fetched {len(data)} rows (req={per_request}), used={len(rows)}, upserted={affected}, total={total_upserted}, "
            f"after={after_cursor} ({after_human}) -> next_after={next_after} ({next_after_human})"
        )

        # Prevent infinite loop on duplicate cursor and advance strictly older
        if last_oldest_ts is not None and next_after >= last_oldest_ts:
            print("Pagination cursor did not advance; stopping to avoid loop.")
            break
        last_oldest_ts = next_after
        after_cursor = str(next_after)

        # Respect rate limits a bit
        if args.sleep_sec > 0:
            time.sleep(args.sleep_sec)

    if args.refresh_mv:
        try:
            ensure_and_refresh_mv(db, args.instrument_id, args.bar)
        except Exception as exc:
            print(f"Post-ingest MV refresh failed: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
