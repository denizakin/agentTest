"""CLI: Run a simple Backtrader backtest using DB candles.

Example:
  python src/main_backtest.py --inst BTC-USDT --tf 15m --since 2024-01-01 --cash 10000 --plot
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List

import pandas as pd
import backtrader as bt
from sqlalchemy import text

from config import load_env_file
from db.db_conn import DbConn
from backtest.strategies.registry import get_strategy, available_strategies


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    txt = value.strip()
    # Epoch seconds or milliseconds
    if txt.isdigit():
        val = int(txt)
        if len(txt) <= 10:
            val *= 1000
        return datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)
    # ISO8601 or 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM[:SS]'
    try:
        if len(txt) == 10 and txt[4] == '-' and txt[7] == '-':
            return datetime.strptime(txt, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if "T" in txt or txt.endswith("Z") or "+" in txt:
            iso = txt.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        # space separated
        fmt = "%Y-%m-%d %H:%M:%S" if txt.count(":") == 2 else "%Y-%m-%d %H:%M"
        return datetime.strptime(txt, fmt).replace(tzinfo=timezone.utc)
    except Exception:
        raise ValueError(f"Unsupported time format: {value}")


def _tf_to_view(inst: str, tf: str) -> Optional[str]:
    inst = inst.upper()
    base = None
    if inst.startswith("BTC-"):
        base = "btc"
    elif inst.startswith("ETH-"):
        base = "eth"
    else:
        return None
    tf_norm = tf.lower()
    if tf_norm == "1m":
        return None
    allowed = {"5m", "15m", "1h", "4h", "1d", "1w", "1mo"}
    if tf_norm not in allowed:
        raise ValueError(f"Unsupported timeframe: {tf}. Allowed: {sorted(allowed)}")
    return f"mv_candlesticks_{base}_{tf_norm}"


def _fetch_df(db: DbConn, inst: str, tf: str, since: Optional[datetime], until: Optional[datetime], view: Optional[str] = None) -> pd.DataFrame:
    view = view or _tf_to_view(inst, tf)
    if view is None:
        sql = (
            "SELECT ts, open, high, low, close, volume "
            "FROM candlesticks WHERE instrument_id = :inst"
        )
    else:
        sql = (
            f"SELECT ts, open, high, low, close, volume FROM {view}"
        )

    where_clauses = []
    params = {"inst": inst}
    if view is None:
        # base table requires instrument filter
        pass
    else:
        # mv already fixed instrument
        params.pop("inst", None)

    if since is not None:
        where_clauses.append("ts >= :since")
        params["since"] = since
    if until is not None:
        where_clauses.append("ts <= :until")
        params["until"] = until

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " ORDER BY ts ASC"

    with db.session_scope() as s:
        rows = s.execute(text(sql), params).all()

    if not rows:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])  # empty

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    # Normalize to UTC naive datetimes for Backtrader
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("UTC").dt.tz_localize(None)

    # Ensure numeric columns are float (handle Decimal/str -> float); drop rows with NaNs after coercion
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    # De-dup on timestamp just in case and keep first occurrence
    df = df.drop_duplicates(subset=["ts"]).sort_values("ts", ascending=True).reset_index(drop=True)
    return df


def _fmt(x, nd: int = 2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "n/a"


def run_once(df_in: pd.DataFrame, strat_name: str, params: Dict[str, Any], *,
             cash: float, commission: float, coc: bool, use_sizer: bool, stake: int,
             slip_perc: float = 0.0, slip_fixed: float = 0.0, slip_open: bool = True,
             do_plot: bool = False, verbose: bool = True) -> Tuple[float, Dict[str, Any]]:
    cerebro = bt.Cerebro()
    datafeed = bt.feeds.PandasData(
        dataname=df_in,
        datetime="ts",
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None,
    )
    cerebro.adddata(datafeed)
    cerebro.broker.setcash(float(cash))
    cerebro.broker.setcommission(commission=float(commission))
    # Configure slippage (percentage takes precedence over fixed)
    if float(slip_perc) > 0.0:
        cerebro.broker.set_slippage_perc(perc=float(slip_perc), slip_open=bool(slip_open))
    elif float(slip_fixed) > 0.0:
        cerebro.broker.set_slippage_fixed(fixed=float(slip_fixed), slip_open=bool(slip_open))
    cerebro.broker.set_coc(bool(coc))
    if use_sizer:
        cerebro.addsizer(bt.sizers.FixedSize, stake=int(stake))
    from backtest.strategies.registry import get_strategy  # local import for multiprocessing safety
    StrategyCls = get_strategy(strat_name)
    allowed = {}
    try:
        allowed_keys = set(getattr(StrategyCls, "params", {}).keys())
        allowed = {k: v for k, v in params.items() if k in allowed_keys}
    except Exception:
        allowed = params
    cerebro.addstrategy(StrategyCls, **allowed)

    # Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    start_val = cerebro.broker.getvalue()
    if verbose:
        print(f"[{strat_name}] Starting Value: {start_val:.2f}")
    results = cerebro.run()
    end_val = cerebro.broker.getvalue()
    if verbose:
        print(f"[{strat_name}] Final Value:    {end_val:.2f}")

    # Analyzer summaries
    try:
        s = results[0].analyzers.sharpe.get_analysis()  # type: ignore[attr-defined]
        dd = results[0].analyzers.drawdown.get_analysis()  # type: ignore[attr-defined]
        sq = results[0].analyzers.sqn.get_analysis()  # type: ignore[attr-defined]
        ta = results[0].analyzers.trades.get_analysis()  # type: ignore[attr-defined]

        maxdd = (dd.get('max') or {}).get('drawdown') if isinstance(dd, dict) else None

        # Extract trade counts
        total_closed = ((ta.get('total') or {}).get('closed') if isinstance(ta, dict) else None)
        if total_closed is None:
            total_closed = ((ta.get('strike') or {}).get('total') if isinstance(ta, dict) else 0) or 0
        won_total = ((ta.get('won') or {}).get('total') if isinstance(ta, dict) else None)
        if won_total is None:
            won_total = ((ta.get('strike') or {}).get('won') if isinstance(ta, dict) else 0) or 0
        lost_total = ((ta.get('lost') or {}).get('total') if isinstance(ta, dict) else None)
        if lost_total is None:
            lost_total = ((ta.get('strike') or {}).get('lost') if isinstance(ta, dict) else 0) or 0

        # Win rate
        win_rate = (won_total / total_closed * 100.0) if total_closed else None

        # Profit factor: gross profits / gross losses
        gross_won = (((ta.get('won') or {}).get('pnl') or {}).get('total') if isinstance(ta, dict) else None)
        gross_lost_signed = (((ta.get('lost') or {}).get('pnl') or {}).get('total') if isinstance(ta, dict) else None)
        gross_lost = abs(float(gross_lost_signed)) if gross_lost_signed not in (None, 0) else 0.0
        profit_factor = (float(gross_won) / gross_lost) if gross_won is not None and gross_lost > 0 else None

        pnl_net_total = (((ta.get('pnl') or {}).get('net') or {}).get('total') if isinstance(ta, dict) else None)

        if verbose:
            print(f"[{strat_name}] Sharpe: {_fmt(s.get('sharperatio'))}")
            print(f"[{strat_name}] MaxDD:  {_fmt(maxdd)}%")
            print(f"[{strat_name}] SQN:    {_fmt(sq.get('sqn'))}")
            print(f"[{strat_name}] Trades: closed={int(total_closed)} won={int(won_total)} lost={int(lost_total)} pnl_net={_fmt(pnl_net_total)}")
            print(f"[{strat_name}] WinRate: {_fmt(win_rate)}%  ProfitFactor: {_fmt(profit_factor, nd=3)}")

        metrics = {
            "sharpe": s.get('sharperatio') if isinstance(s, dict) else None,
            "maxdd": maxdd,
            "sqn": sq.get('sqn') if isinstance(sq, dict) else None,
            "closed": total_closed,
            "won": won_total,
            "lost": lost_total,
            "pnl_net": pnl_net_total,
            "winrate": win_rate,
            "pf": profit_factor,
        }
    except Exception as exc:
        if verbose:
            print(f"[{strat_name}] Analyzer summary unavailable: {exc}")
        metrics = {}

    if do_plot:
        try:
            cerebro.plot(style="candlestick")
        except Exception as exc:
            print(f"Plotting failed: {exc}")
    return float(end_val), metrics


def run_backtest(inst: str, tf: str, since: Optional[str], until: Optional[str], cash: float, commission: float,
                 stake: int, plot: bool, refresh: bool, use_sizer: bool, coc: bool,
                 strategy_name: str, strat_params: dict, baseline: bool = True,
                 parallel_baseline: bool = False,
                 slip_perc: float = 0.0, slip_fixed: float = 0.0, slip_open: bool = True) -> int:
    load_env_file()
    db = DbConn()

    since_dt = _parse_time(since)
    until_dt = _parse_time(until)

    # Optional: refresh MV before fetch
    view = _tf_to_view(inst, tf)
    if refresh and view is not None:
        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))

    df = _fetch_df(db, inst, tf, since_dt, until_dt, view=view)
    if df.empty:
        print("No data returned for the given parameters.")
        return 1
    else:
        print(f"Loaded {len(df)} bars from {df['ts'].iloc[0]} to {df['ts'].iloc[-1]}")

    data = bt.feeds.PandasData(
        dataname=df,
        datetime="ts",
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None,
    )

    end_main: float
    end_bh: float = 0.0
    # Baseline in parallel: start baseline first, then run main, then await baseline
    if baseline and parallel_baseline:
        try:
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=2) as ex:
                fut = ex.submit(
                    run_once, df, "buyhold", {},
                    cash=cash, commission=commission, coc=coc,
                    use_sizer=use_sizer, stake=stake,
                    slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                    do_plot=False,
                )
                # Run main while baseline executes in parallel
                end_main, _ = run_once(
                    df, strategy_name, strat_params,
                    cash=cash, commission=commission, coc=coc,
                    use_sizer=use_sizer, stake=stake,
                    slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                    do_plot=bool(plot)
                )
                end_bh = float(fut.result())
        except Exception as exc:
            print(f"Parallel baseline failed: {exc}; falling back to sequential.")
            end_main, _ = run_once(
                df, strategy_name, strat_params,
                cash=cash, commission=commission, coc=coc,
                use_sizer=use_sizer, stake=stake,
                slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                do_plot=bool(plot)
            )
            end_bh, _ = run_once(
                df, "buyhold", {},
                cash=cash, commission=commission, coc=coc,
                use_sizer=use_sizer, stake=stake,
                slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                do_plot=False,
            )
    else:
        # Sequential path or no baseline requested
        end_main, _ = run_once(
            df, strategy_name, strat_params,
            cash=cash, commission=commission, coc=coc,
            use_sizer=use_sizer, stake=stake,
            slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
            do_plot=bool(plot)
        )
        if baseline:
            end_bh, _ = run_once(
                df, "buyhold", {},
                cash=cash, commission=commission, coc=coc,
                use_sizer=use_sizer, stake=stake,
                slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                do_plot=False,
            )

    if baseline:
        diff = end_main - end_bh
        pct = (diff / end_bh * 100.0) if end_bh else 0.0
        print("\nComparison vs Buy&Hold:")
        print(f"  Buy&Hold: {end_bh:.2f}")
        print(f"  Strategy: {end_main:.2f}")
        print(f"  Edge:     {diff:+.2f} ({pct:+.2f}%)")

    return 0


def _parse_kv_pairs(pairs: Optional[str]) -> dict:
    """Parse comma-separated key=value pairs into a dict with basic type coercion."""
    if not pairs:
        return {}
    out = {}
    for item in pairs.split(','):
        if not item:
            continue
        if '=' not in item:
            continue
        k, v = item.split('=', 1)
        k = k.strip()
        v = v.strip()
        # basic type coercion
        low = v.lower()
        if low in ("true", "false"):
            out[k] = (low == "true")
            continue
        try:
            if '.' in v:
                out[k] = float(v)
            else:
                out[k] = int(v)
            continue
        except ValueError:
            pass
        out[k] = v
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a simple Backtrader backtest from DB candles")
    p.add_argument("--inst", default="BTC-USDT", help="Instrument ID, e.g., BTC-USDT or ETH-USDT")
    p.add_argument("--tf", default="15m", help="Timeframe: 1m,5m,15m,1h,4h,1d,1w,1mo")
    p.add_argument("--since", default=None, help="Start time (ISO/date/epoch)")
    p.add_argument("--until", default=None, help="End time (ISO/date/epoch)")
    p.add_argument("--cash", type=float, default=10000.0)
    p.add_argument("--commission", type=float, default=0.001, help="Commission as fraction (e.g., 0.001 = 0.1%)")
    p.add_argument("--stake", type=int, default=1, help="Fixed position size in units")
    p.add_argument("--plot", action="store_true", help="Plot results (requires display)")
    p.add_argument("--refresh", action="store_true", help="Refresh MV concurrently before fetching (tf != 1m)")
    p.add_argument("--use-sizer", action="store_true", help="Use FixedSize sizer (not needed for target-% orders)")
    p.add_argument("--coc", action="store_true", help="Cheat-on-close: fill market orders on same bar")
    p.add_argument("--no-baseline", action="store_true", help="Skip Buy&Hold baseline run")
    p.add_argument("--parallel-baseline", action="store_true", help="Run Buy&Hold baseline in a parallel process")
    # Fees & slippage
    p.add_argument("--slip-perc", type=float, default=0.0, help="Price slippage as fraction (e.g., 0.0005 = 5 bps)")
    p.add_argument("--slip-fixed", type=float, default=0.0, help="Fixed price slippage per fill (same units as price)")
    p.add_argument("--no-slip-open", action="store_true", help="Do not apply slippage to open orders")
    # Strategy selection and parameters
    p.add_argument("--strategy", default="sma", help=f"Strategy name. Available: {available_strategies()}")
    p.add_argument(
        "--sp",
        default="",
        help=(
            "Comma-separated strategy params (key=value). "
            "Example: fast=10,slow=20,invest=0.9,use_target=false"
        ),
    )
    p.add_argument("--list-strategies", action="store_true", help="List available strategy names and exit")
    # Walk-forward optimization (WFO)
    p.add_argument("--wfo", action="store_true", help="Enable walk-forward optimization (train/test rolling windows)")
    p.add_argument("--wfo-train-months", type=int, default=12, help="Train window size in months")
    p.add_argument("--wfo-test-months", type=int, default=3, help="Test window size in months")
    p.add_argument("--wfo-step-months", type=int, default=3, help="Step size to advance windows in months")
    p.add_argument("--wfo-grid", default="", help="Param grid like fast=5:30:1,slow=10:60:5 (same format as --opt-grid)")
    p.add_argument("--wfo-constraint", default="", help="Constraint expression on params, e.g., fast<slow")
    p.add_argument("--wfo-objective", default="final", choices=["final", "sharpe", "pf"], help="Metric to pick best train run")
    p.add_argument("--wfo-maxcpus", type=int, default=0, help="Max CPUs per train optimization (0=all)")
    p.add_argument("--wfo-top", type=int, default=5, help="Show top N folds by test result")
    # Optimization (built-in Backtrader optstrategy)
    p.add_argument("--optimize", action="store_true", help="Enable Backtrader optimization for the selected strategy")
    p.add_argument(
        "--opt-grid",
        default="",
        help=(
            "Parameter grid as name=start:stop:step,comma-separated. "
            "Example: fast=5:30:1,slow=10:60:5"
        ),
    )
    p.add_argument("--opt-maxcpus", type=int, default=0, help="Max CPUs for optimization (0 = all cores)")
    p.add_argument("--opt-top", type=int, default=10, help="Show top N results by final value")
    p.add_argument(
        "--opt-constraint",
        default="",
        help="Optional constraint expression using param names, e.g., fast<slow",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_strategies:
        print("Available strategies:")
        print(available_strategies())
        return 0
    strat_params = _parse_kv_pairs(args.sp)
    if args.wfo:
        return run_wfo(
            inst=str(args.inst),
            tf=str(args.tf),
            since=args.since,
            until=args.until,
            cash=float(args.cash),
            commission=float(args.commission),
            strategy_name=str(args.strategy),
            grid_spec=str(args.wfo_grid or args.opt_grid),
            train_months=int(args.wfo_train_months),
            test_months=int(args.wfo_test_months),
            step_months=int(args.wfo_step_months),
            constraint=str(args.wfo_constraint),
            objective=str(args.wfo_objective),
            maxcpus=int(args.wfo_maxcpus),
            slip_perc=float(args.slip_perc),
            slip_fixed=float(args.slip_fixed),
            slip_open=not bool(args.no_slip_open),
        )
    if args.optimize:
        return run_optimize(
            inst=str(args.inst),
            tf=str(args.tf),
            since=args.since,
            until=args.until,
            cash=float(args.cash),
            commission=float(args.commission),
            strategy_name=str(args.strategy),
            grid_spec=str(args.opt_grid),
            maxcpus=int(args.opt_maxcpus),
            constraint=str(args.opt_constraint),
            slip_perc=float(args.slip_perc),
            slip_fixed=float(args.slip_fixed),
            slip_open=not bool(args.no_slip_open),
        )

    return run_backtest(
        inst=str(args.inst),
        tf=str(args.tf),
        since=args.since,
        until=args.until,
        cash=float(args.cash),
        commission=float(args.commission),
        stake=int(args.stake),
        plot=bool(args.plot),
        refresh=bool(args.refresh),
        use_sizer=bool(args.use_sizer),
        coc=bool(args.coc),
        strategy_name=str(args.strategy),
        strat_params=strat_params,
        baseline=not bool(args.no_baseline),
        parallel_baseline=bool(args.parallel_baseline),
        slip_perc=float(args.slip_perc),
        slip_fixed=float(args.slip_fixed),
        slip_open=not bool(args.no_slip_open),
    )


def _parse_grid(grid: str) -> Dict[str, List[int]]:
    """Parse grid string like 'fast=5:30:1,slow=10:60:5' into dict of name -> list of ints.

    Only integer ranges are supported. Inclusive stop is applied (like Python range with stop+step).
    """
    result: Dict[str, List[int]] = {}
    if not grid:
        return result
    for item in grid.split(','):
        item = item.strip()
        if not item or '=' not in item:
            continue
        name, rng = item.split('=', 1)
        name = name.strip()
        parts = [p.strip() for p in rng.split(':')]
        if len(parts) == 3 and all(p.lstrip('-').isdigit() for p in parts):
            start, stop, step = map(int, parts)
            if step == 0:
                continue
            vals = list(range(start, stop + (1 if (stop - start) * step >= 0 else -1), step))
            result[name] = vals
        else:
            # fallback: single int
            try:
                result[name] = [int(rng)]
            except ValueError:
                pass
    return result


def _constraint_ok(params: Dict[str, Any], expr: str) -> bool:
    if not expr:
        return True
    try:
        # Evaluate with param dict as locals, no builtins
        return bool(eval(expr, {"__builtins__": {}}, params))
    except Exception:
        return True


def _pick_best_by_objective(rows: List[Dict[str, Any]], objective: str) -> Optional[Dict[str, Any]]:
    if not rows:
        return None
    key = objective.lower()
    def score(row: Dict[str, Any]) -> float:
        val = row.get(key)
        try:
            return float(val)
        except Exception:
            return float("-inf")
    return max(rows, key=score)


def run_optimize(inst: str, tf: str, since: Optional[str], until: Optional[str], cash: float, commission: float,
                 strategy_name: str, grid_spec: str, maxcpus: int, constraint: str,
                 slip_perc: float = 0.0, slip_fixed: float = 0.0, slip_open: bool = True) -> int:
    load_env_file()
    db = DbConn()

    since_dt = _parse_time(since)
    until_dt = _parse_time(until)

    view = _tf_to_view(inst, tf)
    if view is not None:
        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # Do not block if MV not present; ignore errors
            try:
                conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
            except Exception:
                pass

    df = _fetch_df(db, inst, tf, since_dt, until_dt, view=view)
    if df.empty:
        print("No data returned for the given parameters.")
        return 1
    else:
        print(f"Loaded {len(df)} bars from {df['ts'].iloc[0]} to {df['ts'].iloc[-1]}")

    grid = _parse_grid(grid_spec)
    if not grid:
        print("No optimization grid provided. Use --opt-grid, e.g., fast=5:30:1,slow=10:60:5")
        return 2

    # Set up Cerebro for optimization
    cerebro = bt.Cerebro()
    datafeed = bt.feeds.PandasData(
        dataname=df,
        datetime="ts",
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None,
    )
    cerebro.adddata(datafeed)
    cerebro.broker.setcash(float(cash))
    cerebro.broker.setcommission(commission=float(commission))
    if float(slip_perc) > 0.0:
        cerebro.broker.set_slippage_perc(perc=float(slip_perc), slip_open=bool(slip_open))
    elif float(slip_fixed) > 0.0:
        cerebro.broker.set_slippage_fixed(fixed=float(slip_fixed), slip_open=bool(slip_open))

    StrategyCls = get_strategy(strategy_name)
    # Add analyzers to apply to each optimization run
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    cerebro.optreturn = False  # return full strategy instances
    cerebro.optstrategy(StrategyCls, **grid)
    print(f"Starting optimization for '{strategy_name}' with grid: {grid}")
    results = cerebro.run(maxcpus=int(maxcpus))

    # Flatten and collect metrics
    flat: List[bt.Strategy] = []
    for res in results:
        # res can be a list of 1 strategy instance
        if isinstance(res, (list, tuple)) and res:
            flat.append(res[0])
        elif isinstance(res, bt.Strategy):
            flat.append(res)

    rows: List[Dict[str, Any]] = []
    for strat in flat:
        # Extract params for this run
        p = getattr(strat, 'params', None)
        p_dict = {}
        if p is not None:
            for k in dir(p):
                if k.startswith('_'):
                    continue
                try:
                    val = getattr(p, k)
                except Exception:
                    continue
                if isinstance(val, (int, float, bool)):
                    p_dict[k] = val

        if not _constraint_ok(p_dict, constraint):
            continue

        # Metrics via analyzers
        try:
            s = strat.analyzers.sharpe.get_analysis()
            dd = strat.analyzers.drawdown.get_analysis()
            sq = strat.analyzers.sqn.get_analysis()
            ta = strat.analyzers.trades.get_analysis()
        except Exception:
            continue

        maxdd = (dd.get('max') or {}).get('drawdown') if isinstance(dd, dict) else None
        total_closed = ((ta.get('total') or {}).get('closed') if isinstance(ta, dict) else None)
        if total_closed is None:
            total_closed = ((ta.get('strike') or {}).get('total') if isinstance(ta, dict) else 0) or 0
        won_total = ((ta.get('won') or {}).get('total') if isinstance(ta, dict) else None)
        if won_total is None:
            won_total = ((ta.get('strike') or {}).get('won') if isinstance(ta, dict) else 0) or 0
        gross_won = (((ta.get('won') or {}).get('pnl') or {}).get('total') if isinstance(ta, dict) else None)
        gross_lost_signed = (((ta.get('lost') or {}).get('pnl') or {}).get('total') if isinstance(ta, dict) else None)
        gross_lost = abs(float(gross_lost_signed)) if gross_lost_signed not in (None, 0) else 0.0
        profit_factor = (float(gross_won) / gross_lost) if gross_won is not None and gross_lost > 0 else None
        win_rate = (won_total / total_closed * 100.0) if total_closed else None

        try:
            final_value = float(strat.broker.getvalue())
        except Exception:
            final_value = float('nan')

        rows.append({
            'params': p_dict,
            'final': final_value,
            'sharpe': s.get('sharperatio') if isinstance(s, dict) else None,
            'maxdd': maxdd,
            'winrate': win_rate,
            'pf': profit_factor,
        })

    if not rows:
        print("No optimization results collected (possibly due to constraint or failures).")
        return 3

    rows.sort(key=lambda r: (r['final'] if r['final'] is not None else float('-inf')), reverse=True)
    topn = 10
    try:
        from argparse import Namespace
        if isinstance(globals().get("args"), Namespace):  # type: ignore
            topn = int(getattr(globals()["args"], "opt_top", 10))  # type: ignore
    except Exception:
        pass
    topn = max(1, int(min(len(rows), topn)))
    print(f"\nTop {topn} results by Final Value:")
    for i, r in enumerate(rows[:topn], 1):
        print(
            f"#{i} final={_fmt(r['final'])} sharpe={_fmt(r['sharpe'])} maxdd={_fmt(r['maxdd'])}% "
            f"winrate={_fmt(r['winrate'])}% pf={_fmt(r['pf'], nd=3)} params={r['params']}"
        )

    return 0


def _month_delta(dt: datetime, months: int) -> datetime:
    # naive month delta for UTC dt
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    day = min(dt.day, 28)  # safe fallback
    return dt.replace(year=year, month=month, day=day)


def _slice_df_by_range(df: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
    mask = (df["ts"] >= start) & (df["ts"] <= end)
    return df.loc[mask].copy()


def run_wfo(inst: str, tf: str, since: Optional[str], until: Optional[str], cash: float, commission: float,
            strategy_name: str, grid_spec: str, train_months: int, test_months: int, step_months: int,
            constraint: str, objective: str, maxcpus: int,
            slip_perc: float = 0.0, slip_fixed: float = 0.0, slip_open: bool = True) -> int:
    load_env_file()
    db = DbConn()

    since_dt = _parse_time(since)
    until_dt = _parse_time(until)

    view = _tf_to_view(inst, tf)
    if view is not None:
        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            try:
                conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
            except Exception:
                pass

    df = _fetch_df(db, inst, tf, since_dt, until_dt, view=view)
    if df.empty:
        print("No data returned for the given parameters.")
        return 1
    else:
        print(f"Loaded {len(df)} bars from {df['ts'].iloc[0]} to {df['ts'].iloc[-1]}")

    grid = _parse_grid(grid_spec)
    if not grid:
        print("No WFO grid provided. Use --wfo-grid (or --opt-grid), e.g., fast=5:30:1,slow=10:60:5")
        return 2

    start_ts = df["ts"].min()
    end_ts = df["ts"].max()
    folds: List[Dict[str, Any]] = []

    train_start = start_ts
    while True:
        train_end = _month_delta(train_start, train_months)
        test_end = _month_delta(train_end, test_months)
        if train_end >= end_ts or train_start >= end_ts:
            break
        test_start = train_end
        if test_start >= end_ts:
            break
        test_end = min(test_end, end_ts)

        train_df = _slice_df_by_range(df, train_start, train_end)
        test_df = _slice_df_by_range(df, test_start, test_end)
        if train_df.empty or test_df.empty:
            train_start = _month_delta(train_start, step_months)
            continue

        # Optimize on train (reuse run_optimize approach but without printing top table)
        cerebro = bt.Cerebro()
        datafeed = bt.feeds.PandasData(
            dataname=train_df,
            datetime="ts",
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            openinterest=None,
        )
        cerebro.adddata(datafeed)
        cerebro.broker.setcash(float(cash))
        cerebro.broker.setcommission(commission=float(commission))
        if float(slip_perc) > 0.0:
            cerebro.broker.set_slippage_perc(perc=float(slip_perc), slip_open=bool(slip_open))
        elif float(slip_fixed) > 0.0:
            cerebro.broker.set_slippage_fixed(fixed=float(slip_fixed), slip_open=bool(slip_open))

        StrategyCls = get_strategy(strategy_name)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.optreturn = False
        cerebro.optstrategy(StrategyCls, **grid)
        results = cerebro.run(maxcpus=int(maxcpus))

        flat: List[bt.Strategy] = []
        for res in results:
            if isinstance(res, (list, tuple)) and res:
                flat.append(res[0])
            elif isinstance(res, bt.Strategy):
                flat.append(res)

        train_rows: List[Dict[str, Any]] = []
        for strat in flat:
            p_dict = {}
            p = getattr(strat, "params", None)
            if p is not None:
                for k in dir(p):
                    if k.startswith("_"):
                        continue
                    try:
                        val = getattr(p, k)
                    except Exception:
                        continue
                    if isinstance(val, (int, float, bool)):
                        p_dict[k] = val
            if not _constraint_ok(p_dict, constraint):
                continue
            try:
                s = strat.analyzers.sharpe.get_analysis()
                dd = strat.analyzers.drawdown.get_analysis()
                ta = strat.analyzers.trades.get_analysis()
            except Exception:
                continue
            maxdd = (dd.get("max") or {}).get("drawdown") if isinstance(dd, dict) else None
            total_closed = ((ta.get("total") or {}).get("closed") if isinstance(ta, dict) else None)
            if total_closed is None:
                total_closed = ((ta.get("strike") or {}).get("total") if isinstance(ta, dict) else 0) or 0
            won_total = ((ta.get("won") or {}).get("total") if isinstance(ta, dict) else None)
            if won_total is None:
                won_total = ((ta.get("strike") or {}).get("won") if isinstance(ta, dict) else 0) or 0
            gross_won = (((ta.get("won") or {}).get("pnl") or {}).get("total") if isinstance(ta, dict) else None)
            gross_lost_signed = (((ta.get("lost") or {}).get("pnl") or {}).get("total") if isinstance(ta, dict) else None)
            gross_lost = abs(float(gross_lost_signed)) if gross_lost_signed not in (None, 0) else 0.0
            profit_factor = (float(gross_won) / gross_lost) if gross_won is not None and gross_lost > 0 else None
            win_rate = (won_total / total_closed * 100.0) if total_closed else None
            train_rows.append({
                "params": p_dict,
                "final": float(strat.broker.getvalue()) if hasattr(strat, "broker") else None,
                "sharpe": s.get("sharperatio") if isinstance(s, dict) else None,
                "maxdd": maxdd,
                "winrate": win_rate,
                "pf": profit_factor,
            })

        best = _pick_best_by_objective(train_rows, objective)
        if not best:
            train_start = _month_delta(train_start, step_months)
            continue

        # Run best params on test set (single run, no plotting)
        test_end_val, test_metrics = run_once(
            test_df, strategy_name, best["params"],
            cash=cash, commission=commission, coc=True,  # keep coc default true for consistency
            use_sizer=False, stake=1,
            slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
            do_plot=False, verbose=False,
        )

        folds.append({
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "params": best["params"],
            "train_obj": best.get(objective),
            "test_final": test_end_val,
            "test_metrics": test_metrics,
        })

        train_start = _month_delta(train_start, step_months)

    if not folds:
        print("No WFO folds produced (check date ranges and window sizes).")
        return 3

    print("\nWFO Fold Results (test periods):")
    for i, f in enumerate(folds, 1):
        m = f["test_metrics"]
        print(
            f"#{i} test={f['test_start'].date()}->{f['test_end'].date()} final={_fmt(f['test_final'])} "
            f"sharpe={_fmt(m.get('sharpe'))} maxdd={_fmt(m.get('maxdd'))}% "
            f"winrate={_fmt(m.get('winrate'))}% pf={_fmt(m.get('pf'), nd=3)} params={f['params']}"
        )

    # Aggregate OOS metrics
    finals = [f["test_final"] for f in folds if f.get("test_final") is not None]
    avg_final = sum(finals) / len(finals) if finals else float("nan")
    print("\nWFO Summary (out-of-sample test):")
    print(f"  Folds: {len(folds)}")
    print(f"  Avg Final: {_fmt(avg_final)}")

    # Show top test folds by final value
    topn = min(len(folds), 5)
    folds_sorted = sorted(folds, key=lambda f: f.get("test_final", float("-inf")), reverse=True)
    print(f"  Top {topn} folds by test Final:")
    for i, f in enumerate(folds_sorted[:topn], 1):
        print(
            f"    #{i} test={f['test_start'].date()}->{f['test_end'].date()} final={_fmt(f['test_final'])} params={f['params']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
