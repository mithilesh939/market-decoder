from __future__ import annotations

from risk.price_collar import PriceCollarRule
'''
class RiskEngine:

    def __init__(self):

        self.price_rule = PriceCollarRule("risk/config.json")

    def validate(self, order, current_price):

        return self.price_rule.validate(order, current_price)
        '''




from dataclasses import dataclass, field
from typing import Any, List, Protocol

from .order import Order


class RiskRule(Protocol):
    def check(self, order: Order, current_price: float) -> Any: ...


@dataclass(frozen=True)
class EngineDecision:
    accepted: bool
    rule_name: str
    reason: str
    details: dict = field(default_factory=dict)


class RiskEngine:
    def __init__(self, rules: List[RiskRule]):
        self.rules = rules
        self.decision_log: List[EngineDecision] = []

    def evaluate(self, order: Order, current_price: float) -> EngineDecision:
        for rule in self.rules:
            result = rule.check(order, current_price)
            if not result.accepted:
                decision = EngineDecision(
                    accepted=False, rule_name=type(rule).__name__,
                    reason=result.reason, details=result.details,
                )
                self.decision_log.append(decision)
                return decision

        decision = EngineDecision(
            accepted=True, rule_name="ALL", reason="passed all risk checks", details={},
        )
        self.decision_log.append(decision)
        return decision