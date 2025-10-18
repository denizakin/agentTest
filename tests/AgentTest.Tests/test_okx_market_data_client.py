"""Tests for OKX market data client."""
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLIENT_DIR = PROJECT_ROOT / "src" / "AgentTest"
if str(CLIENT_DIR) not in sys.path:
    sys.path.append(str(CLIENT_DIR))

from okx_market_data_client import OkxApiError, OkxMarketDataClient  # type: ignore


class FakeMarketApi:
    """Lightweight stub to emulate the python-okx MarketAPI."""

    def __init__(self, response=None, exception=None) -> None:
        self.response = response or {"code": "0", "data": []}
        self.exception = exception
        self.last_kwargs = None

    def get_candlesticks(self, **kwargs):
        self.last_kwargs = kwargs
        if self.exception:
            raise self.exception
        return self.response


def test_get_candlesticks_passes_parameters_and_returns_response():
    fake_response = {"code": "0", "data": [["timestamp", "open", "high", "low", "close", "volume"]]}
    market_api = FakeMarketApi(response=fake_response)
    client = OkxMarketDataClient(market_api=market_api)

    result = client.get_candlesticks(
        instrument_id="BTC-USDT",
        bar="5m",
        limit=50,
        before="12345",
        after="67890",
    )

    assert result == fake_response
    assert market_api.last_kwargs == {
        "instId": "BTC-USDT",
        "bar": "5m",
        "limit": "50",
        "before": "12345",
        "after": "67890",
    }


def test_get_candlesticks_raises_on_api_exception():
    market_api = FakeMarketApi(exception=RuntimeError("boom"))
    client = OkxMarketDataClient(market_api=market_api)

    with pytest.raises(OkxApiError) as err:
        client.get_candlesticks("BTC-USDT")

    assert "Failed to retrieve candlesticks" in str(err.value)


def test_get_candlesticks_raises_on_error_code():
    market_api = FakeMarketApi(response={"code": "51000", "msg": "invalid instId"})
    client = OkxMarketDataClient(market_api=market_api)

    with pytest.raises(OkxApiError) as err:
        client.get_candlesticks("BTC-USDT")

    assert "OKX API error 51000" in str(err.value)
