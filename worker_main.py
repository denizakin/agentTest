from __future__ import annotations

import contextvars
import logging
import os
import io
from contextlib import redirect_stdout, redirect_stderr
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
from db.run_results_repo import RunResultsRepo
from db.strategies_repo import StrategiesRepo
from db.optimization_results_repo import OptimizationResultsRepo
from main_backtest import run_backtest, run_optimize, run_wfo


POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "1.0"))
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "2"))
RUN_CTX: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar("run_id", default=None)
WORKER_CTX: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar("worker_id", default=None)
LOG_GUARD: contextvars.ContextVar[bool] = contextvars.ContextVar("log_guard", default=False)


class RunLogHandler(logging.Handler):
    """Logging handler that writes worker logs into run_logs table when run_id is set."""

    def __init__(self, db: DbConn) -> None:
        super().__init__()
        self.db = db
        self.repo = RunLogsRepo()

    def emit(self, record: logging.LogRecord) -> None:
        if LOG_GUARD.get():
            return
        token = LOG_GUARD.set(True)
        run_id = getattr(record, "run_id", None) or RUN_CTX.get()
        if run_id is None:
            LOG_GUARD.reset(token)
            return
        msg = self.format(record)
        session = None
        try:
            with self.db.session_scope() as session:
                self.repo.append(session, int(run_id), record.levelname, msg)
                session.commit()
        except Exception:
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
        finally:
            LOG_GUARD.reset(token)


class _WorkerFormatter(logging.Formatter):
    """Log formatter that includes worker ID from context variable."""

    def format(self, record: logging.LogRecord) -> str:
        wid = WORKER_CTX.get()
        prefix = f"[worker-{wid}]" if wid is not None else "[worker-?]"
        record.worker_prefix = prefix  # type: ignore[attr-defined]
        return super().format(record)


def get_logger(db: DbConn) -> logging.Logger:
    logger = logging.getLogger("worker")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    stream = logging.StreamHandler()
    stream.setLevel(logging.INFO)
    stream.setFormatter(_WorkerFormatter("[%(asctime)s] %(worker_prefix)s %(levelname)s %(message)s"))
    db_handler = RunLogHandler(db)
    db_handler.setLevel(logging.INFO)
    logger.addHandler(stream)
    logger.addHandler(db_handler)
    logger.propagate = False
    return logger


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

    # Import helper functions for dynamic strategies
    from backtest.strategies.helpers import price_fmt

    module_name = f"dyn_strategy_{strategy_id}_{uuid4().hex[:8]}"
    module_globals: Dict[str, Any] = {"__name__": module_name, "bt": bt, "price_fmt": price_fmt}
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


