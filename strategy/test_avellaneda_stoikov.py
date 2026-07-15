"""
test_avellaneda_stoikov.py

Plain assert-based tests. Includes a regression test for the unit-
mismatch bug caught during development (see module docstring in
avellaneda_stoikov.py for the full story).

Run: python3 strategy/test_avellaneda_stoikov.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy.avellaneda_stoikov import AvellanedaStoikovMarketMaker, convert_tick_volatility_to_price_volatility


def test_zero_inventory_reservation_price_equals_fair_value():
    print("running: zero inventory -> reservation price == fair value ... ", end="")
    mm = AvellanedaStoikovMarketMaker(gamma=0.0005, kappa=1.5, session_duration_s=3600, quote_size=0.01)
    q = mm.generate_quote(fair_value=64200.0, inventory=0, volatility=4.0, elapsed_s=0)
    assert abs(q.reservation_price - 64200.0) < 1e-9
    print("PASS")


def test_long_inventory_shifts_reservation_price_down():
    print("running: long inventory shifts reservation price down (more eager to sell) ... ", end="")
    mm = AvellanedaStoikovMarketMaker(gamma=0.0005, kappa=1.5, session_duration_s=3600, quote_size=0.01)
    q = mm.generate_quote(fair_value=64200.0, inventory=5.0, volatility=4.0, elapsed_s=0)
    assert q.reservation_price < 64200.0
    print("PASS")


def test_short_inventory_shifts_reservation_price_up():
    print("running: short inventory shifts reservation price up (more eager to buy) ... ", end="")
    mm = AvellanedaStoikovMarketMaker(gamma=0.0005, kappa=1.5, session_duration_s=3600, quote_size=0.01)
    q = mm.generate_quote(fair_value=64200.0, inventory=-5.0, volatility=4.0, elapsed_s=0)
    assert q.reservation_price > 64200.0
    print("PASS")


def test_higher_volatility_widens_spread():
    print("running: higher volatility widens the spread ... ", end="")
    mm = AvellanedaStoikovMarketMaker(gamma=0.0005, kappa=1.5, session_duration_s=3600, quote_size=0.01)
    q_low = mm.generate_quote(fair_value=64200.0, inventory=0, volatility=1.0, elapsed_s=0)
    q_high = mm.generate_quote(fair_value=64200.0, inventory=0, volatility=10.0, elapsed_s=0)
    assert q_high.spread > q_low.spread
    print("PASS")


def test_inventory_skew_shrinks_near_session_end():
    print("running: inventory skew shrinks as session end approaches ... ", end="")
    mm = AvellanedaStoikovMarketMaker(gamma=0.0005, kappa=1.5, session_duration_s=3600, quote_size=0.01)
    q_early = mm.generate_quote(fair_value=64200.0, inventory=5.0, volatility=4.0, elapsed_s=0)
    q_late = mm.generate_quote(fair_value=64200.0, inventory=5.0, volatility=4.0, elapsed_s=3599)
    assert abs(q_late.reservation_price - 64200.0) < abs(q_early.reservation_price - 64200.0)
    print("PASS")


def test_bid_below_reservation_below_ask():
    print("running: bid < reservation_price < ask always holds ... ", end="")
    mm = AvellanedaStoikovMarketMaker(gamma=0.0005, kappa=1.5, session_duration_s=3600, quote_size=0.01)
    q = mm.generate_quote(fair_value=64200.0, inventory=2.0, volatility=4.0, elapsed_s=100)
    assert q.bid_price < q.reservation_price < q.ask_price
    print("PASS")


def test_invalid_parameters_rejected():
    print("running: invalid gamma/kappa/session_duration rejected ... ", end="")
    for kwargs in [
        dict(gamma=0, kappa=1.5, session_duration_s=3600, quote_size=0.01),
        dict(gamma=0.1, kappa=0, session_duration_s=3600, quote_size=0.01),
        dict(gamma=0.1, kappa=1.5, session_duration_s=0, quote_size=0.01),
    ]:
        try:
            AvellanedaStoikovMarketMaker(**kwargs)
            assert False, f"expected ValueError for {kwargs}"
        except ValueError:
            pass
    print("PASS")


def test_volatility_conversion_regression():
    """Regression test for the real bug caught during development: using
    a raw tick-level log-return std directly as sigma (without unit
    conversion) produces either a negligible or an absurd skew. This
    test locks in the CORRECT behavior using real numbers from an actual
    demo run on real BTC trade data."""
    print("running: volatility conversion produces sane real-world skew (regression test) ... ", end="")
    real_price = 107174.39
    real_tick_vol = 0.00000715
    real_trades_per_sec = 27.31

    price_vol = convert_tick_volatility_to_price_volatility(real_tick_vol, real_price, real_trades_per_sec)
    assert 0.1 < price_vol < 100, f"price_vol={price_vol} is not in a sane range"

    mm = AvellanedaStoikovMarketMaker(gamma=0.0005, kappa=1.5, session_duration_s=3600, quote_size=0.01)
    q = mm.generate_quote(fair_value=real_price, inventory=0.05, volatility=price_vol, elapsed_s=0)
    skew = real_price - q.reservation_price
    assert 0 < skew < 500, f"skew=${skew:.2f} is not sane for a small real position"
    print("PASS")


def test_volatility_conversion_rejects_nonpositive_rate():
    print("running: volatility conversion rejects non-positive trades_per_second ... ", end="")
    try:
        convert_tick_volatility_to_price_volatility(0.00001, 64200.0, 0)
        assert False
    except ValueError:
        pass
    print("PASS")


def main():
    tests = [
        test_zero_inventory_reservation_price_equals_fair_value,
        test_long_inventory_shifts_reservation_price_down,
        test_short_inventory_shifts_reservation_price_up,
        test_higher_volatility_widens_spread,
        test_inventory_skew_shrinks_near_session_end,
        test_bid_below_reservation_below_ask,
        test_invalid_parameters_rejected,
        test_volatility_conversion_regression,
        test_volatility_conversion_rejects_nonpositive_rate,
    ]
    for t in tests:
        t()
    print("\nAll Avellaneda-Stoikov tests passed.")


if __name__ == "__main__":
    main()
