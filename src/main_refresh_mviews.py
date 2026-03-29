"""CLI: Incrementally refresh candles schema tables.

Calls candles.refresh_incremental() for each matching table in candles.refresh_state.

Examples:
  # Refresh all candles tables
  python src/main_refresh_mviews.py

  # Refresh only BTC tables
  python src/main_refresh_mviews.py --inst btc

  # Refresh BTC 5m and 15m
  python src/main_refresh_mviews.py --inst btc --tfs 5m,15m
"""
from __future__ import annotations

import argparse
import re
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import text

from config import load_env_file
from db.db_conn import DbConn


SUPPORTED_TFS: Tuple[str, ...] = ("5m", "15m", "1h", "4h", "1d", "1w", "1mo")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Refresh candles schema tables incrementally")
    p.add_argument(
        "--inst",
        default=None,
        help="Coin symbol to refresh (e.g. btc, eth). If omitted, refreshes all instruments.",
    )
    p.add_argument(
        "--tfs",
        default=None,
        help=f"Comma-separated timeframes to refresh. Supported: {','.join(SUPPORTED_TFS)}. If omitted, refreshes all.",
    )
    p.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    return p.parse_args()


def _select_tables(conn, inst: Optional[str], tfs: Optional[Sequence[str]]) -> List[str]:
    """Return table names from candles.refresh_state matching the filters."""
    rows = conn.execute(text("SELECT table_name FROM candles.refresh_state ORDER BY table_name")).fetchall()
    names = [r[0] for r in rows]

    if inst:
        coin = inst.strip().lower()
        names = [n for n in names if re.match(rf"^candlesticks_{re.escape(coin)}_", n)]

    if tfs:
        tf_set = {t.strip().lower() for t in tfs}
        names = [n for n in names if n.rsplit("_", 1)[-1] in tf_set]

    return names


def main() -> int:
    args = parse_args()
    load_env_file()
    db = DbConn(echo=args.echo)

    tfs: Optional[List[str]] = None
    if args.tfs:
        tfs = [s.strip().lower() for s in args.tfs.split(",") if s.strip()]
        unknown = [t for t in tfs if t not in SUPPORTED_TFS]
        if unknown:
            print(f"Unsupported timeframes: {unknown}. Supported: {list(SUPPORTED_TFS)}")
            return 2

    with db.engine.connect() as conn:
        tables = _select_tables(conn, args.inst, tfs)
        if not tables:
            print("No candles tables matched the given filters.")
            return 0

        for table_name in tables:
            print(f"Refreshing candles.{table_name} ...", end=" ", flush=True)
            try:
                conn.execute(text("SELECT candles.refresh_incremental(:t)"), {"t": table_name})
                conn.commit()
                print("ok")
            except Exception as exc:
                print(f"failed: {exc}")
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
