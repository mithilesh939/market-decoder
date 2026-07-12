from __future__ import annotations

from dataclasses import dataclass
from enum import Enum



'''@dataclass
class Order:
    symbol: str
    side: str        
    price: float
    quantity: float


class Order:

    def __init__(self, symbol, side, price, quantity):
        self.symbol = symbol
        self.side = side
        self.price = price
        self.quantity = quantity


order = Order(
    symbol="BTCUSDT",
    side="BUY",
    price=64250,
    quantity=2
    )

print(order.symbol) '''





class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Order:
    symbol: str
    side: Side
    price: float
    quantity: float

    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"order price must be positive, got {self.price}")
        if self.quantity <= 0:
            raise ValueError(f"order quantity must be positive, got {self.quantity}")