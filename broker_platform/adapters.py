from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from .models import BrokerCapabilities


class BrokerAdapter(ABC):
    broker_id: str

    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        raise NotImplementedError

    @abstractmethod
    def validate_offline_candidate(
        self,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    def submit_order(self, candidate: dict[str, Any]) -> None:
        raise RuntimeError(
            f"BROKER_WRITE_DISABLED:{self.broker_id}"
        )


class AlpacaPreparedAdapter(BrokerAdapter):
    broker_id = "alpaca"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=True,
            live_supported=True,
            market_orders=True,
            limit_orders=True,
            fractional_market=True,
            notional_market=True,
            cancel=True,
            replace=True,
            read_account=True,
            read_positions=True,
            read_orders=True,
            actual_network_enabled=False,
            actual_write_enabled=False,
        )

    def validate_offline_candidate(
        self,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        caps = self.capabilities()
        order_type = candidate.get("order_type")
        checks = {
            "candidate_present": bool(candidate),
            "candidate_submit_flag_off": (
                candidate.get("submit_allowed") is False
            ),
            "order_type_supported": (
                order_type == "market" and caps.market_orders
            ) or (
                order_type == "limit" and caps.limit_orders
            ),
            "symbol_present": bool(candidate.get("symbol")),
            "side_valid": candidate.get("side") in {"buy", "sell"},
            "network_disabled": caps.actual_network_enabled is False,
            "write_disabled": caps.actual_write_enabled is False,
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
            "broker_submission_allowed": False,
        }


class FutureBrokerAdapter(BrokerAdapter):
    def __init__(
        self,
        broker_id: str,
        *,
        read_preparation_supported: bool,
    ) -> None:
        self.broker_id = broker_id
        self.read_preparation_supported = read_preparation_supported

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker_id=self.broker_id,
            paper_supported=False,
            live_supported=False,
            market_orders=False,
            limit_orders=False,
            fractional_market=False,
            notional_market=False,
            cancel=False,
            replace=False,
            read_account=self.read_preparation_supported,
            read_positions=self.read_preparation_supported,
            read_orders=self.read_preparation_supported,
            actual_network_enabled=False,
            actual_write_enabled=False,
        )

    def validate_offline_candidate(
        self,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "checks": {
                "candidate_submit_flag_off": (
                    candidate.get("submit_allowed") is False
                ),
                "adapter_connection_not_implemented": True,
                "network_disabled": True,
                "write_disabled": True,
            },
            "failed": ["BROKER_CONNECTION_NOT_IMPLEMENTED"],
            "valid": False,
            "broker_submission_allowed": False,
        }


class BrokerAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, BrokerAdapter] = {}

    def register(self, adapter: BrokerAdapter) -> None:
        if not adapter.broker_id:
            raise ValueError("BROKER_ID_REQUIRED")
        if adapter.broker_id in self._adapters:
            raise ValueError(
                f"DUPLICATE_BROKER_ADAPTER:{adapter.broker_id}"
            )
        self._adapters[adapter.broker_id] = adapter

    def get(self, broker_id: str) -> BrokerAdapter:
        if broker_id not in self._adapters:
            raise KeyError(f"BROKER_ADAPTER_NOT_FOUND:{broker_id}")
        return self._adapters[broker_id]

    def capability_matrix(self) -> dict[str, Any]:
        rows = []
        for broker_id, adapter in sorted(self._adapters.items()):
            rows.append(adapter.capabilities().as_json())
        return {
            "stage": "R13_BROKER_CAPABILITY_MATRIX",
            "broker_count": len(rows),
            "brokers": rows,
            "actual_network_enabled": False,
            "actual_write_enabled": False,
        }


def build_default_registry() -> BrokerAdapterRegistry:
    registry = BrokerAdapterRegistry()
    registry.register(AlpacaPreparedAdapter())
    registry.register(FutureBrokerAdapter(
        "etrade",
        read_preparation_supported=True,
    ))
    registry.register(FutureBrokerAdapter(
        "ibkr",
        read_preparation_supported=True,
    ))
    registry.register(FutureBrokerAdapter(
        "schwab",
        read_preparation_supported=True,
    ))
    return registry