def process_backtest(run_id: int, payload: dict, repo: BacktestsRepo, db: DbConn, results_out: Optional[Dict[str, Any]] = None) -> None:
    logger = get_logger(db)
    def log_msg(level: str, msg: str) -> None:
        logger.log(getattr(logging, level, logging.INFO), msg, extra={"run_id": run_id})

    with db.session_scope() as session:
        try:
            repo.update_status(session, run_id, status="running", progress=5)
        except Exception as exc:
            session.rollback()
            log_msg("ERROR", f"Failed to mark running: {exc}")
            raise
    log_msg("INFO", f"Backtest started (run_id={run_id})")
    with db.session_scope() as session:
        try:
            repo.update_status(session, run_id, status="running", progress=20)
        except Exception:
            session.rollback()

    strategy_id = payload.get("strategy_id")
    instrument_id = payload.get("instrument_id")
    bar = payload.get("bar")
    start_ts = payload.get("start_ts")
    end_ts = payload.get("end_ts")
    strategy_name = payload.get("strategy_name") or payload.get("strategy") or "sma"

    if not strategy_id or not instrument_id or not bar:
        raise ValueError("missing strategy_id/instrument_id/bar")

    # Strategy params can be either nested under "params" key (old job queue format)
    # or flat in the payload (worker loop format from run.params).
    # We merge both sources and filter out meta keys.
    nested_params = payload.get("params") or {}
    merged = {**payload, **nested_params}

    meta_keys = {
        "strategy_id",
        "instrument_id",
        "bar",
        "start_ts",
        "end_ts",
        "cash",
        "commission",
        "stake",
        "plot",
        "refresh",
        "use_sizer",
        "coc",
        "baseline",
        "parallel_baseline",
        "slip_perc",
        "slip_fixed",
        "slip_open",
        "strategy",
        "strategy_name",
        "params",
        "type",
        "run_id",
        "data",
    }
    strat_params = {k: v for k, v in merged.items() if k not in meta_keys}

    cash = float(merged.get("cash", 10000))
    commission = float(merged.get("commission", 0.001))
    stake = int(merged.get("stake", 1))
    plot = bool(merged.get("plot", False))
    refresh = bool(merged.get("refresh", False))
    use_sizer = bool(merged.get("use_sizer", False))
    coc = bool(merged.get("coc", False))
    baseline = bool(merged.get("baseline", True))
    parallel_baseline = bool(merged.get("parallel_baseline", False))
    slip_perc = float(merged.get("slip_perc", 0.0))
    slip_fixed = float(merged.get("slip_fixed", 0.0))
    slip_open = bool(merged.get("slip_open", True))

    # Progress callback based on elapsed time between start/end_ts or data range
    start_dt = pd.to_datetime(start_ts) if start_ts else None
    end_dt = pd.to_datetime(end_ts) if end_ts else None
    last_pct = {"v": 0.0}

    def on_progress(frac: float) -> None:
        pct = round(max(0.0, min(1.0, frac)) * 100.0, 2)
        if pct <= last_pct["v"]:
            return
        last_pct["v"] = pct
        try:
            with db.session_scope() as s:
                repo.update_status(s, run_id, status="running", progress=pct)
        except Exception:
            pass

    log_msg("INFO", f"Running backtest for strategy_id={strategy_id}, strategy={strategy_name}, strat_params={strat_params}")

    class _Writer(io.StringIO):
        def __init__(self, level: int) -> None:
            super().__init__()
            self.level = level
            self._last_line: Optional[str] = None
        def write(self, s: str) -> int:
            for line in s.splitlines():
                line = line.strip()
                if line and line != self._last_line:
                    logger.log(self.level, line, extra={"run_id": run_id})
                    self._last_line = line
            return len(s)
        def flush(self) -> None:
            return

    out_writer = _Writer(logging.INFO)
    err_writer = _Writer(logging.ERROR)
    with redirect_stdout(out_writer), redirect_stderr(err_writer):
        rc = run_backtest(
            inst=str(instrument_id),
            tf=str(bar),
            since=start_ts,
            until=end_ts,
            cash=cash,
            commission=commission,
            stake=stake,
            plot=plot,
            refresh=refresh,
            use_sizer=use_sizer,
            coc=coc,
            strategy_name=str(strategy_name),
            strat_params=strat_params,
            baseline=baseline,
            parallel_baseline=parallel_baseline,
            slip_perc=slip_perc,
            slip_fixed=slip_fixed,
            slip_open=slip_open,
            log_to_db=True,
            results_out=results_out,
            on_progress=on_progress,
            run_id=run_id,
        )

    with db.session_scope() as session:
        try:
            repo.update_status(session, run_id, status="running", progress=90)
        except Exception:
            session.rollback()

    if rc != 0:
        raise RuntimeError(f"run_backtest exited with code {rc}")

    with db.session_scope() as session:
        repo.update_status(
            session,
            run_id,
            status="succeeded",
            progress=100,
            error=None,
        )

    # TODO: store metrics in run_results


