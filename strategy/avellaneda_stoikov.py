
from __future__ import annotations

import math
from dataclasses import dataclass


def convert_tick_volatility_to_price_volatility(
    tick_log_return_std: float,
    price_level: float,
    trades_per_second: float,
) -> float:
    """
    Converts a TICK-LEVEL log-return std (what
    features.microstructure.compute_realized_volatility returns -- tiny,
    dimensionless, e.g. ~0.00001 for real BTC) into a PRICE-DIFFUSION
    volatility in dollars-per-sqrt-second, which is what the AS formula's
    sigma actually represents.

    WHY NECESSARY, not optional: plugging a raw tick log-return std
    directly into gamma*sigma^2*(T-t) either produces a negligible effect
    or an absurd one. Caught during development: an early version used
    sigma=5.0 as a placeholder and produced a reservation price that
    moved by tens of thousands of dollars for a small inventory position.

    DERIVATION: under random-walk scaling, variance grows linearly with
    ticks elapsed. If trades arrive at trades_per_second and each tick's
    log return has variance tick_log_return_std^2, the per-second
    log-return std is sqrt(trades_per_second) * tick_log_return_std;
    multiplying by price_level converts to dollar scale.
    """
    if trades_per_second <= 0:
        raise ValueError(f"trades_per_second must be positive, got {trades_per_second}")
    return price_level * tick_log_return_std * math.sqrt(trades_per_second)


@dataclass(frozen=True)
class ASQuote:
    reservation_price: float
    bid_price: float
    ask_price: float
    spread: float
    bid_size: float
    ask_size: float


class AvellanedaStoikovMarketMaker:
    def __init__(self, gamma: float, kappa: float, session_duration_s: float, quote_size: float):
        if gamma <= 0:
            raise ValueError(f"gamma must be positive, got {gamma}")
        if kappa <= 0:
            raise ValueError(f"kappa must be positive, got {kappa}")
        if session_duration_s <= 0:
            raise ValueError(f"session_duration_s must be positive, got {session_duration_s}")
        self.gamma = gamma
        self.kappa = kappa
        self.session_duration_s = session_duration_s
        self.quote_size = quote_size

    def generate_quote(self, fair_value: float, inventory: float, volatility: float, elapsed_s: float) -> ASQuote:
        elapsed_s = min(elapsed_s, self.session_duration_s)
        time_remaining = self.session_duration_s - elapsed_s

        reservation_price = fair_value - inventory * self.gamma * (volatility ** 2) * time_remaining
        spread = (
            self.gamma * (volatility ** 2) * time_remaining
            + (2.0 / self.gamma) * math.log(1.0 + self.gamma / self.kappa)
        )
        half_spread = spread / 2.0

        return ASQuote(
            reservation_price=reservation_price,
            bid_price=reservation_price - half_spread,
            ask_price=reservation_price + half_spread,
            spread=spread,
            bid_size=self.quote_size,
            ask_size=self.quote_size,
        )
