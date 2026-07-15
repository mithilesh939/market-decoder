
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from market_decoder import decode_to_dataframes
from features.microstructure import compute_vwap, compute_realized_volatility, compute_trade_intensity, compute_trade_imbalance


def main():
    if len(sys.argv) != 2:
        print("usage: python3 features/demo.py <path_to_trades.bin>")
        sys.exit(1)

    data_file = sys.argv[1]
    record_count = os.path.getsize(data_file) // 33
    if record_count > 1_000_000:
        print(f"WARNING: ~{record_count:,} records -- decode_to_dataframes() builds a "
              f"Python dict per row, the exact pattern that OOM-killed the backtest. "
              f"Use tools/extract_trades_slice.py first.")
        sys.exit(1)

    print(f"Decoding {data_file} ({record_count:,} real trades)...")
    dfs = decode_to_dataframes(data_file)
    trades = dfs["trades"].sort_values("timestamp_ns").reset_index(drop=True)

    prices = (trades["price"] / 1_000_000).to_numpy()
    qtys = (trades["size"] / 1_000_000).to_numpy()
    timestamps_ns = trades["timestamp_ns"].to_numpy()

    window = min(1000, len(prices) // 2)
    print(f"Computing features over {len(prices):,} real trades, rolling window={window}...\n")

    vwap = compute_vwap(prices, qtys, window)
    vol = compute_realized_volatility(prices, window)
    intensity = compute_trade_intensity(timestamps_ns, window)
    imbalance = compute_trade_imbalance(prices, qtys, window)

    print(f"Real price range:        {prices.min():.2f} - {prices.max():.2f}")
    print(f"Final VWAP:               {vwap.iloc[-1]:.2f}")
    print(f"Final realized vol:       {vol.iloc[-1]:.8f} (per-tick log-return std)")
    print(f"Final trade intensity:    {intensity.iloc[-1]:.2f} trades/sec")
    print(f"Final trade imbalance:    {imbalance.iloc[-1]:+.4f} "
          f"({'buy-skewed' if imbalance.iloc[-1] > 0 else 'sell-skewed'}, tick-rule proxy)")


if __name__ == "__main__":
    main()
