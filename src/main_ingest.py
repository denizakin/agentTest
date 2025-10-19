"""CLI: Ingest OKX candlesticks into PostgreSQL.

Fetches latest kline data via OkxMarketDataClient and upserts rows
into the `candlesticks` table using SQLAlchemy.
"""
from __future__ import annotations

import argparse
from typing import List

from config import load_env_file
from db.db_conn import DbConn
from db.candles_repo import CandlesRepo, parse_okx_candle_row
from api.okx_market_data_client import OkxMarketDataClient


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest OKX candlesticks into DB")
    p.add_argument("--inst", dest="instrument_id", default="BTC-USDT", help="Instrument ID, e.g. BTC-USDT")
    p.add_argument("--bar", dest="bar", default="1m", help="Candle granularity, e.g. 1m, 5m, 1h")
    p.add_argument("--limit", dest="limit", type=int, default=50, help="Number of rows to fetch (<=300)")
    p.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    return p.parse_args()


def main() -> int:
    load_env_file()
    args = parse_args()

    client = OkxMarketDataClient()
    resp = client.get_candlesticks(
        instrument_id=args.instrument_id,
        bar=args.bar,
        limit=args.limit,
    )
    data = resp.get("data") or []
    if not data:
        print("No candlestick rows returned from OKX.")
        return 1

    rows = [parse_okx_candle_row(args.instrument_id, r) for r in data]

    db = DbConn(echo=args.echo)
    repo = CandlesRepo()
    with db.session_scope() as s:
        affected = repo.upsert_many(s, rows)
        print(f"Upserted rows: {affected}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

