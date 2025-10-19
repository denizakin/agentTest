"""OKX market data client responsible for candlestick retrieval."""
from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from okx import MarketData  # type: ignore
except ImportError as exc:  # pragma: no cover - executed only when dependency missing
    MarketData = None
    _IMPORT_ERROR: Optional[ImportError] = exc
else:
    _IMPORT_ERROR = None


class OkxApiError(RuntimeError):
    """Raised when the OKX API responds with an error or the request fails."""


class OkxMarketDataClient:
    """High level helper for OKX candlestick (k-line) queries.

    Reads OKX credentials and environment flag from the central config
    module (see ``src/config.py``). Ensure ``load_env_file`` is
    able to read ``resources/.env`` or the variables are present in the
    process environment.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        passphrase: Optional[str] = None,
        flag: Optional[str] = None,
    ) -> None:
        """
        Create a new OKX market data client.

        Parameters:
            api_key: Optional API key. Defaults to the OKX_API_KEY env var.
            secret_key: Optional API secret. Defaults to OKX_SECRET_KEY env var.
            passphrase: Optional passphrase. Defaults to OKX_PASSPHRASE env var.
            flag: Trading flag (0=real, 1=test). Defaults to "0".
        """
        # Enforce using central config for env values
        from config import load_env_file, get_okx_api_config  # type: ignore

        load_env_file()
        okx_cfg = get_okx_api_config()

        self.api_key = api_key or okx_cfg.get("OKX_API_KEY")
        self.secret_key = secret_key or okx_cfg.get("OKX_SECRET_KEY")
        self.passphrase = passphrase or okx_cfg.get("OKX_PASSPHRASE")
        env_flag = okx_cfg.get("OKX_FLAG")
        self.flag = flag if flag is not None else (env_flag or "0")
        self._market_api = self._build_market_api()

    def get_candlesticks(
        self,
        instrument_id: str,
        bar: str = "1m",
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve candlestick data for the specified instrument.

        Parameters:
            instrument_id: Instrument identifier (e.g., "BTC-USDT").
            bar: Candlestick granularity such as "1m", "5m", "1h".
            limit: Number of rows to fetch (max allowed by OKX is 300).
            before: Pagination cursor to get data before this timestamp/id.
            after: Pagination cursor to get data after this timestamp/id.

        Returns:
            Raw response dictionary as returned by the OKX SDK.

        Raises:
            OkxApiError: When the API reports an error or cannot be reached.
        """
        params: Dict[str, Any] = {
            "instId": instrument_id,
            "bar": bar,
            "limit": str(limit),
        }
        if before:
            params["before"] = str(before)
        if after:
            params["after"] = str(after)

        try:
            response = self._market_api.get_candlesticks(**params)
        except Exception as exc:
            raise OkxApiError(f"Failed to retrieve candlesticks: {exc}") from exc

        if isinstance(response, dict):
            code = response.get("code")
            if code not in (None, "0", 0):
                message = response.get("msg") or response.get("message") or "unknown error"
                raise OkxApiError(f"OKX API error {code}: {message}")
        return response

    def _build_market_api(self) -> Any:
        """Instantiate the python-okx MarketAPI or raise when unavailable."""
        if MarketData is None:
            raise ImportError(
                "python-okx is required to use OkxMarketDataClient. Install python-okx 0.4.0."
            ) from _IMPORT_ERROR

        return MarketData.MarketAPI(
            api_key=self.api_key,
            api_secret_key=self.secret_key,
            passphrase=self.passphrase,
            flag=self.flag,
        )
