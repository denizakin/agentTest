from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.backtests_repo import BacktestsRepo, NewBacktest
from db.optimization_results_repo import OptimizationResultsRepo
from db.strategies_repo import StrategiesRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue

router = APIRouter(prefix="/optimizations", tags=["optimizations"])
backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()
opt_results_repo = OptimizationResultsRepo()


def _safe_float(val: Any) -> Optional[float]:
    """Convert to float, returning None for NaN/Inf/None."""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f or f == float('inf') or f == float('-inf'):
            return None
        return f
    except (TypeError, ValueError):
        return None


class ParamRange(BaseModel):
    """Parameter range for optimization: start:stop:step"""
    start: float
    stop: float
    step: float


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
    long_count: Optional[int] = None
    short_count: Optional[int] = None
    won_count: Optional[int] = None
    lost_count: Optional[int] = None
    best_pnl: Optional[float] = None
    worst_pnl: Optional[float] = None
    avg_pnl: Optional[float] = None
    backtest_run_id: Optional[int] = None


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
    cash: Optional[float] = None
    commission: Optional[float] = None
    slip_perc: Optional[float] = None
    slip_fixed: Optional[float] = None
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    maxcpus: Optional[int] = None


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
                best_final_value=_safe_float(best_result.final_value) if best_result else None,
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
    def _fmt_num(v: float) -> str:
        return str(int(v)) if v == int(v) else str(v)

    grid_parts = []
    for param_name, param_range in payload.param_ranges.items():
        grid_parts.append(
            f"{param_name}={_fmt_num(param_range.start)}:{_fmt_num(param_range.stop)}:{_fmt_num(param_range.step)}"
        )
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
                "grid": {k: v.model_dump() for k, v in payload.param_ranges.items()},
                "grid_spec": grid_spec,
                "constraint": payload.constraint,
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

    # Enqueue job (worker polls DB for queued runs, but we keep queue for consistency)
    job = Job(payload={"type": "optimize", "run_id": run.id})
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
            final_value=_safe_float(r.final_value),
            sharpe=_safe_float(r.sharpe),
            maxdd=_safe_float(r.maxdd),
            winrate=_safe_float(r.winrate),
            profit_factor=_safe_float(r.profit_factor),
            sqn=_safe_float(r.sqn),
            total_trades=r.total_trades,
            long_count=r.long_count,
            short_count=r.short_count,
            best_pnl=_safe_float(r.best_pnl),
            worst_pnl=_safe_float(r.worst_pnl),
            avg_pnl=_safe_float(r.avg_pnl),
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
        cash=_safe_float(run.cash),
        commission=_safe_float(run.commission),
        slip_perc=_safe_float(run.slip_perc),
        slip_fixed=_safe_float(run.slip_fixed),
        start_ts=params.get("start_ts"),
        end_ts=params.get("end_ts"),
        maxcpus=params.get("maxcpus"),
    )
