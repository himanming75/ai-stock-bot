from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrokerCapabilities:
    broker_id: str
    paper_supported: bool
    fractional_supported: bool
    market_orders_supported: bool
    limit_orders_supported: bool
    stop_orders_supported: bool
    streaming_supported: bool
    oauth_required: bool
    adapter_state: str

    def as_json(self) -> dict[str, Any]:
        return {
            "broker_id": self.broker_id,
            "paper_supported": self.paper_supported,
            "fractional_supported": self.fractional_supported,
            "market_orders_supported": self.market_orders_supported,
            "limit_orders_supported": self.limit_orders_supported,
            "stop_orders_supported": self.stop_orders_supported,
            "streaming_supported": self.streaming_supported,
            "oauth_required": self.oauth_required,
            "adapter_state": self.adapter_state,
        }


class BrokerAdapter:
    broker_id = "base"

    def capabilities(self) -> BrokerCapabilities:
        raise NotImplementedError

    def connect(self) -> None:
        raise RuntimeError(f"BROKER_NETWORK_DISABLED:{self.broker_id}")

    def get_account(self) -> None:
        raise RuntimeError(f"BROKER_READ_DISABLED:{self.broker_id}")

    def submit_order(self, order: dict[str, Any]) -> None:
        raise RuntimeError(f"BROKER_WRITE_DISABLED:{self.broker_id}")

    def cancel_order(self, order_id: str) -> None:
        raise RuntimeError(f"BROKER_CANCEL_DISABLED:{self.broker_id}")


class AlpacaAdapter(BrokerAdapter):
    broker_id = "alpaca"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=True,
            fractional_supported=True,
            market_orders_supported=True,
            limit_orders_supported=True,
            stop_orders_supported=True,
            streaming_supported=True,
            oauth_required=False,
            adapter_state="READY_INTERFACE_ONLY",
        )


class ETradeAdapter(BrokerAdapter):
    broker_id = "etrade"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=False,
            fractional_supported=False,
            market_orders_supported=True,
            limit_orders_supported=True,
            stop_orders_supported=True,
            streaming_supported=False,
            oauth_required=True,
            adapter_state="SKELETON_ONLY",
        )


class IBKRAdapter(BrokerAdapter):
    broker_id = "ibkr"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=True,
            fractional_supported=True,
            market_orders_supported=True,
            limit_orders_supported=True,
            stop_orders_supported=True,
            streaming_supported=True,
            oauth_required=False,
            adapter_state="SKELETON_ONLY",
        )


class SchwabAdapter(BrokerAdapter):
    broker_id = "schwab"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=False,
            fractional_supported=True,
            market_orders_supported=True,
            limit_orders_supported=True,
            stop_orders_supported=True,
            streaming_supported=True,
            oauth_required=True,
            adapter_state="SKELETON_ONLY",
        )


class TradierAdapter(BrokerAdapter):
    broker_id = "tradier"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=True,
            fractional_supported=False,
            market_orders_supported=True,
            limit_orders_supported=True,
            stop_orders_supported=True,
            streaming_supported=True,
            oauth_required=True,
            adapter_state="SKELETON_ONLY",
        )


class MockBrokerAdapter(BrokerAdapter):
    broker_id = "mock"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=True,
            fractional_supported=True,
            market_orders_supported=True,
            limit_orders_supported=True,
            stop_orders_supported=True,
            streaming_supported=False,
            oauth_required=False,
            adapter_state="READY_OFFLINE",
        )

    def preview_account(self) -> dict[str, Any]:
        return {
            "account_id": "mock-account",
            "status": "ACTIVE_FIXTURE",
            "cash": "100000",
            "equity": "100000",
            "buying_power": "200000",
            "broker_network_used": False,
        }


class BrokerRegistry:
    def __init__(self) -> None:
        self._adapters = {
            "alpaca": AlpacaAdapter(),
            "etrade": ETradeAdapter(),
            "ibkr": IBKRAdapter(),
            "schwab": SchwabAdapter(),
            "tradier": TradierAdapter(),
            "mock": MockBrokerAdapter(),
        }

    def list_capabilities(self) -> list[dict[str, Any]]:
        return [
            self._adapters[key].capabilities().as_json()
            for key in sorted(self._adapters)
        ]

    def get(self, broker_id: str) -> BrokerAdapter:
        try:
            return self._adapters[broker_id]
        except KeyError as exc:
            raise KeyError(f"UNKNOWN_BROKER:{broker_id}") from exc
