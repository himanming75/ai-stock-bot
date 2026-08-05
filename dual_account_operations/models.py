from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AccountPolicy:
    account_key: str
    read_allowed: bool
    write_allowed: bool
    strategy_execution_allowed: bool
    kill_switch_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyProfile:
    name: str
    description: str
    account_policies: tuple[AccountPolicy, ...]
    global_read_allowed: bool
    global_write_allowed: bool
    operator_ack_required: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["account_policies"] = [
            item.to_dict()
            for item in self.account_policies
        ]
        return value
