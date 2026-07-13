"""
extract_trades_slice.py

Extracts the last N trade records from a binary trades file via a raw
byte copy -- no decoding, no pandas, no Python objects per row. This is
what makes it safe on any file size: it never holds more than one
33-byte record's worth of understanding in memory, it just copies bytes.

Usage: python3 extract_trades_slice.py <input.bin> <output.bin> <num_records>
"""
import sys

RECORD_SIZE = 33  # TradeMsg, see include/protocol.hpp


def extract_last_n(input_path: str, output_path: str, num_records: int):
    import os
    file_size = os.path.getsize(input_path)
    if file_size % RECORD_SIZE != 0:
        raise ValueError(
            f"{input_path} size ({file_size} bytes) is not a multiple of "
            f"{RECORD_SIZE} -- this doesn't look like a pure-trades file "
            f"(e.g. it might contain Quote messages too)."
        )
    total_records = file_size // RECORD_SIZE
    n = min(num_records, total_records)
    start_byte = (total_records - n) * RECORD_SIZE

    with open(input_path, "rb") as f_in, open(output_path, "wb") as f_out:
        f_in.seek(start_byte)
        remaining = n * RECORD_SIZE
        chunk_size = 4 * 1024 * 1024  # 4MB chunks, bounded memory regardless of n
        while remaining > 0:
            chunk = f_in.read(min(chunk_size, remaining))
            f_out.write(chunk)
            remaining -= len(chunk)

    print(f"Extracted last {n:,} of {total_records:,} records "
          f"({n * RECORD_SIZE / 1e6:.1f} MB) to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: python3 extract_trades_slice.py <input.bin> <output.bin> <num_records>")
        sys.exit(1)
    extract_last_n(sys.argv[1], sys.argv[2], int(sys.argv[3]))
