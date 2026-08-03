from __future__ import annotations
from typing import Any
from paper_broker_adapter.base import BrokerAdapter

class AlpacaReadOnlyAdapter(BrokerAdapter):
    name = "ALPACA_READ_ONLY"

    def __init__(self, network_enabled: bool = False) -> None:
        self.network_enabled = bool(network_enabled)

    def capabilities(self) -> dict[str, Any]:
        return {
            "account_read": False,
            "positions_read": False,
            "orders_read": False,
            "market_data_read": False,
            "order_submit": False,
            "order_cancel": False,
            "network_required": True,
            "credentials_required": True,
            "read_only": True,
        }

    def health_check(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "healthy": False,
            "state": "NETWORK_AND_CREDENTIALS_DISABLED",
            "read_only": True,
            "network_used": False,
            "credentials_used": False,
        }

    def get_account_snapshot(self) -> dict[str, Any]:
        return {
            "state": "READ_ONLY_ADAPTER_NOT_CONNECTED",
            "adapter": self.name,
        }

    def get_positions_snapshot(self) -> list[dict[str, Any]]:
        return []
