from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.accounts_repo import AccountsRepo, NewAccount
from web.deps import get_db

router = APIRouter(prefix="/accounts", tags=["accounts"])
repo = AccountsRepo()

ALLOWED_PLATFORMS = ("binance", "okx")


class AccountResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    platform: str
    is_demo: bool = False
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    created_at: str
    updated_at: str


class CreateAccountRequest(BaseModel):
    name: str
    platform: str
    description: Optional[str] = None
    is_demo: bool = False
    api_key: Optional[str] = None
    secret_key: Optional[str] = None


class UpdateAccountRequest(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    description: Optional[str] = None
    is_demo: Optional[bool] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None


def _to_response(obj) -> AccountResponse:
    return AccountResponse(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        platform=obj.platform,
        is_demo=bool(obj.is_demo),
        api_key=obj.api_key,
        secret_key=obj.secret_key,
        created_at=obj.created_at.isoformat(),
        updated_at=obj.updated_at.isoformat(),
    )


@router.get("", response_model=List[AccountResponse])
def list_accounts(session: Session = Depends(get_db)) -> List[AccountResponse]:
    return [_to_response(a) for a in repo.list_all(session)]


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: CreateAccountRequest,
    session: Session = Depends(get_db),
) -> AccountResponse:
    if payload.platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"platform must be one of {ALLOWED_PLATFORMS}")
    try:
        obj = repo.create(
            session,
            NewAccount(
                name=payload.name,
                platform=payload.platform,
                description=payload.description,
                is_demo=payload.is_demo,
                api_key=payload.api_key,
                secret_key=payload.secret_key,
            ),
        )
        session.commit()
        session.refresh(obj)
        return _to_response(obj)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Account with this name already exists")


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    payload: UpdateAccountRequest,
    session: Session = Depends(get_db),
) -> AccountResponse:
    if payload.platform is not None and payload.platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"platform must be one of {ALLOWED_PLATFORMS}")
    fields = {k: v for k, v in payload.model_dump().items() if v is not None or k == "is_demo"}
    obj = repo.update(session, account_id, **fields)
    if obj is None:
        raise HTTPException(status_code=404, detail="Account not found")
    session.commit()
    session.refresh(obj)
    return _to_response(obj)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    session: Session = Depends(get_db),
) -> None:
    deleted = repo.delete(session, account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")
    session.commit()
