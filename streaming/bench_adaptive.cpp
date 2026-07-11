// bench_adaptive.cpp
//
// Compares three consumer batching strategies under a BURSTY workload --
// alternating "quiet" periods (low arrival rate) and "burst" periods
// (high arrival rate), which is what a real market data / order flow
// consumer actually sees, not a constant rate.
//
// This is a deterministic discrete-event simulation, not a real-time
// multithreaded benchmark: arrival "time" is a simulated tick counter,
// not wall-clock time. That's a deliberate choice -- it makes the result
// fully reproducible on any hardware (unlike bench_concurrency.cpp, which
// needs real multi-core contention to mean anything), because the thing
// being measured is a SCHEDULING POLICY question, not a hardware question:
// given a backlog of size N, is it better to process 1 item or a batch?
//
// Strategies compared:
//   1. batch=1    -- process every item immediately as it arrives.
//                    Best latency when quiet, but falls behind during
//                    bursts because per-item overhead dominates.
//   2. batch=256  -- always wait to accumulate up to 256 items before
//                    processing as a batch. Great throughput during
//                    bursts, but adds needless latency during quiet
//                    periods where the queue never fills.
//   3. adaptive   -- batch size scales with current backlog: small
//                    backlog -> small batch (low latency), large backlog
//                    -> large batch (high throughput), no fixed constant
//                    to hand-tune.
//
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <random>
#include <vector>

namespace {

struct SimEvent {
    uint64_t seq;
    uint64_t arrival_tick;
};

// Fixed per-item and per-batch processing costs (in simulated "ticks").
// PER_ITEM_COST models real work (e.g. a risk check). PER_BATCH_OVERHEAD
// models fixed costs paid once per batch regardless of size (e.g. a
// cache-line touch, a syscall, a lock acquisition) -- this is what makes
// batch=1 genuinely worse under load: it pays that fixed cost on every
// single item instead of amortizing it.
constexpr uint64_t PER_ITEM_COST = 2;
constexpr uint64_t PER_BATCH_OVERHEAD = 20;

// Generates a bursty arrival schedule: 2000 ticks quiet (1 arrival every
// ~20 ticks), then 500 ticks of burst (1 arrival every ~1 tick), repeated
// 4 times. Fixed seed for reproducibility.
std::vector<SimEvent> make_bursty_schedule() {
    std::mt19937 rng(7);
    std::vector<SimEvent> events;
    uint64_t tick = 0;
    uint64_t seq = 0;

    for (int cycle = 0; cycle < 4; ++cycle) {
        // Quiet period
        std::uniform_int_distribution<int> quiet_gap(15, 25);
        uint64_t quiet_end = tick + 2000;
        while (tick < quiet_end) {
            events.push_back({seq++, tick});
            tick += quiet_gap(rng);
        }
        // Burst period
        std::uniform_int_distribution<int> burst_gap(0, 2);
        uint64_t burst_end = tick + 500;
        while (tick < burst_end) {
            events.push_back({seq++, tick});
            tick += burst_gap(rng);
        }
    }
    return events;
}

struct Result {
    double avg_latency_quiet;
    double avg_latency_burst;
    uint64_t finish_tick;
    uint64_t max_backlog;
};

// Runs the simulation for a given strategy. `adaptive` toggles between
// fixed-batch-size and backlog-scaled batch size.
Result simulate(const std::vector<SimEvent>& events, int fixed_batch_size, bool adaptive) {
    std::deque<SimEvent> queue;
    size_t next_arrival = 0;
    uint64_t tick = 0;
    uint64_t max_backlog = 0;

    double quiet_latency_sum = 0; uint64_t quiet_count = 0;
    double burst_latency_sum = 0; uint64_t burst_count = 0;

    // A tick is "burst" if the previous inter-arrival gap was small; we
    // approximate by checking the local arrival density around this tick
    // using the event schedule itself (cycle position), since we control
    // generation above (0-2000 quiet, 2000-2500 burst, repeating every 2500).
    auto is_burst_tick = [](uint64_t t) {
        return (t % 2500) >= 2000;
    };

    while (next_arrival < events.size() || !queue.empty()) {
        // Admit all events that have arrived by current tick.
        while (next_arrival < events.size() && events[next_arrival].arrival_tick <= tick) {
            queue.push_back(events[next_arrival]);
            ++next_arrival;
        }
        max_backlog = std::max(max_backlog, (uint64_t)queue.size());

        bool no_more_arrivals = (next_arrival >= events.size());

        // Decide the batch size this strategy WANTS right now.
        int desired_batch;
        if (adaptive) {
            size_t backlog = queue.size();
            if (backlog < 4)        desired_batch = 1;
            else if (backlog < 32)  desired_batch = 16;
            else                     desired_batch = 256;
        } else {
            desired_batch = fixed_batch_size;
        }

        bool batch_is_full = (int)queue.size() >= desired_batch;

        if (queue.empty()) {
            if (!no_more_arrivals) tick = events[next_arrival].arrival_tick;
            continue;
        }

        // A FIXED strategy with desired_batch > 1 genuinely WAITS for the
        // batch to fill (that's the real-world behavior being modeled --
        // e.g. a consumer that only wakes up every 256 messages). It will
        // only process a partial batch if no more arrivals are coming
        // (otherwise we'd never finish). This is what exposes the real
        // latency cost of large fixed batches during quiet periods.
        if (!adaptive && desired_batch > 1 && !batch_is_full && !no_more_arrivals) {
            tick = events[next_arrival].arrival_tick; // wait for the next arrival
            continue;
        }

        int batch_size = std::min<int>(desired_batch, (int)queue.size());

        // Process the batch: fixed overhead once, plus per-item cost.
        uint64_t processing_cost = PER_BATCH_OVERHEAD + PER_ITEM_COST * batch_size;
        tick += processing_cost;

        for (int i = 0; i < batch_size; ++i) {
            SimEvent e = queue.front();
            queue.pop_front();
            double latency = (double)(tick - e.arrival_tick);
            if (is_burst_tick(e.arrival_tick)) {
                burst_latency_sum += latency;
                ++burst_count;
            } else {
                quiet_latency_sum += latency;
                ++quiet_count;
            }
        }
    }

    return {
        quiet_count ? quiet_latency_sum / quiet_count : 0.0,
        burst_count ? burst_latency_sum / burst_count : 0.0,
        tick,
        max_backlog,
    };
}

} // namespace

int main() {
    auto events = make_bursty_schedule();
    printf("Simulated %zu events across 4 quiet/burst cycles.\n\n", events.size());
    printf("%-14s %12s %12s %10s %10s\n", "STRATEGY", "QUIET_LAT", "BURST_LAT", "FINISH", "MAX_BACKLOG");

    auto print_result = [](const char* name, const Result& r) {
        printf("%-14s %12.1f %12.1f %10lu %10lu\n",
               name, r.avg_latency_quiet, r.avg_latency_burst,
               (unsigned long)r.finish_tick, (unsigned long)r.max_backlog);
    };

    print_result("batch=1",   simulate(events, 1, false));
    print_result("batch=16",  simulate(events, 16, false));
    print_result("batch=256", simulate(events, 256, false));
    print_result("adaptive",  simulate(events, 0, true));

    printf("\nQUIET_LAT / BURST_LAT are average per-item latency (arrival to processed), in simulated ticks.\n");
    printf("FINISH is the tick the last event was processed (lower = cleared backlog faster).\n");
    printf("MAX_BACKLOG is the largest queue depth seen (lower = less memory pressure / risk of drops).\n");
    return 0;
}
