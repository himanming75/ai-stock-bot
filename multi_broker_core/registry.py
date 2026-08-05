from __future__ import annotations
from .capabilities import BrokerCapabilities


class CapabilityRegistry:
    def __init__(self) -> None:
        self._items: dict[str, BrokerCapabilities] = {}

    def register(self, capabilities: BrokerCapabilities) -> None:
        key = capabilities.broker.upper()
        if key in self._items:
            raise ValueError(f"broker already registered: {key}")
        self._items[key] = capabilities

    def get(self, broker: str) -> BrokerCapabilities:
        key = broker.upper()
        if key not in self._items:
            raise KeyError(f"unknown broker: {broker}")
        return self._items[key]

    def list_all(self) -> list[BrokerCapabilities]:
        return [self._items[key] for key in sorted(self._items)]


def default_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(BrokerCapabilities(
        broker="MOCK", account_read=True, positions_read=True, orders_read=True,
        market_data_read=False, paper_trading=True, order_submission=False,
        order_cancel=False, fractional_shares=True, extended_hours=False,
        options=False, streaming=False,
    ))
    registry.register(BrokerCapabilities(
        broker="ALPACA", account_read=True, positions_read=True, orders_read=True,
        market_data_read=True, paper_trading=True, order_submission=False,
        order_cancel=False, fractional_shares=True, extended_hours=True,
        options=True, streaming=True,
    ))
    registry.register(BrokerCapabilities(
        broker="ETRADE", account_read=False, positions_read=False, orders_read=False,
        market_data_read=False, paper_trading=False, order_submission=False,
        order_cancel=False, fractional_shares=False, extended_hours=False,
        options=True, streaming=False,
    ))
    registry.register(BrokerCapabilities(
        broker="IBKR", account_read=False, positions_read=False, orders_read=False,
        market_data_read=False, paper_trading=True, order_submission=False,
        order_cancel=False, fractional_shares=True, extended_hours=True,
        options=True, streaming=True,
    ))
    return registry
