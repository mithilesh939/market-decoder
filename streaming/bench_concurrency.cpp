// bench_concurrency.cpp
//
// Benchmarks two SEPARATE bottleneck fixes, each isolated from the other:
//
//   1. Lock-free ring buffer vs. mutex+condvar queue (the "thread waiting"
//      bottleneck).
//   2. Cache-line-padded ring buffer vs. unpadded (the "false sharing"
//      bottleneck) -- same lock-free logic both times, only the memory
//      layout differs.
//
// IMPORTANT HONESTY NOTE, read before trusting these numbers:
// Both comparisons only measure a real effect if the producer and
// consumer threads are actually running simultaneously on separate
// physical cores. On a single-core machine (or a VM pinned to one
// vCPU), the OS just time-slices the two threads, and BOTH comparisons
// will show noise, not the real effect -- or may even show the "wrong"
// winner by chance. This binary was developed and correctness-tested on
// a 1-vCPU sandbox; the numbers printed by THAT environment should be
// treated as "the code runs and produces a plausible-looking number",
// not as validated performance claims. Re-run on real multi-core
// hardware (e.g. WSL, a laptop) before citing these numbers anywhere.
//
#include "../streaming/event.hpp"
#include "../streaming/mutex_queue.hpp"
#include "../streaming/ring_buffer.hpp"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <thread>

using namespace pipeline;
using Clock = std::chrono::steady_clock;

constexpr size_t kNumEvents = 2'000'000;
constexpr size_t kRingCapacity = 1 << 16; // 65536, power of two

// ---------------------------------------------------------------------------
// Benchmark 1: MutexQueue baseline
// ---------------------------------------------------------------------------
double bench_mutex_queue() {
    MutexQueue<Event> q;
    std::atomic<uint64_t> checksum{0};

    auto t0 = Clock::now();

    std::thread producer([&] {
        for (uint64_t i = 0; i < kNumEvents; ++i) {
            q.push(Event{i, i * 2, Clock::now()});
        }
    });
    std::thread consumer([&] {
        uint64_t received = 0;
        uint64_t local_checksum = 0;
        while (received < kNumEvents) {
            Event e = q.pop_blocking();
            local_checksum ^= (e.seq * 0x9E3779B97F4A7C15ULL) ^ e.payload;
            ++received;
        }
        checksum.store(local_checksum);
    });

    producer.join();
    consumer.join();
    auto t1 = Clock::now();

    double ns = std::chrono::duration<double, std::nano>(t1 - t0).count();
    printf("MutexQueue        total=%.2f ms   %.1f ns/event   checksum=%llu\n",
           ns / 1e6, ns / kNumEvents, (unsigned long long)checksum.load());
    return ns;
}

// ---------------------------------------------------------------------------
// Benchmark 2: lock-free ring buffer (template parameter controls padding)
// ---------------------------------------------------------------------------
template <bool PAD>
double bench_ring_buffer(const char* label) {
    SPSCRingBuffer<Event, kRingCapacity, PAD> rb;
    std::atomic<uint64_t> checksum{0};

    auto t0 = Clock::now();

    std::thread producer([&] {
        for (uint64_t i = 0; i < kNumEvents; ++i) {
            Event e{i, i * 2, Clock::now()};
            while (!rb.try_push(e)) {
                // busy-poll: the whole point of the lock-free design is
                // to avoid a syscall/context-switch here.
            }
        }
    });
    std::thread consumer([&] {
        uint64_t received = 0;
        uint64_t local_checksum = 0;
        Event e;
        while (received < kNumEvents) {
            if (rb.try_pop(e)) {
                local_checksum ^= (e.seq * 0x9E3779B97F4A7C15ULL) ^ e.payload;
                ++received;
            }
        }
        checksum.store(local_checksum);
    });

    producer.join();
    consumer.join();
    auto t1 = Clock::now();

    double ns = std::chrono::duration<double, std::nano>(t1 - t0).count();
    printf("%-18s total=%.2f ms   %.1f ns/event   checksum=%llu\n",
           label, ns / 1e6, ns / kNumEvents, (unsigned long long)checksum.load());
    return ns;
}

int main() {
    unsigned hw_threads = std::thread::hardware_concurrency();
    printf("hardware_concurrency() reports: %u\n", hw_threads);
    if (hw_threads < 2) {
        printf("WARNING: fewer than 2 logical cores available. The comparisons\n");
        printf("below cannot show a real concurrency effect on this machine --\n");
        printf("treat these numbers as \"code runs correctly\", not \"X is faster\".\n");
    }
    printf("Transferring %zu events producer -> consumer, best of 3 runs.\n\n", kNumEvents);

    double best_mutex = 1e18, best_padded = 1e18, best_unpadded = 1e18;
    for (int i = 0; i < 3; ++i) {
        best_mutex    = std::min(best_mutex, bench_mutex_queue());
        best_padded   = std::min(best_padded, bench_ring_buffer<true>("RingBuffer(padded)"));
        best_unpadded = std::min(best_unpadded, bench_ring_buffer<false>("RingBuffer(unpadded)"));
        printf("\n");
    }

    printf("--- best of 3 ---\n");
    printf("MutexQueue          : %.1f ns/event\n", best_mutex / kNumEvents);
    printf("RingBuffer (padded)  : %.1f ns/event  (%.2fx vs mutex)\n",
           best_padded / kNumEvents, best_mutex / best_padded);
    printf("RingBuffer (unpadded): %.1f ns/event  (%.2fx vs padded)\n",
           best_unpadded / kNumEvents, best_padded / best_unpadded);

    return 0;
}
