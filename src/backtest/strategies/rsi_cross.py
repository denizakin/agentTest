from __future__ import annotations

import backtrader as bt


class RsiCrossStrategy(bt.Strategy):
    """RSI cross strategy.

    - Buy when RSI crosses up above lower threshold.
    - Close when RSI crosses down below upper threshold.
    """

    params = dict(
        period=14,
        lower=30.0,
        upper=70.0,
        invest=0.95,
        use_target=False,
        min_size=1e-6,
        printlog=True,
    )

    def log(self, txt: str) -> None:
        if not getattr(self.p, "printlog", False):
            return
        dt = self.datas[0].datetime.datetime(0)
        print(f"{dt.isoformat()} - {txt}")

    def __init__(self) -> None:
        self.rsi = bt.indicators.RSI(self.data.close, period=int(self.p.period))
        self.cross_up = bt.indicators.CrossOver(self.rsi, float(self.p.lower))
        self.cross_dn = bt.indicators.CrossOver(float(self.p.upper), self.rsi)
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            self.log(f"ORDER {order.getstatusname()} id={order.ref} size={order.created.size}")
            return
        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(
                f"ORDER {side} EXECUTED, price={order.executed.price:.2f}, size={order.executed.size:.6f}, cost={order.executed.value:.2f}, comm={order.executed.comm:.2f}"
            )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(
                f"ORDER {order.getstatusname().upper()} id={order.ref} created_size={order.created.size} executed_size={order.executed.size}"
            )
        self.order = None

    def next(self) -> None:
        if self.order:
            return
        price = float(self.data.close[0])
        cross_up = self.cross_up[0] > 0
        cross_dn = self.cross_dn[0] > 0

        if not self.position and cross_up:
            self.log(f"RSI BUY (cross up) rsi={self.rsi[0]:.2f} close={price:.2f}")
            if self.p.use_target:
                self.order = self.order_target_percent(target=float(self.p.invest))
            else:
                cash = float(self.broker.getcash())
                size = (cash * float(self.p.invest)) / price if price else 0.0
                if size < float(self.p.min_size):
                    size = float(self.p.min_size)
                self.order = self.buy(size=size)
        elif self.position and cross_dn:
            self.log(f"RSI CLOSE (cross down) rsi={self.rsi[0]:.2f} close={price:.2f}")
            if self.p.use_target:
                self.order = self.order_target_percent(target=0.0)
            else:
                self.order = self.close()

