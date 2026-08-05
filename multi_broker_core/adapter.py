from __future__ import annotations
from abc import ABC, abstractmethod
from .capabilities import BrokerCapabilities
from .models import AccountSnapshot, OrderRequest, OrderSnapshot, PositionSnapshot


class BrokerAdapter(ABC):
    @property
    @abstractmethod
    def broker_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        raise NotImplementedError

    @abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_account(self) -> AccountSnapshot:
        raise NotImplementedError

    @abstractmethod
    def list_positions(self) -> list[PositionSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def list_orders(self) -> list[OrderSnapshot]:
        raise NotImplementedError

    def submit_order(self, request: OrderRequest) -> OrderSnapshot:
        raise PermissionError("Order submission disabled by multi-broker core safety contract")

    def cancel_order(self, order_id: str) -> OrderSnapshot:
        raise PermissionError("Order cancellation disabled by multi-broker core safety contract")
