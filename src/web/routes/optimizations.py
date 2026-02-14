from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.backtests_repo import BacktestsRepo
from db.optimization_results_repo import OptimizationResultsRepo
from db.strategies_repo import StrategiesRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue

router = APIRouter(prefix="/optimizations", tags=["optimizations"])
backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()
opt_results_repo = OptimizationResultsRepo()


class ParamRange(BaseModel):
    """Parameter range for optimization: start:stop:step"""
    start: int
    stop: int
    step: int


class OptimizationRequest(BaseModel):
    strategy_id: int
    instrument_id: str
    bar: str
    param_ranges: Dict[str, ParamRange]  # e.g., {"fast": {start: 5, stop: 30, step: 1}}
    constraint: Optional[str] = None  # e.g., "fast < slow"
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    cash: Optional[float] = 10000
    commission: Optional[float] = 0.001
    slip_perc: Optional[float] = 0.0
    slip_fixed: Optional[float] = 0.0
    slip_open: Optional[bool] = True
    maxcpus: Optional[int] = 1


class OptimizationSummary(BaseModel):
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
    total_variants: Optional[int] = None
    best_final_value: Optional[float] = None
    best_params: Optional[Dict[str, Any]] = None


class OptimizationVariant(BaseModel):
    id: int
    variant_params: Dict[str, Any]
    final_value: Optional[float]
    sharpe: Optional[float]
    maxdd: Optional[float]
    winrate: Optional[float]
    profit_factor: Optional[float]
    sqn: Optional[float]
    total_trades: Optional[int]


class OptimizationDetail(BaseModel):
    run_id: int
    strategy_id: int
    strategy_name: str
    instrument_id: str
    bar: str
    status: str
    submitted_at: datetime
    ended_at: Optional[datetime]
    progress: int
    error: Optional[str]
    param_ranges: Dict[str, Any]
    constraint: Optional[str]
    total_variants: int
    variants: List[OptimizationVariant]


@router.get("", response_model=List[OptimizationSummary])
def list_optimizations(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db),
) -> List[OptimizationSummary]:
    """List recent optimization runs."""
    rows = backtests_repo.list_recent(session, limit=limit, offset=offset, run_type="optimize")
    summaries: List[OptimizationSummary] = []

    for r in rows:
        # Get best result for this optimization
        best_result = opt_results_repo.get_best_result(session, r.id)
        total_variants = opt_results_repo.count_results(session, r.id)

        summaries.append(
            OptimizationSummary(
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
                total_variants=total_variants if total_variants > 0 else None,
                best_final_value=float(best_result.final_value) if best_result and best_result.final_value else None,
                best_params=best_result.variant_params if best_result else None,
            )
        )
    return summaries


@router.post("", response_model=OptimizationSummary, status_code=status.HTTP_202_ACCEPTED)
def enqueue_optimization(
    payload: OptimizationRequest,
    queue: JobQueue = Depends(get_job_queue),
    session: Session = Depends(get_db),
) -> OptimizationSummary:
    """Enqueue an optimization job."""
    # Verify strategy exists
    strat = strategies_repo.get_by_id(session, payload.strategy_id)
    if strat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy not found")

    # Build grid spec string: "param1=start:stop:step,param2=start:stop:step"
    grid_parts = []
    for param_name, param_range in payload.param_ranges.items():
        grid_parts.append(f"{param_name}={param_range.start}:{param_range.stop}:{param_range.step}")
    grid_spec = ",".join(grid_parts)

    # Create run header
    run = backtests_repo.create(
        session,
        NewBacktest(
            run_type="optimize",
            strategy_id=payload.strategy_id,
            instrument_id=payload.instrument_id,
            timeframe=payload.bar,
            strategy=strat.name,
            params={
                "grid": payload.param_ranges,
                "constraint": payload.constraint,
                "start_ts": payload.start_ts,
                "end_ts": payload.end_ts,
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

    # Enqueue job
    job = Job(
        type="optimize",
        payload={
            "run_id": run.id,
            "instrument_id": payload.instrument_id,
            "bar": payload.bar,
            "strategy": strat.name,
            "grid_spec": grid_spec,
            "constraint": payload.constraint or "",
            "since": payload.start_ts,
            "until": payload.end_ts,
            "cash": payload.cash or 10000,
            "commission": payload.commission or 0.001,
            "slip_perc": payload.slip_perc or 0.0,
            "slip_fixed": payload.slip_fixed or 0.0,
            "slip_open": payload.slip_open if payload.slip_open is not None else True,
            "maxcpus": payload.maxcpus or 1,
        },
    )
    queue.enqueue(job)

    return OptimizationSummary(
        run_id=run.id,
        job_id="n/a",
        strategy_id=payload.strategy_id,
        strategy_name=strat.name,
        instrument_id=payload.instrument_id,
        bar=payload.bar,
        status="queued",
        submitted_at=run.started_at,
        progress=0,
    )


@router.get("/{run_id}", response_model=OptimizationDetail)
def get_optimization_detail(
    run_id: int,
    limit: int = 100,  # Top N variants to return
    session: Session = Depends(get_db),
) -> OptimizationDetail:
    """Get detailed optimization results including all variants."""
    run = backtests_repo.get_by_id(session, run_id)
    if run is None or run.run_type != "optimize":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="optimization not found")

    # Get optimization variants
    results = opt_results_repo.get_results_by_run(session, run_id, limit=limit)
    total_variants = opt_results_repo.count_results(session, run_id)

    variants = [
        OptimizationVariant(
            id=r.id,
            variant_params=r.variant_params,
            final_value=float(r.final_value) if r.final_value else None,
            sharpe=float(r.sharpe) if r.sharpe else None,
            maxdd=float(r.maxdd) if r.maxdd else None,
            winrate=float(r.winrate) if r.winrate else None,
            profit_factor=float(r.profit_factor) if r.profit_factor else None,
            sqn=float(r.sqn) if r.sqn else None,
            total_trades=r.total_trades,
        )
        for r in results
    ]

    params = run.params or {}

    return OptimizationDetail(
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
        total_variants=total_variants,
        variants=variants,
    )
