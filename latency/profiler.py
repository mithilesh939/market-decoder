from pathlib import Path
import csv

from dataclasses import dataclass, field
from time import perf_counter_ns
import numpy as np


@dataclass
class StageProfiler:
    name: str
    samples: list[int] = field(default_factory=list)

    def measure(self, start_ns: int):
        self.samples.append(perf_counter_ns() - start_ns)

    def summary(self):
        if not self.samples:
            return None

        x = np.asarray(self.samples, dtype=np.float64)

        return {
            "count": len(x),
            "avg": float(np.mean(x)),
            "min": float(np.min(x)),
            "p50": float(np.percentile(x, 50)),
            "p95": float(np.percentile(x, 95)),
            "p99": float(np.percentile(x, 99)),
            "p999": float(np.percentile(x, 99.9)),
            "max": float(np.max(x)),
        }


class LatencyProfiler:

    def __init__(self):
        self.stages = {}

    def stage(self, name: str):
        if name not in self.stages:
            self.stages[name] = StageProfiler(name)
        return self.stages[name]

    def report(self):

        print()
        print("=" * 90)
        print("LATENCY PROFILE")
        print("=" * 90)

        header = (
            f"{'Stage':15}"
            f"{'Avg(ns)':>12}"
            f"{'P50':>12}"
            f"{'P95':>12}"
            f"{'P99':>12}"
            f"{'P99.9':>12}"
            f"{'Max':>12}"
        )

        print(header)
        print("-" * len(header))

        for stage in self.stages.values():

            s = stage.summary()

            if s is None:
                continue

            print(
                f"{stage.name:15}"
                f"{s['avg']:12.1f}"
                f"{s['p50']:12.1f}"
                f"{s['p95']:12.1f}"
                f"{s['p99']:12.1f}"
                f"{s['p999']:12.1f}"
                f"{s['max']:12.1f}"
            )

        print("=" * 90)

        self.export_csv()

    def export_csv(self, output_dir="results/latency"):

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for stage in self.stages.values():

            file = out / f"{stage.name.lower()}_latency.csv"

            with open(file, "w", newline="") as f:

                writer = csv.writer(f)
                writer.writerow(["sample_id", "latency_ns"])

                for i, value in enumerate(stage.samples):
                    writer.writerow([i, value])

        print(f"\nLatency samples exported to {out.resolve()}")