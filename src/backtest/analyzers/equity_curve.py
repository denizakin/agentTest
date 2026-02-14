from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any
import backtrader as bt


class EquityCurve(bt.Analyzer):
    """Analyzer to capture equity curve (portfolio value over time)."""

    def __init__(self):
        super().__init__()
        self.equity_data: List[Dict[str, Any]] = []
        print("[EquityCurve] Analyzer initialized", flush=True)

    def prenext(self):
        """Record portfolio value during prenext phase (warming up indicators)."""
        self._record_value()

    def nextstart(self):
        """Record portfolio value at the first next() call."""
        self._record_value()

    def next(self):
        """Record portfolio value at each bar."""
        self._record_value()

    def _record_value(self):
        """Helper to record current portfolio value."""
        dt = self.strategy.datetime.datetime(0)
        ts = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        value = self.strategy.broker.getvalue()

        self.equity_data.append({
            "ts": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
            "value": float(value),
        })

    def get_analysis(self):
        """Return the equity curve data."""
        print(f"[EquityCurve] get_analysis called, returning {len(self.equity_data)} points", flush=True)
        return {"equity": self.equity_data}
