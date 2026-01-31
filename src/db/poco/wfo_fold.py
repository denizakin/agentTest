from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Numeric

from db.base import Base


class WfoFold(Base):
    __tablename__ = "wfo_folds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False)
    fold_index = Column(Integer, nullable=False)
    train_start = Column(DateTime(timezone=True), nullable=False)
    train_end = Column(DateTime(timezone=True), nullable=False)
    test_start = Column(DateTime(timezone=True), nullable=False)
    test_end = Column(DateTime(timezone=True), nullable=False)
    params = Column(JSON, nullable=True)
    train_objective = Column(Numeric(30, 8), nullable=True)
    metrics = Column(JSON, nullable=True)
