#pragma once
// ---------------------------------------------------------------------------
// protocol.hpp
//
// Binary wire protocol for synthetic exchange market data.
//
// Design goal (mirrors Optiver's real approach): every message is a
// fixed-size, tightly packed struct with a known byte layout. That means
// "decoding" a message from a raw buffer is nothing more than a
// reinterpret_cast<const MsgType*>(ptr) -- no field-by-field parsing,
// no heap allocation, no copying.
//
// Wire format per record:
//   [1 byte  MsgType]  [N bytes payload, N depends on MsgType]
//
// All multi-byte fields are fixed-width integers in native (little-endian
// on x86/ARM) byte order. #pragma pack(push, 1) removes compiler struct
// padding so sizeof(Struct) == the exact wire size.
// ---------------------------------------------------------------------------

#include <cstdint>
#include <cstddef>

namespace md {

enum class MsgType : uint8_t {
    Quote    = 1,
    Trade    = 2,
    OrderAck = 3,
};

#pragma pack(push, 1)

// A top-of-book quote update.
struct QuoteMsg {
    MsgType  type;          // = MsgType::Quote
    uint64_t timestamp_ns;  // exchange timestamp, nanoseconds since epoch
    uint32_t symbol_id;     // interned symbol id (see SymbolTable)
    int64_t  bid_price;     // fixed-point price, scaled by 1e6
    int64_t  ask_price;     // fixed-point price, scaled by 1e6
    uint32_t bid_size;
    uint32_t ask_size;
};

// A trade print.
struct TradeMsg {
    MsgType  type;          // = MsgType::Trade
    uint64_t timestamp_ns;
    uint32_t symbol_id;
    int64_t  price;         // fixed-point, scaled by 1e6
    uint32_t size;
    uint64_t trade_id;
};

// Acknowledgement of an order action (new/cancel/replace).
struct OrderAckMsg {
    MsgType  type;          // = MsgType::OrderAck
    uint64_t timestamp_ns;
    uint64_t order_id;
    uint32_t symbol_id;
    int64_t  price;
    uint32_t size;
    uint8_t  side;          // 0 = buy, 1 = sell
    uint8_t  status;        // 0 = new, 1 = filled, 2 = cancelled, 3 = rejected
};

#pragma pack(pop)

static_assert(sizeof(QuoteMsg)    == 37, "QuoteMsg wire size changed");
static_assert(sizeof(TradeMsg)    == 33, "TradeMsg wire size changed");
static_assert(sizeof(OrderAckMsg) == 35, "OrderAckMsg wire size changed");

// Returns the wire size (bytes) of a message given its type tag.
// Used by the decoder to know how far to advance the read cursor.
inline size_t wire_size(MsgType t) {
    switch (t) {
        case MsgType::Quote:    return sizeof(QuoteMsg);
        case MsgType::Trade:    return sizeof(TradeMsg);
        case MsgType::OrderAck: return sizeof(OrderAckMsg);
    }
    return 0; // unknown type -- caller should treat as corrupt stream
}

} // namespace md
