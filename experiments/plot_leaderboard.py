import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("results/optimization/leaderboard.csv")

df = df.sort_values("pnl", ascending=False)

plt.figure(figsize=(12,6))
plt.bar(range(len(df)), df["pnl"])
plt.xlabel("Strategy Rank")
plt.ylabel("PnL")
plt.title("Hyperparameter Optimization Results")
plt.tight_layout()

plt.savefig("results/optimization/pnl_ranking.png", dpi=200)

print("Saved results/optimization/pnl_ranking.png")