from dataclasses import dataclass


@dataclass
class RegimeStats:
    name: str

    fills: int = 0
    submitted_orders: int = 0
    pnl: float = 0.0
    rejected: int = 0
    inventory_sum: float = 0.0
    observations: int = 0

    def update(
        self,
        pnl_delta,
        inventory,
        rejected,
        submitted,
        filled,
    ):
        self.pnl += pnl_delta

        if submitted:
            self.submitted_orders += 1

        if filled:
            self.fills += 1

        self.inventory_sum += abs(inventory)
        self.observations += 1
        self.rejected += rejected

    @property
    def avg_inventory(self) -> float:
        if self.observations == 0:
            return 0.0
        return self.inventory_sum / self.observations

    @property
    def fill_rate(self) -> float:
        if self.observations == 0:
            return 0.0
        return 100.0 * self.fills / self.observations

    @property
    def reject_rate(self) -> float:
        if self.observations == 0:
            return 0.0
        return 100.0 * self.rejected / self.observations


class RegimeAnalyzer:

    def __init__(self):
        self.low = RegimeStats("Low Vol")
        self.medium = RegimeStats("Medium Vol")
        self.high = RegimeStats("High Vol")

    def bucket(self, sigma, low_threshold, high_threshold):

        if sigma < low_threshold:
            return self.low

        if sigma < high_threshold:
            return self.medium

        return self.high