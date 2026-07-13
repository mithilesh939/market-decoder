#!/usr/bin/env bash
# build.sh — builds the market_decoder_native pybind11 extension.
#
# Requires: g++ (C++17), python3, pybind11 (`pip install pybind11`).
set -euo pipefail
cd "$(dirname "$0")"

PYBIND_INCLUDES=$(python3 -m pybind11 --includes)
EXT_SUFFIX=$(python3-config --extension-suffix)

g++ -O3 -Wall -Wextra -shared -std=c++17 -fPIC \
    $PYBIND_INCLUDES \
    bindings.cpp \
    -o "market_decoder_native${EXT_SUFFIX}"

echo "Built market_decoder_native${EXT_SUFFIX}"
