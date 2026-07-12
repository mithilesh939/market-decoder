"""
backtest.py

Replays REAL historical trades (tools/real_market_data.bin) through the
MarketMaker pricing model + the full RiskEngine pipeline, tracking
inventory/PnL over time.

METHODOLOGY, stated explicitly:
- Fair value = last real trade price (standard simplification -- we only
  have real trade prints + one order-book snapshot, not continuous book
  depth over time).
- Each new trade is checked against the quote resting from the PREVIOUS
  fair value -- no lookahead bias.
- Every simulated fill goes through the REAL RiskEngine before applying.
- Full quoted size fills when crossed -- no partial fills or queue
  modeling. Real backtests model queue priority; out of scope here and
  flagged rather than silently assumed.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from python.market_decoder import decode_to_dataframes
from risk.order import Order, Side
from risk.price_collar import PriceCollarRule
from risk.order_size_limit import OrderSizeLimitRule
from risk.inventory_limit import InventoryLimitRule, InventoryTracker
from risk.kill_switch import KillSwitchRule
from risk.engine import RiskEngine
from strategy.market_maker import MarketMaker


@dataclass
class BacktestPoint:
    tick: int
    timestamp_ns: int
    trade_price: float
    fair_value: float
    inventory: float
    cash: float
    mark_to_market_pnl: float
    our_bid: float
    our_ask: float
    fill_side: str
    fill_rejected_reason: str


@dataclass
class BacktestResult:
    points: List[BacktestPoint] = field(default_factory=list)
    total_fills: int = 0
    rejected_fills: int = 0

    def final_pnl(self) -> float:
        return self.points[-1].mark_to_market_pnl if self.points else 0.0

    def final_inventory(self) -> float:
        return self.points[-1].inventory if self.points else 0.0


def run_backtest(
    bin_file_path: str, symbol: str = "BTCUSDT",
    half_spread: float = 5.0, skew_per_unit_inventory: float = 50.0,
    quote_size: float = 0.01, risk_config: Optional[dict] = None,
) -> BacktestResult:
    dfs = decode_to_dataframes(bin_file_path)
    trades = dfs["trades"].sort_values("timestamp_ns").reset_index(drop=True)
    if len(trades) < 2:
        raise ValueError("need at least 2 real trades to run a backtest")

    if risk_config is None:
        risk_config = {symbol: {"price_collar_percent": 2.0, "max_order_size": 1.0, "max_inventory": 0.5}}

    maker = MarketMaker(half_spread, skew_per_unit_inventory, quote_size)
    tracker = InventoryTracker()
    kill_switch = KillSwitchRule()
    engine = RiskEngine([kill_switch, PriceCollarRule(risk_config),
                         OrderSizeLimitRule(risk_config), InventoryLimitRule(risk_config, tracker)])

    result = BacktestResult()
    cash = 0.0
    fair_value = trades.iloc[0]["price"] / 1_000_000

    for i in range(1, len(trades)):
        row = trades.iloc[i]
        trade_price = row["price"] / 1_000_000
        timestamp_ns = int(row["timestamp_ns"])

        quote = maker.generate_quote(fair_value, tracker.position(symbol))
        fill_side, fill_rejected_reason = "", ""

        if trade_price >= quote.ask_price:
            order = Order(symbol, Side.SELL, quote.ask_price, quote.ask_size)
            decision = engine.evaluate(order, current_price=fair_value)
            if decision.accepted:
                tracker.apply_fill(order)
                cash += quote.ask_price * quote.ask_size
                fill_side = "SELL"
                result.total_fills += 1
            else:
                fill_rejected_reason = decision.reason
                result.rejected_fills += 1
        elif trade_price <= quote.bid_price:
            order = Order(symbol, Side.BUY, quote.bid_price, quote.bid_size)
            decision = engine.evaluate(order, current_price=fair_value)
            if decision.accepted:
                tracker.apply_fill(order)
                cash -= quote.bid_price * quote.bid_size
                fill_side = "BUY"
                result.total_fills += 1
            else:
                fill_rejected_reason = decision.reason
                result.rejected_fills += 1

        fair_value = trade_price
        inventory = tracker.position(symbol)
        mtm_pnl = cash + inventory * fair_value

        result.points.append(BacktestPoint(
            tick=i, timestamp_ns=timestamp_ns, trade_price=trade_price,
            fair_value=fair_value, inventory=inventory, cash=cash,
            mark_to_market_pnl=mtm_pnl, our_bid=quote.bid_price, our_ask=quote.ask_price,
            fill_side=fill_side, fill_rejected_reason=fill_rejected_reason,
        ))

    return result