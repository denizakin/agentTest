from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.strategy import Strategy

ALLOWED_STATUSES: Sequence[str] = ("draft", "prod", "archived")


@dataclass(frozen=True)
class NewStrategy:
    name: str
    status: str = "draft"
    tag: Optional[str] = None
    notes: Optional[str] = None
    code: Optional[str] = None


class StrategiesRepo:
    """Repository for CRUD operations on strategies."""

    def create(self, session: Session, new_strategy: NewStrategy) -> Strategy:
        if new_strategy.status not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid status '{new_strategy.status}'. Allowed: {ALLOWED_STATUSES}")

        obj = Strategy(
            name=new_strategy.name,
            status=new_strategy.status,
            tag=new_strategy.tag,
            notes=new_strategy.notes,
            code=new_strategy.code,
        )
        session.add(obj)
        session.flush()  # ensures PK is populated
        return obj

    def list_all(self, session: Session, limit: int = 100, offset: int = 0) -> List[Strategy]:
        stmt = (
            select(Strategy)
            .order_by(Strategy.strategy_id)
            .offset(offset)
            .limit(limit)
        )
        rows = session.scalars(stmt).all()
        return list(rows)

    def get_by_id(self, session: Session, strategy_id: int) -> Optional[Strategy]:
        return session.get(Strategy, strategy_id)

