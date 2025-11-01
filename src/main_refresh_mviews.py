"""CLI: Refresh materialized views for BTC/ETH timeframes.

Examples:
  # Refresh all BTC & ETH views concurrently
  python src/main_refresh_mviews.py

  # Refresh only BTC 5m,15m blocking
  python src/main_refresh_mviews.py --inst btc --tfs 5m,15m --blocking
"""
from __future__ import annotations

import argparse
from typing import Iterable, List, Sequence, Tuple

from sqlalchemy import text

from config import load_env_file
from db.db_conn import DbConn


SUPPORTED_TFS: Tuple[str, ...] = ("5m", "15m", "1h", "4h", "1d", "1w", "1mo")
ORDERED_TFS: Tuple[str, ...] = ("5m", "15m", "1h", "4h", "1d", "1w", "1mo")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Refresh candle materialized views")
    p.add_argument(
        "--inst",
        default="both",
        choices=["btc", "eth", "both"],
        help="Which instrument views to refresh",
    )
    p.add_argument(
        "--tfs",
        default=",".join(ORDERED_TFS),
        help=f"Comma-separated timeframes to refresh. Supported: {','.join(SUPPORTED_TFS)}",
    )
    p.add_argument("--blocking", action="store_true", help="Use blocking REFRESH (faster, but locks reads)")
    p.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    return p.parse_args()


def _mv_names(inst_opt: str, tfs: Sequence[str]) -> List[str]:
    insts: Iterable[str]
    if inst_opt == "both":
        insts = ("btc", "eth")
    else:
        insts = (inst_opt,)

    # Keep timeframes in canonical order but filter by requested
    requested = {tf.strip().lower() for tf in tfs}
    ordered = [tf for tf in ORDERED_TFS if tf in requested]

    names: List[str] = []
    for inst in insts:
        for tf in ordered:
            names.append(f"mv_candlesticks_{inst}_{tf}")
    return names


def main() -> int:
    args = parse_args()
    load_env_file()
    db = DbConn(echo=args.echo)

    tfs = [s for s in (args.tfs.split(",") if args.tfs else []) if s]
    unknown = [tf for tf in tfs if tf not in SUPPORTED_TFS]
    if unknown:
        print(f"Unsupported timeframes: {unknown}. Supported: {list(SUPPORTED_TFS)}")
        return 2

    names = _mv_names(args.inst, tfs)
    if not names:
        print("No materialized views selected to refresh.")
        return 0

    cmd = "REFRESH MATERIALIZED VIEW CONCURRENTLY {}" if not args.blocking else "REFRESH MATERIALIZED VIEW {}"

    # CONCURRENTLY must run outside a transaction; use AUTOCOMMIT for both modes for simplicity.
    with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for name in names:
            try:
                print(f"Refreshing {name} ({'concurrent' if not args.blocking else 'blocking'}) ...", end=" ")
                conn.execute(text(cmd.format(name)))
                print("ok")
            except Exception as exc:
                print(f"failed: {exc}")
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

