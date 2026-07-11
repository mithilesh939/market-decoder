#pragma once
// ---------------------------------------------------------------------------
// mutex_queue.hpp
//
// A deliberately conventional producer/consumer queue: std::queue guarded
// by a std::mutex, with a condition_variable so the consumer sleeps
// instead of spinning when empty. This is the "before" baseline for
// bench_concurrency.cpp -- the version most people reach for first, and a
// fair comparison point because it's correct and simple, not a strawman.
// ---------------------------------------------------------------------------

#include <condition_variable>
#include <mutex>
#include <queue>

namespace pipeline {

template <typename T>
class MutexQueue {
public:
    void push(const T& item) {
        {
            std::lock_guard<std::mutex> lock(mu_);
            q_.push(item);
        }
        cv_.notify_one();
    }

    // Blocks until an item is available.
    T pop_blocking() {
        std::unique_lock<std::mutex> lock(mu_);
        cv_.wait(lock, [this] { return !q_.empty(); });
        T item = std::move(q_.front());
        q_.pop();
        return item;
    }

    bool try_pop(T& out) {
        std::lock_guard<std::mutex> lock(mu_);
        if (q_.empty()) return false;
        out = std::move(q_.front());
        q_.pop();
        return true;
    }

private:
    std::mutex mu_;
    std::condition_variable cv_;
    std::queue<T> q_;
};

} // namespace pipeline
