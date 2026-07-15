#pragma once

#include "protocol.hpp"

#include <cstdio>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace md {

class NaiveDecoder {
public:
    explicit NaiveDecoder(const std::string& path) {
        FILE* f = fopen(path.c_str(), "rb");
        if (!f) throw std::runtime_error("NaiveDecoder: failed to open " + path);

        fseek(f, 0, SEEK_END);
        long len = ftell(f);
        fseek(f, 0, SEEK_SET);

        buffer_.resize(static_cast<size_t>(len));
        size_t read = fread(buffer_.data(), 1, buffer_.size(), f);
        fclose(f);

        if (read != buffer_.size()) {
            throw std::runtime_error("NaiveDecoder: short read on " + path);
        }
    }

    size_t decode_all(MessageVisitor& visitor) const {
        size_t offset = 0;
        size_t count = 0;

        while (offset < buffer_.size()) {
            MsgType type = static_cast<MsgType>(buffer_[offset]);
            size_t msg_size = wire_size(type);
            if (msg_size == 0 || offset + msg_size > buffer_.size()) {
                throw std::runtime_error("NaiveDecoder: corrupt stream");
            }

            // Heap-allocate + field-by-field copy, on purpose, to
            // represent the "naive first draft" most people write.
            switch (type) {
                case MsgType::Quote: {
                    auto msg = std::make_unique<QuoteMsg>();
                    std::memcpy(msg.get(), buffer_.data() + offset, sizeof(QuoteMsg));
                    visitor.on_quote(*msg);
                    break;
                }
                case MsgType::Trade: {
                    auto msg = std::make_unique<TradeMsg>();
                    std::memcpy(msg.get(), buffer_.data() + offset, sizeof(TradeMsg));
                    visitor.on_trade(*msg);
                    break;
                }
                case MsgType::OrderAck: {
                    auto msg = std::make_unique<OrderAckMsg>();
                    std::memcpy(msg.get(), buffer_.data() + offset, sizeof(OrderAckMsg));
                    visitor.on_order_ack(*msg);
                    break;
                }
            }

            offset += msg_size;
            ++count;
        }
        return count;
    }

private:
    std::vector<uint8_t> buffer_;
};

} // namespace md
