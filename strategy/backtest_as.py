from __future__ import annotations
from dataclasses import dataclass, field
from time import perf_counter_ns
from analytics.regime import RegimeAnalyzer


from latency.profiler import LatencyProfiler
from analytics.tca import TCAReport, TradeCost


import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from market_decoder import decode_to_dataframes
from risk.order import Order, Side
from risk.price_collar import PriceCollarRule
from risk.order_size_limit import OrderSizeLimitRule
from risk.inventory_limit import InventoryLimitRule, InventoryTracker
from risk.kill_switch import KillSwitchRule
from risk.engine import RiskEngine
from strategy.backtest import BacktestPoint, BacktestResult
from strategy.avellaneda_stoikov import AvellanedaStoikovMarketMaker, convert_tick_volatility_to_price_volatility
from features.microstructure import compute_realized_volatility, compute_trade_intensity


def run_backtest_avellaneda_stoikov(
    bin_file_path: str,
    symbol: str = "BTCUSDT",
    gamma: float = 0.0005,
    kappa: float = 1.5,
    quote_size: float = 0.01,
    vol_window: int = 1000,
    risk_config: dict | None = None,
    verbose: bool = True,
) -> BacktestResult:
    dfs = decode_to_dataframes(bin_file_path)
    trades = dfs["trades"].sort_values("timestamp_ns").reset_index(drop=True)
    if len(trades) < vol_window + 2:
        raise ValueError(f"need at least {vol_window + 2} trades, got {len(trades)}")

    prices = (trades["price"] / 1_000_000).to_numpy()
    timestamps_ns = trades["timestamp_ns"].to_numpy()

    tick_vol = compute_realized_volatility(prices, vol_window).to_numpy()
    valid_vol = tick_vol[~np.isnan(tick_vol)]

    low_threshold = np.percentile(valid_vol, 33)
    high_threshold = np.percentile(valid_vol, 66)
    trade_intensity = compute_trade_intensity(timestamps_ns, vol_window).to_numpy()
    valid_vol = tick_vol[~np.isnan(tick_vol)]

    low_threshold = np.percentile(valid_vol, 33)
    high_threshold = np.percentile(valid_vol, 66)

    print("\nVolatility thresholds")
    print(f"Low    < {low_threshold:.6f}")
    print(f"Medium < {high_threshold:.6f}")
    print(f"High   >= {high_threshold:.6f}")
    session_duration_s = float(timestamps_ns[-1] - timestamps_ns[0]) / 1e9
    start_ts = int(timestamps_ns[0])

    if risk_config is None:
        risk_config = {symbol: {"price_collar_percent": 2.0, "max_order_size": 1.0, "max_inventory": 0.5}}

    maker = AvellanedaStoikovMarketMaker(gamma, kappa, session_duration_s, quote_size)
    tracker = InventoryTracker()
    kill_switch = KillSwitchRule()
    engine = RiskEngine([kill_switch, PriceCollarRule(risk_config), OrderSizeLimitRule(risk_config),
                         InventoryLimitRule(risk_config, tracker)])

    result = BacktestResult()
    tca = TCAReport()
    regimes = RegimeAnalyzer()
    profiler = LatencyProfiler()
    buy_fills = 0
    sell_fills = 0


    
    cash = 0.0
    fair_value = float(prices[0])
    last_mtm_pnl = 0.0 
    loop_start = perf_counter_ns()

    for i in range(1, len(prices)):
        loop_start = perf_counter_ns()
        trade_price = float(prices[i])
        timestamp_ns = int(timestamps_ns[i])

        raw_tick_vol = tick_vol[i - 1]
        intensity = trade_intensity[i - 1]

        if np.isnan(raw_tick_vol) or np.isnan(intensity) or intensity <= 0:
            fair_value = trade_price
            continue

        elapsed_s = (timestamp_ns - start_ts) / 1e9
        price_vol = convert_tick_volatility_to_price_volatility(raw_tick_vol, fair_value, intensity)
        quote_start = perf_counter_ns()
        quote = maker.generate_quote(
            fair_value,
            tracker.position(symbol),
            price_vol,
            elapsed_s,
        )
        sigma = raw_tick_vol
        regime = regimes.bucket(
            raw_tick_vol,
            low_threshold,
            high_threshold,
        )

        profiler.stage("Quote").measure(quote_start)
        
        fill_side = ""
        fill_rejected_reason = ""

        if trade_price >= quote.ask_price:

            order = Order(symbol, Side.SELL, quote.ask_price, quote.ask_size)

            risk_start = perf_counter_ns()
            decision = engine.evaluate(order, current_price=fair_value)
            profiler.stage("Risk").measure(risk_start)

            if decision.accepted:

                tracker.apply_fill(order)

                fee = quote.ask_price * quote.ask_size * 0.0004
                cash += quote.ask_price * quote.ask_size - fee

                tca.add(
                    TradeCost(
                        side="SELL",
                        fill_price=quote.ask_price,
                        fair_price=fair_value,
                        quantity=quote.ask_size,
                        spread=quote.ask_price - quote.bid_price,
                    )
                )

                if verbose and result.total_fills == 0:
                    print("\nFIRST SELL")
                    print("fair:", fair_value)
                    print("fill:", quote.ask_price)
                    print("qty :", quote.ask_size)

                fill_side = "SELL"
                sell_fills += 1
                result.total_fills += 1

            else:

                fill_rejected_reason = decision.reason
                result.rejected_fills += 1

        elif trade_price <= quote.bid_price:

            order = Order(symbol, Side.BUY, quote.bid_price, quote.bid_size)

            risk_start = perf_counter_ns()
            decision = engine.evaluate(order, current_price=fair_value)
            profiler.stage("Risk").measure(risk_start)

            if decision.accepted:

                tracker.apply_fill(order)

                fee = quote.bid_price * quote.bid_size * 0.0004
                cash -= quote.bid_price * quote.bid_size + fee

                tca.add(
                    TradeCost(
                        side="BUY",
                        fill_price=quote.bid_price,
                        fair_price=fair_value,
                        quantity=quote.bid_size,
                        spread=quote.ask_price - quote.bid_price,
                    )
                )

                if verbose and result.total_fills == 0:
                    print("\nFIRST BUY")
                    print("fair:", fair_value)
                    print("fill:", quote.bid_price)
                    print("qty :", quote.bid_size)

                fill_side = "BUY"
                buy_fills += 1
                result.total_fills += 1

            else:

                fill_rejected_reason = decision.reason
                result.rejected_fills += 1

        #

        fair_value = trade_price

        inventory = tracker.position(symbol)
        mtm_pnl = cash + inventory * fair_value

        pnl_delta = mtm_pnl - last_mtm_pnl
        last_mtm_pnl = mtm_pnl
        submitted = (
            trade_price >= quote.ask_price or
            trade_price <= quote.bid_price
        )

        regime.update(
            pnl_delta=pnl_delta,
            inventory=inventory,
            rejected=1 if fill_rejected_reason else 0,
            submitted=submitted,
            filled=bool(fill_side),
        )

        result.points.append(
            BacktestPoint(
                tick=i,
                timestamp_ns=timestamp_ns,
                trade_price=trade_price,
                fair_value=fair_value,
                inventory=inventory,
                cash=cash,
                mark_to_market_pnl=mtm_pnl,
                our_bid=quote.bid_price,
                our_ask=quote.ask_price,
                fill_side=fill_side,
                fill_rejected_reason=fill_rejected_reason,
            )
        )

        profiler.stage("Tick").measure(loop_start)

    for i in range(1, len(prices)):
        loop_start = perf_counter_ns()
        trade_price = float(prices[i])
        timestamp_ns = int(timestamps_ns[i])

        raw_tick_vol = tick_vol[i - 1]
        intensity = trade_intensity[i - 1]

        if np.isnan(raw_tick_vol) or np.isnan(intensity) or intensity <= 0:
            fair_value = trade_price
            continue

        elapsed_s = (timestamp_ns - start_ts) / 1e9
        price_vol = convert_tick_volatility_to_price_volatility(raw_tick_vol, fair_value, intensity)
        quote_start = perf_counter_ns()
        quote = maker.generate_quote(
            fair_value,
            tracker.position(symbol),
            price_vol,
            elapsed_s,
        )
        sigma = raw_tick_vol
        regime = regimes.bucket(
            raw_tick_vol,
            low_threshold,
            high_threshold,
        )

        profiler.stage("Quote").measure(quote_start)
        
        fill_side = ""
        fill_rejected_reason = ""

        if trade_price >= quote.ask_price:

            order = Order(symbol, Side.SELL, quote.ask_price, quote.ask_size)

            risk_start = perf_counter_ns()
            decision = engine.evaluate(order, current_price=fair_value)
            profiler.stage("Risk").measure(risk_start)

            if decision.accepted:

                tracker.apply_fill(order)

                fee = quote.ask_price * quote.ask_size * 0.0004
                cash += quote.ask_price * quote.ask_size - fee

                tca.add(
                    TradeCost(
                        side="SELL",
                        fill_price=quote.ask_price,
                        fair_price=fair_value,
                        quantity=quote.ask_size,
                        spread=quote.ask_price - quote.bid_price,
                    )
                )

                if verbose and result.total_fills == 0:
                    print("\nFIRST SELL")
                    print("fair:", fair_value)
                    print("fill:", quote.ask_price)
                    print("qty :", quote.ask_size)

                fill_side = "SELL"
                sell_fills += 1
                result.total_fills += 1

            else:

                fill_rejected_reason = decision.reason
                result.rejected_fills += 1

        elif trade_price <= quote.bid_price:

            order = Order(symbol, Side.BUY, quote.bid_price, quote.bid_size)

            risk_start = perf_counter_ns()
            decision = engine.evaluate(order, current_price=fair_value)
            profiler.stage("Risk").measure(risk_start)

            if decision.accepted:

                tracker.apply_fill(order)

                fee = quote.bid_price * quote.bid_size * 0.0004
                cash -= quote.bid_price * quote.bid_size + fee

                tca.add(
                    TradeCost(
                        side="BUY",
                        fill_price=quote.bid_price,
                        fair_price=fair_value,
                        quantity=quote.bid_size,
                        spread=quote.ask_price - quote.bid_price,
                    )
                )

                if verbose and result.total_fills == 0:
                    print("\nFIRST BUY")
                    print("fair:", fair_value)
                    print("fill:", quote.bid_price)
                    print("qty :", quote.bid_size)

                fill_side = "BUY"
                buy_fills += 1
                result.total_fills += 1

            else:

                fill_rejected_reason = decision.reason
                result.rejected_fills += 1

        #

        fair_value = trade_price

        inventory = tracker.position(symbol)
        mtm_pnl = cash + inventory * fair_value

        pnl_delta = mtm_pnl - last_mtm_pnl
        last_mtm_pnl = mtm_pnl
        submitted = (
            trade_price >= quote.ask_price or
            trade_price <= quote.bid_price
        )

        regime.update(
            pnl_delta=pnl_delta,
            inventory=inventory,
            rejected=1 if fill_rejected_reason else 0,
            submitted=submitted,
            filled=bool(fill_side),
        )

        result.points.append(
            BacktestPoint(
                tick=i,
                timestamp_ns=timestamp_ns,
                trade_price=trade_price,
                fair_value=fair_value,
                inventory=inventory,
                cash=cash,
                mark_to_market_pnl=mtm_pnl,
                our_bid=quote.bid_price,
                our_ask=quote.ask_price,
                fill_side=fill_side,
                fill_rejected_reason=fill_rejected_reason,
            )
        )

        profiler.stage("Tick").measure(loop_start)
    if verbose:

        profiler.report()

        print("\n" + "=" * 80)
        print("TRANSACTION COST ANALYSIS")
        print("=" * 80)

        summary = tca.summary()

        for k, v in summary.items():
            print(f"{k:30s}: {v}")

        print("\n" + "=" * 80)
        print("REGIME ANALYSIS")
        print("=" * 80)

        for r in [regimes.low, regimes.medium, regimes.high]:
            fill_rate = (
                100.0 * r.fills / r.submitted_orders
                if r.submitted_orders else 0.0
            )

            print(
                f"{r.name:10s} | "
                f"Ticks={r.observations:7d} | "
                f"Submitted={r.submitted_orders:5d} | "
                f"Executed={r.fills:5d} | "
                f"FillRate={fill_rate:6.2f}% | "
                f"PnL={r.pnl:10.2f} | "
                f"AvgInv={r.avg_inventory:7.4f} | "
                f"Rejected={r.rejected:5d}"
           )

        print("\n" + "=" * 80)
        print("FILL SUMMARY")
        print("=" * 80)
        print("BUY :", buy_fills)
        print("SELL:", sell_fills)
        print("TOTAL:", buy_fills + sell_fills)

    return result       