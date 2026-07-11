CXX      := g++
CXXFLAGS := -std=c++17 -O3 -Wall -Wextra -march=native

.PHONY: all test bench clean run-demo streaming

all: generate benchmark test_decoder streaming

generate: src/generate.cpp include/protocol.hpp
	$(CXX) $(CXXFLAGS) src/generate.cpp -o generate

benchmark: bench/benchmark.cpp include/decoder.hpp include/naive_decoder.hpp
	$(CXX) $(CXXFLAGS) bench/benchmark.cpp -o benchmark

test_decoder: tests/test_decoder.cpp include/decoder.hpp include/naive_decoder.hpp
	$(CXX) $(CXXFLAGS) tests/test_decoder.cpp -o test_decoder

# --- Streaming pipeline (Layer 2: ring buffer, cache alignment, adaptive batching) ---

test_ring_buffer: tests/test_ring_buffer.cpp streaming/ring_buffer.hpp
	$(CXX) $(CXXFLAGS) -pthread tests/test_ring_buffer.cpp -o test_ring_buffer

bench_concurrency: streaming/bench_concurrency.cpp streaming/ring_buffer.hpp streaming/mutex_queue.hpp streaming/event.hpp
	$(CXX) $(CXXFLAGS) -pthread streaming/bench_concurrency.cpp -o bench_concurrency

bench_adaptive: streaming/bench_adaptive.cpp
	$(CXX) $(CXXFLAGS) streaming/bench_adaptive.cpp -o bench_adaptive

streaming: test_ring_buffer bench_concurrency bench_adaptive

test: test_decoder test_ring_buffer
	./test_decoder
	./test_ring_buffer

# Generates 2M synthetic messages and runs the benchmark against them.
bench: generate benchmark
	./generate market_data.bin 2000000
	./benchmark market_data.bin

# Runs the streaming pipeline benchmarks. NOTE: bench_concurrency needs
# multi-core hardware for trustworthy numbers -- see README.
bench-streaming: streaming
	./bench_concurrency
	@echo ""
	./bench_adaptive

run-demo: bench

clean:
	rm -f generate benchmark test_decoder test_ring_buffer bench_concurrency bench_adaptive market_data.bin
