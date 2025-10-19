from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, List, Mapping

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from db.poco.candlestick import Candlestick


@dataclass(frozen=True)
class CandleRow:
    instrument_id: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class CandlesRepo:
    """Repository for inserting/upserting candlestick rows."""

    def upsert_many(self, session: Session, rows: Iterable[CandleRow]) -> int:
        payload: List[Mapping[str, object]] = [
            {
                "instrument_id": r.instrument_id,
                "ts": r.ts,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
        if not payload:
            return 0

        stmt = insert(Candlestick.__table__).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Candlestick.instrument_id, Candlestick.ts],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        result = session.execute(stmt)
        # SQLAlchemy may return -1 for rowcount in some drivers; fall back to len(payload)
        return result.rowcount if result.rowcount and result.rowcount > 0 else len(payload)


def parse_okx_candle_row(inst_id: str, row: list) -> CandleRow:
    """Parse OKX kline row into CandleRow.

    OKX typically returns rows as:
        [ts_ms, open, high, low, close, volume, ...]
    """
    ts_ms = int(row[0])
    return CandleRow(
        instrument_id=inst_id,
        ts=datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc),
        open=Decimal(str(row[1])),
        high=Decimal(str(row[2])),
        low=Decimal(str(row[3])),
        close=Decimal(str(row[4])),
        volume=Decimal(str(row[5])),
    )

