from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Numeric

from db.base import Base


class OptimizationResult(Base):
    """Stores individual optimization variant results."""
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False)
    variant_params = Column(JSON, nullable=False)  # Parameter combination for this variant
    final_value = Column(Numeric(30, 8), nullable=True)
    sharpe = Column(Numeric(18, 8), nullable=True)
    maxdd = Column(Numeric(18, 8), nullable=True)
    winrate = Column(Numeric(18, 8), nullable=True)
    profit_factor = Column(Numeric(18, 8), nullable=True)
    sqn = Column(Numeric(18, 8), nullable=True)
    total_trades = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")
