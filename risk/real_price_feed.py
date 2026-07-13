"""
real_price_feed.py

Bridges the C++ decoder (via the pybind11 bindings in python/) to the
risk engine: extracts the latest REAL trade price from decoded market
data, so the risk engine evaluates orders against a genuine market price
instead of a hardcoded constant.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from python.market_decoder import decode_to_dataframes  # noqa: E402


def get_latest_price(bin_file_path: str) -> float:
    """Returns the price (real dollars, unscaled) of the most recent
    trade in a decoded binary market data file. Raises ValueError if
    there are no trades -- silently falling back to a default price
    would defeat the entire point of wiring in real data."""
    dfs = decode_to_dataframes(bin_file_path)
    trades = dfs["trades"]
    if len(trades) == 0:
        raise ValueError(f"no trades found in {bin_file_path} -- cannot get a live price")

    last_trade = trades.iloc[-1]
    return last_trade["price"] / 1_000_000  # undo the fixed-point scale