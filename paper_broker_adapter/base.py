from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class BrokerAdapter(ABC):
    name = "BASE"
    read_only = True

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_account_snapshot(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_positions_snapshot(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def submit_order(self, *_: Any, **__: Any) -> None:
        raise PermissionError(
            "Broker writes are disabled by the V97 safe API boundary."
        )

    def cancel_order(self, *_: Any, **__: Any) -> None:
        raise PermissionError(
            "Order cancellation writes are disabled by the V97 safe API boundary."
        )
