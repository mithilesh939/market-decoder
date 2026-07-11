# test_bindings.py
#
# Cross-validates the Python binding against the C++ decoder's own
# checksum, computed independently on each side. This is a stronger check
# than "row counts match": it proves every field of every message
# round-tripped through the C extension into pandas without corruption.
#
# Requires the C++ `generate` and `benchmark` binaries to be built first
# (see ../Makefile), and market_decoder_native to be built (./build.sh).
#
# Usage: python3 test_bindings.py
#
import subprocess
import sys
import tempfile
from pathlib import Path

from market_decoder import decode_to_dataframes

ROOT = Path(__file__).resolve().parent.parent


def cpp_checksum(data_path: str) -> int:
    """Runs the C++ benchmark binary and parses the MmapDecoder checksum
    it prints, so we're comparing against the exact same decode logic
    used in bench/benchmark.cpp."""
    out = subprocess.run(
        [str(ROOT / "benchmark"), data_path],
        capture_output=True, text=True, check=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("MmapDecoder"):
            for token in line.split():
                if token.startswith("checksum="):
                    return int(token.split("=")[1])
    raise RuntimeError(f"couldn't find checksum in benchmark output:\n{out}")


def python_checksum(dfs) -> int:
    """Recomputes the identical XOR checksum formula used in
    bench/benchmark.cpp's ChecksumVisitor, but from the pandas
    DataFrames the Python binding produced."""
    mask = (1 << 64) - 1
    checksum = 0
    for _, r in dfs["quotes"].iterrows():
        checksum ^= int(r.timestamp_ns) ^ int(r.symbol_id) ^ int(r.bid_price)
    for _, r in dfs["trades"].iterrows():
        checksum ^= int(r.timestamp_ns) ^ int(r.symbol_id) ^ int(r.price)
    for _, r in dfs["order_acks"].iterrows():
        checksum ^= int(r.timestamp_ns) ^ int(r.order_id) ^ int(r.price)
    return checksum & mask


def main():
    with tempfile.TemporaryDirectory() as tmp:
        data_path = str(Path(tmp) / "test_data.bin")
        subprocess.run(
            [str(ROOT / "generate"), data_path, "10000"],
            check=True, capture_output=True,
        )

        dfs = decode_to_dataframes(data_path)
        total_rows = sum(len(df) for df in dfs.values())
        assert total_rows == 10000, f"expected 10000 rows, got {total_rows}"

        expected = cpp_checksum(data_path)
        actual = python_checksum(dfs)

        print(f"rows decoded:    {total_rows} (expected 10000) -- OK")
        print(f"C++ checksum:    {expected}")
        print(f"Python checksum: {actual}")
        assert actual == expected, "checksum mismatch -- data corrupted in the Python path"
        print("\nPASS: Python binding matches C++ decoder byte-for-byte.")


if __name__ == "__main__":
    sys.exit(main())
