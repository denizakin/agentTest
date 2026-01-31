from __future__ import annotations

import backtrader as bt

from .helpers import price_fmt


class BuyHoldStrategy(bt.Strategy):
    """Buy-and-hold strategy.

    Buys once at the first bar using invest% of available cash and holds.
    """

    params = dict(
        invest=0.99,
        min_size=1e-6,
        printlog=True,
    )

    def log(self, txt: str) -> None:
        if not getattr(self.p, "printlog", False):
            return
        dt = self.datas[0].datetime.datetime(0)
        print(f"{dt.isoformat()} - {txt}")

    def __init__(self) -> None:
        self.ordered = False

    def next(self) -> None:
        if self.ordered:
            return
        price = float(self.data.close[0])
        cash = float(self.broker.getcash())
        size = (cash * float(self.p.invest)) / price if price else 0.0
        if size < float(self.p.min_size):
            size = float(self.p.min_size)
        self.log(f"BUY&HOLD: buy size={size:.8f} price={price_fmt(price)}")
        self.buy(size=size)
        self.ordered = True

