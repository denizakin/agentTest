from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, JSON, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from db.base import Base


class RunHeader(Base):
    __tablename__ = "run_headers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(20), nullable=False)  # backtest | optimize | wfo
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
    notes = Column(String, nullable=True)

    results = relationship("RunResult", back_populates="header", cascade="all, delete-orphan")
    wfo_folds = relationship("WfoFold", back_populates="header", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_run_headers_type_ts", "run_type", "started_at"),
        Index("ix_run_headers_inst_tf", "instrument_id", "timeframe"),
    )


class RunResult(Base):
    __tablename__ = "run_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(50), nullable=False)  # main | baseline | opt_variant | wfo_test | wfo_train
    params = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)  # include final, sharpe, maxdd, winrate, pf, etc.
    plot_path = Column(String, nullable=True)

    header = relationship("RunHeader", back_populates="results")

    __table_args__ = (
        Index("ix_run_results_run_label", "run_id", "label"),
    )


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
    metrics = Column(JSON, nullable=True)  # test metrics

    header = relationship("RunHeader", back_populates="wfo_folds")

    __table_args__ = (
        Index("ix_wfo_folds_run_fold", "run_id", "fold_index"),
    )

