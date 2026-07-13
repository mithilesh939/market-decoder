# market-decoder

A low-latency, no-copy binary market data decoder in C++17 — the kind of
protocol-encoding work Optiver's Chicago tech interns have shipped to
production.

## Why this exists

Exchanges send a constant stream of binary messages (quotes, trades, order
acknowledgements). The obvious way to handle them — read bytes, allocate a
struct, copy each field in — works, but every allocation and copy costs
CPU time you don't get back. At high message rates that overhead becomes
the bottleneck.

The fix used here: design the wire format so it **is** the in-memory struct
layout. Then "decoding" a message is a pointer cast, not a parse.

## Architecture

```
market-decoder/
├── include/
│   ├── protocol.hpp       # packed wire-format structs (Quote, Trade, OrderAck)
│   ├── decoder.hpp        # MmapDecoder — no-copy, mmap + reinterpret_cast
│   └── naive_decoder.hpp  # NaiveDecoder — baseline, heap alloc + memcpy per msg
├── src/generate.cpp       # writes synthetic market data to a binary file
├── bench/benchmark.cpp    # throughput comparison, naive vs no-copy
└── tests/test_decoder.cpp # correctness: both decoders must agree exactly
```

**Wire format:** `[1 byte MsgType][fixed-size payload]`, repeated back to
back. `#pragma pack(push, 1)` on every struct removes compiler padding, so
`sizeof(Struct)` is exactly the on-wire byte count — no translation layer
needed between "bytes on disk" and "struct in memory."

**MmapDecoder** memory-maps the file (`mmap`, `MADV_SEQUENTIAL` for
readahead) and walks it with a raw pointer, casting each record's bytes
directly to the matching struct type. No allocation, no `memcpy`, for the
entire decode.

**NaiveDecoder** exists purely as an honest baseline: `fread` the whole
file into a `vector<uint8_t>`, then `make_unique` + `memcpy` a struct per
message — the version most people write on a first pass.

A `ChecksumVisitor` in the benchmark XORs message fields together so the
compiler can't optimize the decode loop away as dead code, without adding
meaningful overhead of its own.

## Results

Measured on this machine, 2,000,000 synthetic messages, best of 5 runs:

```
NaiveDecoder   messages=2000000   best=25.38 ns/msg   (~39.4M msgs/sec)
MmapDecoder    messages=2000000   best=10.30 ns/msg   (~97.1M msgs/sec)
```

**~2.5x throughput improvement**, with both decoders producing an
identical checksum over the decoded stream — confirming the speedup isn't
coming from skipped work. Run `make bench` to reproduce on your own
machine.

## Build & run

```bash
make          # builds generate, benchmark, test_decoder
make test     # correctness tests (no external framework required)
make bench    # generates 2M messages and runs the throughput comparison
```

Requires only g++ (C++17) — no CMake, no third-party dependencies.

## Python bindings (pybind11 + Pandas)

