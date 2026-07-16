# Quant Grafana Stack

Real Grafana + TimescaleDB, fully code-provisioned (no manual UI clicking).

## Setup

1. Copy this whole `grafana-stack/` folder into your project, e.g.
   `/mnt/c/Projects/market-decoder-optiver/grafana-stack/`

2. Start the stack (from inside `grafana-stack/`):
   ```bash
   docker compose up -d
   ```
   First boot runs `init-db/01_schema.sql` automatically (creates hypertables +
   seeds `pipeline_status`).

3. Open Grafana: http://localhost:3000
   Login: `admin` / `admin` (change it when prompted).
   You should immediately see **Quant Engineering / 01 - Executive Overview**
   in the left nav — it's auto-provisioned, not something you build by hand.

4. Load your real data:
   ```bash
   pip install pandas sqlalchemy psycopg2-binary
   python ingest/load_data.py --csv-dir /mnt/c/Projects/market-decoder-optiver/data
   ```
   This scans for CSVs matching common naming patterns (`*bars*.csv`,
   `*trade*.csv`, `*latency*.csv`, etc.) and loads them into the matching
   TimescaleDB table. **The column-name mappings in `load_data.py` are my
   best guess** — send me one sample row from each of your real CSVs and
   I'll fix the mappings exactly instead of guessing.

5. Refresh the Executive Overview dashboard — panels should populate.

## What's here

- `docker-compose.yml` — TimescaleDB + Grafana 11, dark theme by default.
- `init-db/01_schema.sql` — hypertables: `market_bars`, `trades`,
  `latency_samples`, `risk_events`, `backtest_equity`, `mm_quotes`,
  `pipeline_status`.
- `provisioning/` — datasource + dashboard auto-provisioning, so the whole
  stack is reproducible from git, not a manually-clicked Grafana instance.
- `dashboards/01_executive_overview.json` — first working dashboard: 15
  panels (KPI stats with sparklines + thresholds, PnL curve, latency trend,
  pipeline health), matching the "Page 1 — Executive Overview" spec.

## Next dashboards (not built yet — say the word and I'll generate them the same way)

- `02_market_analytics.json` — candlestick (Grafana's native candlestick
  panel), returns histogram, rolling volatility, monthly-return heatmap,
  correlation matrix.
- `03_latency_engineering.json` — P50/P90/P95/P99/P99.9 stat panels,
  latency heatmap, decoder comparison bar chart.
- `04_risk_analytics.json` — risk event timeline, risk heatmap, radar chart.
- `05_market_making.json` — Avellaneda-Stoikov params, quote skew, fill timeline.
- Pages 6–10 similarly.

Each one is a generated JSON file dropped into `dashboards/` — Grafana
picks it up automatically within ~10s (`updateIntervalSeconds: 10` in
`dashboards.yml`), no restart needed.
