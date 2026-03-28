from __future__ import annotations

from typing import List, Dict, Any, Optional
import random


def _max_drawdown_pct(equity_curve: List[float]) -> float:
    """Return maximum drawdown as a positive percentage (0–100)."""
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd
    return max_dd


def run_monte_carlo(
    pnls: List[float],
    initial_cash: float,
    n_sims: int = 500,
    timestamps: Optional[List[int]] = None,
    actual_equity: Optional[List[float]] = None,
    percentiles: tuple = (5, 25, 50, 75, 95),
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation by shuffling the PnL sequence.

    Args:
        pnls: Per-trade PnLs used for shuffling simulations.
        initial_cash: Starting portfolio value.
        n_sims: Number of shuffle simulations.
        timestamps: Unix timestamps (seconds) for each trade's close, same length as pnls.
                    A synthetic t0 = timestamps[0] - 86400 is prepended for initial_cash.
        actual_equity: Optional override for the "actual" equity curve (n_trades+1 values).
                       When provided (e.g. from combined equity curve), it replaces the
                       cumulative-sum curve. Useful for WFO where open positions at fold
                       boundaries would otherwise cause a mismatch.
        percentiles: Which percentile bands to compute.

    Returns dict with:
      - 'actual': equity values (len = n_trades+1)
      - 'timestamps': unix seconds (len = n_trades+1), only if timestamps was provided
      - 'p5'..'p95': percentile band values (same length)
      - 'dd_actual', 'dd_p5'..'dd_p95': max drawdown distribution (%)
    """
    n_trades = len(pnls)
    if n_trades == 0:
        empty = [initial_cash]
        result: Dict[str, Any] = {
            "actual": empty,
            **{f"p{p}": empty for p in percentiles},
            "n_trades": 0,
            "n_sims": n_sims,
            "dd_actual": 0.0,
            **{f"dd_p{p}": 0.0 for p in percentiles},
        }
        if timestamps is not None:
            result["timestamps"] = timestamps
        return result

    # "actual" equity: use provided curve if given (WFO combined-equity-aligned),
    # otherwise compute from cumulative PnLs
    if actual_equity is not None and len(actual_equity) == n_trades + 1:
        actual = actual_equity
    else:
        actual = [initial_cash]
        for pnl in pnls:
            actual.append(actual[-1] + pnl)

    dd_actual = _max_drawdown_pct(actual)

    # Run simulations using the provided pnls (shuffled order)
    step_values: List[List[float]] = [[] for _ in range(n_trades + 1)]
    step_values[0] = [initial_cash] * n_sims

    sim_pnls = list(pnls)
    sim_max_dds: List[float] = []

    for _ in range(n_sims):
        random.shuffle(sim_pnls)
        curve = [initial_cash]
        eq = initial_cash
        for i, pnl in enumerate(sim_pnls):
            eq += pnl
            curve.append(eq)
            step_values[i + 1].append(eq)
        sim_max_dds.append(_max_drawdown_pct(curve))

    for step in range(1, n_trades + 1):
        step_values[step].sort()
    sim_max_dds.sort()

    def get_pct(sorted_vals: List[float], pct: int) -> float:
        if not sorted_vals:
            return 0.0
        idx = int(pct / 100 * (len(sorted_vals) - 1))
        return sorted_vals[idx]

    result = {
        "actual": actual,
        "n_trades": n_trades,
        "n_sims": n_sims,
        "dd_actual": round(dd_actual, 2),
    }
    for p in percentiles:
        result[f"p{p}"] = [get_pct(step_values[i], p) for i in range(n_trades + 1)]
        result[f"dd_p{p}"] = round(get_pct(sim_max_dds, p), 2)

    if timestamps is not None and len(timestamps) == n_trades:
        # Prepend t0 = first timestamp − 1 day (for the initial_cash point)
        result["timestamps"] = [timestamps[0] - 86400] + timestamps

    return result
