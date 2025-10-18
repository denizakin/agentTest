"""Quick smoke script to fetch BTC-USDT candlesticks from OKX."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from urllib import parse, request

PROJECT_ROOT = Path(__file__).resolve().parent
CLIENT_PATH = PROJECT_ROOT / "src" / "AgentTest"
import sys

if str(CLIENT_PATH) not in sys.path:
    sys.path.append(str(CLIENT_PATH))

from okx_market_data_client import OkxMarketDataClient, OkxApiError  # type: ignore


class RestMarketApi:
    """Minimal MarketAPI replacement using the public OKX REST endpoint."""

    BASE_URL = "https://www.okx.com/api/v5/market/candles"

    def get_candlesticks(self, **kwargs: Any) -> Dict[str, Any]:
        query_string = parse.urlencode(kwargs)
        url = f"{self.BASE_URL}?{query_string}"
        with request.urlopen(url, timeout=10) as response:
            payload = response.read()
        return json.loads(payload)


def main() -> None:
    client = OkxMarketDataClient(market_api=RestMarketApi())
    try:
        data = client.get_candlesticks(
            instrument_id="BTC-USDT",
            bar="1m",
            limit=10,
        )
    except OkxApiError as exc:
        print(f"Request failed: {exc}")
        raise SystemExit(1) from exc

    print("Fetched candlesticks:")
    for row in data.get("data", []):
        print(row)


if __name__ == "__main__":
    main()
