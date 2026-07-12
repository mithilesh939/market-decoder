import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))



from python.market_decoder import decode_to_dataframes
from order import Order
from engine import RiskEngine


# Decode real market data
dfs = decode_to_dataframes("tools/real_market_data.bin")

trades = dfs["trades"]

# Latest market price
latest_price = trades.iloc[-1]["price"] / 1_000_000

print(f"Latest Market Price: {latest_price}")

engine = RiskEngine()

orders = [
    Order("BTCUSDT", "BUY", latest_price + 10, 1),
    Order("BTCUSDT", "BUY", latest_price + 5000, 1),
    Order("BTCUSDT", "SELL", latest_price - 20, 2),
]

for order in orders:

    result = engine.validate(order, latest_price)

    print(order)
    print(result)