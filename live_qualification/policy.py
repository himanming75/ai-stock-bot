from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LiveLongRunPolicy:
    required_cycles: int
    maximum_failed_cycles: int
    maximum_heartbeat_gap_seconds: int
    require_zero_duplicate_cycles: bool
    require_zero_unresolved_drift: bool
    require_kill_switch_response: bool
    require_crash_resume_test: bool
    fail_closed: bool

    def evaluate(self) -> dict[str, Any]:
        checks = {
            "required_cycles_positive": self.required_cycles > 0,
            "maximum_failed_cycles_nonnegative": (
                self.maximum_failed_cycles >= 0
            ),
            "heartbeat_gap_positive": (
                self.maximum_heartbeat_gap_seconds > 0
            ),
            "zero_duplicate_cycles_required": (
                self.require_zero_duplicate_cycles is True
            ),
            "zero_unresolved_drift_required": (
                self.require_zero_unresolved_drift is True
            ),
            "kill_switch_response_required": (
                self.require_kill_switch_response is True
            ),
            "crash_resume_required": (
                self.require_crash_resume_test is True
            ),
            "fail_closed": self.fail_closed is True,
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }
