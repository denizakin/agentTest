from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.run_log import RunLog


class RunLogsRepo:
    """Append-only log storage per run."""

    def append(self, session: Session, run_id: int, level: str, message: str) -> None:
        log = RunLog(run_id=run_id, level=level, message=message, ts=datetime.now(tz=timezone.utc))
        session.add(log)

    def list_logs(self, session: Session, run_id: int, limit: int = 200, offset: int = 0) -> List[RunLog]:
        stmt = (
            select(RunLog)
            .where(RunLog.run_id == run_id)
            .order_by(RunLog.ts.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())
