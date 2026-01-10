from __future__ import annotations

import os
import threading
import time
from typing import Optional, Tuple, Any, Dict
from uuid import uuid4

import backtrader as bt
import pandas as pd

from config import load_env_file
from db.backtests_repo import BacktestsRepo
from db.db_conn import DbConn
from db.run_logs_repo import RunLogsRepo
from db.strategies_repo import StrategiesRepo


POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "1.0"))
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "2"))


def _load_strategy_class(strategy_id: int, db: DbConn) -> Tuple[Any, Dict[str, Any]]:
    """Load strategy code from DB and return (StrategyClass, params)."""
    strat_repo = StrategiesRepo()
    with db.session_scope() as session:
        strat = strat_repo.get_by_id(session, strategy_id)
        if strat is None:
            raise ValueError("strategy not found")
        code = strat.code
        if not code:
            raise ValueError("strategy code empty")

    module_name = f"dyn_strategy_{strategy_id}_{uuid4().hex[:8]}"
    module_globals: Dict[str, Any] = {"__name__": module_name, "bt": bt}
    exec(code, module_globals)  # noqa: S102 - trusted internal code
    strategy_class = None
    for obj in module_globals.values():
        if isinstance(obj, type) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
            strategy_class = obj
            break
    if strategy_class is None:
        raise ValueError("no bt.Strategy subclass found in code")
    return strategy_class, {}


def _fetch_candles(db: DbConn, instrument_id: str, start_ts: Optional[str], end_ts: Optional[str]) -> pd.DataFrame:
    filters = ["instrument_id = :inst"]
    params: Dict[str, Any] = {"inst": instrument_id}
    if start_ts:
        filters.append("ts >= :start_ts")
        params["start_ts"] = start_ts
    if end_ts:
        filters.append("ts <= :end_ts")
        params["end_ts"] = end_ts
    where = " AND ".join(filters)
    query = f"""
        SELECT ts as datetime, open, high, low, close, volume
        FROM candlesticks
        WHERE {where}
        ORDER BY ts ASC
    """
    df = pd.read_sql(query, db.engine, params=params)
    if df.empty:
        raise ValueError("no candle data for given range")
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df.set_index("datetime", inplace=True)
    return df


def process_backtest(run_id: int, payload: dict, repo: BacktestsRepo, db: DbConn) -> None:
    logs = RunLogsRepo()
    def log_msg(level: str, msg: str) -> None:
        with db.session_scope() as s:
            try:
                logs.append(s, run_id, level, msg)
                s.commit()
            except Exception:
                s.rollback()

    with db.session_scope() as session:
        repo.update_status(session, run_id, status="running", progress=5)
    log_msg("INFO", f"Backtest started (run_id={run_id})")

    strategy_id = payload.get("strategy_id")
    instrument_id = payload.get("instrument_id")
    bar = payload.get("bar")
    params = payload.get("params") or {}
    start_ts = payload.get("start_ts")
    end_ts = payload.get("end_ts")

    if not strategy_id or not instrument_id or not bar:
        raise ValueError("missing strategy_id/instrument_id/bar")

    StrategyCls, strat_params = _load_strategy_class(strategy_id, db)
    log_msg("INFO", f"Loaded strategy_id={strategy_id}")
    df = _fetch_candles(db, instrument_id, start_ts, end_ts)
    log_msg("INFO", f"Fetched {len(df)} candles for {instrument_id} ({start_ts or 'begin'} to {end_ts or 'end'})")

    cerebro = bt.Cerebro()
    cash = float(params.get("cash", 10000))
    cerebro.broker.setcash(cash)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(StrategyCls, **strat_params)

    with db.session_scope() as session:
        repo.update_status(session, run_id, status="running", progress=50)

    cerebro.run()
    final_value = cerebro.broker.getvalue()
    pnl = final_value - cash
    log_msg("INFO", f"Finished backtest; PnL={pnl:.2f}, final_value={final_value:.2f}")

    with db.session_scope() as session:
        repo.update_status(
            session,
            run_id,
            status="succeeded",
            progress=100,
            error=None,
        )

    # TODO: store metrics in run_results

    # Placeholder: metrics can be stored in run_results table later.


def worker_loop(worker_id: int, db: DbConn, stop_event: threading.Event) -> None:
    repo = BacktestsRepo()
    while not stop_event.is_set():
        with db.session_scope() as session:
            run = repo.fetch_next_queued(session)
            if run:
                run_id = run.id
                payload = run.params or {}
                payload.update(
                    {
                        "strategy_id": getattr(run, "strategy_id", None) or payload.get("strategy_id"),
                        "instrument_id": run.instrument_id,
                        "bar": run.timeframe,
                    }
                )
                try:
                    process_backtest(run_id, payload, repo, db)
                except Exception as exc:  # pragma: no cover - runtime safety
                    with db.session_scope() as s2:
                        repo.update_status(s2, run_id, status="failed", progress=100, error=str(exc))
        time.sleep(POLL_SECONDS)


def main() -> None:
    load_env_file()
    db = DbConn()
    stop_event = threading.Event()
    threads: list[threading.Thread] = []
    for idx in range(CONCURRENCY):
        t = threading.Thread(target=worker_loop, args=(idx, db, stop_event), daemon=True)
        t.start()
        threads.append(t)
    print(f"Worker started with concurrency={CONCURRENCY}, poll={POLL_SECONDS}s")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Stopping workers...")
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)


if __name__ == "__main__":
    main()
