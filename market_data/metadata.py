from dataclasses import dataclass


@dataclass(slots=True)
class DatasetMetadata:

    symbol: str

    exchange: str

    year: int

    month: int

    rows: int

    start_timestamp: int

    end_timestamp: int

    csv_size_bytes: int

    binary_size_bytes: int