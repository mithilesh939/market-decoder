
#include "../include/decoder.hpp"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <unistd.h>
#include <vector>

using namespace md;
using Clock = std::chrono::steady_clock;

constexpr int SAMPLE_INTERVAL_MS = 50;

struct Sample {
    double elapsed_ms;
    long rss_kb;
    double cpu_percent_since_start;
};

long read_rss_kb() {
    std::ifstream f("/proc/self/status");
    std::string line;
    while (std::getline(f, line)) {
        if (line.rfind("VmRSS:", 0) == 0) {
            long kb = 0;
            sscanf(line.c_str(), "VmRSS: %ld kB", &kb);
            return kb;
        }
    }
    return -1;
}

double read_cpu_seconds() {
    std::ifstream f("/proc/self/stat");
    std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    size_t paren = content.rfind(')');
    if (paren == std::string::npos) return 0.0;
    std::istringstream iss(content.substr(paren + 2));
    std::string field;
    std::vector<std::string> fields;
    while (iss >> field) fields.push_back(field);
    if (fields.size() < 13) return 0.0;
    long utime = std::stol(fields[11]);
    long stime = std::stol(fields[12]);
    long clk_tck = sysconf(_SC_CLK_TCK);
    return static_cast<double>(utime + stime) / clk_tck;
}

int main(int argc, char** argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <market_data_file> <output_csv_path>\n", argv[0]);
        return 1;
    }
    std::string data_path = argv[1];
    std::string csv_path = argv[2];

    std::vector<Sample> samples;
    std::atomic<bool> done{false};
    auto t_start = Clock::now();

    std::thread sampler([&] {
        while (!done.load(std::memory_order_relaxed)) {
            auto now = Clock::now();
            double elapsed_ms = std::chrono::duration<double, std::milli>(now - t_start).count();
            long rss = read_rss_kb();
            double cpu_s = read_cpu_seconds();
            double cpu_pct = elapsed_ms > 0 ? (cpu_s * 1000.0 / elapsed_ms) * 100.0 : 0.0;
            samples.push_back({elapsed_ms, rss, cpu_pct});
            std::this_thread::sleep_for(std::chrono::milliseconds(SAMPLE_INTERVAL_MS));
        }
    });

    struct CountingVisitor : MessageVisitor {
        size_t count = 0;
        uint64_t checksum = 0;
        void on_quote(const QuoteMsg& m) override { checksum ^= m.timestamp_ns; ++count; }
        void on_trade(const TradeMsg& m) override { checksum ^= m.timestamp_ns; ++count; }
        void on_order_ack(const OrderAckMsg& m) override { checksum ^= m.timestamp_ns; ++count; }
    };

    MmapDecoder decoder(data_path);
    CountingVisitor visitor;
    auto t_decode_start = Clock::now();
    size_t count = decoder.decode_all(visitor);
    auto t_decode_end = Clock::now();

    done.store(true, std::memory_order_relaxed);
    sampler.join();

    double decode_ms = std::chrono::duration<double, std::milli>(t_decode_end - t_decode_start).count();
    double ns_per_msg = (decode_ms * 1e6) / count;
    double msgs_per_sec = count / (decode_ms / 1000.0);

    long peak_rss_kb = 0;
    for (auto& s : samples) peak_rss_kb = std::max(peak_rss_kb, s.rss_kb);

    std::ofstream csv(csv_path);
    csv << "elapsed_ms,rss_kb,cpu_percent\n";
    for (auto& s : samples) {
        csv << s.elapsed_ms << "," << s.rss_kb << "," << s.cpu_percent_since_start << "\n";
    }
    csv.close();

    printf("Decoded %zu messages from %s\n", count, data_path.c_str());
    printf("  decode time:   %.2f ms\n", decode_ms);
    printf("  throughput:    %.2f ns/msg  (%.1fM msgs/sec)\n", ns_per_msg, msgs_per_sec / 1e6);
    printf("  peak RSS:      %.1f MB\n", peak_rss_kb / 1024.0);
    printf("  samples taken: %zu (written to %s)\n", samples.size(), csv_path.c_str());
    printf("  checksum:      %llu\n", (unsigned long long)visitor.checksum);

    return 0;
}
