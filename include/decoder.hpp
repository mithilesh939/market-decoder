#pragma once

#include "protocol.hpp"

#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>

#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace md {


struct MessageVisitor {
    virtual void on_quote(const QuoteMsg&) {}
    virtual void on_trade(const TradeMsg&) {}
    virtual void on_order_ack(const OrderAckMsg&) {}
    virtual ~MessageVisitor() = default;
};

class MmapDecoder {
public:
    explicit MmapDecoder(const std::string& path) {
        fd_ = open(path.c_str(), O_RDONLY);
        if (fd_ < 0) {
            throw std::runtime_error("MmapDecoder: failed to open " + path);
        }

        struct stat st{};
        if (fstat(fd_, &st) != 0) {
            close(fd_);
            throw std::runtime_error("MmapDecoder: fstat failed for " + path);
        }
        size_ = static_cast<size_t>(st.st_size);

        if (size_ == 0) {
            data_ = nullptr;
            return;
        }

        
#ifdef MAP_POPULATE
        int mmap_flags = MAP_PRIVATE | MAP_POPULATE;
#else
        int mmap_flags = MAP_PRIVATE;
#endif
        void* mapped = mmap(nullptr, size_, PROT_READ, mmap_flags, fd_, 0);
        if (mapped == MAP_FAILED) {
            close(fd_);
            throw std::runtime_error("MmapDecoder: mmap failed for " + path);
        }
        data_ = static_cast<const uint8_t*>(mapped);

        // Advise the kernel we'll read sequentially -- enables readahead.
        madvise(mapped, size_, MADV_SEQUENTIAL);
    }

    ~MmapDecoder() {
        if (data_) munmap(const_cast<uint8_t*>(data_), size_);
        if (fd_ >= 0) close(fd_);
    }

    MmapDecoder(const MmapDecoder&) = delete;
    MmapDecoder& operator=(const MmapDecoder&) = delete;

    // Walks every record in the file, invoking the matching visitor method.
    // Returns the number of messages decoded.
    size_t decode_all(MessageVisitor& visitor) const {
        size_t offset = 0;
        size_t count = 0;

        while (offset < size_) {
            MsgType type = static_cast<MsgType>(data_[offset]);
            size_t msg_size = wire_size(type);

            if (msg_size == 0 || offset + msg_size > size_) {
                throw std::runtime_error(
                    "MmapDecoder: corrupt stream at offset " + std::to_string(offset));
            }

            switch (type) {
                case MsgType::Quote: {
                    QuoteMsg m;
                    std::memcpy(&m, data_ + offset, sizeof(QuoteMsg));
                    visitor.on_quote(m);
                    break;
                }
                case MsgType::Trade: {
                    TradeMsg m;
                    std::memcpy(&m, data_ + offset, sizeof(TradeMsg));
                    visitor.on_trade(m);
                    break;
                }
                case MsgType::OrderAck: {
                    OrderAckMsg m;
                    std::memcpy(&m, data_ + offset, sizeof(OrderAckMsg));
                    visitor.on_order_ack(m);
                    break;
                }
            }

            offset += msg_size;
            ++count;
        }
        return count;
    }

    size_t size_bytes() const { return size_; }

private:
    int fd_ = -1;
    const uint8_t* data_ = nullptr;
    size_t size_ = 0;
};

} // namespace md
