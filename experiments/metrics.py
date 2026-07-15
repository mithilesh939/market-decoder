from strategy.backtest import BacktestResult


def extract_metrics(result: BacktestResult, params: dict) -> dict:
    """
    Convert one backtest result into a dictionary suitable
    for optimization and leaderboard generation.
    """

    pnl = result.final_pnl()

    fills = result.total_fills
    rejected = result.rejected_fills

    fill_rate = (
        fills / (fills + rejected)
        if (fills + rejected) > 0
        else 0.0
    )

    return {
        "gamma": params["gamma"],
        "kappa": params["kappa"],
        "quote_size": params["quote_size"],
        "inventory_limit": params["inventory_limit"],
        "pnl": pnl,
        "fills": fills,
        "rejected": rejected,
        "fill_rate": fill_rate,
    }