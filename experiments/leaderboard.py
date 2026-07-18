

import csv


def load_results(path):

    rows = []

    with open(path, newline="") as f:

        reader = csv.DictReader(f)

        for row in reader:

            row["pnl"] = float(row["pnl"])
            row["fills"] = int(row["fills"])
            row["rejected"] = int(row["rejected"])
            row["fill_rate"] = float(row["fill_rate"])

            rows.append(row)

    return rows


def main():

    results = load_results(
        "results/optimization/leaderboard.csv"
    )

    results.sort(
        key=lambda x: x["pnl"],
        reverse=True,
    )

    print("=" * 90)
    print("TOP 10 STRATEGIES")
    print("=" * 90)

    print(
        f"{'Rank':<6}"
        f"{'PnL':>12}"
        f"{'Gamma':>10}"
        f"{'Kappa':>10}"
        f"{'Quote':>10}"
        f"{'Inv':>10}"
        f"{'Fills':>10}"
    )

    print("-" * 90)

    for rank, r in enumerate(results[:10], start=1):

        print(
            f"{rank:<6}"
            f"{r['pnl']:>12.2f}"
            f"{float(r['gamma']):>10.4f}"
            f"{float(r['kappa']):>10.2f}"
            f"{float(r['quote_size']):>10.3f}"
            f"{float(r['inventory_limit']):>10.2f}"
            f"{r['fills']:>10d}"
        )

    print("=" * 90)

    pnl = [r["pnl"] for r in results]

    print(f"Strategies : {len(results)}")
    print(f"Best PnL   : {max(pnl):.2f}")
    print(f"Worst PnL  : {min(pnl):.2f}")
    print(f"Average    : {sum(pnl)/len(pnl):.2f}")


if __name__ == "__main__":
    main()
