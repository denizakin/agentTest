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
        invest=0.95,  # invest % of available cash on buys
        use_target=False,  # default to explicit size for reliability
        min_size=1e-6,  # avoid zero-size due to rounding
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
            self.log(f"ORDER {order.getstatusname()} id={order.ref} size={order.created.size}")
            return
        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(
                f"ORDER {side} EXECUTED, price={order.executed.price:.2f}, size={order.executed.size:.6f}, "
                f"cost={order.executed.value:.2f}, comm={order.executed.comm:.2f}"
            )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(
                f"ORDER {order.getstatusname().upper()} id={order.ref} created_size={order.created.size} executed_size={order.executed.size}"
            )
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
                self.log(f"order_target_percent to {self.p.invest*100:.1f}% -> order={self.order}")
            else:
                cash = float(self.broker.getcash())
                size = (cash * float(self.p.invest)) / float(price) if price else 0.0
                if size < float(self.p.min_size):
                    size = float(self.p.min_size)
                self.log(f"BUY attempt: cash={cash:.2f} price={price:.2f} size={size:.8f}")
                self.order = self.buy(size=size)
        elif cross < 0:
            self.log(f"SIGNAL SELL (cross down) @ close={price:.2f}")
            if self.p.use_target:
                # reduce exposure to 0% (flat)
                self.order = self.order_target_percent(target=0.0)
                self.log(f"order_target_percent to 0% -> order={self.order}")
            else:
                if self.position.size > 0:
                    self.log(f"CLOSE position size={self.position.size}")
                    self.order = self.close()

    def notify_cashvalue(self, cash, value):
        # track portfolio changes
        self.log(f"CASH/VALUE updated: cash={cash:.2f} value={value:.2f}")
