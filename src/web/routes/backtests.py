from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.backtests_repo import BacktestsRepo, NewBacktest
from db.run_logs_repo import RunLogsRepo
from db.strategies_repo import StrategiesRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue

router = APIRouter(prefix="/backtests", tags=["backtests"])
backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()
runlogs_repo = RunLogsRepo()


class BacktestRequest(BaseModel):
    strategy_id: int
    instrument_id: str
    bar: str
    params: Optional[Dict[str, Any]] = None
    start_ts: Optional[str] = None  # ISO timestamp (inclusive)
    end_ts: Optional[str] = None    # ISO timestamp (inclusive)


class BacktestSummary(BaseModel):
    run_id: int
    job_id: str
    strategy_id: int
    strategy_name: Optional[str] = None
    instrument_id: str
    bar: str
    status: str
    submitted_at: datetime
    progress: int = 0
    error: Optional[str] = None


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
                strategy_id=r.strategy_id or 0,
                strategy_name=r.strategy,
                instrument_id=r.instrument_id,
                bar=r.timeframe,
                status=r.status or "unknown",
                submitted_at=r.started_at,
                progress=getattr(r, "progress", 0) or 0,
                error=getattr(r, "error", None),
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
            strategy_id=payload.strategy_id,
            instrument_id=payload.instrument_id,
            timeframe=payload.bar,
            strategy_name=strat.name,
            params={
                "strategy_id": payload.strategy_id,
                **(payload.params or {}),
                **({"start_ts": payload.start_ts} if payload.start_ts else {}),
                **({"end_ts": payload.end_ts} if payload.end_ts else {}),
            },
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
        progress=0,
    )


@router.get("/{run_id}", response_model=BacktestSummary)
def get_backtest(run_id: int, session: Session = Depends(get_db)) -> BacktestSummary:
    run = backtests_repo.get(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest not found")
    return BacktestSummary(
        run_id=run.id,
        job_id="n/a",
        strategy_id=run.strategy_id or 0,
        strategy_name=run.strategy,
        instrument_id=run.instrument_id,
        bar=run.timeframe,
        status=run.status or "unknown",
        submitted_at=run.started_at,
        progress=getattr(run, "progress", 0) or 0,
        error=getattr(run, "error", None),
    )


class RunLogItem(BaseModel):
    ts: datetime
    level: str
    message: str


@router.get("/{run_id}/logs", response_model=List[RunLogItem])
def list_backtest_logs(run_id: int, limit: int = 200, offset: int = 0, session: Session = Depends(get_db)) -> List[RunLogItem]:
    run = backtests_repo.get(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest not found")
    logs = runlogs_repo.list_logs(session, run_id, limit=limit, offset=offset)
    return [RunLogItem(ts=log.ts, level=log.level, message=log.message) for log in logs]
