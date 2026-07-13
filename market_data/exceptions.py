class MarketDataError(Exception):
    pass


class InvalidRowError(MarketDataError):
    pass


class CorruptedDatasetError(MarketDataError):
    pass