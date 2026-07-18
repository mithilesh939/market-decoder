# Market Decoder — Low-Latency Trading Analytics Platform

> High-performance market data decoding, real-time analytics, risk monitoring, and visualization — modeled on the core infrastructure behind quantitative trading firms.

![C++](https://img.shields.io/badge/C++17-blue)
![Python](https://img.shields.io/badge/Python-3.11-yellow)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PostgreSQL-blue)
![Grafana](https://img.shields.io/badge/Grafana-Dashboard-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

This project implements an end-to-end market data pipeline: a low-latency binary protocol decoder written in C++, a streaming/concurrency layer, a pre-trade risk engine, a market-making strategy module, and a TimescaleDB + Grafana analytics layer running against **695+ million real Binance BTCUSDT trades** spanning January–June 2025.

The emphasis throughout is on the systems-engineering problems behind electronic trading infrastructure, not on producing a profitable strategy:

- Zero-copy, cache-friendly binary protocol decoding
- Lock-free / concurrent streaming pipelines
- High-throughput time-series ingestion and storage
- Pre-trade risk rule enforcement
- Real-time observability and monitoring

---

## Architecture

```
Binance historical trade archive (CSV)
        │  tools/convert_binance_csv.py
        ▼
33-byte packed binary protocol (include/protocol.hpp)
        │
        ├──────────────► C++ Decoder Layer (src/, bench/)
        │                 Naive vs. memory-mapped decode paths
        │                 benchmarked for throughput/latency
        │
        ├──────────────► Streaming Layer (streaming/)
        │                 Ring buffer, mutex-queue baseline,
        │                 adaptive batching, concurrency benchmarks
        │
        ├──────────────► Risk Engine (risk/)
        │                 Price collar, order size limits,
        │                 inventory limits, kill switch
        │
        ├──────────────► Strategy Layer (strategy/)
        │                 Avellaneda–Stoikov market maker + backtester
        │
        └──────────────► tools/load_trades.py
                          ▼
                  TimescaleDB hypertable `trades`
                  (compressed columnstore, 695M rows)
                          │
                          ▼
              Continuous aggregates (1h / 1d OHLCV)
                          │
                          ▼
                       Grafana
          Executive dashboard: price/volume, risk metrics,
          decoder latency comparison, system health
```

---

## Components

### Decoder (`src/`, `bench/`, `include/`)
Binary protocol decoder with naive and memory-mapped implementations, benchmarked head-to-head.

### Streaming Layer (`streaming/`)
Ring buffer and mutex-queue message passing, with adaptive batching. Benchmarked separately for single-core decode latency vs. multi-core concurrent throughput (`bench_concurrency`, `bench_adaptive`).

### Risk Engine (`risk/`)
Configurable, independent pre-trade rules — price collar, order size limits, inventory limits, kill switch — designed so new rules can be added without touching the core engine.

### Strategy Layer (`strategy/`)
Avellaneda–Stoikov market-making model with a backtesting harness (`backtest.py`, `backtest_as.py`), run against real historical price data.

### Analytics (`analytics/`)
Latency, market regime, TCA, throughput, and summary statistics modules.

### Python Bindings (`python/`)
Pybind11 bindings exposing the C++ decoder to Python for research workflows.

### Data Pipeline & Dashboard (`tools/`, `grafana-stack/`)
- `convert_binance_csv.py` — converts raw Binance CSV exports into the internal 33-byte binary wire format
- `load_trades.py` — streams the binary files into a TimescaleDB hypertable via bulk `COPY`
- `setup_ohlcv_aggregates.sql` — builds 1-hour/1-day OHLCV continuous aggregates so dashboard queries never scan raw tick data
- `validate_data.py` — verifies date coverage, missing days, and row-level sanity checks
- `grafana-stack/` — Docker Compose stack (TimescaleDB + Grafana) with the full executive dashboard

---

## Results

### Decoder performance
| Decoder | Latency | Throughput |
|---|---|---|
| Naive | 20.23 ns/message | 49.4M msg/s |
| Memory-mapped | 8.26 ns/message | 121.1M msg/s |

*Measured via `make bench` (best of 5 runs, 2M synthetic messages, checksum-verified identical output between decoders — confirms both paths decode correctly, not just fast).*

### Data pipeline
- **695,541,427** real Binance BTCUSDT trades loaded, Jan 1 – Jun 30 2025
- Raw binary size **23 GB** → compressed TimescaleDB hypertable **15 GB** (1.5x, native columnstore compression)
- **181 / 181 expected days present — 0 missing days**, verified via automated integrity check (`tools/validate_data.py`)
- **0 rows** with zero/negative price or quantity across all 695M+ records
- 27 compressed chunks, queried through 1h/1d continuous aggregates (~4,500 rows total) so dashboard panels never touch the raw 695M-row table directly

**Monthly trade volume:**

| Month | Trades |
|---|---:|
| Jan 2025 | 135,946,515 |
| Feb 2025 | 128,881,324 |
| Mar 2025 | 136,245,963 |
| Apr 2025 | 104,290,701 |
| May 2025 | 108,937,329 |
| Jun 2025 | 81,239,595 |
| **Total** | **695,541,427** |

### Risk & performance analytics (BTC market benchmark, computed from real price data)
- Sharpe ratio (annualized): `[CONFIRM]`
- Historical VaR (95% / 99%, 1-day): `[CONFIRM]`
- Max drawdown: `[CONFIRM]`
- Decoder benchmark p50 / p95 / p99 latency by decoder type: `[CONFIRM]`

*(pull these from the dashboard's Risk & Performance row after the final run and paste them in here as concrete, quotable numbers)*

---

## Technology Stack

| Layer | Tools |
|---|---|
| Core | C++17, Python 3.11, Pybind11 |
| Database | PostgreSQL, TimescaleDB (hypertables + native compression + continuous aggregates) |
| Visualization | Grafana 11 |
| Build | Make, GCC |
| Data source | Binance historical trade archive |

---

## Project Structure

```
market-decoder-optiver/
├── src/                  C++ decoder core
├── bench/                Decoder benchmarks (naive vs. memory-mapped)
├── streaming/             Ring buffer, concurrency, adaptive batching
├── risk/                  Pre-trade risk engine
├── strategy/              Avellaneda-Stoikov market maker + backtester
├── analytics/             Latency, regime, TCA, throughput analysis
├── features/               Microstructure feature extraction
├── python/                 Pybind11 bindings
├── include/                 Shared headers / wire protocol definition
├── tests/                    C++ unit tests
├── tools/
│   ├── convert_binance_csv.py
│   ├── load_trades.py
│   ├── setup_ohlcv_aggregates.sql
│   └── validate_data.py
├── grafana-stack/
│   ├── docker-compose.yml
│   ├── init-db/
│   ├── provisioning/
│   └── dashboards/executive-overview.json
├── Makefile
└── README.md
```

---

## Reproducing This Project

**1. Build and test the C++ layer:**
```bash
make clean && make
make test              # runs test_decoder, test_ring_buffer
make bench             # generates 2M synthetic messages, benchmarks decoders
make bench-streaming   # concurrency + adaptive batching benchmarks
```

**2. Bring up the data stack:**
```bash
cd grafana-stack && docker compose up -d
```

**3. Load real market data** (requires Binance historical CSVs converted to the internal binary format via `tools/convert_binance_csv.py`):
```bash
pip install psycopg2-binary pandas numpy --break-system-packages
python3 tools/load_trades.py --truncate
```

**4. Build the OHLCV aggregates powering the dashboard:**
```bash
docker exec -i quant-timescaledb psql -U quant -d quant < tools/setup_ohlcv_aggregates.sql
```

**5. Validate data integrity:**
```bash
python3 tools/validate_data.py
```

**6. Import the dashboard:** Grafana → Dashboards → New → Import → upload `grafana-stack/dashboards/executive-overview.json`

---
## Dashboard

Grafana executive dashboard, running against the full 6-month, 695M-row dataset described below.

### Executive Summary & Key Metrics
![Executive Summary](docs/screenshots/01-executive-summary.png)

### Risk Metrics & Price Chart
![Risk and Price](docs/screenshots/02-risk-and-price.png)

### Latency, Drawdown & Volatility Analytics
![Latency and Analytics](docs/screenshots/03-latency-and-analytics.png)

### Comparison Tables & Market Regime
![Comparison Tables](docs/screenshots/04-comparison-tables.png)

Full dashboard definition (queries, panel configs): [`grafana-stack/dashboards/executive-overview.json`](grafana-stack/dashboards/executive-overview.json)

## Future Work

- SIMD-optimized parsing
- Lock-free processing pipeline
- Live exchange connectivity (currently historical-only)
- Multi-symbol support and order book reconstruction
- Full strategy backtesting engine wired into the risk/dashboard layer (currently, market-data metrics and strategy backtests are separate — see note below)
- Latency regression tracking across decoder versions

---

## Scope Notes

Some metrics that would require live strategy execution (equity curve, win rate, expectancy, slippage/TCA on real fills) are intentionally kept separate from the market-data dashboard — the `trades` table holds raw market ticks, not strategy positions. The `strategy/` module's backtest results are a separate artifact from the live dashboard and are not conflated with buy-and-hold market benchmarks shown there.

Decoder latency figures are measured from real, timed runs of the C++ decoder; the input stream used for that specific benchmark is synthetic (standard practice for latency/throughput testing, not requiring a live feed).

---

## Acknowledgements

Developed for learning and research purposes to understand the infrastructure behind modern electronic markets and quantitative trading systems.

Not affiliated with or endorsed by Optiver, Jane Street, IMC, Hudson River Trading, Tower Research, or any exchange.

---

## License

MIT License