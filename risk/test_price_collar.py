"""
test_price_collar.py

Plain assert-based tests targeting specific behavioral edge cases, not
just "does it run." Run: python3 risk/test_price_collar.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from risk.order import Order, Side
from risk.price_collar import PriceCollarRule, RuleResult
from risk.engine import RiskEngine


CONFIG = {"BTCUSDT": {"price_collar_percent": 2.0}}


def test_order_far_outside_collar_rejected():
    print("running: order far outside collar is rejected ... ", end="")
    rule = PriceCollarRule(CONFIG)
    result = rule.check(Order("BTCUSDT", Side.BUY, 70000, 1), current_price=64200)
    assert not result.accepted
    assert result.details["lower"] == 64200 * 0.98
    assert result.details["upper"] == 64200 * 1.02
    print("PASS")


def test_order_within_collar_accepted():
    print("running: order within collar is accepted ... ", end="")
    rule = PriceCollarRule(CONFIG)
    result = rule.check(Order("BTCUSDT", Side.BUY, 64220, 2), current_price=64200)
    assert result.accepted
    print("PASS")


def test_boundary_is_inclusive():
    """Spec says lower <= price <= upper -- exactly AT the boundary must
    be accepted, not rejected. Classic off-by-one that would silently
    reject valid orders in production."""
    print("running: exact boundary prices are accepted (inclusive) ... ", end="")
    rule = PriceCollarRule(CONFIG)
    current_price = 64200
    upper, lower = current_price * 1.02, current_price * 0.98
    assert rule.check(Order("BTCUSDT", Side.BUY, upper, 1), current_price).accepted
    assert rule.check(Order("BTCUSDT", Side.SELL, lower, 1), current_price).accepted
    print("PASS")


def test_just_outside_boundary_rejected():
    print("running: one cent outside boundary is rejected ... ", end="")
    rule = PriceCollarRule(CONFIG)
    upper = 64200 * 1.02
    result = rule.check(Order("BTCUSDT", Side.BUY, upper + 0.01, 1), 64200)
    assert not result.accepted
    print("PASS")


def test_side_does_not_affect_collar():
    """The collar is symmetric regardless of BUY vs SELL -- a rule that
    accidentally only checked one side would be a real, dangerous bug."""
    print("running: BUY and SELL are checked identically ... ", end="")
    rule = PriceCollarRule(CONFIG)
    buy = rule.check(Order("BTCUSDT", Side.BUY, 70000, 1), 64200)
    sell = rule.check(Order("BTCUSDT", Side.SELL, 70000, 1), 64200)
    assert buy.accepted == sell.accepted == False
    print("PASS")


def test_missing_symbol_raises_not_silently_passes():
    """A missing config entry must be a loud failure, not a silent
    'no limit' -- that's exactly the kind of silent gap that causes
    real incidents."""
    print("running: missing symbol config raises, doesn't silently pass ... ", end="")
    rule = PriceCollarRule(CONFIG)
    try:
        rule.check(Order("DOGEUSDT", Side.BUY, 1.0, 1), current_price=0.5)
        assert False, "expected KeyError for unconfigured symbol"
    except KeyError:
        pass
    print("PASS")


def test_invalid_order_construction_rejected():
    print("running: zero/negative price or quantity rejected at construction ... ", end="")
    try:
        Order("BTCUSDT", Side.BUY, price=0, quantity=1)
        assert False
    except ValueError:
        pass
    try:
        Order("BTCUSDT", Side.BUY, price=100, quantity=-1)
        assert False
    except ValueError:
        pass
    print("PASS")


def test_invalid_current_price_rejected():
    print("running: zero/negative current_price rejected ... ", end="")
    rule = PriceCollarRule(CONFIG)
    try:
        rule.check(Order("BTCUSDT", Side.BUY, 100, 1), current_price=0)
        assert False
    except ValueError:
        pass
    print("PASS")


def test_engine_fail_fast_stops_at_first_rejection():
    """With two rules where the first rejects, the second must NEVER
    even be evaluated -- this is what makes fail-fast actually fail-fast."""
    print("running: engine stops at first rejecting rule (fail-fast) ... ", end="")

    class AlwaysRejectRule:
        def __init__(self):
            self.was_called = False
        def check(self, order, current_price):
            self.was_called = True
            return RuleResult(False, "always rejects", {})

    never_reached = AlwaysRejectRule()
    engine = RiskEngine([PriceCollarRule(CONFIG), never_reached])
    decision = engine.evaluate(Order("BTCUSDT", Side.BUY, 70000, 1), current_price=64200)

    assert not decision.accepted
    assert decision.rule_name == "PriceCollarRule"
    assert not never_reached.was_called, "second rule should never run after first rejects"
    print("PASS")


def test_engine_decision_log_accumulates():
    print("running: engine decision_log records every evaluation ... ", end="")
    engine = RiskEngine([PriceCollarRule(CONFIG)])
    engine.evaluate(Order("BTCUSDT", Side.BUY, 64220, 1), 64200)
    engine.evaluate(Order("BTCUSDT", Side.BUY, 70000, 1), 64200)
    assert len(engine.decision_log) == 2
    assert engine.decision_log[0].accepted
    assert not engine.decision_log[1].accepted
    print("PASS")


def main():
    tests = [
        test_order_far_outside_collar_rejected, test_order_within_collar_accepted,
        test_boundary_is_inclusive, test_just_outside_boundary_rejected,
        test_side_does_not_affect_collar, test_missing_symbol_raises_not_silently_passes,
        test_invalid_order_construction_rejected, test_invalid_current_price_rejected,
        test_engine_fail_fast_stops_at_first_rejection, test_engine_decision_log_accumulates,
    ]
    for t in tests:
        t()
    print("\nAll price collar tests passed.")


if __name__ == "__main__":
    main()