"""
inventory.py

Tracks multi-symbol inventory positions and enforces maximum inventory limit rules.
"""
from __future__ import annotations


class InventoryTracker:
    """Tracks current net inventory positions across symbols."""
    def __init__(self):
        self.positions: dict[str, float] = {}

    def get_position(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0)

    def apply_fill(self, order) -> None:
        current = self.get_position(order.symbol)
        qty = order.quantity if "BUY" in str(order.side).upper() else -order.quantity
        self.positions[order.symbol] = current + qty


class InventoryLimitRule:
    """Rejects orders that would cause position inventory to exceed configured limits."""
    def __init__(self, config: dict, tracker: InventoryTracker):
        self.config = config
        self.tracker = tracker
        self.name = "InventoryLimitRule"

    def evaluate(self, order, current_price: float = 0.0):
        from risk.engine import RiskDecision
        symbol_cfg = self.config.get(order.symbol, {})
        max_inv = symbol_cfg.get("max_inventory", float("inf"))
        
        current_pos = self.tracker.get_position(order.symbol)
        qty_change = order.quantity if "BUY" in str(order.side).upper() else -order.quantity
        projected_pos = abs(current_pos + qty_change)
        
        if projected_pos > max_inv:
            return RiskDecision(False, self.name, f"Projected inventory {projected_pos} exceeds limit {max_inv}")
        return RiskDecision(True, self.name)
