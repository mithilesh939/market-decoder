from pathlib import Path
from datetime import datetime, timedelta
import traceback

import pandas as pd
from sqlalchemy import create_engine, text

DB = "postgresql+psycopg2://quant:quant_dev_password@localhost:5432/quant"

ROOT = Path("/mnt/c/Projects/market-decoder-optiver")

LATENCY = ROOT / "results" / "latency"
OPT = ROOT / "results" / "optimization"

print("=" * 60, flush=True)
print("STARTING INGESTION", flush=True)
print("=" * 60, flush=True)

print(f"Project Root : {ROOT}", flush=True)
print(f"Latency Path : {LATENCY}", flush=True)
print(f"Opt Path     : {OPT}", flush=True)

print("\nChecking files...", flush=True)

for f in [
    LATENCY / "tick_latency.csv",
    LATENCY / "quote_latency.csv",
    LATENCY / "risk_latency.csv",
    OPT / "leaderboard.csv",
]:
    print(f"{f} -> {'FOUND' if f.exists() else 'MISSING'}", flush=True)

print("\nCreating database engine...", flush=True)

engine = create_engine(
    DB,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

print("Opening database connection...", flush=True)

try:

    with engine.begin() as conn:

        print("✓ Database connected", flush=True)

        print("Truncating latency_samples_v2...", flush=True)
        conn.execute(text("TRUNCATE TABLE latency_samples_v2;"))
        print("✓ latency_samples_v2 truncated", flush=True)

        print("Truncating mm_optimization_runs...", flush=True)
        conn.execute(text("TRUNCATE TABLE mm_optimization_runs RESTART IDENTITY;"))
        print("✓ mm_optimization_runs truncated", flush=True)

        files = [
            ("tick_latency.csv", "tick"),
            ("quote_latency.csv", "quote"),
            ("risk_latency.csv", "risk"),
        ]

        base = datetime.utcnow()
        total = 0

        for filename, metric in files:

            print(f"\nLoading {filename}...", flush=True)

            df = pd.read_csv(LATENCY / filename)

            print(f"Rows: {len(df)}", flush=True)

            df["metric_type"] = metric

            df["time"] = [
                base + timedelta(microseconds=i)
                for i in range(len(df))
            ]

            df = df[
                [
                    "time",
                    "metric_type",
                    "sample_id",
                    "latency_ns",
                ]
            ]

            print("Writing to latency_samples_v2...", flush=True)

            df.to_sql(
                "latency_samples_v2",
                con=conn,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=5000,
            )

            print(f"✓ Imported {len(df)} rows", flush=True)

            total += len(df)

        print("\nLoading leaderboard...", flush=True)

        leaderboard = pd.read_csv(
            OPT / "leaderboard.csv"
        )

        print(f"Rows: {len(leaderboard)}", flush=True)

        leaderboard.to_sql(
            "mm_optimization_runs",
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=5000,
        )

        print("✓ Optimization imported", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("INGESTION COMPLETE", flush=True)
    print("=" * 60, flush=True)
    print(f"Latency rows      : {total}", flush=True)
    print(f"Optimization rows : {len(leaderboard)}", flush=True)

except Exception as e:

    print("\nERROR OCCURRED", flush=True)
    print(type(e).__name__, flush=True)
    print(e, flush=True)

    traceback.print_exc()