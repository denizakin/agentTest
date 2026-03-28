from __future__ import annotations

from typing import List, Optional
from dataclasses import dataclass, field
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.trade_definition import TradeDefinition


@dataclass
class NewTradeDefinition:
    strategy_id: Optional[int]
    strategy_name: str
    instrument_id: str
    timeframe: str
    status: str = "paused"
    params: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    account_id: Optional[int] = None


class TradeDefinitionsRepo:

    def list_all(self, session: Session) -> List[TradeDefinition]:
        stmt = select(TradeDefinition).order_by(TradeDefinition.created_at.desc())
        return list(session.scalars(stmt).all())

    def get(self, session: Session, def_id: int) -> Optional[TradeDefinition]:
        return session.get(TradeDefinition, def_id)

    def create(self, session: Session, data: NewTradeDefinition) -> TradeDefinition:
        td = TradeDefinition(
            strategy_id=data.strategy_id,
            account_id=data.account_id,
            strategy_name=data.strategy_name,
            instrument_id=data.instrument_id,
            timeframe=data.timeframe,
            status=data.status,
            params=data.params,
            notes=data.notes,
        )
        session.add(td)
        session.flush()
        return td

    def update_status(self, session: Session, def_id: int, status: str) -> Optional[TradeDefinition]:
        td = session.get(TradeDefinition, def_id)
        if td:
            td.status = status
            session.add(td)
        return td

    def delete(self, session: Session, def_id: int) -> bool:
        td = session.get(TradeDefinition, def_id)
        if td:
            session.delete(td)
            return True
        return False
