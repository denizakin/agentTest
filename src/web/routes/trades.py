from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.strategies_repo import StrategiesRepo
from db.trade_definitions_repo import TradeDefinitionsRepo, NewTradeDefinition
from web.deps import get_db

router = APIRouter(prefix="/trades", tags=["trades"])
repo = TradeDefinitionsRepo()
strategies_repo = StrategiesRepo()


class CreateTradeDefinitionRequest(BaseModel):
    strategy_id: int
    instrument_id: str
    timeframe: str
    status: str = "paused"
    params: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    account_id: Optional[int] = None


class UpdateTradeDefinitionRequest(BaseModel):
    status: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    account_id: Optional[int] = None


class TradeDefinitionResponse(BaseModel):
    id: int
    strategy_id: Optional[int]
    account_id: Optional[int]
    strategy_name: str
    instrument_id: str
    timeframe: str
    status: str
    params: Optional[Dict[str, Any]]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=List[TradeDefinitionResponse])
def list_trade_definitions(session: Session = Depends(get_db)) -> List[TradeDefinitionResponse]:
    rows = repo.list_all(session)
    return [
        TradeDefinitionResponse(
            id=r.id,
            strategy_id=r.strategy_id,
            account_id=r.account_id,
            strategy_name=r.strategy_name,
            instrument_id=r.instrument_id,
            timeframe=r.timeframe,
            status=r.status,
            params=r.params,
            notes=r.notes,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("", response_model=TradeDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_trade_definition(
    payload: CreateTradeDefinitionRequest,
    session: Session = Depends(get_db),
) -> TradeDefinitionResponse:
    strat = strategies_repo.get_by_id(session, payload.strategy_id)
    if strat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy not found")

    if payload.status not in ("active", "paused", "stopped"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid status")

    td = repo.create(
        session,
        NewTradeDefinition(
            strategy_id=payload.strategy_id,
            strategy_name=strat.name,
            instrument_id=payload.instrument_id,
            timeframe=payload.timeframe,
            status=payload.status,
            params=payload.params,
            notes=payload.notes,
            account_id=payload.account_id,
        ),
    )
    session.commit()
    session.refresh(td)
    return TradeDefinitionResponse(
        id=td.id,
        strategy_id=td.strategy_id,
        account_id=td.account_id,
        strategy_name=td.strategy_name,
        instrument_id=td.instrument_id,
        timeframe=td.timeframe,
        status=td.status,
        params=td.params,
        notes=td.notes,
        created_at=td.created_at,
        updated_at=td.updated_at,
    )


@router.patch("/{def_id}", response_model=TradeDefinitionResponse)
def update_trade_definition(
    def_id: int,
    payload: UpdateTradeDefinitionRequest,
    session: Session = Depends(get_db),
) -> TradeDefinitionResponse:
    td = repo.get(session, def_id)
    if td is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="trade definition not found")

    if payload.status is not None:
        if payload.status not in ("active", "paused", "stopped"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid status")
        td.status = payload.status
    if payload.params is not None:
        td.params = payload.params
    if payload.notes is not None:
        td.notes = payload.notes
    if payload.account_id is not None:
        td.account_id = payload.account_id

    session.add(td)
    session.commit()
    session.refresh(td)
    return TradeDefinitionResponse(
        id=td.id,
        strategy_id=td.strategy_id,
        account_id=td.account_id,
        strategy_name=td.strategy_name,
        instrument_id=td.instrument_id,
        timeframe=td.timeframe,
        status=td.status,
        params=td.params,
        notes=td.notes,
        created_at=td.created_at,
        updated_at=td.updated_at,
    )


@router.delete("/{def_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_definition(def_id: int, session: Session = Depends(get_db)) -> None:
    found = repo.delete(session, def_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="trade definition not found")
    session.commit()
