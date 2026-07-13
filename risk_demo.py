"""
risk_demo.py

End-to-end: decode REAL market data (C++ decoder + pybind11) -> extract
the latest real trade price -> run test orders through the risk engine
against that REAL price, not a hardcoded constant.

Run from the repo root: python3 risk_demo.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from risk.order import Order, Side
from risk.price_collar import PriceCollarRule
from risk.engine import RiskEngine
from risk.real_price_feed import get_latest_price

CONFIG = {"BTCUSDT": {"price_collar_percent": 2.0}}
DATA_FILE = "tools/real_market_data.bin"  # produced by tools/fetch_real_data.py


def main():
    real_price = get_latest_price(DATA_FILE)
    print(f"Latest REAL trade price (decoded from live Binance data via the "
          f"C++/pybind11 pipeline): ${real_price:,.2f}\n")

    engine = RiskEngine([PriceCollarRule(CONFIG)])

    test_orders = [
        Order("BTCUSDT", Side.BUY,  real_price,        1),  # exactly at market
        Order("BTCUSDT", Side.BUY,  real_price * 1.01, 1),  # +1%, within 2% collar
        Order("BTCUSDT", Side.BUY,  real_price * 1.05, 1),  # +5%, outside collar
        Order("BTCUSDT", Side.SELL, real_price * 0.90, 1),  # -10%, outside collar
    ]

    for order in test_orders:
        decision = engine.evaluate(order, current_price=real_price)
        status = "ACCEPT" if decision.accepted else "REJECT"
        print(f"{status:7s} {order.side.value:4s} {order.quantity} @ ${order.price:,.2f}  -- {decision.reason}")


if __name__ == "__main__":
    main()