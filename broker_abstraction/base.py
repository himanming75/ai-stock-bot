from __future__ import annotations
from abc import ABC, abstractmethod


class ReadOnlyBrokerAdapter(ABC):
    broker_name: str
    environment: str

    @abstractmethod
    def accounts(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def positions(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def orders(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def quotes(self, symbols: list[str]) -> list[dict]:
        raise NotImplementedError

    def submit_order(self, *args, **kwargs):
        raise PermissionError("BROKER_WRITE_DISABLED")

    def cancel_order(self, *args, **kwargs):
        raise PermissionError("BROKER_WRITE_DISABLED")

    def replace_order(self, *args, **kwargs):
        raise PermissionError("BROKER_WRITE_DISABLED")
