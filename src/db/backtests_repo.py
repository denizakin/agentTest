from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, text
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
            status="queued",
            progress=0,
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

    def fetch_next_queued(self, session: Session) -> Optional[RunHeader]:
        """
        Fetch the next queued backtest row using SKIP LOCKED to avoid contention.
        """
        stmt = (
            select(RunHeader)
            .where(RunHeader.run_type == "backtest")
            .where(RunHeader.status == "queued")
            .order_by(RunHeader.started_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return session.scalar(stmt)

    def get(self, session: Session, run_id: int) -> Optional[RunHeader]:
        return session.get(RunHeader, run_id)

    def update_status(
        self,
        session: Session,
        run_id: int,
        status: str,
        progress: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        run = session.get(RunHeader, run_id)
        if run is None:
            raise ValueError("run not found")
        run.status = status
        if progress is not None:
            run.progress = progress
        if error is not None:
            run.error = error
        if status in {"succeeded", "failed"}:
            run.ended_at = datetime.now(tz=timezone.utc)
