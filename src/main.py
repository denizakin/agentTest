"""Simple entry-point to fetch live candlesticks from OKX and print JSON.

Run from project root:
    python src/main.py --inst BTC-USDT --bar 1m --limit 10

Requires python-okx and an optional resources/.env with OKX_* values.
If no credentials are provided, public endpoints may still work for
market data, depending on OKX policy and library behavior.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from api.okx_market_data_client import OkxMarketDataClient, OkxApiError
from config import load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch live OKX candlesticks")
    parser.add_argument("--inst", dest="instrument_id", default="BTC-USDT", help="Instrument ID, e.g. BTC-USDT")
    parser.add_argument("--bar", dest="bar", default="1m", help="Candle granularity, e.g. 1m, 5m, 1h")
    parser.add_argument("--limit", dest="limit", type=int, default=10, help="Number of rows to fetch (<=300)")
    parser.add_argument("--before", dest="before", default=None, help="Pagination cursor: before")
    parser.add_argument("--after", dest="after", default=None, help="Pagination cursor: after")
    return parser.parse_args()


def main() -> int:
    # Load environment variables from resources/.env if available
    load_env_file()

    args = parse_args()

    client = OkxMarketDataClient()
    try:
        resp: Dict[str, Any] = client.get_candlesticks(
            instrument_id=args.instrument_id,
            bar=args.bar,
            limit=args.limit,
            before=args.before,
            after=args.after,
        )
    except OkxApiError as exc:
        print(f"Error fetching candlesticks: {exc}")
        return 1

    print("Raw response JSON:")
    print(json.dumps(resp, indent=2, ensure_ascii=False))

    data = resp.get("data") or []
    if data:
        print("\nParsed rows (timestamp, open, high, low, close, volume):")
        for row in data:
            # Rows are typically [ts, o, h, l, c, vol, ...]
            print(row)
    else:
        print("\nNo data array found in response.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
