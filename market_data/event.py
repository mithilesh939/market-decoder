"""
Core market event used throughout the trading infrastructure.
Every downstream component consumes Event objects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Side(Enum):
    BUY = 1
    SELL = -1


class Exchange(Enum):
    BINANCE = "BINANCE"
    NASDAQ = "NASDAQ"
    SIMULATOR = "SIMULATOR"


@dataclass(slots=True, frozen=True)
class Event:
    trade_id: int
    timestamp: int          # microseconds since epoch
    symbol: str
    price: float
    quantity: float
    side: Side

    exchange: Exchange

    quote_qty: float = 0.0

    best_match: bool = True

    sequence: Optional[int] = None