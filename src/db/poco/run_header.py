from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text

from db.base import Base


class RunHeader(Base):
    __tablename__ = "run_headers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(20), nullable=False)  # e.g., backtest, optimize
    instrument_id = Column(String(30), nullable=False)
    timeframe = Column(String(10), nullable=False)
    strategy = Column(String(50), nullable=False)
    params = Column(JSON, nullable=True)
    cash = Column(Numeric(30, 8), nullable=True)
    commission = Column(Numeric(18, 8), nullable=True)
    slip_perc = Column(Numeric(18, 8), nullable=True)
    slip_fixed = Column(Numeric(18, 8), nullable=True)
    slip_open = Column(Boolean, nullable=True)
    baseline = Column(Boolean, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

