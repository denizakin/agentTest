"""CLI: Fetch top N market caps from CoinMarketCap and persist snapshots.

Example:
    python src/main_cmc_market_caps.py --limit 100 --convert USD
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from config import load_env_file
from db.db_conn import DbConn
from db.market_caps_repo import MarketCapsRepo, MarketCapRow


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch top market caps from CoinMarketCap and store in DB")
    p.add_argument("--limit", type=int, default=100, help="How many assets to fetch (max 5000 per CMC docs)")
    p.add_argument("--convert", default="USD", help="Fiat/crypto symbol to convert market cap into (e.g., USD, USDT)")
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

    data = payload.get("data") or []
    return data


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

    snapshot_ts = datetime.now(timezone.utc)
    rows: List[MarketCapRow] = []
    convert_key = args.convert.upper()
    for item in listings:
        symbol = item.get("symbol")
        quote = (item.get("quote") or {}).get(convert_key) or {}
        mc_val = quote.get("market_cap")
        if symbol and mc_val is not None:
            rows.append(MarketCapRow(snapshot_ts=snapshot_ts, symbol=symbol, market_cap_usd=Decimal(str(mc_val))))

    if not rows:
        print("No market cap rows parsed; nothing to insert.")
        return 0

    repo = MarketCapsRepo()
    db = DbConn(echo=args.echo)
    with db.session_scope() as s:
        affected = repo.upsert_many(s, rows)

    print(f"Fetched {len(listings)} listings, parsed {len(rows)} rows, upserted {affected} rows at {snapshot_ts.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
