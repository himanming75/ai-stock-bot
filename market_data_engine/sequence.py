from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import Bar, MarketDataMessage, Quote, Trade


class SequenceDecision(str, Enum):
    ACCEPT = "ACCEPT"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    NO_SEQUENCE = "NO_SEQUENCE"


@dataclass
class SequenceGuard:
    _last: dict[tuple[str, str], int] = None

    def __post_init__(self):
        if self._last is None:
            self._last = {}

    @staticmethod
    def _kind(message: MarketDataMessage) -> str:
        if isinstance(message, Quote):
            return "quote"
        if isinstance(message, Trade):
            return "trade"
        if isinstance(message, Bar):
            return "bar"
        raise TypeError("unsupported message")

    def check(self, message: MarketDataMessage) -> SequenceDecision:
        if message.sequence is None:
            return SequenceDecision.NO_SEQUENCE
        key = (self._kind(message), message.symbol)
        previous = self._last.get(key)
        if previous is None or message.sequence > previous:
            self._last[key] = message.sequence
            return SequenceDecision.ACCEPT
        if message.sequence == previous:
            return SequenceDecision.DUPLICATE
        return SequenceDecision.OUT_OF_ORDER
