"""
Loads existing analytics/backtest/latency CSV outputs into the TimescaleDB
tables defined in init-db/01_schema.sql.

ASSUMPTION (flag this back to me): I don't have your real CSV column names yet,
so each *_MAPPING dict below is my best guess based on the component descriptions
you gave (decoder latency percentiles, Avellaneda-Stoikov market maker, tick
backtester, risk engine). Send me one sample row from each of your real CSVs
(market_data/, latency/, backtest, risk) and I'll correct these mappings exactly.

Usage:
    pip install pandas sqlalchemy psycopg2-binary
    python load_data.py --csv-dir /mnt/c/Projects/market-decoder-optiver/data
"""

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

DB_URL = "postgresql+psycopg2://quant:quant_dev_password@localhost:5432/quant"

# --- column name guesses: edit these to match your real CSVs -------------
MARKET_BARS_MAPPING = {
    "timestamp": "time", "date": "time",
    "symbol": "symbol",
    "open": "open", "high": "high", "low": "low", "close": "close",
    "volume": "volume", "vwap": "vwap",
}

TRADES_MAPPING = {
    "timestamp": "time", "date": "time",
    "symbol": "symbol", "side": "side",
    "price": "price", "qty": "qty", "quantity": "qty",
    "pnl": "pnl", "strategy": "strategy",
}

LATENCY_MAPPING = {
    "timestamp": "time", "date": "time",
    "decoder": "decoder_type", "decoder_type": "decoder_type",
    "latency_ns": "latency_ns", "latency": "latency_ns",
    "cpu_pct": "cpu_pct",
    "cache_misses": "cache_misses",
    "branch_mispred": "branch_mispred",
    "context_switches": "context_switches",
}

RISK_EVENTS_MAPPING = {
    "timestamp": "time", "date": "time",
    "event_type": "event_type", "type": "event_type",
    "symbol": "symbol", "severity": "severity", "details": "details",
}

BACKTEST_EQUITY_MAPPING = {
    "timestamp": "time", "date": "time",
    "strategy": "strategy", "equity": "equity",
    "drawdown": "drawdown", "rolling_sharpe": "rolling_sharpe",
}

MM_QUOTES_MAPPING = {
    "timestamp": "time", "date": "time",
    "symbol": "symbol",
    "reservation_price": "reservation_price",
    "optimal_spread": "optimal_spread",
    "bid": "bid", "ask": "ask",
    "inventory": "inventory", "fill_rate": "fill_rate",
}

TABLE_CONFIG = [
    # (glob pattern to find your CSVs, target table, column mapping)
    ("**/*bars*.csv",      "market_bars",     MARKET_BARS_MAPPING),
    ("**/*ohlcv*.csv",     "market_bars",     MARKET_BARS_MAPPING),
    ("**/*trade*.csv",     "trades",          TRADES_MAPPING),
    ("**/*latency*.csv",   "latency_samples", LATENCY_MAPPING),
    ("**/*risk*.csv",      "risk_events",     RISK_EVENTS_MAPPING),
    ("**/*equity*.csv",    "backtest_equity", BACKTEST_EQUITY_MAPPING),
    ("**/*backtest*.csv",  "backtest_equity", BACKTEST_EQUITY_MAPPING),
    ("**/*quote*.csv",     "mm_quotes",       MM_QUOTES_MAPPING),
]


def load_csv(path: Path, table: str, mapping: dict, engine):
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {c: mapping[c] for c in df.columns if c in mapping}
    df = df.rename(columns=rename)

    keep = [c for c in mapping.values() if c in df.columns]
    if "time" not in keep:
        print(f"  skip {path.name}: no recognizable time column, columns were {list(df.columns)}")
        return
    df = df[keep]
    df["time"] = pd.to_datetime(df["time"], utc=True)

    df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=1000)
    print(f"  loaded {len(df):>6} rows -> {table}  (from {path.name})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", required=True, help="Root directory to scan for CSVs")
    args = ap.parse_args()

    root = Path(args.csv_dir)
    engine = create_engine(DB_URL)

    seen = set()
    for pattern, table, mapping in TABLE_CONFIG:
        for path in root.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            print(f"[{table}] {path}")
            try:
                load_csv(path, table, mapping, engine)
            except Exception as e:
                print(f"  ERROR loading {path}: {e}")

    if not seen:
        print(f"No matching CSVs found under {root}. "
              f"Check the glob patterns in TABLE_CONFIG match your actual filenames.")


if __name__ == "__main__":
    main()
