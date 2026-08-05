from __future__ import annotations
from collections.abc import Callable
from .adapter import BrokerAdapter
from .mock_adapter import MockBrokerAdapter


class BrokerFactory:
    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., BrokerAdapter]] = {}
        self.register("MOCK", MockBrokerAdapter)

    def register(self, broker: str, builder: Callable[..., BrokerAdapter]) -> None:
        key = broker.upper()
        if key in self._builders:
            raise ValueError(f"broker factory already registered: {key}")
        self._builders[key] = builder

    def create(self, broker: str, **kwargs) -> BrokerAdapter:
        key = broker.upper()
        if key not in self._builders:
            raise KeyError(f"broker adapter not implemented: {broker}")
        return self._builders[key](**kwargs)

    def implemented_brokers(self) -> list[str]:
        return sorted(self._builders)