The `python/` directory wires the C++ decoder up to Python for research/
backtesting use — the second half of the real Optiver project this repo
is modeled on ("a Python C extension that reads data from these files and
presents them as Pandas dataframes").

```
python/
├── bindings.cpp          # pybind11 module: decode() -> dict of row-lists
├── market_decoder.py     # thin wrapper: row-lists -> pandas DataFrames
├── build.sh               # builds the compiled extension
└── test_bindings.py       # cross-validation test (see below)
```

**Usage:**

```python
from market_decoder import decode_to_dataframes

dfs = decode_to_dataframes("market_data.bin")
dfs["quotes"]      # pandas DataFrame
dfs["trades"]      # pandas DataFrame
dfs["order_acks"]  # pandas DataFrame
```

**Build:**

```bash
cd python
pip install pybind11 pandas --break-system-packages   # if not already installed
./build.sh
python3 test_bindings.py
```

**Design:** the C++ side (`bindings.cpp`) does the minimum necessary —
decode records and hand back plain Python dicts — and leaves DataFrame
construction to the Python wrapper. This keeps the compiled surface small
and keeps pandas a Python-only dependency, not something the C++ build
needs to know about.

**Correctness — cross-validated, not just row-counted:** `test_bindings.py`
doesn't just check row counts match. It computes the exact same XOR
checksum formula used by `bench/benchmark.cpp`'s `ChecksumVisitor`, once
from the C++ decoder's own output and once by reading the fields back out
of the pandas DataFrames the Python binding produced. Both paths landed on
the same 64-bit value (`506744000` on a 10,000-message test file),
confirming every field of every message round-trips through the Python
extension without corruption — not just that the same *number* of rows
came out.

## Layer 2: Streaming Pipeline (Lock-Free Ring Buffer, Cache Alignment, Adaptive Batching)

Project 1 above solves *decode* latency for a static file. This layer
solves a different, related problem: how decoded events move from a
producer (the decoder) to a consumer (e.g. a risk check or strategy) in a
live system, where "read a file fast" isn't enough — the handoff between
threads matters too.

Three bottlenecks, three targeted fixes, each benchmarked independently
rather than as one combined "it's faster now" claim:

| Bottleneck | Fix | Where |
|---|---|---|
| Thread waiting (mutex sleep/wake via the kernel scheduler) | Lock-free SPSC ring buffer, busy-poll instead of blocking | `streaming/ring_buffer.hpp` vs `streaming/mutex_queue.hpp` |
| False sharing (producer/consumer indices on the same cache line) | Pad head/tail atomics to separate 64-byte cache lines | `streaming/ring_buffer.hpp` (`PAD_CACHE_LINES` template flag) |
| Fixed batch size is wrong for *some* workload regime | Adaptive batching: batch size scales with current backlog | `streaming/bench_adaptive.cpp` |

### Honesty note on hardware

This project was developed on a **1-vCPU sandbox**. That's a real
constraint worth being upfront about: the ring-buffer-vs-mutex and
padded-vs-unpadded comparisons are fundamentally about two threads
running *simultaneously* on separate physical cores — on 1 core they
just time-slice, so any "X% faster" claim from that environment would be
unverifiable at best and misleading at worst. Rather than fabricate or
hand-wave that, here's what's actually true from measurements taken here,
and what still needs multi-core validation:

**Measured on 1 vCPU (Intel Xeon @ 2.80GHz), 2,000,000 events, best of 3 runs:**

```
MutexQueue           : 161.7 ns/event
RingBuffer (padded)  : 108.6 ns/event   (1.49x vs mutex)
RingBuffer (unpadded): 108.8 ns/event   (1.00x vs padded)
```

- The **mutex-vs-ring-buffer gap (1.49x) is real and trustworthy even on
  1 core** — most of that cost is context-switch and syscall overhead
  from the condition variable waking a sleeping thread, which is a real
  cost regardless of core count.
- The **padded-vs-unpadded result showing no difference (1.00x) is
  exactly what the theory predicts on 1 core** — false sharing requires
  real cache-coherency traffic between two cores actually executing at
  the same time. A null result here isn't a failed experiment; it's a
  consistent one. This comparison needs to be re-run on real multi-core
  hardware (`make bench-streaming`) before drawing any conclusion about
  whether the padding helps.

Run `make bench-streaming` on a real multi-core machine to get a
trustworthy padded-vs-unpadded number and update this section.

### Adaptive batching (fully hardware-independent)

Unlike the two comparisons above, this one doesn't need real concurrency
to mean something — it's a scheduling-policy question, validated with a
deterministic discrete-event simulation (`streaming/bench_adaptive.cpp`)
under a bursty arrival pattern (quiet periods, then burst periods,
repeated 4 cycles). Reproducible on any machine:

```
STRATEGY          QUIET_LAT    BURST_LAT     FINISH  MAX_BACKLOG
batch=1             17068.3      21477.0      52954         1951
batch=16              478.8        609.7      11217          359
batch=256            1616.3       1039.0      10951          428
adaptive              175.2        512.0      10654          290
```

- **batch=1 is catastrophic**, not just slow: its fixed per-item overhead
  (22 simulated ticks) exceeds the average arrival gap during quiet
  periods (~20 ticks), so it can *never* catch up — the backlog grows
  unboundedly for the entire run. This is the real-world argument for why
  naive per-message processing breaks down under sustained load, not just
  bursts.
- **batch=256 pays a real latency cost during quiet periods** (1616 ticks)
  because it genuinely waits to accumulate a full batch before processing
  — a fixed large batch is a bad trade when traffic is sparse.
- **Adaptive wins in both regimes** — 175.2 quiet latency (better than
  every fixed option, including batch=1's quiet-only case) and 512.0
  burst latency (better than batch=256, competitive with batch=16) —
  without a hand-tuned constant.

An earlier version of this simulation had a bug worth noting: the
"fixed batch=256" strategy was implemented to *cap* at 256 rather than
*wait* for 256, which accidentally made it behave like the adaptive
strategy and produced a misleadingly small gap between them. Fixed by
making fixed-batch strategies genuinely block until the batch fills (or
input ends) — which is what exposed the real quiet-period latency cost
above.

### Build & run

```bash
make streaming          # builds test_ring_buffer, bench_concurrency, bench_adaptive
make test                # includes ring buffer correctness tests
make bench-streaming     # runs both streaming benchmarks
```

## Design decisions / trade-offs

- **Fixed-point prices** (`int64_t`, scaled by 1e6) instead of floats —
  exchanges do this to avoid floating-point rounding in price comparisons;
  it's standard practice in trading systems.
- **`#pragma pack(1)`** trades a small amount of unaligned-access cost on
  some architectures for a wire format with zero translation overhead.
  Worth it here because decode throughput dominates.
- **mmap over read()** avoids a full up-front copy into user space and lets
  the kernel manage paging; for a decode-once-sequentially workload this is
  a clear win, though a real system would also want to handle files larger
  than available address space (not implemented here — noted as a known
  limitation).
- **Visitor pattern, not a returned vector of messages** — keeps memory
  flat and avoids ever materializing "all messages" as a data structure,
  matching how a real feed handler processes messages as they arrive.

## Known limitations / next steps

- No corruption/malformed-stream recovery beyond a thrown exception —
  a production system would want to skip-and-log or halt-and-alert.
- Single-threaded decode. A natural extension: shard the file into
  N contiguous regions (each aligned to a message boundary found by a
  quick forward scan) and decode in parallel.
- No live/streaming ingestion — this decodes a static file. Extending to
  a socket-fed ring buffer would be the natural "v2."

## Why this maps to Optiver's work

Optiver's Chicago tech interns have shipped a near-identical project: a
custom binary file format for captured exchange messages, designed so
decoding is close to a `memcpy`, because most low-latency code there is
written in C. This project follows the same core idea — pack format,
no-copy decode, benchmark the win — end to end, with tests and reproducible
numbers.
