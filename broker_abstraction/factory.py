from __future__ import annotations

from .adapters.alpaca import AlpacaReadOnlyAdapter
from .adapters.etrade import ETradeReadOnlyAdapter


class BrokerFactory:
    @staticmethod
    def create(
        broker: str,
        *,
        snapshot: dict,
    ):
        name = broker.upper()
        if name == "ALPACA":
            return AlpacaReadOnlyAdapter(snapshot)
        if name == "ETRADE":
            return ETradeReadOnlyAdapter(snapshot)
        raise ValueError("UNKNOWN_BROKER")
