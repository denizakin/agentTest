from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.poco.run_header import RunHeader
from db.poco.run_result import RunResult
from db.poco.wfo_fold import WfoFold
from db.poco.optimization_result import OptimizationResult
from db.run_trades_repo import RunTradesRepo


class RunLogger:
    """Persist backtest/optimization/WFO runs and related artifacts."""

    def __init__(self, plot_dir: Path = Path("resources/plots")) -> None:
        self.plot_dir = plot_dir
        self.plot_dir.mkdir(parents=True, exist_ok=True)
        self.trades_repo = RunTradesRepo()

    def start_run(
        self,
        session: Session,
        run_type: str,
        instrument_id: str,
        timeframe: str,
        strategy: str,
        params: Dict[str, Any],
        cash: Optional[float],
        commission: Optional[float],
        slip_perc: Optional[float],
        slip_fixed: Optional[float],
        slip_open: Optional[bool],
        baseline: Optional[bool] = None,
        notes: Optional[str] = None,
    ) -> int:
        now = datetime.now(timezone.utc)
        header = RunHeader(
            run_type=run_type,
            instrument_id=instrument_id,
            timeframe=timeframe,
            strategy=strategy,
            params=params,
            cash=cash,
            commission=commission,
            slip_perc=slip_perc,
            slip_fixed=slip_fixed,
            slip_open=slip_open,
            baseline=baseline,
            started_at=now,
            notes=notes,
        )
        session.add(header)
        session.flush()
        return int(header.id)

    def complete_run(self, session: Session, run_id: int) -> None:
        header = session.get(RunHeader, run_id)
        if header:
            header.ended_at = datetime.now(timezone.utc)
            session.add(header)

    def log_result(
        self,
        session: Session,
        run_id: int,
        label: str,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        plot_path: Optional[str] = None,
        trades: Optional[List[Dict[str, Any]]] = None,
        equity: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        # Store equity curve in metrics JSON if provided
        if equity:
            metrics = {**metrics, "equity": equity}
            print(f"[log_result] Added {len(equity)} equity points to metrics for label={label}", flush=True)
        else:
            print(f"[log_result] No equity data provided for label={label}", flush=True)

        print(f"[log_result] Creating RunResult for label={label}, metrics keys: {list(metrics.keys())}", flush=True)
        result = RunResult(
            run_id=run_id,
            label=label,
            params=params,
            metrics=metrics,
            plot_path=plot_path,
        )
        print(f"[log_result] RunResult created, adding to session...", flush=True)
        session.add(result)
        print(f"[log_result] Flushing session...", flush=True)
        session.flush()
        print(f"[log_result] Successfully saved result for label={label}", flush=True)

        # Save trades to run_trades table if provided
        if trades and label == "main":  # Only save trades for main strategy, not baseline
            self.trades_repo.save_trades(session, run_id, trades)

        return int(result.id)

    def log_optimization_variant(
        self,
        session: Session,
        run_id: int,
        variant_params: Dict[str, Any],
        final_value: Optional[float] = None,
        sharpe: Optional[float] = None,
        maxdd: Optional[float] = None,
        winrate: Optional[float] = None,
        profit_factor: Optional[float] = None,
        sqn: Optional[float] = None,
        total_trades: Optional[int] = None,
    ) -> int:
        """Log a single optimization variant result."""
        opt_result = OptimizationResult(
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
        session.add(opt_result)
        session.flush()
        return int(opt_result.id)

    def log_wfo_fold(
        self,
        session: Session,
        run_id: int,
        fold_index: int,
        train_range: Tuple[datetime, datetime],
        test_range: Tuple[datetime, datetime],
        params: Dict[str, Any],
        train_objective: Optional[float],
        metrics: Dict[str, Any],
    ) -> int:
        fold = WfoFold(
            run_id=run_id,
            fold_index=fold_index,
            train_start=train_range[0],
            train_end=train_range[1],
            test_start=test_range[0],
            test_end=test_range[1],
            params=params,
            train_objective=train_objective,
            metrics=metrics,
        )
        session.add(fold)
        session.flush()
        return int(fold.id)

    def save_plot(self, figs, run_id: int, label: str) -> Optional[str]:
        """Save matplotlib figures produced by backtrader.plot()."""
        try:
            from matplotlib.figure import Figure
        except Exception:
            return None

        paths = []
        if not figs:
            return None
        # backtrader.plot may return list[list[Figure]] or list[Figure]
        flat = []
        for item in figs:
            if isinstance(item, (list, tuple)):
                flat.extend(item)
            else:
                flat.append(item)
        for idx, fig in enumerate(flat, 1):
            if not isinstance(fig, Figure):
                continue
            fname = f"run_{run_id}_{label}_{idx}.png"
            fpath = self.plot_dir / fname
            fig.savefig(fpath)
            paths.append(str(fpath))
        if not paths:
            return None
        # return first path; additional ones can be inferred by pattern
        return paths[0]

