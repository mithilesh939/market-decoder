from market_data.reader import BinanceCSVReader

reader = BinanceCSVReader(
    "data/binance/BTCUSDT/2025/BTCUSDT-trades-2025-01.csv"
)
for i, event in enumerate(reader):

    print(event)

    if i == 4:

        break