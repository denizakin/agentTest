from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.run_header import RunHeader


@dataclass(frozen=True)
class NewBacktest:
    instrument_id: str
    timeframe: str
    strategy_name: str
    params: Optional[Dict] = None
    notes: Optional[str] = None


class BacktestsRepo:
    """Repository for creating and listing backtest runs."""

    def create(self, session: Session, new_bt: NewBacktest) -> RunHeader:
        run = RunHeader(
            run_type="backtest",
            instrument_id=new_bt.instrument_id,
            timeframe=new_bt.timeframe,
            strategy=new_bt.strategy_name,
            params=new_bt.params,
            started_at=datetime.now(tz=timezone.utc),
            notes=new_bt.notes,
        )
        session.add(run)
        session.flush()
        return run

    def list_recent(self, session: Session, limit: int = 50, offset: int = 0) -> List[RunHeader]:
        stmt = (
            select(RunHeader)
            .where(RunHeader.run_type == "backtest")
            .order_by(RunHeader.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = session.scalars(stmt).all()
        return list(rows)