def process_optimization(run_id: int, payload: dict, repo: BacktestsRepo, db: DbConn) -> None:
    logger = get_logger(db)
    def log_msg(level: str, msg: str) -> None:
        logger.log(getattr(logging, level, logging.INFO), msg, extra={"run_id": run_id})

    with db.session_scope() as session:
        try:
            repo.update_status(session, run_id, status="running", progress=5)
        except Exception as exc:
            session.rollback()
            log_msg("ERROR", f"Failed to mark running: {exc}")
            raise
    log_msg("INFO", f"Optimization started (run_id={run_id})")
    log_msg("INFO", f"Optimization payload keys: {list(payload.keys())}")

    instrument_id = payload.get("instrument_id")
    bar = payload.get("bar")
    strategy = payload.get("strategy")
    grid_spec = payload.get("grid_spec")
    constraint = payload.get("constraint") or ""
    since = payload.get("start_ts") or payload.get("since")
    until = payload.get("end_ts") or payload.get("until")
    cash = float(payload.get("cash", 10000))
    commission = float(payload.get("commission", 0.001))
    slip_perc = float(payload.get("slip_perc", 0.0))
    slip_fixed = float(payload.get("slip_fixed", 0.0))
    slip_open = bool(payload.get("slip_open", True))
    maxcpus = int(payload.get("maxcpus", 1))

    missing = []
    if not instrument_id: missing.append("instrument_id")
    if not bar: missing.append("bar")
    if not strategy: missing.append("strategy")
    if not grid_spec: missing.append(f"grid_spec (got: {grid_spec!r})")
    if missing:
        raise ValueError(f"missing required optimization parameters: {', '.join(missing)}")

    log_msg("INFO", f"Running optimization for strategy={strategy}, grid={grid_spec}")

    last_pct = {"v": 0.0}

    def on_progress(frac: float) -> None:
        pct = round(max(0.0, min(1.0, frac)) * 100.0, 2)
        if pct <= last_pct["v"]:
            return
        last_pct["v"] = pct
        try:
            with db.session_scope() as s:
                repo.update_status(s, run_id, status="running", progress=pct)
        except Exception:
            pass

    class _Writer(io.StringIO):
        def __init__(self, level: int) -> None:
            super().__init__()
            self.level = level
            self._last_line: Optional[str] = None
        def write(self, s: str) -> int:
            for line in s.splitlines():
                line = line.strip()
                if line and line != self._last_line:
                    logger.log(self.level, line, extra={"run_id": run_id})
                    self._last_line = line
            return len(s)
        def flush(self) -> None:
            return

    out_writer = _Writer(logging.INFO)
    err_writer = _Writer(logging.ERROR)
    with redirect_stdout(out_writer), redirect_stderr(err_writer):
        rc = run_optimize(
            inst=str(instrument_id),
            tf=str(bar),
            since=since,
            until=until,
            cash=cash,
            commission=commission,
            strategy_name=str(strategy),
            grid_spec=str(grid_spec),
            maxcpus=maxcpus,
            constraint=str(constraint),
            slip_perc=slip_perc,
            slip_fixed=slip_fixed,
            slip_open=slip_open,
            run_id=run_id,
            on_progress=on_progress,
        )

    if rc == 3:
        # No optimization results collected (constraint filtered all, or no valid runs)
        log_msg("WARNING", "Optimization completed but no results collected (possibly due to constraint or failures)")
        with db.session_scope() as session:
            repo.update_status(session, run_id, status="succeeded", progress=100, error="No results collected")
        return
    elif rc != 0:
        raise RuntimeError(f"run_optimize exited with code {rc}")

    with db.session_scope() as session:
        repo.update_status(
            session,
            run_id,
            status="succeeded",
            progress=100,
            error=None,
        )


def process_wfo(run_id: int, payload: dict, repo: BacktestsRepo, db: DbConn) -> None:
    logger = get_logger(db)
    def log_msg(level: str, msg: str) -> None:
        logger.log(getattr(logging, level, logging.INFO), msg, extra={"run_id": run_id})

    with db.session_scope() as session:
        try:
            repo.update_status(session, run_id, status="running", progress=5)
        except Exception as exc:
            session.rollback()
            log_msg("ERROR", f"Failed to mark running: {exc}")
            raise
    log_msg("INFO", f"WFO started (run_id={run_id})")

    instrument_id = payload.get("instrument_id")
    bar = payload.get("bar")
    strategy = payload.get("strategy")
    grid_spec = payload.get("grid_spec")
    constraint = payload.get("constraint") or ""
    objective = payload.get("objective", "final")
    train_months = int(payload.get("train_months", 12))
    test_months = int(payload.get("test_months", 3))
    step_months = int(payload.get("step_months", 3))
    since = payload.get("start_ts") or payload.get("since")
    until = payload.get("end_ts") or payload.get("until")
    cash = float(payload.get("cash", 10000))
    commission = float(payload.get("commission", 0.001))
    slip_perc = float(payload.get("slip_perc", 0.0))
    slip_fixed = float(payload.get("slip_fixed", 0.0))
    slip_open = bool(payload.get("slip_open", True))
    maxcpus = int(payload.get("maxcpus", 1))

    missing = []
    if not instrument_id: missing.append("instrument_id")
    if not bar: missing.append("bar")
    if not strategy: missing.append("strategy")
    if not grid_spec: missing.append(f"grid_spec (got: {grid_spec!r})")
    if missing:
        raise ValueError(f"missing required WFO parameters: {', '.join(missing)}")

    log_msg("INFO", f"Running WFO for strategy={strategy}, grid={grid_spec}, "
            f"train={train_months}m test={test_months}m step={step_months}m obj={objective}")

    last_pct = {"v": 0.0}

    def on_progress(frac: float) -> None:
        pct = round(max(0.0, min(1.0, frac)) * 100.0, 2)
        if pct <= last_pct["v"]:
            return
        last_pct["v"] = pct
        try:
            with db.session_scope() as s:
                repo.update_status(s, run_id, status="running", progress=pct)
        except Exception:
            pass

    class _Writer(io.StringIO):
        def __init__(self, level: int) -> None:
            super().__init__()
            self.level = level
            self._last_line: Optional[str] = None
        def write(self, s: str) -> int:
            for line in s.splitlines():
                line = line.strip()
                if line and line != self._last_line:
                    logger.log(self.level, line, extra={"run_id": run_id})
                    self._last_line = line
            return len(s)
        def flush(self) -> None:
            return

    out_writer = _Writer(logging.INFO)
    err_writer = _Writer(logging.ERROR)
    with redirect_stdout(out_writer), redirect_stderr(err_writer):
        rc = run_wfo(
            inst=str(instrument_id),
            tf=str(bar),
            since=since,
            until=until,
            cash=cash,
            commission=commission,
            strategy_name=str(strategy),
            grid_spec=str(grid_spec),
            train_months=train_months,
            test_months=test_months,
            step_months=step_months,
            constraint=str(constraint),
            objective=str(objective),
            maxcpus=maxcpus,
            slip_perc=slip_perc,
            slip_fixed=slip_fixed,
            slip_open=slip_open,
            run_id=run_id,
            on_progress=on_progress,
        )

    if rc == 3:
        log_msg("WARNING", "WFO completed but no folds produced (check date ranges and window sizes)")
        with db.session_scope() as session:
            repo.update_status(session, run_id, status="succeeded", progress=100, error="No folds produced")
        return
    elif rc != 0:
        raise RuntimeError(f"run_wfo exited with code {rc}")

    with db.session_scope() as session:
        repo.update_status(session, run_id, status="succeeded", progress=100, error=None)


