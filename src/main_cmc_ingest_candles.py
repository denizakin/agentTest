"""CLI: Fetch top-N coins from CoinMarketCap, then ingest OKX candlesticks incrementally.

Behavior:
- Pull top N (default 100) by market cap from CMC.
- For each symbol, assume USDT spot pair on OKX (e.g., BTC -> BTC-USDT).
- Determine last stored candle ts in DB; start from there +1ms, otherwise 2017-01-01 UTC.
- Fetch candlesticks from OKX up to now, upserting into `candlesticks`.

Usage example:
    python src/main_cmc_ingest_candles.py --limit 100 --bar 1m --per-req 300 --sleep 0.2
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from api.okx_market_data_client import OkxMarketDataClient
from config import load_env_file
from db.candles_repo import CandlesRepo, parse_okx_candle_row
from db.db_conn import DbConn


START_TS = datetime(2017, 1, 1, tzinfo=timezone.utc)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CMC -> OKX candlestick ingester for top market cap assets")
    p.add_argument("--limit", type=int, default=100, help="How many top assets to fetch from CMC")
    p.add_argument("--convert", default="USD", help="CMC convert symbol (default USD)")
    p.add_argument("--bar", default="1m", help="OKX candle granularity (e.g., 1m, 1h, 1d)")
    p.add_argument("--per-req", dest="per_req", type=int, default=300, help="Rows per OKX request (<=300)")
    p.add_argument("--max-rows", dest="max_rows", type=int, default=200_000, help="Max rows per instrument")
    p.add_argument("--sleep", dest="sleep_sec", type=float, default=0.2, help="Sleep seconds between OKX requests")
    p.add_argument("--use-history-first", action="store_true", help="Start with history endpoint for deeper range")
    p.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    return p.parse_args()


def _fetch_cmc_listings(api_key: str, limit: int, convert: str) -> List[dict]:
    params = f"limit={limit}&convert={convert.upper()}"
    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "X-CMC_PRO_API_KEY": api_key,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    status = payload.get("status") or {}
    if status.get("error_code"):
        raise RuntimeError(f"CMC error {status.get('error_code')}: {status.get('error_message')}")

    return payload.get("data") or []


def _is_stablecoin(item: dict) -> bool:
    symbol = (item.get("symbol") or "").upper()
    tags = [t.lower() for t in (item.get("tags") or []) if isinstance(t, str)]
    if any("stablecoin" in t for t in tags):
        return True
    # Fallback symbol-based list for safety
    known = {
        "USDT",
        "USDC",
        "DAI",
        "TUSD",
        "BUSD",
        "FDUSD",
        "USDD",
        "PYUSD",
        "GUSD",
        "USDP",
        "LUSD",
        "FRAX",
        "EURS",
        "EURT",
        "EURL",
    }
    return symbol in known


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
    max_rows: int,
    per_request: int,
    sleep_sec: float,
    bar: str,
    use_history_first: bool = False,
) -> int:
    total_upserted = 0
    after_cursor: Optional[str] = None  # start from latest
    last_oldest_ts: Optional[int] = None
    use_history = use_history_first

    while total_upserted < max_rows:
        remain = max_rows - total_upserted
        per_req = max(1, min(int(per_request), 300, remain))

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
            except Exception as exc:
                attempt += 1
                if attempt > 3:
                    print(f"  [{instrument_id}] failed after retries: {exc}")
                    return total_upserted
                delay = 0.5 * (2 ** (attempt - 1))
                print(f"  [{instrument_id}] transient error: {exc}; retrying in {delay:.2f}s (attempt {attempt}/3)")
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


def main() -> int:
    load_env_file()
    args = parse_args()

    api_key = os.getenv("CMC_API_KEY")
    if not api_key:
        print("Missing CMC_API_KEY in environment/resources/.env")
        return 2

    try:
        listings = _fetch_cmc_listings(api_key=api_key, limit=args.limit, convert=args.convert)
    except Exception as exc:
        print(f"Failed to fetch CoinMarketCap listings: {exc}")
        return 1

    filtered = [item for item in listings if item.get("symbol") and not _is_stablecoin(item)]
    if not filtered:
        print("No non-stablecoin symbols from CMC response; aborting.")
        return 1

    symbols = [item.get("symbol") for item in filtered]
    if len(symbols) < len(listings):
        skipped = len(listings) - len(symbols)
        print(f"Skipped {skipped} stablecoin entries; proceeding with {len(symbols)} symbols.")

    db = DbConn(echo=args.echo)
    repo = CandlesRepo()
    client = OkxMarketDataClient()

    print(f"Processing {len(symbols)} symbols from CMC top list...")
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
