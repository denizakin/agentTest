from __future__ import annotations

import backtrader as bt


class SimpleSmaStrategy(bt.Strategy):
    """A minimal SMA crossover strategy with logging.

    - Buy when fast SMA crosses above slow SMA.
    - Sell when fast SMA crosses below slow SMA.
    - Logs signals, orders, and trades for debugging.
    """

    params = dict(
        fast=10,
        slow=20,
        printlog=True,
        invest=0.95,  # target portfolio percent on long entries
        use_target=True,  # use order_target_percent for sizing
    )

    def __init__(self) -> None:
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data.close, period=int(self.p.fast))
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data.close, period=int(self.p.slow))
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        self.order = None

    # ----- Logging helpers -----
    def log(self, txt: str) -> None:
        if not getattr(self.p, "printlog", False):
            return
        dt = self.datas[0].datetime.datetime(0)
        print(f"{dt.isoformat()} - {txt}")

    # ----- Backtrader notifications -----
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(
                f"ORDER {side} EXECUTED, price={order.executed.price:.2f}, size={order.executed.size:.6f}, "
                f"cost={order.executed.value:.2f}, comm={order.executed.comm:.2f}"
            )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"ORDER {order.getstatusname().upper()} for size={order.executed.size:.6f}")
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(
            f"TRADE CLOSED, pnl_gross={trade.pnl:.2f}, pnl_net={trade.pnlcomm:.2f}"
        )

    def next(self) -> None:
        if self.order:
            return  # pending order in flight

        cross = self.crossover[0]
        price = self.data.close[0]

        if cross > 0:
            self.log(f"SIGNAL BUY (cross up) @ close={price:.2f}")
            if self.p.use_target:
                self.order = self.order_target_percent(target=float(self.p.invest))
            else:
                # fallback: size ~ invest% of cash / price
                cash = float(self.broker.getcash())
                size = (cash * float(self.p.invest)) / float(price) if price else 0.0
                self.order = self.buy(size=size)
        elif cross < 0:
            self.log(f"SIGNAL SELL (cross down) @ close={price:.2f}")
            if self.p.use_target:
                # reduce exposure to 0% (flat)
                self.order = self.order_target_percent(target=0.0)
            else:
                if self.position.size > 0:
                    self.order = self.sell(size=self.position.size)
