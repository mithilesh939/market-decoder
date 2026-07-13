from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from .event import Event, Side, Exchange
from .exceptions import InvalidRowError


class BinanceCSVReader(Iterator[Event]):

    """
    Streams Binance CSV files one row at a time.

    Memory usage: O(1)

    Supports datasets of arbitrary size.
    """

    def __init__(self, csv_file: str):

        self.path = Path(csv_file)

        self.file = open(self.path, "r", newline="")
        print(f"Opened: {self.path}")

        self.reader = csv.reader(self.file)

        self.rows_read = 0

    def __iter__(self):

        return self

    def __next__(self) -> Event:

        while True:

            try:

                row = next(self.reader)
                print(row)

            except StopIteration:

                self.close()

                raise

            self.rows_read += 1

            try:

                return self._parse(row)

            except InvalidRowError:

                continue

    def _parse(self, row):

        if len(row) != 7:

            raise InvalidRowError()

        trade_id = int(row[0])

        price = float(row[1])

        quantity = float(row[2])

        quote_qty = float(row[3])

        timestamp = int(row[4])

        buyer_is_maker = row[5].lower() == "true"

        best_match = row[6].lower() == "true"

        side = Side.SELL if buyer_is_maker else Side.BUY

        return Event(
            trade_id=trade_id,
            timestamp=timestamp,
            symbol="BTCUSDT",
            price=price,
            quantity=quantity,
            side=side,
            exchange=Exchange.BINANCE,
            quote_qty=quote_qty,
            best_match=best_match,
            sequence=self.rows_read,
        )

    def close(self):

        if not self.file.closed:

            self.file.close()