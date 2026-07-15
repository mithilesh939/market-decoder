
from __future__ import annotations
import csv, os, re, subprocess, sys
from dataclasses import dataclass
from typing import List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "python"))

from risk.order import Order, Side
from risk.price_collar import PriceCollarRule
from risk.order_size_limit import OrderSizeLimitRule
from risk.inventory import InventoryLimitRule, InventoryTracker
from risk.kill_switch import KillSwitchRule
from risk.engine import RiskEngine
from strategy.backtest import run_backtest, BacktestResult


@dataclass
class DecoderBenchmark:
    naive_ns_per_msg: float
    naive_msgs_per_sec: float
    mmap_ns_per_msg: float
    mmap_msgs_per_sec: float
    checksums_match: bool
    message_count: int
    speedup: float


def run_decoder_benchmark(data_file: str) -> DecoderBenchmark:
    binary = os.path.join(REPO_ROOT, "benchmark")
    if not os.path.exists(binary):
        raise FileNotFoundError(f"{binary} not found -- run `make benchmark` first")
    result = subprocess.run([binary, data_file], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"./benchmark failed: {result.stderr}")
    out = result.stdout
    naive_match = re.search(r"NaiveDecoder\s+messages=(\d+)\s+best=([\d.]+) ns/msg\s+\(~?([\d.]+)M msgs/sec\)\s+checksum=(\d+)", out)
    mmap_match = re.search(r"MmapDecoder\s+messages=(\d+)\s+best=([\d.]+) ns/msg\s+\(~?([\d.]+)M msgs/sec\)\s+checksum=(\d+)", out)
    if not naive_match or not mmap_match:
        raise RuntimeError(f"could not parse ./benchmark output:\n{out}")
    naive_ns, naive_mps, naive_checksum = float(naive_match[2]), float(naive_match[3]), naive_match[4]
    mmap_ns, mmap_mps, mmap_checksum = float(mmap_match[2]), float(mmap_match[3]), mmap_match[4]
    return DecoderBenchmark(
        naive_ns_per_msg=naive_ns, naive_msgs_per_sec=naive_mps * 1e6,
        mmap_ns_per_msg=mmap_ns, mmap_msgs_per_sec=mmap_mps * 1e6,
        checksums_match=(naive_checksum == mmap_checksum),
        message_count=int(naive_match[1]), speedup=naive_ns / mmap_ns,
    )


@dataclass
class ScaleTestResult:
    message_count: int
    decode_ms: float
    peak_rss_mb: float
    file_size_mb: float
    rss_curve_ms: List[float]
    rss_curve_mb: List[float]


def run_scale_test(data_file: str) -> ScaleTestResult:
    binary = os.path.join(REPO_ROOT, "bench_scale")
    if not os.path.exists(binary):
        raise FileNotFoundError(f"{binary} not found -- run `make bench_scale` first")
    csv_out = data_file + ".rss.csv"
    result = subprocess.run([binary, data_file, csv_out], capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"./bench_scale failed: {result.stderr}")
    out = result.stdout
    count_match = re.search(r"Decoded (\d+) messages", out)
    decode_ms_match = re.search(r"decode time:\s+([\d.]+) ms", out)
    rss_match = re.search(r"peak RSS:\s+([\d.]+) MB", out)
    if not (count_match and decode_ms_match and rss_match):
        raise RuntimeError(f"could not parse ./bench_scale output:\n{out}")
    rss_ms, rss_mb = [], []
    with open(csv_out) as f:
        for row in csv.DictReader(f):
            rss_ms.append(float(row["elapsed_ms"]))
            rss_mb.append(float(row["rss_kb"]) / 1024.0)
    return ScaleTestResult(
        message_count=int(count_match[1]), decode_ms=float(decode_ms_match[1]),
        peak_rss_mb=float(rss_match[1]), file_size_mb=os.path.getsize(data_file) / 1024.0 / 1024.0,
        rss_curve_ms=rss_ms, rss_curve_mb=rss_mb,
    )


@dataclass
class RiskEngineSummary:
    accepted: int
    rejected_by_rule: dict
    sample_decisions: list


def run_risk_engine_demo(current_price: float, symbol: str = "BTCUSDT") -> RiskEngineSummary:
    config = {symbol: {"price_collar_percent": 2.0, "max_order_size": 1.0, "max_inventory": 0.02}}
    tracker = InventoryTracker()
    kill_switch = KillSwitchRule()
    engine = RiskEngine([kill_switch, PriceCollarRule(config), OrderSizeLimitRule(config),
                         InventoryLimitRule(config, tracker)])
    test_orders = [
        Order(symbol, Side.BUY, current_price, 0.01),
        Order(symbol, Side.BUY, current_price * 1.01, 0.01),
        Order(symbol, Side.BUY, current_price * 1.05, 0.01),
        Order(symbol, Side.SELL, current_price * 0.90, 0.01),
        Order(symbol, Side.BUY, current_price, 5.0),
        Order(symbol, Side.SELL, current_price, 0.01),
    ]
    rejected_by_rule: dict = {}
    accepted = 0
    decisions = []
    for order in test_orders:
        decision = engine.evaluate(order, current_price=current_price)
        decisions.append(decision)
        if decision.accepted:
            accepted += 1
            tracker.apply_fill(order)
        else:
            rejected_by_rule[decision.rule_name] = rejected_by_rule.get(decision.rule_name, 0) + 1
    return RiskEngineSummary(accepted=accepted, rejected_by_rule=rejected_by_rule, sample_decisions=decisions)


def run_market_maker_backtest(data_file: str, **kwargs) -> BacktestResult:
    return run_backtest(data_file, **kwargs)
