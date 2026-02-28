from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.backtests_repo import BacktestsRepo, NewBacktest
from db.strategies_repo import StrategiesRepo
from db.wfo_folds_repo import WfoFoldsRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue

router = APIRouter(prefix="/walkforwards", tags=["walkforwards"])
backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()
wfo_folds_repo = WfoFoldsRepo()


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


# ── Request / Response models ───────────────────────────────────────────

class ParamRange(BaseModel):
    start: float
    stop: float
    step: float


class WfoRequest(BaseModel):
    strategy_id: int
    instrument_id: str
    bar: str
    param_ranges: Dict[str, ParamRange]
    constraint: Optional[str] = None
    objective: str = "final"  # final | sharpe | pf
    train_months: int = 12
    test_months: int = 3
    step_months: int = 3
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    cash: Optional[float] = 10000
    commission: Optional[float] = 0.001
    slip_perc: Optional[float] = 0.0
    slip_fixed: Optional[float] = 0.0
    slip_open: Optional[bool] = True
    maxcpus: Optional[int] = 1


class WfoSummary(BaseModel):
    run_id: int
    strategy_id: int
    strategy_name: Optional[str] = None
    instrument_id: str
    bar: str
    status: str
    submitted_at: datetime
    progress: int = 0
    error: Optional[str] = None
    total_folds: int = 0
    objective: Optional[str] = None
    train_months: Optional[int] = None
    test_months: Optional[int] = None
    step_months: Optional[int] = None


class WfoFoldItem(BaseModel):
    id: int
    fold_index: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    params: Optional[Dict[str, Any]] = None
    train_objective: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None


class WfoDetail(BaseModel):
    run_id: int
    strategy_id: int
    strategy_name: str
    instrument_id: str
    bar: str
    status: str
    submitted_at: datetime
    ended_at: Optional[datetime] = None
    progress: int = 0
    error: Optional[str] = None
    param_ranges: Dict[str, Any] = {}
    constraint: Optional[str] = None
    objective: Optional[str] = None
    train_months: Optional[int] = None
    test_months: Optional[int] = None
    step_months: Optional[int] = None
    total_folds: int = 0
    folds: List[WfoFoldItem] = []
    cash: Optional[float] = None
    commission: Optional[float] = None
    slip_perc: Optional[float] = None
    slip_fixed: Optional[float] = None
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    maxcpus: Optional[int] = None


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("", response_model=List[WfoSummary])
def list_walkforwards(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db),
) -> List[WfoSummary]:
    rows = backtests_repo.list_recent(session, limit=limit, offset=offset, run_type="wfo")
    summaries: List[WfoSummary] = []
    for r in rows:
        total_folds = wfo_folds_repo.count_folds(session, r.id)
        params = r.params or {}
        summaries.append(
            WfoSummary(
                run_id=r.id,
                strategy_id=r.strategy_id or 0,
                strategy_name=r.strategy,
                instrument_id=r.instrument_id,
                bar=r.timeframe,
                status=r.status or "unknown",
                submitted_at=r.started_at,
                progress=getattr(r, "progress", 0) or 0,
                error=getattr(r, "error", None),
                total_folds=total_folds,
                objective=params.get("objective"),
                train_months=params.get("train_months"),
                test_months=params.get("test_months"),
                step_months=params.get("step_months"),
            )
        )
    return summaries


@router.post("", response_model=WfoSummary, status_code=status.HTTP_202_ACCEPTED)
def enqueue_walkforward(
    payload: WfoRequest,
    queue: JobQueue = Depends(get_job_queue),
    session: Session = Depends(get_db),
) -> WfoSummary:
    strat = strategies_repo.get_by_id(session, payload.strategy_id)
    if strat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy not found")

    # Build grid spec string
    grid_parts = []
    for param_name, param_range in payload.param_ranges.items():
        grid_parts.append(f"{param_name}={int(param_range.start)}:{int(param_range.stop)}:{int(param_range.step)}")
    grid_spec = ",".join(grid_parts)

    run = backtests_repo.create(
        session,
        NewBacktest(
            run_type="wfo",
            strategy_id=payload.strategy_id,
            instrument_id=payload.instrument_id,
            timeframe=payload.bar,
            strategy=strat.name,
            params={
                "grid": {k: v.model_dump() for k, v in payload.param_ranges.items()},
                "grid_spec": grid_spec,
                "constraint": payload.constraint,
                "objective": payload.objective,
                "train_months": payload.train_months,
                "test_months": payload.test_months,
                "step_months": payload.step_months,
                "start_ts": payload.start_ts,
                "end_ts": payload.end_ts,
                "maxcpus": payload.maxcpus or 1,
            },
            cash=payload.cash,
            commission=payload.commission,
            slip_perc=payload.slip_perc,
            slip_fixed=payload.slip_fixed,
            slip_open=payload.slip_open,
            baseline=False,
        ),
    )
    session.commit()

    job = Job(payload={"type": "wfo", "run_id": run.id})
    queue.enqueue(job)

    return WfoSummary(
        run_id=run.id,
        strategy_id=payload.strategy_id,
        strategy_name=strat.name,
        instrument_id=payload.instrument_id,
        bar=payload.bar,
        status="queued",
        submitted_at=run.started_at,
        progress=0,
        objective=payload.objective,
        train_months=payload.train_months,
        test_months=payload.test_months,
        step_months=payload.step_months,
    )


@router.get("/{run_id}", response_model=WfoDetail)
def get_walkforward_detail(
    run_id: int,
    session: Session = Depends(get_db),
) -> WfoDetail:
    run = backtests_repo.get_by_id(session, run_id)
    if run is None or run.run_type != "wfo":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="walkforward run not found")

    folds = wfo_folds_repo.list_by_run(session, run_id)
    params = run.params or {}

    fold_items = [
        WfoFoldItem(
            id=f.id,
            fold_index=f.fold_index,
            train_start=f.train_start,
            train_end=f.train_end,
            test_start=f.test_start,
            test_end=f.test_end,
            params=f.params,
            train_objective=_safe_float(f.train_objective),
            metrics=f.metrics,
        )
        for f in folds
    ]

    return WfoDetail(
        run_id=run.id,
        strategy_id=run.strategy_id or 0,
        strategy_name=run.strategy,
        instrument_id=run.instrument_id,
        bar=run.timeframe,
        status=run.status or "unknown",
        submitted_at=run.started_at,
        ended_at=run.ended_at,
        progress=getattr(run, "progress", 0) or 0,
        error=getattr(run, "error", None),
        param_ranges=params.get("grid", {}),
        constraint=params.get("constraint"),
        objective=params.get("objective"),
        train_months=params.get("train_months"),
        test_months=params.get("test_months"),
        step_months=params.get("step_months"),
        total_folds=len(fold_items),
        folds=fold_items,
        cash=_safe_float(run.cash),
        commission=_safe_float(run.commission),
        slip_perc=_safe_float(run.slip_perc),
        slip_fixed=_safe_float(run.slip_fixed),
        start_ts=params.get("start_ts"),
        end_ts=params.get("end_ts"),
        maxcpus=params.get("maxcpus"),
    )
