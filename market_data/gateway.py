from .reader import MarketDataReader


class MarketDataGateway:

    def __init__(self, reader: MarketDataReader):

        self.reader = reader

    def stream(self):

        yield from self.reader