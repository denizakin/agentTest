from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from db.backtests_repo import BacktestsRepo, NewBacktest
from db.run_logs_repo import RunLogsRepo
from db.run_results_repo import RunResultsRepo
from db.run_trades_repo import RunTradesRepo
from db.strategies_repo import StrategiesRepo
from taskqueue.types import Job, JobQueue
from web.deps import get_db, get_job_queue
from sqlalchemy import text
from backtest.strategies.registry import get_strategy_params

router = APIRouter(prefix="/backtests", tags=["backtests"])
backtests_repo = BacktestsRepo()
strategies_repo = StrategiesRepo()
runlogs_repo = RunLogsRepo()
runresults_repo = RunResultsRepo()
runtrades_repo = RunTradesRepo()


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
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None


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
        params = r.params or {}
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
                start_ts=params.get("start_ts"),
                end_ts=params.get("end_ts"),
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
            run_type="backtest",
            strategy_id=payload.strategy_id,
            instrument_id=payload.instrument_id,
            timeframe=payload.bar,
            strategy=strat.name,
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


from typing import Optional, Dict, Any


class RunResultItem(BaseModel):
    label: str
    params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    plot_path: Optional[str] = None


@router.get("/{run_id}/results", response_model=List[RunResultItem])
def list_backtest_results(run_id: int, session: Session = Depends(get_db)) -> List[RunResultItem]:
    run = backtests_repo.get(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest not found")
    rows = runresults_repo.list_by_run(session, run_id)
    return [RunResultItem(label=r.label, params=r.params, metrics=r.metrics, plot_path=r.plot_path) for r in rows]


class TradeItem(BaseModel):
    entry_ts: datetime
    exit_ts: datetime
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: Optional[float] = None
    mae: Optional[float] = None
    mfe: Optional[float] = None
    commission: Optional[float] = None


@router.get("/{run_id}/trades", response_model=List[TradeItem])
def list_backtest_trades(run_id: int, session: Session = Depends(get_db)) -> List[TradeItem]:
    run = backtests_repo.get(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest not found")
    trades = runtrades_repo.list_trades(session, run_id)
    return [
        TradeItem(
            entry_ts=t.entry_ts,
            exit_ts=t.exit_ts,
            side=t.side,
            entry_price=float(t.entry_price),
            exit_price=float(t.exit_price),
            size=float(t.size),
            pnl=float(t.pnl),
            pnl_pct=float(t.pnl_pct) if t.pnl_pct else None,
            mae=float(t.mae) if t.mae else None,
            mfe=float(t.mfe) if t.mfe else None,
            commission=float(t.commission) if t.commission else None,
        )
        for t in trades
    ]


# ---- Chart endpoint ----
class ChartCandle(BaseModel):
    time: str  # ISO timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


class ChartSignal(BaseModel):
    time: str  # ISO timestamp
    side: str  # BUY/SELL
    price: Optional[float] = None
    message: Optional[str] = None


class ChartResponse(BaseModel):
    candles: List[ChartCandle]
    signals: List[ChartSignal]


def _mv_name(inst: str, tf: str) -> str:
    tf_norm = tf.lower()
    allowed = {"1m", "5m", "15m", "1h", "4h", "1d", "1w", "1mo"}
    if tf_norm not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unsupported bar: {tf}")
    # Extract coin symbol (BTC-USDT -> btc, ETH-USDT -> eth)
    inst_lower = inst.lower()
    if "-" in inst_lower:
        coin = inst_lower.split("-")[0]
    else:
        coin = inst_lower
    return f"mv_candlesticks_{coin}_{tf_norm}"


@router.get("/{run_id}/chart", response_model=ChartResponse)
def get_backtest_chart(run_id: int, session: Session = Depends(get_db)) -> ChartResponse:
    run = backtests_repo.get(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest not found")

    params = run.params or {}
    start_ts = params.get("start_ts")
    end_ts = params.get("end_ts")

    # For 1m, use base table; otherwise use MV
    if run.timeframe.lower() == "1m":
        view = "candlesticks"
        where: List[str] = [f"instrument_id = :instrument_id"]
        sql_params: Dict[str, Any] = {"instrument_id": run.instrument_id}
    else:
        view = _mv_name(run.instrument_id, run.timeframe)
        where = []
        sql_params = {}

    if start_ts:
        where.append("ts >= :start_ts")
        sql_params["start_ts"] = start_ts
    if end_ts:
        where.append("ts <= :end_ts")
        sql_params["end_ts"] = end_ts
    where_clause = (" WHERE " + " AND ".join(where)) if where else ""

    # Query from MV or base table
    timeout_ms = 5000
    try:
        session.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
        sql = f"SELECT ts, open, high, low, close, volume FROM {view}{where_clause} ORDER BY ts ASC"
        rows = session.execute(text(sql), sql_params).all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"failed to load candles: {exc}"
        )

    # Convert to ChartCandle objects (data should already be in correct timeframe from MV)
    # Database stores timestamps in UTC, convert to Istanbul timezone for display
    from zoneinfo import ZoneInfo
    istanbul_tz = ZoneInfo("Europe/Istanbul")

    candles = [
        ChartCandle(
            time=ts.astimezone(istanbul_tz).isoformat() if ts.tzinfo else ts.replace(tzinfo=timezone.utc).astimezone(istanbul_tz).isoformat(),
            open=float(o),
            high=float(h),
            low=float(l),
            close=float(c),
            volume=float(v),
        )
        for ts, o, h, l, c, v in rows
    ]

    # Get signals from run_trades table instead of parsing logs
    # This ensures we get ALL trades, not limited by log size
    trades = runtrades_repo.list_trades(session, run_id, limit=10000, offset=0)

    signals: List[ChartSignal] = []
    for trade in trades:
        # Add entry signal
        if trade.entry_ts and trade.entry_price:
            signals.append(ChartSignal(
                time=trade.entry_ts.astimezone(istanbul_tz).isoformat() if trade.entry_ts.tzinfo else trade.entry_ts.replace(tzinfo=timezone.utc).astimezone(istanbul_tz).isoformat(),
                side="BUY" if trade.side == "LONG" else "SELL",
                price=float(trade.entry_price),
                message=f"Entry {trade.side} @ {trade.entry_price:.2f}"
            ))

        # Add exit signal
        if trade.exit_ts and trade.exit_price:
            signals.append(ChartSignal(
                time=trade.exit_ts.astimezone(istanbul_tz).isoformat() if trade.exit_ts.tzinfo else trade.exit_ts.replace(tzinfo=timezone.utc).astimezone(istanbul_tz).isoformat(),
                side="SELL" if trade.side == "LONG" else "BUY",
                price=float(trade.exit_price),
                message=f"Exit {trade.side} @ {trade.exit_price:.2f} (PnL: {trade.pnl:.2f})"
            ))

    # Sort signals by time
    signals.sort(key=lambda s: s.time)

    return ChartResponse(candles=candles, signals=signals)


class StrategyParamsResponse(BaseModel):
    strategy_id: int
    strategy_name: str
    params: Dict[str, Any]


@router.get("/strategies/{strategy_id}/params", response_model=StrategyParamsResponse)
def get_strategy_parameters(strategy_id: int, session: Session = Depends(get_db)) -> StrategyParamsResponse:
    """Get default parameters for a strategy."""
    strat = strategies_repo.get_by_id(session, strategy_id)
    if strat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy not found")

    try:
        params = get_strategy_params(strat.name)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to get strategy params: {e}")

    return StrategyParamsResponse(
        strategy_id=strategy_id,
        strategy_name=strat.name,
        params=params
    )
