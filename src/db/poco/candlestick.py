from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, Numeric, String, UniqueConstraint

from db.base import Base


class Candlestick(Base):
    __tablename__ = "candlesticks"

    # Instrument ID, e.g., BTC-USDT
    instrument_id = Column(String(30), primary_key=True)
    # Candle open time (UTC)
    ts = Column(DateTime(timezone=True), primary_key=True)

    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(30, 12), nullable=False)

    __table_args__ = (
        UniqueConstraint("instrument_id", "ts", name="uq_candles_inst_ts"),
        Index("ix_candles_inst_ts", "instrument_id", "ts"),
    )