def worker_loop(worker_id: int, db: DbConn, stop_event: threading.Event) -> None:
    WORKER_CTX.set(worker_id)
    repo = BacktestsRepo()
    results_repo = RunResultsRepo()
    logger = get_logger(db)
    while not stop_event.is_set():
        run = None
        payload: Dict[str, Any] = {}
        run_type = None
        with db.session_scope() as session:
            run = repo.fetch_next_queued(session)
            if run:
                # Mark as running immediately so other workers skip it.
                repo.update_status(session, run.id, status="running", progress=1)
                session.commit()
                run_type = run.run_type
                payload = dict(run.params) if run.params else {}
                payload.update(
                    {
                        "strategy_id": getattr(run, "strategy_id", None) or payload.get("strategy_id"),
                        "instrument_id": run.instrument_id,
                        "bar": run.timeframe,
                        "strategy": run.strategy,
                        "start_ts": payload.get("start_ts"),
                        "end_ts": payload.get("end_ts"),
                        "cash": float(run.cash) if run.cash is not None else payload.get("cash", 10000),
                        "commission": float(run.commission) if run.commission is not None else payload.get("commission", 0.001),
                        "slip_perc": float(run.slip_perc) if run.slip_perc is not None else payload.get("slip_perc", 0.0),
                        "slip_fixed": float(run.slip_fixed) if run.slip_fixed is not None else payload.get("slip_fixed", 0.0),
                        "slip_open": bool(run.slip_open) if run.slip_open is not None else payload.get("slip_open", True),
                    }
                )
                run_id = run.id

        if not run:
            time.sleep(POLL_SECONDS)
            continue

        token = RUN_CTX.set(run_id)
        try:
            logger.info("Worker %s picked run_id=%s type=%s", worker_id, run_id, run_type, extra={"run_id": run_id})

            if run_type == "optimize":
                process_optimization(run_id, payload, repo, db)
            elif run_type == "wfo":
                process_wfo(run_id, payload, repo, db)
            else:
                # Default to backtest
                results_out: Dict[str, Any] = {}
                process_backtest(run_id, payload, repo, db, results_out=results_out)
                # Persist metrics if available
                if results_out:
                    with db.session_scope() as s3:
                        metrics_main = results_out.get("main") or {}
                        plot_path = results_out.get("plot_path")
                        results_repo.add_result(s3, run_id, label="main", params=payload.get("params") or {}, metrics=metrics_main, plot_path=plot_path)
                        baseline_metrics = results_out.get("baseline")
                        if baseline_metrics is not None:
                            results_repo.add_result(s3, run_id, label="baseline", params={}, metrics=baseline_metrics, plot_path=None)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Worker %s failed run_id=%s: %s", worker_id, run_id, exc, extra={"run_id": run_id})
            with db.session_scope() as s2:
                repo.update_status(s2, run_id, status="failed", progress=100, error=str(exc))
        finally:
            RUN_CTX.reset(token)
        time.sleep(POLL_SECONDS)


def main() -> None:
    load_env_file()
    db = DbConn()
    logger = get_logger(db)
    stop_event = threading.Event()
    threads: list[threading.Thread] = []
    for idx in range(CONCURRENCY):
        t = threading.Thread(target=worker_loop, args=(idx, db, stop_event), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2.0)  # stagger thread starts
        logger.info("[worker-%s] started (poll=%ss)", idx, POLL_SECONDS)
    logger.info("All workers started (total=%s)", CONCURRENCY)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Stopping workers...")
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)


if __name__ == "__main__":
    main()
