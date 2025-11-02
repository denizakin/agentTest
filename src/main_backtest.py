"""CLI: Run a simple Backtrader backtest using DB candles.

Example:
  python src/main_backtest.py --inst BTC-USDT --tf 15m --since 2024-01-01 --cash 10000 --plot
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Optional

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


def run_backtest(inst: str, tf: str, since: Optional[str], until: Optional[str], cash: float, commission: float,
                 stake: int, plot: bool, refresh: bool, use_sizer: bool, coc: bool,
                 strategy_name: str, strat_params: dict) -> int:
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

    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.broker.setcash(float(cash))
    cerebro.broker.setcommission(commission=float(commission))
    cerebro.broker.set_coc(bool(coc))
    if use_sizer:
        cerebro.addsizer(bt.sizers.FixedSize, stake=int(stake))
    StrategyCls = get_strategy(strategy_name)
    # Filter params to those defined by the strategy (if possible)
    allowed = {}
    try:
        allowed_keys = set(getattr(StrategyCls, "params", {}).keys())
        allowed = {k: v for k, v in strat_params.items() if k in allowed_keys}
    except Exception:
        allowed = strat_params
    cerebro.addstrategy(StrategyCls, **allowed)

    start_val = cerebro.broker.getvalue()
    print(f"Starting Portfolio Value: {start_val:.2f}")
    cerebro.run()
    end_val = cerebro.broker.getvalue()
    print(f"Final Portfolio Value:    {end_val:.2f}")

    if plot:
        try:
            cerebro.plot(style="candlestick")
        except Exception as exc:
            print(f"Plotting failed: {exc}")
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
    )


if __name__ == "__main__":
    raise SystemExit(main())
