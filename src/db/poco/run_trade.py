from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from db.base import Base


class RunTrade(Base):
    __tablename__ = "run_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_ts = Column(DateTime(timezone=True), nullable=False)
    exit_ts = Column(DateTime(timezone=True), nullable=False)
    side = Column(String(10), nullable=False)  # LONG/SHORT
    entry_price = Column(Numeric(20, 8), nullable=False)
    exit_price = Column(Numeric(20, 8), nullable=False)
    size = Column(Numeric(30, 12), nullable=False)
    pnl = Column(Numeric(20, 8), nullable=False)
    pnl_pct = Column(Numeric(10, 4), nullable=True)
    mae = Column(Numeric(20, 8), nullable=True)  # Maximum Adverse Excursion
    mfe = Column(Numeric(20, 8), nullable=True)  # Maximum Favorable Excursion
    commission = Column(Numeric(20, 8), nullable=True)
