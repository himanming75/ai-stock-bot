from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AccountProfile:
    account_key: str
    broker: str
    environment: str
    role: str
    alias: str
    read_enabled: bool
    write_enabled: bool
    strategy_execution_enabled: bool
    kill_switch_active: bool
    actual_connection_validated: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RouteRequest:
    account_key: str
    broker: str
    environment: str
    operation: str
    strategy_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RouteDecision:
    status: str
    allowed: bool
    account_key: str
    route: str
    reason: str
    read_allowed: bool
    write_allowed: bool
    kill_switch_active: bool

    def to_dict(self) -> dict:
        return asdict(self)
