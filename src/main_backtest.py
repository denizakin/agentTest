"""CLI: Run a simple Backtrader backtest using DB candles.

Example:
  python src/main_backtest.py --inst BTC-USDT --tf 15m --since 2024-01-01 --cash 10000 --plot
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

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


def _fetch_df(db: DbConn, inst: str, tf: str, since: Optional[datetime], until: Optional[datetime]) -> pd.DataFrame:
    view = _tf_to_view(inst, tf)
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
             do_plot: bool = False) -> float:
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
    print(f"[{strat_name}] Starting Value: {start_val:.2f}")
    results = cerebro.run()
    end_val = cerebro.broker.getvalue()
    print(f"[{strat_name}] Final Value:    {end_val:.2f}")

    # Analyzer summaries
    try:
        s = results[0].analyzers.sharpe.get_analysis()  # type: ignore[attr-defined]
        dd = results[0].analyzers.drawdown.get_analysis()  # type: ignore[attr-defined]
        sq = results[0].analyzers.sqn.get_analysis()  # type: ignore[attr-defined]
        ta = results[0].analyzers.trades.get_analysis()  # type: ignore[attr-defined]

        print(f"[{strat_name}] Sharpe: {_fmt(s.get('sharperatio'))}")
        maxdd = (dd.get('max') or {}).get('drawdown') if isinstance(dd, dict) else None
        print(f"[{strat_name}] MaxDD:  {_fmt(maxdd)}%")
        print(f"[{strat_name}] SQN:    {_fmt(sq.get('sqn'))}")

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

        print(f"[{strat_name}] Trades: closed={int(total_closed)} won={int(won_total)} lost={int(lost_total)} pnl_net={_fmt(pnl_net_total)}")
        print(f"[{strat_name}] WinRate: {_fmt(win_rate)}%  ProfitFactor: {_fmt(profit_factor, nd=3)}")
    except Exception as exc:
        print(f"[{strat_name}] Analyzer summary unavailable: {exc}")

    if do_plot:
        try:
            cerebro.plot(style="candlestick")
        except Exception as exc:
            print(f"Plotting failed: {exc}")
    return float(end_val)


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

    df = _fetch_df(db, inst, tf, since_dt, until_dt)
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
                end_main = run_once(
                    df, strategy_name, strat_params,
                    cash=cash, commission=commission, coc=coc,
                    use_sizer=use_sizer, stake=stake,
                    slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                    do_plot=bool(plot)
                )
                end_bh = float(fut.result())
        except Exception as exc:
            print(f"Parallel baseline failed: {exc}; falling back to sequential.")
            end_main = run_once(
                df, strategy_name, strat_params,
                cash=cash, commission=commission, coc=coc,
                use_sizer=use_sizer, stake=stake,
                slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                do_plot=bool(plot)
            )
            end_bh = run_once(
                df, "buyhold", {},
                cash=cash, commission=commission, coc=coc,
                use_sizer=use_sizer, stake=stake,
                slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
                do_plot=False,
            )
    else:
        # Sequential path or no baseline requested
        end_main = run_once(
            df, strategy_name, strat_params,
            cash=cash, commission=commission, coc=coc,
            use_sizer=use_sizer, stake=stake,
            slip_perc=slip_perc, slip_fixed=slip_fixed, slip_open=slip_open,
            do_plot=bool(plot)
        )
        if baseline:
            end_bh = run_once(
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
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_strategies:
        print("Available strategies:")
        print(available_strategies())
        return 0
    strat_params = _parse_kv_pairs(args.sp)
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


if __name__ == "__main__":
    raise SystemExit(main())
