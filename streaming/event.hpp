#pragma once
// event.hpp -- the payload type used by all streaming benchmarks. Kept
// separate from protocol.hpp's wire-format structs on purpose: this
// represents a decoded, downstream event (e.g. "risk check this trade"),
// not a raw wire message, so pipeline code doesn't need to know about the
// binary protocol at all.
#include <cstdint>
#include <chrono>

namespace pipeline {

struct Event {
    uint64_t seq = 0;
    uint64_t payload = 0;
    // Timestamp set at push time, read at pop/process time, so benchmarks
    // can measure per-item queueing latency, not just aggregate throughput.
    std::chrono::steady_clock::time_point pushed_at;
};

} // namespace pipeline
