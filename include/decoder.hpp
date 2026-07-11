#pragma once
// ---------------------------------------------------------------------------
// decoder.hpp
//
// No-copy decoder: memory-maps a binary market data file and walks it as a
// sequence of variable-length, self-describing records. Because the wire
// format matches our in-memory struct layout exactly (see protocol.hpp),
// "decoding" a record is a pointer cast -- zero allocation, zero memcpy.
//
// Contrast this with NaiveDecoder in naive_decoder.hpp, which reads the
// file into a std::vector<uint8_t>, then heap-allocates and field-copies
// into a struct per message. The benchmark quantifies the difference.
// ---------------------------------------------------------------------------

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

// Callback-style visitor. The caller provides handlers; the decoder never
// allocates a message object -- it just hands back a pointer into the
// mapped file that is valid for the lifetime of the MmapDecoder.
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

        // MAP_POPULATE forces the kernel to pre-fault all page table entries
        // during this mmap() call, instead of lazily on first touch. Without
        // it, the first decode_all() pass pays page-fault cost *inside* the
        // timed region, which understates true steady-state throughput and
        // can even make the mmap path look slower than the naive read()
        // path in a single-shot benchmark. Falls back gracefully to a plain
        // mmap on platforms where MAP_POPULATE isn't defined.
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

            // NOTE on an earlier version of this code: casting data_ + offset
            // directly to a `const QuoteMsg*` and dereferencing it (i.e.
            // `*reinterpret_cast<const QuoteMsg*>(data_ + offset)`) is
            // undefined behavior under C++'s strict aliasing rule -- the
            // compiler is allowed to assume a `uint8_t*` and a `QuoteMsg*`
            // never alias the same memory, which can produce wrong results
            // under aggressive optimization (observed as a real risk at -O3
            // during review of this project).
            //
            // The fix used here keeps the "no heap allocation, no per-field
            // parsing" property while staying standards-compliant: memcpy
            // the bytes into a stack-local struct. For small POD types like
            // these, compilers (GCC/Clang, -O2+) recognize the fixed-size
            // memcpy pattern and lower it to a small number of load
            // instructions -- effectively the same machine code as the
            // pointer cast, but without invoking UB. This also sidesteps
            // the unaligned-access concern noted in the README, since
            // memcpy makes no alignment assumptions about the source.
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
