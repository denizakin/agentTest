from __future__ import annotations

import re
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from web.deps import get_db
from db.strategies_repo import StrategiesRepo, NewStrategy, ALLOWED_STATUSES
from backtest.strategies.strategy_manager import StrategyManager

router = APIRouter(prefix="/strategies", tags=["strategies"])
repo = StrategiesRepo()
strategy_manager = StrategyManager()


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
    """Create a new strategy record and register it to the filesystem."""
    try:
        # Validate code if provided
        class_name = None
        if payload.code:
            # Validate Python syntax
            try:
                compile(payload.code, '<strategy>', 'exec')
            except SyntaxError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Python syntax error at line {e.lineno}: {e.msg}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Code validation error: {str(e)}"
                )

            # Extract class name from code
            class_match = re.search(r'class\s+(\w+)\s*\(.*bt\.Strategy.*\):', payload.code)
            if not class_match:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Code must contain a class that inherits from bt.Strategy"
                )
            class_name = class_match.group(1)

        # Create database record
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

        # Register strategy to filesystem if code provided and status is prod
        if payload.code and class_name and payload.status == "prod":
            try:
                strategy_manager.register_strategy(
                    name=payload.name,
                    code=payload.code,
                    class_name=class_name
                )
            except Exception as e:
                # If registration fails, rollback the database transaction
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to register strategy to filesystem: {str(e)}"
                )

        return _to_schema(obj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="strategy name already exists")


class UpdateStrategyRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[Literal["draft", "prod", "archived"]] = None
    tag: Optional[str] = None
    notes: Optional[str] = None
    code: Optional[str] = None


@router.patch("/{strategy_id}", response_model=Strategy)
def update_strategy(
    strategy_id: int,
    payload: UpdateStrategyRequest,
    session: Session = Depends(get_db)
) -> Strategy:
    """Update a strategy record and sync to filesystem if needed."""
    obj = repo.get_by_id(session, strategy_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy not found")

    old_status = obj.status
    old_name = obj.name

    # Validate code if provided
    if payload.code is not None:
        try:
            compile(payload.code, '<strategy>', 'exec')
        except SyntaxError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Python syntax error at line {e.lineno}: {e.msg}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Code validation error: {str(e)}"
            )

    # Update fields
    if payload.name is not None:
        obj.name = payload.name
    if payload.status is not None:
        obj.status = payload.status
    if payload.tag is not None:
        obj.tag = payload.tag
    if payload.notes is not None:
        obj.notes = payload.notes
    if payload.code is not None:
        obj.code = payload.code

    try:
        session.commit()
        session.refresh(obj)

        # Handle filesystem registration
        # If status changed to 'prod' and code exists, register
        if old_status != "prod" and obj.status == "prod" and obj.code:
            class_match = re.search(r'class\s+(\w+)\s*\(.*bt\.Strategy.*\):', obj.code)
            if class_match:
                class_name = class_match.group(1)
                try:
                    strategy_manager.register_strategy(
                        name=obj.name,
                        code=obj.code,
                        class_name=class_name
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to register strategy: {str(e)}"
                    )

        # If status changed from 'prod' to something else, unregister
        elif old_status == "prod" and obj.status != "prod":
            try:
                strategy_manager.unregister_strategy(old_name)
            except Exception as e:
                # Log but don't fail - file might not exist
                print(f"Warning: Failed to unregister strategy {old_name}: {e}")

        # If name changed while in prod status, re-register
        elif obj.status == "prod" and payload.name and payload.name != old_name and obj.code:
            try:
                strategy_manager.unregister_strategy(old_name)
                class_match = re.search(r'class\s+(\w+)\s*\(.*bt\.Strategy.*\):', obj.code)
                if class_match:
                    class_name = class_match.group(1)
                    strategy_manager.register_strategy(
                        name=obj.name,
                        code=obj.code,
                        class_name=class_name
                    )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update strategy registration: {str(e)}"
                )

        return _to_schema(obj)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="strategy name already exists")
