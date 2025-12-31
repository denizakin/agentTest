from __future__ import annotations

from typing import List

from sqlalchemy import text
from sqlalchemy.orm import Session


class CoinInstrumentsRepo:
    """Access layer for coin instruments derived from candlesticks."""

    def list_instruments(self, session: Session) -> List[str]:
        result = session.execute(text("select instrument_id from mv_coin_instruments order by instrument_id"))
        return [row[0] for row in result.fetchall()]

    def refresh_view(self, session: Session) -> None:
        """Refresh the materialized view to pick up new instruments."""
        session.execute(text("refresh materialized view mv_coin_instruments"))
