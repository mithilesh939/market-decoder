# 🚀 Market Decoder & Low-Latency Trading Analytics Platform

> High-performance market data decoding, real-time analytics, risk monitoring, and visualization platform inspired by modern quantitative trading infrastructure.

![C++](https://img.shields.io/badge/C++20-blue)
![Python](https://img.shields.io/badge/Python-3.11-yellow)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PostgreSQL-blue)
![Grafana](https://img.shields.io/badge/Grafana-Dashboard-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

This project implements a high-performance market data processing pipeline capable of decoding millions of market messages with ultra-low latency while providing real-time visualization and analytics.

The system combines modern C++, Python, TimescaleDB, and Grafana to simulate the core components of a quantitative trading firm's market data infrastructure.

Rather than focusing only on algorithmic trading strategies, this project emphasizes the engineering challenges behind high-frequency trading systems:

- Efficient binary protocol decoding
- Zero-copy parsing
- Cache-friendly memory access
- High-throughput data ingestion
- Time-series storage
- Real-time monitoring
- Risk management

---

# Architecture

```
                    Historical Market Data
                            │
                            ▼
                  Binary Market Data Files
                            │
                            ▼
             High Performance Market Decoder
                   (C++20 + Python Binding)
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
      Trade Messages                  Quote Messages
            │                               │
            └───────────────┬───────────────┘
                            ▼
                     TimescaleDB
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
    Market Analytics   Risk Engine     Performance Metrics
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
                        Grafana
```

---

# Features

### High Performance Decoder

- Binary protocol decoder written in C++
- Python bindings for research workflows
- Zero-copy memory mapping
- Cache-efficient parsing
- Multi-million message throughput

---

### Time-Series Storage

- TimescaleDB backend
- Optimized hypertables
- Efficient historical queries
- Batch ingestion pipeline
- Scalable market data storage

---

### Grafana Dashboard

Interactive dashboards including:

- Price Action
- Volume Analysis
- Trade Rate
- VWAP
- Spread Analysis
- Latency Metrics
- CPU Usage
- Cache Misses
- Branch Prediction
- Risk Monitoring

---

### Risk Engine

Implements configurable pre-trade risk checks including:

- Price Collar
- Order Size Limits
- Inventory Limits
- Kill Switch
- Rule Engine Framework

---

### Performance Benchmarking

Performance comparison between multiple decoder implementations.

Example benchmark:

| Decoder | Latency |
|----------|---------|
| Naive Decoder | 26.48 ns/message |
| Memory-Mapped Decoder | 7.75 ns/message |

Achieved over **129 million messages per second** using memory-mapped decoding.

---

# Technology Stack

## Core

- C++20
- Python
- Pybind11

## Database

- PostgreSQL
- TimescaleDB

## Visualization

- Grafana

## Build

- Make
- GCC
- CMake

---

# Project Structure

```
market-decoder-optiver/

├── benchmark/
├── dashboard/
├── decoder/
├── include/
├── python/
├── risk/
├── tests/
├── tools/
│   ├── monthly_bins/
│   └── convert_binance_csv.py
├── Makefile
└── README.md
```

---

# Performance

The decoder was evaluated using real market data.

## Decoder Throughput

| Decoder | Throughput |
|----------|-----------:|
| Naive | 37.8 Million msg/s |
| Memory Mapped | 129.1 Million msg/s |

---

# Risk Engine

The rule engine supports independent configurable rules.

Current implementation includes:

- Price Collar
- Inventory Limits
- Order Size Limits
- Kill Switch

Additional rules can be added without modifying the core engine.

---

# Future Work

- FPGA accelerated decoding
- SIMD optimized parser
- Lock-free processing pipeline
- Live exchange connectivity
- Multi-symbol support
- Order book reconstruction
- Strategy backtesting engine
- Real-time anomaly detection
- Latency regression analysis

---

# Learning Outcomes

This project explores many of the software engineering concepts used in modern quantitative trading systems:

- Binary protocol engineering
- Low-latency systems
- Memory optimization
- High-throughput data pipelines
- Time-series databases
- Risk management
- Performance benchmarking
- Real-time observability

---

# Acknowledgements

This project was developed for learning and research purposes to better understand the infrastructure powering modern electronic markets and quantitative trading systems.

It is **not affiliated with or endorsed by Optiver, Jane Street, IMC, Hudson River Trading, Tower Research, or any exchange.**

---

# License

MIT License