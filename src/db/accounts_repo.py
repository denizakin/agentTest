from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.account import Account


@dataclass(frozen=True)
class NewAccount:
    name: str
    platform: str
    description: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    is_demo: bool = False


class AccountsRepo:
    def create(self, session: Session, new_account: NewAccount) -> Account:
        obj = Account(
            name=new_account.name,
            platform=new_account.platform,
            description=new_account.description,
            api_key=new_account.api_key,
            secret_key=new_account.secret_key,
            is_demo=new_account.is_demo,
        )
        session.add(obj)
        session.flush()
        return obj

    def list_all(self, session: Session) -> List[Account]:
        stmt = select(Account).order_by(Account.name)
        return list(session.scalars(stmt).all())

    def get_by_id(self, session: Session, account_id: int) -> Optional[Account]:
        return session.get(Account, account_id)

    def update(self, session: Session, account_id: int, **fields) -> Optional[Account]:
        obj = session.get(Account, account_id)
        if obj is None:
            return None
        for key, value in fields.items():
            setattr(obj, key, value)
        session.flush()
        return obj

    def delete(self, session: Session, account_id: int) -> bool:
        obj = session.get(Account, account_id)
        if obj is None:
            return False
        session.delete(obj)
        session.flush()
        return True
