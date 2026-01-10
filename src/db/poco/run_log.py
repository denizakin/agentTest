from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, Index

from db.base import Base


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    level = Column(String(10), nullable=False, default="INFO")
    message = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_run_logs_run_ts", "run_id", "ts"),
    )
