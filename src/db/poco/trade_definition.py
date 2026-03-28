from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from db.base import Base


class TradeDefinition(Base):
    __tablename__ = "trade_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies.strategy_id", ondelete="SET NULL"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    strategy_name = Column(String(200), nullable=False)
    instrument_id = Column(String(30), nullable=False)
    timeframe = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, server_default="paused")
    params = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active','paused','stopped')", name="ck_trade_def_status"),
    )
