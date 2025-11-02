from __future__ import annotations

from typing import Dict, Type

import backtrader as bt

# Import and register available strategies here
from .simple_sma import SimpleSmaStrategy
from .buy_hold import BuyHoldStrategy
from .rsi_cross import RsiCrossStrategy


STRATEGY_REGISTRY: Dict[str, Type[bt.Strategy]] = {
    # key: human-friendly name -> strategy class
    "sma": SimpleSmaStrategy,
    "buyhold": BuyHoldStrategy,
    "rsi": RsiCrossStrategy,
}


def get_strategy(name: str) -> Type[bt.Strategy]:
    key = name.strip().lower()
    if key not in STRATEGY_REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Available: {', '.join(sorted(STRATEGY_REGISTRY))}")
    return STRATEGY_REGISTRY[key]


def available_strategies() -> str:
    return ", ".join(sorted(STRATEGY_REGISTRY))
