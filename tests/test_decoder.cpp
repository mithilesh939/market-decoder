// test_decoder.cpp
//
// Correctness tests, no external test framework -- just asserts, so this
// project builds with nothing but g++. Run via `make test`.
//
#include "../include/decoder.hpp"
#include "../include/naive_decoder.hpp"

#include <cassert>
#include <cstdio>
#include <cstdlib>

using namespace md;

// Writes 3 hand-constructed messages (one of each type) to a temp file
// and returns the path.
static std::string write_fixture() {
    std::string path = "/tmp/md_test_fixture.bin";
    FILE* f = fopen(path.c_str(), "wb");

    QuoteMsg q{};
    q.type = MsgType::Quote;
    q.timestamp_ns = 111;
    q.symbol_id = 7;
    q.bid_price = 100'000'000;
    q.ask_price = 100'010'000;
    q.bid_size = 50;
    q.ask_size = 60;
    fwrite(&q, sizeof(q), 1, f);

    TradeMsg t{};
    t.type = MsgType::Trade;
    t.timestamp_ns = 222;
    t.symbol_id = 7;
    t.price = 100'005'000;
    t.size = 25;
    t.trade_id = 999;
    fwrite(&t, sizeof(t), 1, f);

    OrderAckMsg o{};
    o.type = MsgType::OrderAck;
    o.timestamp_ns = 333;
    o.order_id = 42;
    o.symbol_id = 7;
    o.price = 100'000'000;
    o.size = 10;
    o.side = 0;
    o.status = 1;
    fwrite(&o, sizeof(o), 1, f);

    fclose(f);
    return path;
}

struct RecordingVisitor : MessageVisitor {
    int quotes = 0, trades = 0, acks = 0;
    QuoteMsg last_quote{};
    TradeMsg last_trade{};
    OrderAckMsg last_ack{};

    void on_quote(const QuoteMsg& m) override { last_quote = m; ++quotes; }
    void on_trade(const TradeMsg& m) override { last_trade = m; ++trades; }
    void on_order_ack(const OrderAckMsg& m) override { last_ack = m; ++acks; }
};

template <typename DecoderT>
void test_decoder_roundtrip(const char* label, const std::string& path) {
    printf("running: %s ... ", label);

    DecoderT decoder(path);
    RecordingVisitor visitor;
    size_t count = decoder.decode_all(visitor);

    assert(count == 3);
    assert(visitor.quotes == 1 && visitor.trades == 1 && visitor.acks == 1);

    assert(visitor.last_quote.symbol_id == 7);
    assert(visitor.last_quote.bid_price == 100'000'000);
    assert(visitor.last_quote.ask_price == 100'010'000);

    assert(visitor.last_trade.trade_id == 999);
    assert(visitor.last_trade.price == 100'005'000);

    assert(visitor.last_ack.order_id == 42);
    assert(visitor.last_ack.status == 1);

    printf("PASS\n");
}

int main() {
    std::string path = write_fixture();

    test_decoder_roundtrip<MmapDecoder>("MmapDecoder roundtrip", path);
    test_decoder_roundtrip<NaiveDecoder>("NaiveDecoder roundtrip", path);

    printf("\nAll tests passed.\n");
    return 0;
}
