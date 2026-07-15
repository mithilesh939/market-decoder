
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from features.microstructure import (
    compute_vwap, compute_realized_volatility, compute_trade_intensity,
    classify_trade_side_tick_rule, compute_trade_imbalance,
    compute_microprice, compute_queue_imbalance,
)


def test_vwap_matches_hand_computation():
    print("running: VWAP matches hand-computed value ... ", end="")
    prices = np.array([100.0, 200.0, 100.0])
    qtys = np.array([1.0, 1.0, 2.0])
    vwap = compute_vwap(prices, qtys, window=3)
    expected = (100 * 1 + 200 * 1 + 100 * 2) / (1 + 1 + 2)
    assert abs(vwap.iloc[-1] - expected) < 1e-9
    print("PASS")


def test_tick_rule_classification():
    print("running: tick rule matches manual classification ... ", end="")
    prices = np.array([100.0, 105.0, 102.0, 108.0, 108.0])
    sides = classify_trade_side_tick_rule(prices)
    assert sides.tolist() == [0, 1, -1, 1, 0]
    print("PASS")


def test_realized_volatility_known_series():
    print("running: realized volatility matches known return series ... ", end="")
    r = 0.01
    p = [100.0, 100 * np.exp(r), 100 * np.exp(r) * np.exp(-r)]
    vol = compute_realized_volatility(np.array(p), window=2)
    expected_std = np.std([0.01, -0.01], ddof=1)
    assert abs(vol.iloc[-1] - expected_std) < 1e-9
    print("PASS")


def test_trade_imbalance_all_buys():
    print("running: monotonic uptick series gives imbalance = +1.0 ... ", end="")
    prices = np.array([100.0, 101.0, 102.0, 103.0])
    qtys = np.array([1.0, 1.0, 1.0, 1.0])
    imb = compute_trade_imbalance(prices, qtys, window=4)
    assert abs(imb.iloc[-1] - 1.0) < 1e-9
    print("PASS")


def test_trade_imbalance_all_sells():
    print("running: monotonic downtick series gives imbalance = -1.0 ... ", end="")
    prices = np.array([103.0, 102.0, 101.0, 100.0])
    qtys = np.array([1.0, 1.0, 1.0, 1.0])
    imb = compute_trade_imbalance(prices, qtys, window=4)
    assert abs(imb.iloc[-1] - (-1.0)) < 1e-9
    print("PASS")


def test_microprice_pulls_toward_thin_side():
    print("running: microprice pulls toward the thinner side ... ", end="")
    mp = compute_microprice(bid_price=100, ask_price=101, bid_size=10, ask_size=1)
    expected = (100 * 1 + 101 * 10) / 11
    assert abs(mp - expected) < 1e-9
    assert mp > 100.5, "thin ask side should pull microprice above plain mid"
    print("PASS")


def test_microprice_symmetric_book_equals_mid():
    print("running: symmetric book gives microprice == plain mid ... ", end="")
    mp = compute_microprice(bid_price=100, ask_price=102, bid_size=5, ask_size=5)
    assert abs(mp - 101.0) < 1e-9
    print("PASS")


def test_queue_imbalance():
    print("running: queue imbalance matches hand computation ... ", end="")
    qi = compute_queue_imbalance(bid_size=30, ask_size=10)
    assert abs(qi - 0.5) < 1e-9
    print("PASS")


def test_microprice_rejects_zero_total_size():
    print("running: microprice rejects zero total size ... ", end="")
    try:
        compute_microprice(bid_price=100, ask_price=101, bid_size=0, ask_size=0)
        assert False, "expected ValueError"
    except ValueError:
        pass
    print("PASS")


def main():
    tests = [
        test_vwap_matches_hand_computation, test_tick_rule_classification,
        test_realized_volatility_known_series, test_trade_imbalance_all_buys,
        test_trade_imbalance_all_sells, test_microprice_pulls_toward_thin_side,
        test_microprice_symmetric_book_equals_mid, test_queue_imbalance,
        test_microprice_rejects_zero_total_size,
    ]
    for t in tests:
        t()
    print("\nAll feature engine tests passed.")


if __name__ == "__main__":
    main()
