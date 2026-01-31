from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, JSON, String, Text

from db.base import Base


class RunResult(Base):
    __tablename__ = "run_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("run_headers.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(length=50), nullable=False)
    params = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    plot_path = Column(Text, nullable=True)
