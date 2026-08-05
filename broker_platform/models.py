from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class BrokerCapabilities:
    broker_id: str
    paper_supported: bool
    live_supported: bool
    market_orders: bool
    limit_orders: bool
    fractional_market: bool
    notional_market: bool
    cancel: bool
    replace: bool
    read_account: bool
    read_positions: bool
    read_orders: bool
    actual_network_enabled: bool
    actual_write_enabled: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "broker_id": self.broker_id,
            "paper_supported": self.paper_supported,
            "live_supported": self.live_supported,
            "market_orders": self.market_orders,
            "limit_orders": self.limit_orders,
            "fractional_market": self.fractional_market,
            "notional_market": self.notional_market,
            "cancel": self.cancel,
            "replace": self.replace,
            "read_account": self.read_account,
            "read_positions": self.read_positions,
            "read_orders": self.read_orders,
            "actual_network_enabled": self.actual_network_enabled,
            "actual_write_enabled": self.actual_write_enabled,
        }


@dataclass(frozen=True)
class AccountDefinition:
    account_id: str
    broker_id: str
    broker_mode: str
    profile_name: str
    enabled: bool
    allocation_weight: Decimal
    maximum_account_notional: Decimal
    credential_vault_mode: str
    tags: tuple[str, ...]

    def validate(self) -> dict[str, Any]:
        checks = {
            "account_id_present": bool(self.account_id),
            "broker_id_present": bool(self.broker_id),
            "broker_mode_valid": self.broker_mode in {"paper", "live"},
            "profile_name_present": bool(self.profile_name),
            "allocation_weight_positive": self.allocation_weight > 0,
            "allocation_weight_not_over_one": self.allocation_weight <= 1,
            "maximum_account_notional_positive": (
                self.maximum_account_notional > 0
            ),
            "credential_mode_matches_broker_mode": (
                self.credential_vault_mode == self.broker_mode
            ),
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }

    def as_json(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "broker_id": self.broker_id,
            "broker_mode": self.broker_mode,
            "profile_name": self.profile_name,
            "enabled": self.enabled,
            "allocation_weight": str(self.allocation_weight),
            "maximum_account_notional": str(
                self.maximum_account_notional
            ),
            "credential_vault_mode": self.credential_vault_mode,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class RoutedOrderPreview:
    route_id: str
    candidate_id: str
    account_id: str
    broker_id: str
    broker_mode: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    requested_notional: Decimal
    routed_notional: Decimal
    route_allowed: bool
    submit_allowed: bool
    blockers: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "candidate_id": self.candidate_id,
            "account_id": self.account_id,
            "broker_id": self.broker_id,
            "broker_mode": self.broker_mode,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "requested_notional": str(self.requested_notional),
            "routed_notional": str(self.routed_notional),
            "route_allowed": self.route_allowed,
            "submit_allowed": self.submit_allowed,
            "blockers": list(self.blockers),
        }
