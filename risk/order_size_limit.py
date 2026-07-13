"""
order_size_limit.py

OrderSizeLimitRule: rejects any single order whose quantity exceeds a
configured maximum for that symbol. Simpler than the price collar --
pure config lookup, no market data needed -- but catches a different
class of fat-finger error: an extra digit on QUANTITY instead of price
(e.g. accidentally submitting 500 BTC instead of 5).
"""
from __future__ import annotations

from .order import Order
from .price_collar import RuleResult


class OrderSizeLimitRule:
    def __init__(self, config: dict[str, dict[str, float]]):
        self.config = config

    def _max_size_for(self, symbol: str) -> float:
        symbol_config = self.config.get(symbol)
        if symbol_config is None:
            raise KeyError(
                f"no risk config found for symbol '{symbol}' -- refusing to "
                f"guess a default order size limit; add it to config.json"
            )
        return symbol_config["max_order_size"]

    def check(self, order: Order, current_price: float) -> RuleResult:
        max_size = self._max_size_for(order.symbol)
        details = {"order_quantity": order.quantity, "max_order_size": max_size}
        if order.quantity <= max_size:
            return RuleResult(True, "within order size limit", details)
        return RuleResult(
            False,
            f"order quantity {order.quantity} exceeds max order size {max_size}",
            details,
        )