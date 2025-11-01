from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


class MvCandlesRepo:
    """Helpers to query materialized candle views for verification."""

    def get_btc_15m_latest(self, session: Session, limit: int = 50) -> List[Tuple]:
        """Return latest rows from mv_candlesticks_btc_15m.

        Columns: ts, instrument_id, open, high, low, close, volume
        """
        stmt = text(
            """
            SELECT ts, instrument_id, open, high, low, close, volume
            FROM mv_candlesticks_btc_15m
            ORDER BY ts DESC
            LIMIT :limit
            """
        )
        rows = session.execute(stmt, {"limit": int(max(1, limit))}).all()
        return rows

