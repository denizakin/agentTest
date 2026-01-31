"""CLI: Read latest top-N from cmc_market_caps, then ingest OKX candlesticks incrementally.

Behavior:
- Pull top N (default 100) by market cap from the latest cmc_market_caps snapshot.
- For each symbol, assume USDT spot pair on OKX (e.g., BTC -> BTC-USDT).
- Determine last stored candle ts in DB; start from there +1ms, otherwise 2017-01-01 UTC.
- Fetch candlesticks from OKX up to now, upserting into `candlesticks`.

Usage example:
    python src/main_cmc_ingest_candles.py --limit 100 --bar 1m --per-req 300 --sleep 0.2
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import text

from api.okx_market_data_client import OkxMarketDataClient, OkxApiError
from config import load_env_file
from db.candles_repo import CandlesRepo, parse_okx_candle_row
from db.db_conn import DbConn
from main_ingest import ensure_and_refresh_mv_multi, DEFAULT_MV_BARS


START_TS = datetime(2017, 1, 1, tzinfo=timezone.utc)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CMC -> OKX candlestick ingester for top market cap assets")
    p.add_argument("--limit", type=int, default=100, help="How many top assets to pull from cmc_market_caps")
    p.add_argument("--bar", default="1m", help="OKX candle granularity (e.g., 1m, 1h, 1d)")
    p.add_argument("--per-req", dest="per_req", type=int, default=300, help="Rows per OKX request (<=300)")
    p.add_argument(
        "--max-rows",
        dest="max_rows",
        type=int,
        default=0,
        help="Optional max rows per instrument (0=unlimited)",
    )
    p.add_argument("--sleep", dest="sleep_sec", type=float, default=0.2, help="Sleep seconds between OKX requests")
    p.add_argument("--use-history-first", action="store_true", help="Start with history endpoint for deeper range")
    p.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    p.add_argument("--refresh-mv", action="store_true", help="Create/refresh per-instrument MV after ingest")
    return p.parse_args()


def _fmt_ms(val: Optional[int]) -> str:
    if val is None:
        return "n/a"
    try:
        return datetime.fromtimestamp(int(val) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    except Exception:
        return "n/a"


def ingest_instrument(
    client: OkxMarketDataClient,
    repo: CandlesRepo,
    session,
    instrument_id: str,
    since_ms: int,
    max_rows: Optional[int],
    per_request: int,
    sleep_sec: float,
    bar: str,
    use_history_first: bool = False,
) -> int:
    max_rows_limit = max_rows if max_rows and max_rows > 0 else None
    total_upserted = 0
    after_cursor: Optional[str] = None  # start from latest
    last_oldest_ts: Optional[int] = None
    use_history = use_history_first

    while True:
        per_req = max(1, min(int(per_request), 300))
        if max_rows_limit is not None:
            remain = max_rows_limit - total_upserted
            if remain <= 0:
                print(f"  [{instrument_id}] reached max_rows limit={max_rows_limit}; stopping.")
                break
            per_req = min(per_req, remain)

        # Fetch page with retry/backoff (simple, single retry loop)
        attempt = 0
        while True:
            try:
                if not use_history:
                    resp = client.get_candlesticks(
                        instrument_id=instrument_id,
                        bar=bar,
                        limit=per_req,
                        after=after_cursor,
                    )
                else:
                    resp = client.get_history_candlesticks(
                        instrument_id=instrument_id,
                        bar=bar,
                        limit=per_req,
                        after=after_cursor,
                    )
                break
            except OkxApiError as exc:
                if str(getattr(exc, "code", "")).strip() == "51001":
                    print(f"  [{instrument_id}] non-retryable OKX error 51001: {exc}")
                    return total_upserted
                attempt += 1
                if attempt > 10:
                    print(f"  [{instrument_id}] failed after retries (10): {exc}")
                    return total_upserted
                delay = 0.5 * (2 ** (attempt - 1))
                print(f"  [{instrument_id}] transient error: {exc}; retrying in {delay:.2f}s (attempt {attempt}/10)")
                time.sleep(delay)
            except Exception as exc:
                attempt += 1
                if attempt > 10:
                    print(f"  [{instrument_id}] failed after retries (10): {exc}")
                    return total_upserted
                delay = 0.5 * (2 ** (attempt - 1))
                print(f"  [{instrument_id}] transient error: {exc}; retrying in {delay:.2f}s (attempt {attempt}/10)")
                time.sleep(delay)

        data = resp.get("data") or []
        if not data:
            if not use_history:
                print(f"  [{instrument_id}] switching to history endpoint...")
                use_history = True
                continue
            print(f"  [{instrument_id}] no more data; stopping.")
            break

        try:
            batch_ts = [int(r[0]) for r in data]
        except Exception:
            print(f"  [{instrument_id}] unexpected data format; stopping.")
            break
        oldest_ts = min(batch_ts)

        # Apply lower bound (since_ms)
        data_to_use = [r for r in data if int(r[0]) >= since_ms]
        if not data_to_use:
            if max(batch_ts) < since_ms:
                print(f"  [{instrument_id}] reached since boundary; stopping.")
                break

        rows = [parse_okx_candle_row(instrument_id, r) for r in data_to_use]
        affected = repo.upsert_many(session, rows)
        total_upserted += affected

        next_after = oldest_ts - 1
        if last_oldest_ts is not None and next_after >= last_oldest_ts:
            print(f"  [{instrument_id}] cursor did not advance; stopping to avoid loop.")
            break
        last_oldest_ts = next_after
        after_cursor = str(next_after)

        print(
            f"  [{instrument_id}] fetched={len(data)} used={len(rows)} upserted={affected} total={total_upserted} "
            f"after={after_cursor} ({_fmt_ms(int(after_cursor)) if after_cursor else 'n/a'})"
        )

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    return total_upserted


def _load_symbols_from_db(db: DbConn, limit: int) -> List[str]:
    """Read latest snapshot from cmc_market_caps, return top-N symbols."""
    with db.engine.connect() as conn:
        latest_ts = conn.execute(text("SELECT max(snapshot_ts) FROM cmc_market_caps")).scalar_one_or_none()
        if latest_ts is None:
            return []

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
    return symbols


def main() -> int:
    load_env_file()
    args = parse_args()

    db = DbConn(echo=args.echo)
    run_started = datetime.now(timezone.utc)
    print(f"Run started at {run_started.isoformat()}")
    symbols = _load_symbols_from_db(db, args.limit)
    if not symbols:
        print("No symbols found in cmc_market_caps; run main_cmc_market_caps.py first.")
        return 1

    repo = CandlesRepo()
    client = OkxMarketDataClient()

    print(f"Processing {len(symbols)} symbols from latest cmc_market_caps snapshot...")
    with db.session_scope() as session:
        for sym in symbols:
            inst_id = f"{sym.upper()}-USDT"
            latest = repo.get_latest_ts(session, inst_id)
            since_dt = latest + timedelta(milliseconds=1) if latest else START_TS
            since_ms = int(since_dt.timestamp() * 1000)
            print(f"- {inst_id}: since {_fmt_ms(since_ms)} (latest={latest.isoformat() if latest else 'none'})")
            upserted = ingest_instrument(
                client=client,
                repo=repo,
                session=session,
                instrument_id=inst_id,
                since_ms=since_ms,
                max_rows=args.max_rows,
                per_request=args.per_req,
                sleep_sec=args.sleep_sec,
                bar=args.bar,
                use_history_first=args.use_history_first,
            )
            session.commit()
            print(f"  [{inst_id}] done, upserted {upserted} rows.")
            if args.refresh_mv:
                try:
                    print(f"  [{inst_id}] refreshing MVs for bars={DEFAULT_MV_BARS} ...")
                    ensure_and_refresh_mv_multi(db, inst_id, DEFAULT_MV_BARS)
                except Exception as exc:
                    print(f"  [{inst_id}] MV refresh failed: {exc}")

    run_finished = datetime.now(timezone.utc)
    duration = run_finished - run_started
    print(f"Run finished at {run_finished.isoformat()} (duration {duration})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
