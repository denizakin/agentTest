from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from db.poco.run_header import RunHeader


@dataclass(frozen=True)
class NewBacktest:
    run_type: str = "backtest"  # backtest or optimize
    strategy_id: int = 0
    instrument_id: str = ""
    timeframe: str = ""
    strategy: str = ""
    params: Optional[Dict] = None
    cash: Optional[float] = None
    commission: Optional[float] = None
    slip_perc: Optional[float] = None
    slip_fixed: Optional[float] = None
    slip_open: Optional[bool] = None
    baseline: Optional[bool] = None
    notes: Optional[str] = None


class BacktestsRepo:
    """Repository for creating and listing backtest runs."""

    def create(self, session: Session, new_bt: NewBacktest) -> RunHeader:
        run = RunHeader(
            run_type=new_bt.run_type,
            strategy_id=new_bt.strategy_id,
            instrument_id=new_bt.instrument_id,
            timeframe=new_bt.timeframe,
            strategy=new_bt.strategy,
            params=new_bt.params,
            cash=new_bt.cash,
            commission=new_bt.commission,
            slip_perc=new_bt.slip_perc,
            slip_fixed=new_bt.slip_fixed,
            slip_open=new_bt.slip_open,
            baseline=new_bt.baseline,
            started_at=datetime.now(tz=timezone.utc),
            notes=new_bt.notes,
            status="queued",
            progress=0,
        )
        session.add(run)
        session.flush()
        return run

    def list_recent(self, session: Session, limit: int = 50, offset: int = 0, run_type: str = "backtest") -> List[RunHeader]:
        stmt = (
            select(RunHeader)
            .where(RunHeader.run_type == run_type)
            .order_by(RunHeader.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = session.scalars(stmt).all()
        return list(rows)

    def fetch_next_queued(self, session: Session) -> Optional[RunHeader]:
        """
        Fetch the next queued backtest/optimize row using SKIP LOCKED to avoid contention.
        """
        stmt = (
            select(RunHeader)
            .where(RunHeader.run_type.in_(["backtest", "optimize", "wfo"]))
            .where(RunHeader.status == "queued")
            .order_by(RunHeader.started_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return session.scalars(stmt).first()

    def get_by_id(self, session: Session, run_id: int) -> Optional[RunHeader]:
        return session.get(RunHeader, run_id)

    def get(self, session: Session, run_id: int) -> Optional[RunHeader]:
        return session.get(RunHeader, run_id)

    def find_matching(
        self,
        session: Session,
        strategy_id: int,
        instrument_id: str,
        timeframe: str,
        params: Optional[Dict] = None,
    ) -> Optional[RunHeader]:
        """Find a succeeded/running/queued backtest with the same strategy/instrument/timeframe/params."""
        stmt = (
            select(RunHeader)
            .where(RunHeader.run_type == "backtest")
            .where(RunHeader.strategy_id == strategy_id)
            .where(RunHeader.instrument_id == instrument_id)
            .where(RunHeader.timeframe == timeframe)
            .where(RunHeader.status.in_(["succeeded", "running", "queued"]))
            .order_by(RunHeader.started_at.desc())
            .limit(20)
        )
        candidates = session.scalars(stmt).all()
        # Compare via JSON to normalize int/float differences (10 vs 10.0)
        target_json = json.dumps(params or {}, sort_keys=True)
        for c in candidates:
            if json.dumps(c.params or {}, sort_keys=True) == target_json:
                return c
        return None

    def update_status(
        self,
        session: Session,
        run_id: int,
        status: str,
        progress: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        values: Dict[str, object] = {"status": status}
        if progress is not None:
            values["progress"] = progress
        if error is not None:
            values["error"] = error
        if status in {"succeeded", "failed"}:
            values["ended_at"] = datetime.now(tz=timezone.utc)

        stmt = (
            update(RunHeader)
            .where(RunHeader.id == run_id)
            .values(**values)
        )
        result = session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError(f"run not found for update_status (id={run_id})")
