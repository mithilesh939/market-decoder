"""
Runs a hyperparameter search over the
Avellaneda-Stoikov market maker.
"""

import os
import sys
import csv
from time import perf_counter

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.parameter_grid import parameter_grid
from experiments.metrics import extract_metrics
from strategy.backtest_as import run_backtest_avellaneda_stoikov


DATASET = "tools/btcusdt_backtest_slice.bin"


def main():

    results = []

    params_list = list(parameter_grid())
    total = len(params_list)

    print("=" * 70)
    print("AVELLANEDA-STOIKOV HYPERPARAMETER OPTIMIZATION")
    print("=" * 70)
    print(f"Total parameter sets: {total}\n")

    overall_start = perf_counter()

    for i, params in enumerate(params_list, start=1):

        print(
            f"[{i:3d}/{total}] "
            f"gamma={params['gamma']:<7} "
            f"kappa={params['kappa']:<4} "
            f"quote={params['quote_size']:<6} "
            f"inv={params['inventory_limit']}"
        )

        risk_config = {
            "BTCUSDT": {
                "price_collar_percent": 2.0,
                "max_order_size": 1.0,
                "max_inventory": params["inventory_limit"],
            }
        }

        result = run_backtest_avellaneda_stoikov(
            DATASET,
            gamma=params["gamma"],
            kappa=params["kappa"],
            quote_size=params["quote_size"],
            risk_config=risk_config,
            verbose=False,
)

        results.append(
            extract_metrics(result, params)
        )

    elapsed = perf_counter() - overall_start

    results.sort(
        key=lambda x: x["pnl"],
        reverse=True,
    )

    output = "results/optimization/leaderboard.csv"

    with open(output, "w", newline="") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=results[0].keys(),
        )

        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 70)
    print("Optimization Complete")
    print("=" * 70)
    print(f"Experiments : {total}")
    print(f"Runtime     : {elapsed:.2f} sec")
    print(f"Leaderboard : {output}")

    print("\nBest Strategy\n")

    best = results[0]

    for k, v in best.items():
        print(f"{k:18s}: {v}")


if __name__ == "__main__":
    main()