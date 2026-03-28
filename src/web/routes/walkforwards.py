from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.backtests_repo import BacktestsRepo, NewBacktest
from db.run_trades_repo import RunTradesRepo
from db.strategies_repo import StrategiesRepo
from db.wfo_folds_repo import WfoFoldsRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue

router = APIRouter(prefix="/walkforwards", tags=["walkforwards"])
backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()
wfo_folds_repo = WfoFoldsRepo()
runtrades_repo = RunTradesRepo()


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
    ended_at: Optional[datetime] = None
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
                ended_at=r.ended_at,
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
    def _fmt_num(v: float) -> str:
        return str(int(v)) if v == int(v) else str(v)

    grid_parts = []
    for param_name, param_range in payload.param_ranges.items():
        grid_parts.append(
            f"{param_name}={_fmt_num(param_range.start)}:{_fmt_num(param_range.stop)}:{_fmt_num(param_range.step)}"
        )
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


@router.get("/{run_id}/monte-carlo")
def get_wfo_monte_carlo(
    run_id: int,
    n_sims: int = 500,
    session: Session = Depends(get_db),
):
    run = backtests_repo.get_by_id(session, run_id)
    if run is None or run.run_type != "wfo":
        raise HTTPException(status_code=404, detail="walkforward run not found")

    from main_backtest import compute_wfo_combined
    try:
        combined = compute_wfo_combined(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Combined equity computation failed: {exc}")

    trades = combined["trades"]
    equity_pts = combined["equity"]   # [{ts: ISO string, value: float}]
    initial_cash = float(combined["initial_cash"])
    final_value = float(combined["final_value"])

    def _to_unix(s: Any) -> int:
        from datetime import datetime, timezone
        if isinstance(s, str):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = s
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    # Build sorted equity floor-lookup: [(unix_ts, value), ...]
    eq_pairs = sorted((_to_unix(e["ts"]), float(e["value"])) for e in equity_pts)

    def _equity_at(unix_ts: int) -> float:
        """Largest equity point with ts <= unix_ts (floor lookup)."""
        lo, hi = 0, len(eq_pairs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if eq_pairs[mid][0] <= unix_ts:
                lo = mid
            else:
                hi = mid - 1
        return eq_pairs[lo][1]

    # Sort trades by exit time to ensure monotonic timestamps.
    trades_sorted = sorted(trades, key=lambda t: _to_unix(t["exit_ts"]))

    # Derive equity deltas from the combined equity curve at each trade exit.
    # This guarantees: sum(pnls) = final_value - initial_cash, so ALL MC paths
    # (actual + every simulation) converge to the same final_value as the
    # combined equity chart, correctly accounting for carry-over compounding.
    timestamps: List[int] = []
    equity_seq: List[float] = [eq_pairs[0][1]]  # t0 equity (= initial_cash)

    for t in trades_sorted:
        exit_unix = _to_unix(t["exit_ts"])
        timestamps.append(exit_unix)
        equity_seq.append(_equity_at(exit_unix))

    # Force last equity point to match final_value exactly, closing any residual
    # gap caused by open positions at the last bar after the last trade exit.
    if len(equity_seq) > 1:
        equity_seq[-1] = final_value

    pnls = [equity_seq[i + 1] - equity_seq[i] for i in range(len(timestamps))]

    # Downsample the full equity curve for the "Actual" line in the chart.
    # This gives bar-level resolution (including inter-fold and intra-fold equity
    # moves from open positions) instead of just trade-exit snapshots.
    max_curve_pts = 600
    stride = max(1, len(eq_pairs) // max_curve_pts)
    equity_curve = [[ts, val] for ts, val in eq_pairs[::stride]]
    if eq_pairs and list(eq_pairs[-1]) != equity_curve[-1]:
        equity_curve.append(list(eq_pairs[-1]))

    from backtest.monte_carlo import run_monte_carlo
    result = run_monte_carlo(
        pnls, initial_cash, n_sims=n_sims,
        timestamps=timestamps if timestamps else None,
        actual_equity=equity_seq,
    )
    return {**result, "initial_cash": initial_cash, "equity_curve": equity_curve}


@router.get("/{run_id}/combined-equity")
def get_combined_equity(run_id: int, session: Session = Depends(get_db)):
    """Re-run WFO test folds sequentially with carry-over capital.

    Returns a continuous equity curve + trades across all out-of-sample periods.
    Each fold uses the best params found for that fold, starting with capital
    left over from the previous fold.
    """
    from main_backtest import compute_wfo_combined
    try:
        result = compute_wfo_combined(run_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Combined equity computation failed: {exc}")
