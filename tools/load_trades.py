
import argparse
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import psycopg2

RECORD_DTYPE = np.dtype([
    ("msg_type", "<u1"),
    ("timestamp_ns", "<u8"),
    ("symbol_id", "<u4"),
    ("price", "<i8"),
    ("size", "<u4"),
    ("trade_id", "<u8"),
], align=False)

assert RECORD_DTYPE.itemsize == 33, f"dtype size drifted: {RECORD_DTYPE.itemsize} != 33"

PRICE_SCALE = 1_000_000
QTY_SCALE = 1_000_000
SYMBOL_MAP = {1: "BTCUSDT"}

CHUNK_RECORDS = 10_000_000  # ~330MB per chunk (33 bytes/record)

DEFAULT_FILES = [
    "tools/monthly_bins/BTCUSDT-trades-2025-01.bin",
    "tools/monthly_bins/BTCUSDT-trades-2025-02.bin",
    "tools/monthly_bins/BTCUSDT-trades-2025-03.bin",
    "tools/monthly_bins/BTCUSDT-trades-2025-04.bin",
    "tools/monthly_bins/BTCUSDT-trades-2025-05.bin",
    "tools/monthly_bins/BTCUSDT-trades-2025-06.bin",
]


def symbol_column(symbol_ids: np.ndarray) -> np.ndarray:
    uniq = np.unique(symbol_ids)
    if len(uniq) == 1:
        name = SYMBOL_MAP.get(int(uniq[0]), f"UNKNOWN_{int(uniq[0])}")
        return np.full(symbol_ids.shape, name, dtype=object)
    # rare mixed-symbol chunk: fall back to a per-row map
    return pd.Series(symbol_ids).map(lambda s: SYMBOL_MAP.get(s, f"UNKNOWN_{s}")).to_numpy()


def load_file(conn, path: str) -> int:
    total = 0
    file_size = os.path.getsize(path)
    read_bytes = 0
    start = time.time()

    with open(path, "rb") as f:
        while True:
            chunk = np.fromfile(f, dtype=RECORD_DTYPE, count=CHUNK_RECORDS)
            n = chunk.shape[0]
            if n == 0:
                break

            df = pd.DataFrame({
                "time": pd.to_datetime(chunk["timestamp_ns"], unit="ns", utc=True),
                "symbol": symbol_column(chunk["symbol_id"]),
                "side": None,
                "price": chunk["price"] / PRICE_SCALE,
                "qty": chunk["size"] / QTY_SCALE,
                "pnl": None,
                "strategy": None,
            })

            buf = io.StringIO()
            df.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N",
                      date_format="%Y-%m-%d %H:%M:%S.%f%z")
            buf.seek(0)

            with conn.cursor() as cur:
                cur.copy_expert(
                    "COPY trades (time, symbol, side, price, qty, pnl, strategy) "
                    "FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', NULL '\\N')",
                    buf,
                )
            conn.commit()

            total += n
            read_bytes += n * RECORD_DTYPE.itemsize
            elapsed = time.time() - start
            rate = total / elapsed if elapsed > 0 else 0
            pct = min(100.0, 100.0 * read_bytes / file_size)
            print(f"  {os.path.basename(path)}: {total:,} rows ({pct:.1f}% of file, "
                  f"{rate:,.0f} rows/sec)")

    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("PGHOST", "localhost"))
    ap.add_argument("--port", default=os.environ.get("PGPORT", "5432"))
    ap.add_argument("--dbname", default=os.environ.get("PGDATABASE", "quant"))
    ap.add_argument("--user", default=os.environ.get("PGUSER", "quant"))
    ap.add_argument("--password", default=os.environ.get("PGPASSWORD", "quant_dev_password"))
    ap.add_argument("--files", nargs="+", default=DEFAULT_FILES)
    ap.add_argument("--truncate", action="store_true",
                     help="Truncate the trades table before loading (recommended for a clean, non-duplicated reload)")
    args = ap.parse_args()

    for path in args.files:
        if not os.path.exists(path):
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            sys.exit(1)

    conn = psycopg2.connect(
        host=args.host, port=args.port, dbname=args.dbname,
        user=args.user, password=args.password,
    )

    try:
        if args.truncate:
            print("Truncating trades table...")
            with conn.cursor() as cur:
                cur.execute("TRUNCATE trades;")
            conn.commit()

        grand_total = 0
        overall_start = time.time()
        for path in args.files:
            print(f"\nLoading {path} ...")
            grand_total += load_file(conn, path)

        elapsed = time.time() - overall_start
        print(f"\nDone. Loaded {grand_total:,} trades in {elapsed:.1f}s "
              f"({grand_total/elapsed:,.0f} rows/sec).")

        with conn.cursor() as cur:
            cur.execute("SELECT MIN(time), MAX(time), COUNT(*) FROM trades;")
            row = cur.fetchone()
            print(f"trades table now spans: {row[0]} -> {row[1]} ({row[2]:,} rows)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()