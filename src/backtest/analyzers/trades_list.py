from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any
import backtrader as bt


class TradesList(bt.Analyzer):
    """Analyzer to capture individual trade details including MAE/MFE."""

    def __init__(self):
        super().__init__()
        self.trades: List[Dict[str, Any]] = []
        self.open_trades: Dict[Any, Dict[str, Any]] = {}

    def notify_trade(self, trade):
        """Called when a trade is opened or closed."""
        if trade.isclosed:
            # Trade is closed, record it
            # Use trade.ref as key since trade object ID changes between open/close
            trade_data = self.open_trades.pop(trade.ref, None)

            # Get exit timestamp and price
            # notify_trade is called on the execution bar, exit price = open[0]
            exit_dt = self.strategy.datetime.datetime(0)
            # Force to UTC regardless of existing timezone info to match candle timestamps
            if exit_dt.tzinfo is not None:
                exit_ts = exit_dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
            else:
                exit_ts = exit_dt.replace(tzinfo=timezone.utc)
            exit_price = float(self.strategy.data.open[0])  # Execution happens at open

            if trade_data is None:
                # Fallback: create trade data if not found in open_trades
                # This shouldn't happen with trade.ref as key, but keep as safety
                print(f"[TradesList] Warning: Trade ref={trade.ref} not found in open_trades", flush=True)
                # Calculate size from trade value and exit price
                size = abs(trade.value / exit_price) if exit_price else 1.0
                # Estimate entry price from PnL (rough approximation)
                est_entry_price = exit_price - (trade.pnl / size) if size and trade.long else exit_price + (trade.pnl / size) if size else exit_price
                trade_data = {
                    "entry_ts": exit_ts,  # Use exit timestamp as fallback
                    "entry_price": est_entry_price,
                    "size": size,
                    "max_price": max(est_entry_price, exit_price),
                    "min_price": min(est_entry_price, exit_price),
                    "is_long": trade.long,  # Store from trade object
                }

            # Calculate MAE and MFE (in total dollar amount, not just price difference)
            entry_price = trade_data["entry_price"]
            max_price = trade_data["max_price"]
            min_price = trade_data["min_price"]
            size = abs(trade_data["size"])

            # Use trade.long to determine position type
            is_long = trade_data.get("is_long", trade.long)
            if is_long:  # LONG position
                mae = (entry_price - min_price) * size  # Total $ loss at worst point
                mfe = (max_price - entry_price) * size  # Total $ gain at best point
            else:  # SHORT position
                mae = (max_price - entry_price) * size
                mfe = (entry_price - min_price) * size

            entry_ts_obj = trade_data.get("entry_ts")
            entry_ts_str = entry_ts_obj.isoformat() if hasattr(entry_ts_obj, 'isoformat') else None
            exit_ts_str = exit_ts.isoformat() if hasattr(exit_ts, 'isoformat') else None

            # Skip trades with missing timestamps
            if not entry_ts_str or not exit_ts_str:
                print(f"[TradesList] Skipping trade with missing timestamp: entry={entry_ts_str}, exit={exit_ts_str}", flush=True)
                return

            # Determine side from trade.long attribute
            side = "LONG" if is_long else "SHORT"
            print(f"[TradesList] Trade closed: ref={trade.ref}, is_long={is_long}, side={side}, size={trade_data['size']:.6f}, pnl={trade.pnl:.2f}", flush=True)

            self.trades.append({
                "entry_ts": entry_ts_str,
                "exit_ts": exit_ts_str,
                "side": side,
                "entry_price": float(entry_price),
                "exit_price": exit_price,  # Use current bar close price, not trade.price
                "size": abs(float(trade_data["size"])),
                "pnl": float(trade.pnl),
                "pnl_pct": float((trade.pnl / abs(trade.value)) * 100) if trade.value != 0 else 0.0,
                "mae": float(mae) if mae else None,
                "mfe": float(mfe) if mfe else None,
                "commission": float(trade.commission) if trade.commission else 0.0,
            })

        else:
            # Trade is opened, track it
            entry_dt = self.strategy.datetime.datetime(0)
            # Force to UTC regardless of existing timezone info to match candle timestamps
            if entry_dt.tzinfo is not None:
                entry_ts = entry_dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
            else:
                entry_ts = entry_dt.replace(tzinfo=timezone.utc)

            print(f"[TradesList] Trade opened: ref={trade.ref}, size={trade.size}, long={trade.long}, price={trade.price}", flush=True)
            # Use trade.ref as key instead of id(trade)
            self.open_trades[trade.ref] = {
                "entry_ts": entry_ts,
                "entry_price": trade.price,
                "size": trade.size,
                "max_price": trade.price,
                "min_price": trade.price,
                "is_long": trade.long,  # Store position type
            }

    def next(self):
        """Update max/min prices for open trades."""
        current_price = self.strategy.data.close[0]
        for trade_data in self.open_trades.values():
            trade_data["max_price"] = max(trade_data["max_price"], current_price)
            trade_data["min_price"] = min(trade_data["min_price"], current_price)

    def stop(self):
        """Called when backtest ends. Close any remaining open trades."""
        if not self.open_trades:
            return

        print(f"[TradesList] Backtest ended with {len(self.open_trades)} open trades, closing them", flush=True)

        # Get current (last) bar data
        exit_dt = self.strategy.datetime.datetime(0)
        # Force to UTC regardless of existing timezone info to match candle timestamps
        if exit_dt.tzinfo is not None:
            exit_ts = exit_dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        else:
            exit_ts = exit_dt.replace(tzinfo=timezone.utc)
        current_price = float(self.strategy.data.close[0])

        for trade_ref, trade_data in list(self.open_trades.items()):
            entry_price = trade_data["entry_price"]
            max_price = trade_data["max_price"]
            min_price = trade_data["min_price"]
            size = trade_data["size"]
            is_long = trade_data.get("is_long", True)

            # Calculate PnL and MAE/MFE for the open position
            if is_long:
                pnl = (current_price - entry_price) * size
                mae = (entry_price - min_price) * size  # Total $ amount
                mfe = (max_price - entry_price) * size  # Total $ amount
            else:
                pnl = (entry_price - current_price) * size
                mae = (max_price - entry_price) * size
                mfe = (entry_price - min_price) * size

            side = "LONG" if is_long else "SHORT"
            entry_ts_obj = trade_data.get("entry_ts")
            entry_ts_str = entry_ts_obj.isoformat() if hasattr(entry_ts_obj, 'isoformat') else None
            exit_ts_str = exit_ts.isoformat() if hasattr(exit_ts, 'isoformat') else None

            if not entry_ts_str or not exit_ts_str:
                print(f"[TradesList] Skipping open trade with missing timestamp", flush=True)
                continue

            print(f"[TradesList] Closing open trade: ref={trade_ref}, side={side}, entry={entry_price:.2f}, exit={current_price:.2f}, pnl={pnl:.2f}", flush=True)

            self.trades.append({
                "entry_ts": entry_ts_str,
                "exit_ts": exit_ts_str,
                "side": side,
                "entry_price": float(entry_price),
                "exit_price": float(current_price),
                "size": abs(float(size)),
                "pnl": float(pnl),
                "pnl_pct": float((pnl / abs(entry_price * size)) * 100) if (entry_price * size) != 0 else 0.0,
                "mae": float(mae) if mae else None,
                "mfe": float(mfe) if mfe else None,
                "commission": 0.0,  # No commission data for open trades
            })

        self.open_trades.clear()

    def get_analysis(self):
        """Return the list of trades."""
        return {"trades": self.trades}
