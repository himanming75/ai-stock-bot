from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class AutomationProfile:
    name: str
    symbols: tuple[str, ...]
    interval_seconds: int
    max_cycles: int
    stop_when_market_closed: bool
    enable_market_pipeline: bool
    enable_execution_planning: bool
    enable_order_ticket_generation: bool
    enable_actual_submission: bool
    require_submission_approval_token: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AutomationProfile":
        return cls(
            name=str(data.get("name", "READ_ONLY")).upper(),
            symbols=tuple(str(x).upper() for x in data.get("symbols", ["SPY", "QQQ", "IWM"])),
            interval_seconds=max(1, int(data.get("interval_seconds", 60))),
            max_cycles=max(1, int(data.get("max_cycles", 10))),
            stop_when_market_closed=bool(data.get("stop_when_market_closed", True)),
            enable_market_pipeline=bool(data.get("enable_market_pipeline", True)),
            enable_execution_planning=bool(data.get("enable_execution_planning", True)),
            enable_order_ticket_generation=bool(data.get("enable_order_ticket_generation", True)),
            enable_actual_submission=bool(data.get("enable_actual_submission", False)),
            require_submission_approval_token=bool(data.get("require_submission_approval_token", True)),
        )

    def as_json(self) -> dict:
        data = asdict(self)
        data["symbols"] = list(self.symbols)
        return data
