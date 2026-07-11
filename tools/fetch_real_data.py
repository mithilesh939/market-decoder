#!/usr/bin/env python3
"""
fetch_real_data.py

Pulls REAL market data from Binance's public REST API and converts it into
the exact binary wire format used by market-decoder (see include/protocol.hpp),
so the existing, UNMODIFIED C++ decoder and benchmark can run against it --
no code changes needed on the C++ side.

Uses only the Python standard library (urllib, struct, json) -- nothing to
pip install. Run this on a machine with normal internet access (this was
built to be run outside Claude's sandboxed environment, which cannot reach
api.binance.com).

Usage:
    python3 fetch_real_data.py [SYMBOL] [NUM_TRADES]

    SYMBOL      Trading pair, default BTCUSDT
    NUM_TRADES  How many real trades to pull, default 20000
                (paginated via Binance's fromId parameter, ~1000 per request)

Output:
    real_market_data.bin   -- binary file, same format as synthetic data,
                               ready to feed straight into ./benchmark
    real_data_summary.json -- stats used to build the comparison dashboard

HONESTY NOTE: Binance's public API does not expose real order-lifecycle
data (order acks) -- that requires an authenticated account and is specific
to YOUR orders, not the market's. This script therefore produces a file
containing real Quote and Trade messages, and ZERO OrderAck messages. That's
an accurate reflection of what's actually publicly available, not a
limitation of the decoder -- MmapDecoder handles any mix of message types,
including none of one type.
"""
import json
import struct
import sys
import time
import urllib.request

BASE_URL = "https://api.binance.com/api/v3"

# Must exactly match the #pragma pack(1) layout in include/protocol.hpp.
# '<' = little-endian, no padding -- matches pack(1) exactly.
QUOTE_FMT = "<BQIqqII"   # type, timestamp_ns, symbol_id, bid_price, ask_price, bid_size, ask_size
TRADE_FMT = "<BQIqIQ"    # type, timestamp_ns, symbol_id, price, size, trade_id
MSG_TYPE_QUOTE = 1
MSG_TYPE_TRADE = 2

assert struct.calcsize(QUOTE_FMT) == 37, "QuoteMsg format drifted from protocol.hpp"
assert struct.calcsize(TRADE_FMT) == 33, "TradeMsg format drifted from protocol.hpp"

PRICE_SCALE = 1_000_000  # fixed-point scale, matches protocol.hpp convention
QTY_SCALE = 1_000_000    # crypto quantities are fractional; scale like price


def http_get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "market-decoder-real-data-test/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_real_trades(symbol: str, target_count: int):
    """Paginates backward through real historical trades using Binance's
    aggTrades endpoint (public, no API key needed), which returns REAL
    executed trade prints -- not synthetic data."""
    trades = []
    end_time = None
    print(f"Fetching real trades for {symbol}...")

    while len(trades) < target_count:
        url = f"{BASE_URL}/aggTrades?symbol={symbol}&limit=1000"
        if end_time is not None:
            url += f"&endTime={end_time}"
        batch = http_get_json(url)
        if not batch:
            break
        trades = batch + trades  # prepend, since we're paging backward in time
        end_time = batch[0]["T"] - 1  # next page: strictly before this batch's earliest trade
        print(f"  fetched {len(trades)} / {target_count} trades so far...")
        time.sleep(0.15)  # be polite to the public API, well under rate limits

    return trades[-target_count:] if len(trades) > target_count else trades


def fetch_real_depth(symbol: str, limit: int = 100):
    """Real order book snapshot -- current live bids/asks."""
    print(f"Fetching real order book depth for {symbol}...")
    return http_get_json(f"{BASE_URL}/depth?symbol={symbol}&limit={limit}")


def encode_trades(trades, symbol_id: int) -> bytes:
    out = bytearray()
    for t in trades:
        timestamp_ns = int(t["T"]) * 1_000_000  # ms -> ns
        price = round(float(t["p"]) * PRICE_SCALE)
        size = round(float(t["q"]) * QTY_SCALE)
        trade_id = int(t["a"])  # aggregate trade id
        out += struct.pack(TRADE_FMT, MSG_TYPE_TRADE, timestamp_ns, symbol_id,
                            price, min(size, 2**32 - 1), trade_id)
    return bytes(out)


def encode_depth_as_quotes(depth, symbol_id: int) -> bytes:
    """Real bid/ask levels, paired index-by-index into QuoteMsg records.
    NOTE: Binance's depth snapshot has no per-level timestamp, only a
    lastUpdateId for the whole snapshot -- so timestamps here are
    synthetic (current fetch time, incrementing by 1us per level) even
    though the prices/sizes themselves are real. Documented here so
    nobody mistakes it for a real per-level timestamp feed."""
    out = bytearray()
    base_ts = int(time.time() * 1_000_000_000)
    bids, asks = depth["bids"], depth["asks"]
    n = min(len(bids), len(asks))
    for i in range(n):
        bid_price = round(float(bids[i][0]) * PRICE_SCALE)
        bid_size = min(round(float(bids[i][1]) * QTY_SCALE), 2**32 - 1)
        ask_price = round(float(asks[i][0]) * PRICE_SCALE)
        ask_size = min(round(float(asks[i][1]) * QTY_SCALE), 2**32 - 1)
        timestamp_ns = base_ts + i * 1000
        out += struct.pack(QUOTE_FMT, MSG_TYPE_QUOTE, timestamp_ns, symbol_id,
                            bid_price, ask_price, bid_size, ask_size)
    return bytes(out)


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    target_trades = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    symbol_id = 1  # single symbol in this run; extend to a real symbol table for multi-symbol

    trades = fetch_real_trades(symbol, target_trades)
    depth = fetch_real_depth(symbol)

    trade_bytes = encode_trades(trades, symbol_id)
    quote_bytes = encode_depth_as_quotes(depth, symbol_id)

    # Interleave: real market data doesn't arrive as "all quotes then all
    # trades" -- write quotes first (order book snapshot is a single point
    # in time) then the trade stream, which is closer to how a real feed
    # handler would see "current book, then a stream of prints."
    with open("real_market_data.bin", "wb") as f:
        f.write(quote_bytes)
        f.write(trade_bytes)

    prices = [float(t["p"]) for t in trades]
    summary = {
        "symbol": symbol,
        "source": "Binance public REST API (api.binance.com)",
        "fetched_at_unix": int(time.time()),
        "num_trades": len(trades),
        "num_quote_levels": min(len(depth["bids"]), len(depth["asks"])),
        "num_order_acks": 0,
        "note": "OrderAck count is 0 because Binance's public API does not "
                "expose real order-lifecycle data without an authenticated "
                "account -- this is a real limitation of public data, not "
                "a decoder limitation.",
        "price_min": min(prices) if prices else None,
        "price_max": max(prices) if prices else None,
        "price_mean": sum(prices) / len(prices) if prices else None,
        "file_bytes": len(quote_bytes) + len(trade_bytes),
        "file_path": "real_market_data.bin",
    }
    with open("real_data_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\nDone.")
    print(f"  Wrote {summary['file_bytes']:,} bytes to real_market_data.bin")
    print(f"  {summary['num_trades']:,} real trades, {summary['num_quote_levels']} real quote levels, 0 order acks")
    print(f"  Price range: {summary['price_min']:.2f} - {summary['price_max']:.2f} (mean {summary['price_mean']:.2f})")
    print("\nNext: run the EXISTING decoder/benchmark against this real file, unmodified:")
    print("  ./benchmark real_market_data.bin")


if __name__ == "__main__":
    main()