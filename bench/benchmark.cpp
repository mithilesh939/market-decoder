// benchmark.cpp
//
// Measures decode throughput of MmapDecoder (no-copy) vs NaiveDecoder
// (heap-allocate + memcpy per message) over the same input file.
//
// Usage: ./benchmark <market_data_file>
//
#include "../include/decoder.hpp"
#include "../include/naive_decoder.hpp"

#include <chrono>
#include <cstdio>
#include <string>

using namespace md;
using Clock = std::chrono::steady_clock;

// A visitor that does the minimum realistic amount of work: accumulate
// a checksum. This prevents the compiler from optimizing the whole decode
// away as dead code, without adding artificial overhead of its own.
struct ChecksumVisitor : MessageVisitor {
    uint64_t checksum = 0;
    void on_quote(const QuoteMsg& m) override {
        checksum ^= m.timestamp_ns ^ m.symbol_id ^ static_cast<uint64_t>(m.bid_price);
    }
    void on_trade(const TradeMsg& m) override {
        checksum ^= m.timestamp_ns ^ m.symbol_id ^ static_cast<uint64_t>(m.price);
    }
    void on_order_ack(const OrderAckMsg& m) override {
        checksum ^= m.timestamp_ns ^ m.order_id ^ static_cast<uint64_t>(m.price);
    }
};

template <typename DecoderT>
void run_bench(const char* label, const std::string& path, int repeats) {
    double best_ns_per_msg = 1e18;
    size_t last_count = 0;
    uint64_t last_checksum = 0;

    for (int r = 0; r < repeats; ++r) {
        DecoderT decoder(path);
        ChecksumVisitor visitor;

        auto t0 = Clock::now();
        size_t count = decoder.decode_all(visitor);
        auto t1 = Clock::now();

        double ns = std::chrono::duration<double, std::nano>(t1 - t0).count();
        double ns_per_msg = ns / static_cast<double>(count);
        best_ns_per_msg = std::min(best_ns_per_msg, ns_per_msg);
        last_count = count;
        last_checksum = visitor.checksum;
    }

    printf("%-14s messages=%-9zu best=%.2f ns/msg  (~%.1fM msgs/sec)  checksum=%llu\n",
           label, last_count, best_ns_per_msg, 1000.0 / best_ns_per_msg,
           static_cast<unsigned long long>(last_checksum));
}

int main(int argc, char** argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <market_data_file>\n", argv[0]);
        return 1;
    }
    std::string path = argv[1];
    const int repeats = 5; // take the best of 5 runs, standard micro-bench practice

    printf("Benchmarking decoders on %s (best of %d runs)\n\n", path.c_str(), repeats);
    run_bench<NaiveDecoder>("NaiveDecoder", path, repeats);
    run_bench<MmapDecoder>("MmapDecoder", path, repeats);
    return 0;
}
