"""
market_maker.py

MarketMaker: a simple market-making pricing model. Given a fair value
and current inventory, generates a two-sided quote.

1. FIXED SPREAD: we quote fair_value +/- half_spread -- our compensation
   for providing liquidity.
2. INVENTORY SKEW: if long, shift both quotes down (more eager to sell,
   less eager to buy more). If short, shift both up. Standard mechanic
   for managing inventory risk without predicting direction.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float


class MarketMaker:
    def __init__(self, half_spread: float, skew_per_unit_inventory: float, quote_size: float):
        self.half_spread = half_spread
        self.skew_per_unit_inventory = skew_per_unit_inventory
        self.quote_size = quote_size

    def generate_quote(self, fair_value: float, current_inventory: float) -> Quote:
        skew = current_inventory * self.skew_per_unit_inventory
        bid = fair_value - self.half_spread - skew
        ask = fair_value + self.half_spread - skew
        return Quote(bid_price=bid, ask_price=ask,
                     bid_size=self.quote_size, ask_size=self.quote_size)