from __future__ import annotations

from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from web.deps import get_db
from db.strategies_repo import StrategiesRepo, NewStrategy, ALLOWED_STATUSES

router = APIRouter(prefix="/strategies", tags=["strategies"])
repo = StrategiesRepo()


class Strategy(BaseModel):
    id: int
    name: str
    status: str = "draft"
    tag: Optional[str] = None
    notes: Optional[str] = None
    code: Optional[str] = None


class CreateStrategyRequest(BaseModel):
    name: str
    status: Literal["draft", "prod", "archived"] = "draft"
    tag: Optional[str] = None
    notes: Optional[str] = None
    code: Optional[str] = None


def _to_schema(db_obj) -> Strategy:
    return Strategy(
        id=db_obj.strategy_id,
        name=db_obj.name,
        status=db_obj.status,
        tag=db_obj.tag,
        notes=db_obj.notes,
        code=db_obj.code,
    )


@router.get("", response_model=List[Strategy])
def list_strategies(
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_db),
) -> List[Strategy]:
    """List strategies from the database."""
    rows = repo.list_all(session, limit=limit, offset=offset)
    return [_to_schema(r) for r in rows]


@router.post("", response_model=Strategy, status_code=status.HTTP_201_CREATED)
def create_strategy(payload: CreateStrategyRequest, session: Session = Depends(get_db)) -> Strategy:
    """Create a new strategy record."""
    try:
        obj = repo.create(
            session,
            NewStrategy(
                name=payload.name,
                status=payload.status,
                tag=payload.tag,
                notes=payload.notes,
                code=payload.code,
            ),
        )
        session.commit()
        session.refresh(obj)
        return _to_schema(obj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="strategy name already exists")
