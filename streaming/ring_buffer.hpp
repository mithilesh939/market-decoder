#pragma once
// ---------------------------------------------------------------------------
// ring_buffer.hpp
//
// Single-producer, single-consumer lock-free ring buffer.
//
// Bottleneck this targets: thread waiting. A mutex-guarded queue puts both
// producer and consumer to sleep on contention (and wakes them via the
// kernel scheduler, which costs microseconds). This SPSC ring buffer never
// blocks -- push/pop either succeed immediately or fail immediately
// (buffer full / empty), so callers busy-poll instead of sleeping. That
// trade only makes sense when you have a spare core to spin on, which is
// exactly the trade low-latency trading systems make.
//
// PAD_CACHE_LINES is a compile-time toggle used to isolate a *second*,
// separate bottleneck: false sharing. If the producer's tail_ index and
// the consumer's head_ index live on the same 64-byte cache line, every
// producer write invalidates the consumer's cached copy of that line (and
// vice versa) even though they're logically independent counters. Padding
// each index out to its own cache line removes that false dependency.
//
// PAD_CACHE_LINES=true  -> head_ and tail_ each on their own cache line.
// PAD_CACHE_LINES=false -> head_ and tail_ adjacent, likely sharing a line.
//
// This lets bench_concurrency.cpp benchmark the *same* ring buffer logic
// with and without padding, to measure the false-sharing cost in
// isolation from the lock-free-vs-mutex question.
// ---------------------------------------------------------------------------

#include <atomic>
#include <cstddef>
#include <array>

namespace pipeline {

constexpr size_t kCacheLineSize = 64;

template <typename T, size_t Capacity, bool PAD_CACHE_LINES = true>
class SPSCRingBuffer {
    static_assert((Capacity & (Capacity - 1)) == 0,
                  "Capacity must be a power of two (fast modulo via mask)");

public:
    SPSCRingBuffer() : head_(0), tail_(0) {}

    // Producer-only. Returns false if the buffer is full.
    bool try_push(const T& item) {
        const size_t tail = tail_.load(std::memory_order_relaxed);
        const size_t next = (tail + 1) & mask_;
        if (next == head_.load(std::memory_order_acquire)) {
            return false; // full
        }
        buffer_[tail] = item;
        tail_.store(next, std::memory_order_release);
        return true;
    }

    // Consumer-only. Returns false if the buffer is empty.
    bool try_pop(T& out) {
        const size_t head = head_.load(std::memory_order_relaxed);
        if (head == tail_.load(std::memory_order_acquire)) {
            return false; // empty
        }
        out = buffer_[head];
        head_.store((head + 1) & mask_, std::memory_order_release);
        return true;
    }

    // Approximate occupancy -- safe to call from either thread for
    // heuristics (e.g. adaptive batching), but is inherently a stale
    // snapshot in a concurrent setting; never used for correctness here,
    // only for scheduling decisions where staleness is acceptable.
    size_t approx_size() const {
        const size_t tail = tail_.load(std::memory_order_relaxed);
        const size_t head = head_.load(std::memory_order_relaxed);
        return (tail - head) & mask_;
    }

    static constexpr size_t capacity() { return Capacity; }

private:
    static constexpr size_t mask_ = Capacity - 1;

    // The padding struct: conditionally reserves a full cache line so the
    // atomic that follows starts on its own line. When PAD_CACHE_LINES is
    // false, this is zero-sized and head_/tail_ end up adjacent.
    struct EmptyPad {};
    struct LinePad { char _pad[kCacheLineSize - sizeof(std::atomic<size_t>)]; };
    using Pad = std::conditional_t<PAD_CACHE_LINES, LinePad, EmptyPad>;

    alignas(PAD_CACHE_LINES ? kCacheLineSize : alignof(std::atomic<size_t>))
        std::atomic<size_t> head_;
    [[no_unique_address]] Pad pad_between_;
    alignas(PAD_CACHE_LINES ? kCacheLineSize : alignof(std::atomic<size_t>))
        std::atomic<size_t> tail_;

    std::array<T, Capacity> buffer_;
};

} // namespace pipeline
