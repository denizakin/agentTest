from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.backtests_repo import BacktestsRepo, NewBacktest
from db.strategies_repo import StrategiesRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue

router = APIRouter(prefix="/backtests", tags=["backtests"])
backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()


class BacktestRequest(BaseModel):
    strategy_id: int
    instrument_id: str
    bar: str
    params: Optional[Dict[str, Any]] = None


class BacktestSummary(BaseModel):
    run_id: int
    job_id: str
    strategy_id: int
    strategy_name: Optional[str] = None
    instrument_id: str
    bar: str
    status: str
    submitted_at: datetime


@router.get("", response_model=List[BacktestSummary])
def list_backtests(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db),
) -> List[BacktestSummary]:
    """
    List recent backtests from run_headers.
    """
    rows = backtests_repo.list_recent(session, limit=limit, offset=offset)
    summaries: List[BacktestSummary] = []
    for r in rows:
        summaries.append(
            BacktestSummary(
                run_id=r.id,
                job_id="n/a",
                strategy_id=0,
                strategy_name=r.strategy,
                instrument_id=r.instrument_id,
                bar=r.timeframe,
                status="unknown",
                submitted_at=r.started_at,
            )
        )
    return summaries


@router.post("", response_model=BacktestSummary, status_code=status.HTTP_202_ACCEPTED)
def enqueue_backtest(
    payload: BacktestRequest,
    queue: JobQueue = Depends(get_job_queue),
    session: Session = Depends(get_db),
) -> BacktestSummary:
    """
    Enqueue a backtest job, persist a run_header row, and return the handle.
    """
    # Verify strategy exists (maps ID to name)
    strat = strategies_repo.get_by_id(session, payload.strategy_id)
    if strat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy not found")

    run = backtests_repo.create(
        session,
        NewBacktest(
            instrument_id=payload.instrument_id,
            timeframe=payload.bar,
            strategy_name=strat.name,
            params=payload.params,
        ),
    )
    session.commit()
    session.refresh(run)

    job = Job(payload={"type": "backtest", "run_id": run.id, "data": payload.model_dump()})
    job_id = queue.enqueue(job)
    return BacktestSummary(
        run_id=run.id,
        job_id=job_id,
        strategy_id=payload.strategy_id,
        strategy_name=strat.name,
        instrument_id=payload.instrument_id,
        bar=payload.bar,
        status="queued",
        submitted_at=datetime.now(tz=timezone.utc),
    )
