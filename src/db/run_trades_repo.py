from __future__ import annotations

from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.run_trade import RunTrade


class RunTradesRepo:
    """Repository for persisting individual trades from backtests."""

    def save_trades(self, session: Session, run_id: int, trades: List[Dict[str, Any]]) -> None:
        """Save a list of trades for a given run."""
        for trade in trades:
            trade_obj = RunTrade(
                run_id=run_id,
                entry_ts=trade["entry_ts"],
                exit_ts=trade["exit_ts"],
                side=trade["side"],
                entry_price=trade["entry_price"],
                exit_price=trade["exit_price"],
                size=trade["size"],
                pnl=trade["pnl"],
                pnl_pct=trade.get("pnl_pct"),
                mae=trade.get("mae"),
                mfe=trade.get("mfe"),
                commission=trade.get("commission"),
            )
            session.add(trade_obj)

    def list_trades(self, session: Session, run_id: int, limit: int = 10000, offset: int = 0) -> List[RunTrade]:
        """Retrieve trades for a given run with pagination."""
        stmt = (
            select(RunTrade)
            .where(RunTrade.run_id == run_id)
            .order_by(RunTrade.entry_ts)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())
