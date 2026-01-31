from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.run_result import RunResult


class RunResultsRepo:
    """Append/list run_results entries."""

    def add_result(self, session: Session, run_id: int, label: str, params: dict, metrics: dict, plot_path: str | None = None) -> RunResult:
        row = RunResult(
            run_id=run_id,
            label=label,
            params=params,
            metrics=metrics,
            plot_path=plot_path,
        )
        session.add(row)
        session.flush()
        return row

    def list_by_run(self, session: Session, run_id: int) -> List[RunResult]:
        stmt = select(RunResult).where(RunResult.run_id == run_id).order_by(RunResult.id.asc())
        return list(session.scalars(stmt).all())
