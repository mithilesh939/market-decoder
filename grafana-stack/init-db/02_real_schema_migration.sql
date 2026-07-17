-- ============================================================
-- Market Decoder Optiver
-- Database Migration v2
-- Safe to run multiple times
-- ============================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

---------------------------------------------------------------
-- Price Series
---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_series (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL DEFAULT 'BTCUSDT',
    price DOUBLE PRECISION,
    volume DOUBLE PRECISION
);

SELECT create_hypertable(
    'price_series',
    'time',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS price_series_symbol_time_idx
ON price_series(symbol, time DESC);

---------------------------------------------------------------
-- Monthly Statistics
---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monthly_stats (

    month TEXT PRIMARY KEY,

    records BIGINT,

    avg_price DOUBLE PRECISION,

    total_volume DOUBLE PRECISION,

    price_change_pct DOUBLE PRECISION,

    volatility DOUBLE PRECISION,

    last_price DOUBLE PRECISION,

    vwap DOUBLE PRECISION,

    win_rate DOUBLE PRECISION,

    max_drawdown DOUBLE PRECISION
);

---------------------------------------------------------------
-- Latency Samples V2
---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS latency_samples_v2 (

    time TIMESTAMPTZ NOT NULL,

    metric_type TEXT NOT NULL,

    sample_id BIGINT,

    latency_ns DOUBLE PRECISION
);

SELECT create_hypertable(
    'latency_samples_v2',
    'time',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS latency_v2_type_time_idx
ON latency_samples_v2(metric_type,time DESC);

---------------------------------------------------------------
-- Market Making Optimization Runs
---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mm_optimization_runs (

    id SERIAL PRIMARY KEY,

    gamma DOUBLE PRECISION,

    kappa DOUBLE PRECISION,

    quote_size DOUBLE PRECISION,

    inventory_limit DOUBLE PRECISION,

    pnl DOUBLE PRECISION,

    fills INTEGER,

    rejected INTEGER,

    fill_rate DOUBLE PRECISION,

    loaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mm_opt_pnl_idx
ON mm_optimization_runs(pnl DESC);

---------------------------------------------------------------
-- System Metrics
---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_metrics(

    time TIMESTAMPTZ NOT NULL,

    cpu_pct DOUBLE PRECISION,

    memory_pct DOUBLE PRECISION,

    decoder_msgs_per_sec DOUBLE PRECISION,

    decoder_latency_ns DOUBLE PRECISION
);

SELECT create_hypertable(
    'system_metrics',
    'time',
    if_not_exists => TRUE
);

---------------------------------------------------------------
-- Dashboard Metadata
---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dashboard_metadata(

    key TEXT PRIMARY KEY,

    value TEXT
);

INSERT INTO dashboard_metadata(key,value)
VALUES
('project','Market Decoder Optiver'),
('version','2.0'),
('dashboard','Professional Quant Dashboard')
ON CONFLICT DO NOTHING;

