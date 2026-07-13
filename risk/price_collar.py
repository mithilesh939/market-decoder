
from __future__ import annotations

import json
'''class PriceCollarRule:

    def __init__(self, config_path):
        with open(config_path, "r") as f:
            self.config = json.load(f)

    def validate(self, order, current_price):

        collar = self.config[order.symbol]["price_collar_percent"]

        lower = current_price * (1 - collar / 100)
        upper = current_price * (1 + collar / 100)

        if lower <= order.price <= upper:
            return {
                "accepted": True,
                "reason": "Within Price Collar",
                "lower": lower,
                "upper": upper
            }

        return {
            "accepted": False,
            "reason": "Outside Price Collar",
            "lower": lower,
            "upper": upper
        }'''






from dataclasses import dataclass, field
from typing import Any

from .order import Order


@dataclass(frozen=True)
class RuleResult:
    accepted: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


class PriceCollarRule:
    def __init__(self, config: dict[str, dict[str, float]]):
        self.config = config

    def _collar_pct_for(self, symbol: str) -> float:
        symbol_config = self.config.get(symbol)
        if symbol_config is None:
            raise KeyError(
                f"no risk config found for symbol '{symbol}' -- refusing to "
                f"guess a default collar; add it to config.json explicitly"
            )
        return symbol_config["price_collar_percent"] / 100.0

    def check(self, order: Order, current_price: float) -> RuleResult:
        if current_price <= 0:
            raise ValueError(f"current_price must be positive, got {current_price}")

        collar_pct = self._collar_pct_for(order.symbol)
        lower = current_price * (1 - collar_pct)
        upper = current_price * (1 + collar_pct)

        details = {
            "lower": lower, "upper": upper,
            "current_price": current_price, "order_price": order.price,
            "collar_percent": collar_pct * 100,
        }

        if lower <= order.price <= upper:
            return RuleResult(True, "within price collar", details)
        return RuleResult(
            False,
            f"order price {order.price} outside allowed range "
            f"[{lower:.2f}, {upper:.2f}] ({collar_pct*100:.1f}% collar)",
            details,
        )