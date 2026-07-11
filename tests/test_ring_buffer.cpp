// test_ring_buffer.cpp
//
// Single-threaded correctness tests for SPSCRingBuffer. Correctness (does
// it preserve order, does it correctly report full/empty) doesn't need
// real concurrency to verify -- only the *performance* claims do, which
// live in bench_concurrency.cpp instead.
//
#include "../streaming/ring_buffer.hpp"

#include <cassert>
#include <cstdio>

using pipeline::SPSCRingBuffer;

int main() {
    printf("running: fifo order preserved ... ");
    {
        SPSCRingBuffer<int, 8> rb;
        for (int i = 0; i < 5; ++i) {
            bool ok = rb.try_push(i);
            assert(ok);
        }
        for (int i = 0; i < 5; ++i) {
            int out = -1;
            bool ok = rb.try_pop(out);
            assert(ok);
            assert(out == i);
        }
    }
    printf("PASS\n");

    printf("running: full buffer rejects push ... ");
    {
        // Capacity 4 usable slots is Capacity-1=3 in this implementation
        // (one slot is always kept empty to distinguish full from empty).
        SPSCRingBuffer<int, 4> rb;
        assert(rb.try_push(1));
        assert(rb.try_push(2));
        assert(rb.try_push(3));
        assert(!rb.try_push(4)); // should be full now
    }
    printf("PASS\n");

    printf("running: empty buffer rejects pop ... ");
    {
        SPSCRingBuffer<int, 4> rb;
        int out;
        assert(!rb.try_pop(out));
    }
    printf("PASS\n");

    printf("running: wraparound after drain-and-refill ... ");
    {
        SPSCRingBuffer<int, 4> rb;
        for (int round = 0; round < 10; ++round) {
            assert(rb.try_push(round));
            assert(rb.try_push(round * 100));
            int a, b;
            assert(rb.try_pop(a));
            assert(rb.try_pop(b));
            assert(a == round);
            assert(b == round * 100);
        }
    }
    printf("PASS\n");

    printf("running: unpadded variant has identical behavior ... ");
    {
        SPSCRingBuffer<int, 8, /*PAD_CACHE_LINES=*/false> rb;
        for (int i = 0; i < 5; ++i) assert(rb.try_push(i));
        for (int i = 0; i < 5; ++i) {
            int out;
            assert(rb.try_pop(out));
            assert(out == i);
        }
    }
    printf("PASS\n");

    printf("\nAll ring buffer tests passed.\n");
    return 0;
}
