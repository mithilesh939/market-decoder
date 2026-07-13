from risk.order_size_limit import OrderSizeLimitRule
from risk.inventory_limit import InventoryLimitRule, InventoryTracker
from risk.kill_switch import KillSwitchRule

CONFIG = {
    "BTCUSDT": {
        "price_collar_percent": 2.0,
        "max_order_size": 5.0,
        "max_inventory": 10.0,
    }
}

tracker = InventoryTracker()
kill_switch = KillSwitchRule()
engine = RiskEngine([
    kill_switch,
    PriceCollarRule(CONFIG),
    OrderSizeLimitRule(CONFIG),
    InventoryLimitRule(CONFIG, tracker),
])