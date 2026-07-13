"""
microstructure.py

Real microstructure features from real trade/quote data.

DESIGN CONSTRAINT: every function uses vectorized pandas/numpy, NEVER a
Python for-loop over trades -- that row-by-row pattern is exactly what
OOM-killed the backtest earlier in this project.

METHODOLOGY NOTE ON TRADE DIRECTION: real OFI needs to know if a trade
was buyer- or seller-initiated. Binance's raw data has this
(is_buyer_maker), but our binary format doesn't store it, and
re-converting 6 months of data to add it is expensive. Trade direction
here is inferred via the TICK RULE (price up = buy-initiated, price down
= sell-initiated) -- a real, established technique (simplified Lee-Ready)
used specifically when explicit side data isn't available. Stated proxy,
not a claim of real side data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_vwap(prices: np.ndarray, quantities: np.ndarray, window: int) -> pd.Series:
    prices = pd.Series(prices)
    quantities = pd.Series(quantities)
    notional = prices * quantities
    rolling_notional = notional.rolling(window, min_periods=1).sum()
    rolling_qty = quantities.rolling(window, min_periods=1).sum()
    return rolling_notional / rolling_qty


def compute_realized_volatility(prices: np.ndarray, window: int) -> pd.Series:
    """Rolling std dev of log returns between consecutive trades. Per-
    tick volatility, NOT annualized or daily-scaled."""
    prices = pd.Series(prices)
    log_returns = np.log(prices / prices.shift(1))
    return log_returns.rolling(window, min_periods=2).std()


def compute_trade_intensity(timestamps_ns: np.ndarray, window: int) -> pd.Series:
    """Trades per second, based on real elapsed time over the last
    `window` trades (a fixed trade-COUNT window, variable time span)."""
    ts = pd.Series(timestamps_ns)
    ts_window_start = ts.shift(window - 1)
    elapsed_ns = ts - ts_window_start
    elapsed_s = elapsed_ns / 1e9
    count_in_window = pd.Series(np.arange(1, len(ts) + 1)).clip(upper=window)
    return count_in_window / elapsed_s.where(elapsed_s > 0, np.nan)


def classify_trade_side_tick_rule(prices: np.ndarray) -> np.ndarray:
    """+1 buy-initiated, -1 sell-initiated, 0 unchanged/first trade."""
    prices = np.asarray(prices, dtype=np.float64)
    diffs = np.diff(prices, prepend=prices[0])
    return np.sign(diffs).astype(np.int8)


def compute_trade_imbalance(prices: np.ndarray, quantities: np.ndarray, window: int) -> pd.Series:
    """Rolling (buy_vol - sell_vol) / (buy_vol + sell_vol), range [-1, 1],
    using tick-rule-classified sides."""
    sides = classify_trade_side_tick_rule(prices)
    quantities = np.asarray(quantities, dtype=np.float64)
    signed_qty = pd.Series(sides * quantities)
    buy_vol = signed_qty.clip(lower=0).rolling(window, min_periods=1).sum()
    sell_vol = (-signed_qty.clip(upper=0)).rolling(window, min_periods=1).sum()
    total = buy_vol + sell_vol
    return (buy_vol - sell_vol) / total.where(total > 0, np.nan)


def compute_microprice(bid_price: float, ask_price: float, bid_size: float, ask_size: float) -> float:
    """Size-weighted mid, weighted TOWARD the thinner side (more likely
    consumed next). Needs real bid/ask + size data, not derivable from
    trades alone."""
    total_size = bid_size + ask_size
    if total_size <= 0:
        raise ValueError("bid_size + ask_size must be positive")
    return (bid_price * ask_size + ask_price * bid_size) / total_size


def compute_queue_imbalance(bid_size: float, ask_size: float) -> float:
    total = bid_size + ask_size
    if total <= 0:
        raise ValueError("bid_size + ask_size must be positive")
    return (bid_size - ask_size) / total
