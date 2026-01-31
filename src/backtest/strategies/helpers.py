"""Helper utilities for backtest strategies."""

from __future__ import annotations


def price_fmt(price: float) -> str:
    """Format price with dynamic precision based on value.

    - >= 1: 2 decimal places (e.g., 45.32)
    - >= 0.01: 4 decimal places (e.g., 0.1234)
    - >= 0.0001: 6 decimal places (e.g., 0.001234)
    - < 0.0001: 8 decimal places (e.g., 0.00001234)
    """
    if price >= 1:
        return f"{price:.2f}"
    elif price >= 0.01:
        return f"{price:.4f}"
    elif price >= 0.0001:
        return f"{price:.6f}"
    else:
        return f"{price:.8f}"
