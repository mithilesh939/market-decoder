-- Runs automatically on first container start (docker-entrypoint-initdb.d)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- MARKET DATA: OHLCV bars (Page 2 - Market Analytics)
-- ============================================================
CREATE TABLE market_bars (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      DOUBLE PRECISION,
    vwap        DOUBLE PRECISION
);
SELECT create_hypertable('market_bars', 'time');
CREATE INDEX ON market_bars (symbol, time DESC);

-- ============================================================
-- TRADES: executed trades / fills (Page 1, 7 - Exec KPIs, Backtesting)
-- ============================================================
CREATE TABLE trades (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT,              -- 'buy' | 'sell'
    price       DOUBLE PRECISION,
    qty         DOUBLE PRECISION,
    pnl         DOUBLE PRECISION,
    strategy    TEXT
);
SELECT create_hypertable('trades', 'time');
CREATE INDEX ON trades (symbol, time DESC);

-- ============================================================
-- LATENCY SAMPLES: decoder latency measurements (Page 3 - Latency Engineering)
-- ============================================================
CREATE TABLE latency_samples (
    time            TIMESTAMPTZ NOT NULL,
    decoder_type    TEXT,          -- 'naive' | 'mmap' | 'simd'
    latency_ns      DOUBLE PRECISION,
    cpu_pct         DOUBLE PRECISION,
    cache_misses    BIGINT,
    branch_mispred  BIGINT,
    context_switches BIGINT
);
SELECT create_hypertable('latency_samples', 'time');
CREATE INDEX ON latency_samples (decoder_type, time DESC);

-- ============================================================
-- RISK EVENTS: kill switch, collar breaches, limit violations (Page 4 - Risk Analytics)
-- ============================================================
CREATE TABLE risk_events (
    time        TIMESTAMPTZ NOT NULL,
    event_type  TEXT,              -- 'price_collar' | 'inventory_limit' | 'kill_switch' | 'rejected_order'
    symbol      TEXT,
    severity    TEXT,              -- 'low' | 'medium' | 'high'
    details     TEXT
);
SELECT create_hypertable('risk_events', 'time');
CREATE INDEX ON risk_events (event_type, time DESC);

-- ============================================================
-- BACKTEST EQUITY: equity curve / rolling stats (Page 7 - Backtesting)
-- ============================================================
CREATE TABLE backtest_equity (
    time            TIMESTAMPTZ NOT NULL,
    strategy        TEXT,
    equity          DOUBLE PRECISION,
    drawdown        DOUBLE PRECISION,
    rolling_sharpe  DOUBLE PRECISION
);
SELECT create_hypertable('backtest_equity', 'time');
CREATE INDEX ON backtest_equity (strategy, time DESC);

-- ============================================================
-- MARKET MAKING QUOTES: Avellaneda-Stoikov outputs (Page 5 - Market Making)
-- ============================================================
CREATE TABLE mm_quotes (
    time                TIMESTAMPTZ NOT NULL,
    symbol              TEXT,
    reservation_price   DOUBLE PRECISION,
    optimal_spread      DOUBLE PRECISION,
    bid                 DOUBLE PRECISION,
    ask                 DOUBLE PRECISION,
    inventory           DOUBLE PRECISION,
    fill_rate           DOUBLE PRECISION
);
SELECT create_hypertable('mm_quotes', 'time');
CREATE INDEX ON mm_quotes (symbol, time DESC);

-- ============================================================
-- PIPELINE STATUS: dataset/pipeline health (Page 8 - Dataset Analytics, Page 1 KPI)
-- ============================================================
CREATE TABLE pipeline_status (
    stage       TEXT PRIMARY KEY,
    status      TEXT,              -- 'completed' | 'running' | 'failed'
    updated_at  TIMESTAMPTZ DEFAULT now(),
    detail      TEXT
);

-- ============================================================
-- Seed pipeline_status so the Executive Overview dashboard has something to show immediately
-- ============================================================
INSERT INTO pipeline_status (stage, status, detail) VALUES
    ('csv_discovery', 'completed', '6 monthly CSVs detected'),
    ('csv_parsing',   'completed', '18 rows loaded'),
    ('aggregation',   'completed', 'Monthly summary built'),
    ('chart_rendering','completed', 'Dashboards rendered')
ON CONFLICT (stage) DO NOTHING;
