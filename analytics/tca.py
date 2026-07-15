from dataclasses import dataclass


@dataclass
class TradeCost:

    side: str

    fill_price: float

    fair_price: float

    quantity: float

    spread: float

    fee_rate: float = 0.0004

    def gross_edge(self):

        if self.side == "BUY":
            return self.fair_price - self.fill_price

        return self.fill_price - self.fair_price

    def spread_capture(self):

        return self.gross_edge() * self.quantity

    def fee(self):

        return self.fill_price * self.quantity * self.fee_rate

    def net_edge(self):

        return self.spread_capture() - self.fee()
    def notional(self):

        return self.fill_price * self.quantity

    def effective_spread(self):

        return 2.0 * abs(self.fill_price - self.fair_price)

    def signed_slippage(self):

        if self.side == "BUY":
            return self.fill_price - self.fair_price
        return self.fair_price - self.fill_price

class TCAReport:

    def __init__(self):

        self.trades = []

    def add(self, trade: TradeCost):

        self.trades.append(trade)

    def summary(self):

        gross = sum(x.spread_capture() for x in self.trades)

        fees = sum(x.fee() for x in self.trades)

        net = sum(x.net_edge() for x in self.trades)

        notionals = [x.notional() for x in self.trades]

        effective = [x.effective_spread() for x in self.trades]

        slippage = [x.signed_slippage() for x in self.trades]

        return {

            "fills": len(self.trades),

            "gross_spread_capture": gross,

            "fees": fees,

            "net_execution_edge": net,

            "average_notional": sum(notionals) / len(notionals),

            "average_effective_spread": sum(effective) / len(effective),

            "average_slippage": sum(slippage) / len(slippage),

        }
    