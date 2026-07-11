// bindings.cpp
//
// pybind11 module exposing MmapDecoder to Python. Mirrors the second half
// of Optiver's real Chicago intern project: "Support to a Python C
// extension that reads data from these files and presents them as
// Pandas dataframes."
//
// This module does the minimum on the C++ side -- decode records and hand
// rows back as plain Python dicts -- and leaves DataFrame construction to
// the thin Python wrapper (market_decoder.py). That keeps the C++ surface
// small and testable, and keeps pandas as a Python-side-only dependency.
//
#include "../include/decoder.hpp"
#include "../include/protocol.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace md;

namespace {

// Visitor that appends each decoded message as a Python dict into one of
// three Python lists (one per message type). Field values are converted to
// native Python types (int) so pandas can infer dtypes without help.
struct PyCollectVisitor : MessageVisitor {
    py::list quotes;
    py::list trades;
    py::list order_acks;

    void on_quote(const QuoteMsg& m) override {
        py::dict row;
        row["timestamp_ns"] = m.timestamp_ns;
        row["symbol_id"]    = m.symbol_id;
        row["bid_price"]    = m.bid_price;
        row["ask_price"]    = m.ask_price;
        row["bid_size"]     = m.bid_size;
        row["ask_size"]     = m.ask_size;
        quotes.append(std::move(row));
    }

    void on_trade(const TradeMsg& m) override {
        py::dict row;
        row["timestamp_ns"] = m.timestamp_ns;
        row["symbol_id"]    = m.symbol_id;
        row["price"]        = m.price;
        row["size"]         = m.size;
        row["trade_id"]     = m.trade_id;
        trades.append(std::move(row));
    }

    void on_order_ack(const OrderAckMsg& m) override {
        py::dict row;
        row["timestamp_ns"] = m.timestamp_ns;
        row["order_id"]     = m.order_id;
        row["symbol_id"]    = m.symbol_id;
        row["price"]        = m.price;
        row["size"]         = m.size;
        row["side"]         = m.side;
        row["status"]       = m.status;
        order_acks.append(std::move(row));
    }
};

} // namespace

// Decodes a binary market data file and returns a dict of row-lists:
// { "quotes": [...], "trades": [...], "order_acks": [...] }
// Each element is a plain dict of native Python types -- ready for
// pd.DataFrame(rows) with no further conversion.
py::dict decode(const std::string& path) {
    MmapDecoder decoder(path);
    PyCollectVisitor visitor;
    decoder.decode_all(visitor);

    py::dict result;
    result["quotes"]     = visitor.quotes;
    result["trades"]     = visitor.trades;
    result["order_acks"] = visitor.order_acks;
    return result;
}

PYBIND11_MODULE(market_decoder_native, m) {
    m.doc() = "No-copy binary market data decoder -- Python bindings";
    m.def("decode", &decode,
          "Decode a binary market data file into row-lists by message type",
          py::arg("path"));
}
