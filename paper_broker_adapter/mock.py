from __future__ import annotations
from typing import Any
from paper_broker_adapter.base import BrokerAdapter

class MockPaperBrokerAdapter(BrokerAdapter):
    name = "MOCK_PAPER"

    def __init__(
        self,
        account: dict[str, Any] | None = None,
        positions: list[dict[str, Any]] | None = None,
    ) -> None:
        self._account = account or {
            "cash": 100000.0,
            "equity": 100000.0,
            "buying_power": 100000.0,
            "currency": "USD",
            "status": "ACTIVE",
        }
        self._positions = positions or []

    def capabilities(self) -> dict[str, Any]:
        return {
            "account_read": True,
            "positions_read": True,
            "orders_read": False,
            "market_data_read": False,
            "order_submit": False,
            "order_cancel": False,
            "network_required": False,
            "credentials_required": False,
            "read_only": True,
        }

    def health_check(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "healthy": True,
            "read_only": True,
            "network_used": False,
            "credentials_used": False,
        }

    def get_account_snapshot(self) -> dict[str, Any]:
        return dict(self._account)

    def get_positions_snapshot(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._positions]
