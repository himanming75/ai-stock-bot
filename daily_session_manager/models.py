from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DailySessionPolicy:
    session_timezone: str
    launch_watchdog_when_market_open: bool
    stop_after_market_close: bool
    allow_weekend_start: bool
    startup_delay_seconds: int
    maximum_daily_launches: int
    actual_submission_allowed: bool
    watchdog_script: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DailySessionPolicy":
        return cls(
            session_timezone=str(
                data.get("session_timezone", "America/New_York")
            ),
            launch_watchdog_when_market_open=bool(
                data.get("launch_watchdog_when_market_open", True)
            ),
            stop_after_market_close=bool(
                data.get("stop_after_market_close", True)
            ),
            allow_weekend_start=bool(
                data.get("allow_weekend_start", False)
            ),
            startup_delay_seconds=max(
                0, int(data.get("startup_delay_seconds", 30))
            ),
            maximum_daily_launches=max(
                1, int(data.get("maximum_daily_launches", 1))
            ),
            actual_submission_allowed=bool(
                data.get("actual_submission_allowed", False)
            ),
            watchdog_script=str(
                data.get(
                    "watchdog_script",
                    "RUN_ACTUAL_AUTOMATION_WATCHDOG.ps1",
                )
            ),
        )

    def as_json(self) -> dict:
        return asdict(self)
