# market_decoder.py
#
# Thin Python wrapper around the market_decoder_native C++ extension.
# The C++ side hands back plain row-dicts; this module's only job is to
# turn those into pandas DataFrames, which is exactly the shape a
# research/backtesting notebook wants to consume.
#
# Usage:
#   from market_decoder import decode_to_dataframes
#   dfs = decode_to_dataframes("market_data.bin")
#   dfs["quotes"], dfs["trades"], dfs["order_acks"]  # each a DataFrame
#
from typing import Dict

import pandas as pd

import market_decoder_native as _native


def decode_to_dataframes(path: str) -> Dict[str, pd.DataFrame]:
    """Decode a binary market data file into a dict of pandas DataFrames,
    one per message type ("quotes", "trades", "order_acks").

    Prices are fixed-point integers scaled by 1e6 on the wire (see
    protocol.hpp); this function does NOT rescale them, so callers doing
    price math should divide by 1_000_000 explicitly, or use
    `denormalize_prices=True` in a future version if that's the
    common case for your workflow.
    """
    raw = _native.decode(path)
    return {
        "quotes": pd.DataFrame(raw["quotes"]),
        "trades": pd.DataFrame(raw["trades"]),
        "order_acks": pd.DataFrame(raw["order_acks"]),
    }
