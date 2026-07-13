from risk.order import Order, Side
from risk.price_collar import PriceCollarRule
from risk.engine import RiskEngine

config = {"BTCUSDT": {"price_collar_percent": 2.0}}
engine = RiskEngine([PriceCollarRule(config)])

d1 = engine.evaluate(Order("BTCUSDT", Side.BUY, 70000, 1), current_price=64200)
print(d1.accepted, d1.reason)   # False, rejected

d2 = engine.evaluate(Order("BTCUSDT", Side.BUY, 64220, 2), current_price=64200)
print(d2.accepted, d2.reason)   # True, passed