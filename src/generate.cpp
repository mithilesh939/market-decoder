// generate.cpp
//
// Generates a synthetic binary market data file: a mix of Quote, Trade and
// OrderAck messages, written back-to-back exactly as they'd appear in
// protocol.hpp. Usage:
//
//   ./generate <output_file> <num_messages>
//
#include "../include/protocol.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>

using namespace md;

int main(int argc, char** argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <output_file> <num_messages>\n", argv[0]);
        return 1;
    }

    std::string out_path = argv[1];
    size_t n = std::stoull(argv[2]);

    FILE* f = fopen(out_path.c_str(), "wb");
    if (!f) {
        fprintf(stderr, "failed to open %s for writing\n", out_path.c_str());
        return 1;
    }

    std::mt19937_64 rng(42); // fixed seed -> reproducible benchmark input
    std::uniform_int_distribution<int> type_dist(1, 3);
    std::uniform_int_distribution<uint32_t> symbol_dist(1, 500);
    std::uniform_int_distribution<int64_t> price_dist(1'000'000, 500'000'000); // $1 - $500
    std::uniform_int_distribution<uint32_t> size_dist(1, 10'000);
    uint64_t ts = 1'700'000'000'000'000ULL; // arbitrary starting ns timestamp
    uint64_t trade_id = 1;
    uint64_t order_id = 1;

    for (size_t i = 0; i < n; ++i) {
        ts += 100 + (i % 50); // monotonically increasing, jittered
        MsgType type = static_cast<MsgType>(type_dist(rng));

        switch (type) {
            case MsgType::Quote: {
                QuoteMsg m{};
                m.type = type;
                m.timestamp_ns = ts;
                m.symbol_id = symbol_dist(rng);
                m.bid_price = price_dist(rng);
                m.ask_price = m.bid_price + 10'000; // 1 cent spread
                m.bid_size = size_dist(rng);
                m.ask_size = size_dist(rng);
                fwrite(&m, sizeof(m), 1, f);
                break;
            }
            case MsgType::Trade: {
                TradeMsg m{};
                m.type = type;
                m.timestamp_ns = ts;
                m.symbol_id = symbol_dist(rng);
                m.price = price_dist(rng);
                m.size = size_dist(rng);
                m.trade_id = trade_id++;
                fwrite(&m, sizeof(m), 1, f);
                break;
            }
            case MsgType::OrderAck: {
                OrderAckMsg m{};
                m.type = type;
                m.timestamp_ns = ts;
                m.order_id = order_id++;
                m.symbol_id = symbol_dist(rng);
                m.price = price_dist(rng);
                m.size = size_dist(rng);
                m.side = static_cast<uint8_t>(order_id % 2);
                m.status = 0;
                fwrite(&m, sizeof(m), 1, f);
                break;
            }
        }
    }

    fclose(f);
    printf("wrote %zu messages to %s\n", n, out_path.c_str());
    return 0;
}
