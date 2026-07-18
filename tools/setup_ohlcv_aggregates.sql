-- setup_ohlcv_aggregates.sql
-- Run: docker exec -i quant-timescaledb psql -U quant -d quant < setup_ohlcv_aggregates.sql
--
-- Creates fast, pre-computed OHLCV (open/high/low/close/volume) bars from the
-- 695M-row `trades` table so Grafana panels never scan raw rows. This is the
-- standard TimescaleDB pattern for dashboards over large trade tables.

-- ── 1-hour bars (for candlestick / intraday zoom) ──────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS trades_ohlcv_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    first(price, time)          AS open,
    max(price)                  AS high,
    min(price)                  AS low,
    last(price, time)           AS close,
    sum(qty)                    AS volume,
    count(*)                    AS trade_count,
    sum(price * qty) / NULLIF(sum(qty), 0) AS vwap
FROM trades
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('trades_ohlcv_1h',
    start_offset      => INTERVAL '3 days',
    end_offset         => INTERVAL '1 hour',
    schedule_interval  => INTERVAL '1 hour',
    if_not_exists      => true);

-- ── 1-day bars (for the full 6-month overview) ─────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS trades_ohlcv_1d
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol,
    first(price, time)         AS open,
    max(price)                 AS high,
    min(price)                 AS low,
    last(price, time)          AS close,
    sum(qty)                   AS volume,
    count(*)                   AS trade_count,
    sum(price * qty) / NULLIF(sum(qty), 0) AS vwap
FROM trades
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('trades_ohlcv_1d',
    start_offset      => INTERVAL '90 days',
    end_offset         => INTERVAL '1 day',
    schedule_interval  => INTERVAL '1 day',
    if_not_exists      => true);

-- ── Backfill both views across the full Jan-Jun 2025 history ──────────────
-- (one-time; the policies above only auto-refresh going forward)
CALL refresh_continuous_aggregate('trades_ohlcv_1h', '2025-01-01', '2025-07-01');
CALL refresh_continuous_aggregate('trades_ohlcv_1d', '2025-01-01', '2025-07-01');

-- ── Sanity check ────────────────────────────────────────────────────────
SELECT 'trades_ohlcv_1h' AS view, count(*) FROM trades_ohlcv_1h
UNION ALL
SELECT 'trades_ohlcv_1d', count(*) FROM trades_ohlcv_1d;