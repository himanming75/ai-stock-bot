from __future__ import annotations
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RoutedAccount:
    account_id_key: str
    account_id_masked: str
    account_type: str
    account_mode: str
    account_status: str
    alias: str
    enabled: bool
    default: bool
    production_read_allowed: bool

    def to_dict(self) -> dict:
        return asdict(self)
