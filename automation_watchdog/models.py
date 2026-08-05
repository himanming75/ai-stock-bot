from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class WatchdogPolicy:
    controller_profile: str
    poll_interval_seconds: int
    maximum_restart_attempts: int
    restart_backoff_seconds: int
    stale_lock_seconds: int
    heartbeat_timeout_seconds: int
    crash_window_seconds: int
    stop_when_market_closed: bool
    actual_submission_allowed: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "WatchdogPolicy":
        return cls(
            controller_profile=str(
                data.get(
                    "controller_profile",
                    "release/paper_automation_controller/config/read_only_profile.json",
                )
            ),
            poll_interval_seconds=max(1, int(data.get("poll_interval_seconds", 5))),
            maximum_restart_attempts=max(
                0, int(data.get("maximum_restart_attempts", 3))
            ),
            restart_backoff_seconds=max(
                1, int(data.get("restart_backoff_seconds", 5))
            ),
            stale_lock_seconds=max(10, int(data.get("stale_lock_seconds", 120))),
            heartbeat_timeout_seconds=max(
                10, int(data.get("heartbeat_timeout_seconds", 120))
            ),
            crash_window_seconds=max(
                60, int(data.get("crash_window_seconds", 600))
            ),
            stop_when_market_closed=bool(
                data.get("stop_when_market_closed", True)
            ),
            actual_submission_allowed=bool(
                data.get("actual_submission_allowed", False)
            ),
        )

    def as_json(self) -> dict:
        return asdict(self)
