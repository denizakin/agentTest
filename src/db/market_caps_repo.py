from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, List, Mapping

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from db.poco.market_cap import MarketCap


@dataclass(frozen=True)
class MarketCapRow:
    snapshot_ts: datetime
    symbol: str
    market_cap_usd: Decimal


class MarketCapsRepo:
    """Repository for inserting/upserting CoinMarketCap snapshot rows."""

    def upsert_many(self, session: Session, rows: Iterable[MarketCapRow]) -> int:
        payload: List[Mapping[str, object]] = [
            {
                "snapshot_ts": r.snapshot_ts,
                "symbol": r.symbol,
                "market_cap_usd": r.market_cap_usd,
            }
            for r in rows
        ]
        if not payload:
            return 0

        stmt = insert(MarketCap.__table__).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[MarketCap.snapshot_ts, MarketCap.symbol],
            set_={"market_cap_usd": stmt.excluded.market_cap_usd},
        )
        result = session.execute(stmt)
        return result.rowcount if result.rowcount and result.rowcount > 0 else len(payload)
