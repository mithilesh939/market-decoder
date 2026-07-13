"""
kill_switch.py

KillSwitchRule: a manual/automatic global halt. When engaged, EVERY
order is rejected regardless of any other rule.

Deliberately placed FIRST in the engine's rule pipeline (see engine
wiring below) rather than last as in the original architecture sketch:
a global halt should short-circuit as early as possible -- both for
correctness (no point evaluating other rules once halted) and safety (a
bug in a later rule's config lookup shouldn't block the kill switch).
"""
from __future__ import annotations

from .order import Order
from .price_collar import RuleResult


class KillSwitchRule:
    def __init__(self):
        self._engaged = False
        self._reason = ""

    def engage(self, reason: str) -> None:
        self._engaged = True
        self._reason = reason

    def disengage(self) -> None:
        self._engaged = False
        self._reason = ""

    @property
    def is_engaged(self) -> bool:
        return self._engaged

    def check(self, order: Order, current_price: float) -> RuleResult:
        if self._engaged:
            return RuleResult(False, f"kill switch engaged: {self._reason}", {"engaged": True})
        return RuleResult(True, "kill switch not engaged", {"engaged": False})