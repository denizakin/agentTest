from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.backtests_repo import BacktestsRepo, NewBacktest
from db.strategies_repo import StrategiesRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue

router = APIRouter(prefix="/jobs", tags=["jobs"])

backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()


class BacktestJobRequest(BaseModel):
    strategy_id: int
    instrument_id: str
    bar: str
    params: Optional[Dict[str, Any]] = None
    start_ts: Optional[str] = None  # ISO timestamp (inclusive)
    end_ts: Optional[str] = None    # ISO timestamp (inclusive)
    plot: Optional[bool] = None
    refresh: Optional[bool] = None
    baseline: Optional[bool] = None
    parallel_baseline: Optional[bool] = None
    use_sizer: Optional[bool] = None
    coc: Optional[bool] = None
    slip_perc: Optional[float] = None
    slip_fixed: Optional[float] = None
    slip_open: Optional[bool] = None
    cash: Optional[float] = None
    commission: Optional[float] = None
    stake: Optional[int] = None


class BacktestJobResponse(BaseModel):
    run_id: int
    job_id: str
    strategy_id: int
    strategy_name: str
    instrument_id: str
    bar: str
    status: str
    submitted_at: datetime
    progress: int = 0
    error: Optional[str] = None


@router.post("/backtest", response_model=BacktestJobResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_backtest_job(
    payload: BacktestJobRequest,
    session: Session = Depends(get_db),
    queue: JobQueue = Depends(get_job_queue),
) -> BacktestJobResponse:
    """
    Enqueue a backtest execution job and persist run_headers entry.

    This is a higher-level job endpoint intended to mirror script-based backtest runs.
    """
    strat = strategies_repo.get_by_id(session, payload.strategy_id)
    if strat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy not found")

    merged_params: Dict[str, Any] = {
        "strategy_id": payload.strategy_id,
        **(payload.params or {}),
        **({"start_ts": payload.start_ts} if payload.start_ts else {}),
        **({"end_ts": payload.end_ts} if payload.end_ts else {}),
    }
    # ensure top-level flags/values are also stored if provided
    for key in [
        "plot", "refresh", "baseline", "parallel_baseline", "use_sizer", "coc",
        "slip_perc", "slip_fixed", "slip_open", "cash", "commission", "stake"
    ]:
        val = getattr(payload, key, None)
        if val is not None and key not in merged_params:
            merged_params[key] = val

    run = backtests_repo.create(
        session,
        NewBacktest(
            strategy_id=payload.strategy_id,
            instrument_id=payload.instrument_id,
            timeframe=payload.bar,
            strategy_name=strat.name,
            params=merged_params,
        ),
    )
    session.commit()
    session.refresh(run)

    job = Job(
        payload={
            "type": "backtest",
            "run_id": run.id,
            "strategy_id": payload.strategy_id,
            "instrument_id": payload.instrument_id,
            "bar": payload.bar,
            "params": payload.params,
        }
    )
    job_id = queue.enqueue(job)

    return BacktestJobResponse(
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
