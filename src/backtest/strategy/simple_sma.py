from __future__ import annotations

import backtrader as bt


class SimpleSmaStrategy(bt.Strategy):
    """A minimal SMA crossover strategy.

    - Buy when fast SMA crosses above slow SMA.
    - Sell when fast SMA crosses below slow SMA.
    """

    params = dict(
        fast=10,
        slow=20,
    )

    def __init__(self) -> None:
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data.close, period=int(self.p.fast))
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data.close, period=int(self.p.slow))
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self) -> None:
        if not self.position:
            if self.crossover > 0:
                self.buy()
        else:
            if self.crossover < 0:
                self.sell()

