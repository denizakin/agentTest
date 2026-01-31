from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Integer, String, Text, UniqueConstraint

from db.base import Base


class Strategy(Base):
    __tablename__ = "strategies"

    strategy_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, server_default="draft")
    tag = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    code = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("name", name="uq_strategy_name"),
        CheckConstraint("status IN ('draft','prod','archived')", name="ck_strategy_status"),
    )

