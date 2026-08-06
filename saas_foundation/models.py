from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class User:
    user_id: str
    email: str
    password_hash: str
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("password_hash", None)
        return value


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    name: str
    owner_user_id: str
    plan: str = "FOUNDATION"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Membership:
    workspace_id: str
    user_id: str
    role: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkspaceSettings:
    workspace_id: str
    selected_strategy: str = "MOMENTUM"
    risk_profile: str = "CONSERVATIVE"
    max_position_weight: float = 0.10
    daily_loss_limit: float = 0.02
    automation_profile: str = "ALL_STOP"
    broker_connections: list[dict[str, Any]] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
