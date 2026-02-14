import backtrader as bt


class RealMaCrossATR(bt.Strategy):
    params = dict(
        short_period=20,
        long_period=50,

        # Risk / pozisyon boyutu
        risk_perc=1.0,          # her işlemde sermayenin % kaçını riske atayım (1.0 = %1)
        allow_short=True,       # short açsın mı

        # ATR ve hedefler
        atr_period=14,
        sl_atr_mult=2.0,        # stop mesafesi = ATR * 2
        tp_rr=2.0,              # take-profit = stop mesafesi * 2 (RR=2)

        # Emri hangi fiyattan sayalım (cheat-on-open kullanmıyorsanız next bar market gibi düşünün)
        use_close_for_entry_ref=True,
    )

    def __init__(self):
        self.sma_s = bt.ind.SMA(self.data.close, period=self.p.short_period)
        self.sma_l = bt.ind.SMA(self.data.close, period=self.p.long_period)
        self.cross = bt.ind.CrossOver(self.sma_s, self.sma_l)

        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)

        self.brackets = []   # aktif bracket emirleri
        self.last_signal = 0

    # --- Yardımcılar ---
    def _cancel_all(self):
        for o in list(self.brackets):
            try:
                self.cancel(o)
            except Exception:
                pass
        self.brackets.clear()

    def _risk_size(self, entry_price, stop_price):
        """
        Risk bazlı lot hesabı:
        risk_cash = equity * risk_perc/100
        per_unit_risk = |entry - stop|
        size = risk_cash / per_unit_risk
        """
        cash_risk = self.broker.getvalue() * (self.p.risk_perc / 100.0)
        per_unit_risk = abs(entry_price - stop_price)
        if per_unit_risk <= 0:
            return 0

        size = cash_risk / per_unit_risk

        # Çok küçükse 0'a çek
        if size < 1e-6:
            return 0

        # Enstrümana göre tam sayı gerekebilir; burada int'e kırpıyoruz.
        # Kripto/forex gibi fractional destekliyorsanız int() kaldırılabilir.
        return int(size)

    def _entry_ref_price(self):
        return float(self.data.close[0]) if self.p.use_close_for_entry_ref else float(self.data.open[0])

    # --- Ana döngü ---
    def next(self):
        if len(self.data) < max(self.p.short_period, self.p.long_period, self.p.atr_period) + 2:
            return

        # Eğer bekleyen bracket emirleri varsa yeni sinyalde önce temizle
        # (aksi halde aynı anda birden fazla bracket kalabiliyor)
        # Ayrıca pozisyon değişiminde de manage ederiz.
        signal = 1 if self.cross[0] > 0 else (-1 if self.cross[0] < 0 else 0)
        if signal == 0:
            return

        # aynı sinyali tekrar tekrar basma
        if signal == self.last_signal:
            return
        self.last_signal = signal

        # Ters sinyal geldiğinde mevcut pozisyonu kapat + emirleri temizle
        if self.position:
            if (self.position.size > 0 and signal < 0) or (self.position.size < 0 and signal > 0):
                self._cancel_all()
                self.close()  # mevcut pozisyonu kapat (piyasa)
                # Kapanış emri bir sonraki barda tamamlanabilir; yine de yeni giriş açabiliriz.
                # İstersen burada "return" deyip kapanıştan sonra giriş açtırırız.
                # return

        # Short izinli değilse ve sinyal short ise çık
        if (signal < 0) and (not self.p.allow_short):
            return

        # Giriş/SL/TP hesapları
        atr = float(self.atr[0])
        if atr <= 0:
            return

        entry_ref = self._entry_ref_price()

        if signal > 0:
            # LONG
            stop_price = entry_ref - atr * self.p.sl_atr_mult
            take_price = entry_ref + (entry_ref - stop_price) * self.p.tp_rr
            size = self._risk_size(entry_ref, stop_price)
            if size <= 0:
                return

            self._cancel_all()
            orders = self.buy_bracket(
                size=size,
                exectype=bt.Order.Market,
                stopprice=stop_price,
                limitprice=take_price
            )
            self.brackets.extend(orders)

        else:
            # SHORT
            stop_price = entry_ref + atr * self.p.sl_atr_mult
            take_price = entry_ref - (stop_price - entry_ref) * self.p.tp_rr
            size = self._risk_size(entry_ref, stop_price)
            if size <= 0:
                return

            self._cancel_all()
            orders = self.sell_bracket(
                size=size,
                exectype=bt.Order.Market,
                stopprice=stop_price,
                limitprice=take_price
            )
            self.brackets.extend(orders)

    def notify_order(self, order):
        # Tamamlanan/iptal edilen emirleri brackets listesinden temizle
        if order.status in [order.Completed, order.Canceled, order.Rejected, order.Margin]:
            if order in self.brackets:
                self.brackets.remove(order)

    def notify_trade(self, trade):
        # İşlem kapanınca emirleri temizle (güvenlik)
        if trade.isclosed:
            self._cancel_all()
