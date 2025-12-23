from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from db.poco.run_log import RunHeader, RunResult, WfoFold


class RunLogger:
    """Persist backtest/optimization/WFO runs and related artifacts."""

    def __init__(self, plot_dir: Path = Path("resources/plots")) -> None:
        self.plot_dir = plot_dir
        self.plot_dir.mkdir(parents=True, exist_ok=True)

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
    ) -> int:
        result = RunResult(
            run_id=run_id,
            label=label,
            params=params,
            metrics=metrics,
            plot_path=plot_path,
        )
        session.add(result)
        session.flush()
        return int(result.id)

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

