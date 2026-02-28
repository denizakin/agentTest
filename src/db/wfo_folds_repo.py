from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.poco.wfo_fold import WfoFold


class WfoFoldsRepo:
    """Read helpers for wfo_folds table."""

    def list_by_run(self, session: Session, run_id: int) -> List[WfoFold]:
        stmt = (
            select(WfoFold)
            .where(WfoFold.run_id == run_id)
            .order_by(WfoFold.fold_index.asc())
        )
        return list(session.scalars(stmt).all())

    def count_folds(self, session: Session, run_id: int) -> int:
        stmt = select(func.count()).select_from(WfoFold).where(WfoFold.run_id == run_id)
        return session.scalar(stmt) or 0
