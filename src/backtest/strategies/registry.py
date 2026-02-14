from __future__ import annotations

from typing import Dict, Type, Any

import backtrader as bt

# Import and register available strategies here
from .simple_sma import SimpleSmaStrategy
from .buy_hold import BuyHoldStrategy
from .rsi_cross import RsiCrossStrategy
from .smagpt import RealMaCrossATR


STRATEGY_REGISTRY: Dict[str, Type[bt.Strategy]] = {
    # key: human-friendly name -> strategy class
    "sma": SimpleSmaStrategy,
    "buyhold": BuyHoldStrategy,
    "rsi": RsiCrossStrategy,

    "smagpt": RealMaCrossATR,}


def get_strategy(name: str) -> Type[bt.Strategy]:
    key = name.strip().lower()
    if key not in STRATEGY_REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Available: {', '.join(sorted(STRATEGY_REGISTRY))}")
    return STRATEGY_REGISTRY[key]


def available_strategies() -> str:
    return ", ".join(sorted(STRATEGY_REGISTRY))


def get_strategy_params(name: str) -> Dict[str, Any]:
    """Get default parameters for a strategy.

    Returns a dict with parameter names as keys and their default values.
    """
    strategy_class = get_strategy(name)
    params_obj = getattr(strategy_class, 'params', None)

    if params_obj is None:
        return {}

    # Backtrader params can be accessed as a tuple of (name, value) pairs
    params_dict = {}
    if hasattr(params_obj, '_gettuple'):
        # Backtrader's params object
        for param_name in dir(params_obj):
            if param_name.startswith('_'):
                continue
            try:
                value = getattr(params_obj, param_name)
                # Only include simple types (int, float, str, bool)
                if isinstance(value, (int, float, str, bool)):
                    params_dict[param_name] = value
            except:
                continue

    return params_dict
