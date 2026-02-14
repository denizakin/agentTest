from __future__ import annotations

from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from db.poco.optimization_result import OptimizationResult


class OptimizationResultsRepo:
    """Repository for optimization results."""

    @staticmethod
    def create_result(
        session: Session,
        run_id: int,
        variant_params: dict,
        final_value: Optional[float] = None,
        sharpe: Optional[float] = None,
        maxdd: Optional[float] = None,
        winrate: Optional[float] = None,
        profit_factor: Optional[float] = None,
        sqn: Optional[float] = None,
        total_trades: Optional[int] = None,
    ) -> OptimizationResult:
        """Create a new optimization result variant."""
        result = OptimizationResult(
            run_id=run_id,
            variant_params=variant_params,
            final_value=final_value,
            sharpe=sharpe,
            maxdd=maxdd,
            winrate=winrate,
            profit_factor=profit_factor,
            sqn=sqn,
            total_trades=total_trades,
        )
        session.add(result)
        session.flush()
        return result

    @staticmethod
    def get_results_by_run(session: Session, run_id: int, limit: Optional[int] = None) -> List[OptimizationResult]:
        """Get all optimization results for a run, ordered by final value descending."""
        query = (
            session.query(OptimizationResult)
            .filter(OptimizationResult.run_id == run_id)
            .order_by(desc(OptimizationResult.final_value))
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def get_best_result(session: Session, run_id: int) -> Optional[OptimizationResult]:
        """Get the best optimization result for a run (highest final value)."""
        return (
            session.query(OptimizationResult)
            .filter(OptimizationResult.run_id == run_id)
            .order_by(desc(OptimizationResult.final_value))
            .first()
        )

    @staticmethod
    def count_results(session: Session, run_id: int) -> int:
        """Count total optimization results for a run."""
        return session.query(OptimizationResult).filter(OptimizationResult.run_id == run_id).count()
