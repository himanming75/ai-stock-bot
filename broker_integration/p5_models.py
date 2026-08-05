from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QualificationPolicy:
    required_cycles: int
    maximum_failed_cycles: int
    maximum_consecutive_failures: int
    require_restart_recovery: bool
    require_duplicate_protection: bool
    require_kill_switch_test: bool
    require_reconciliation_test: bool
    require_market_close_test: bool
    require_next_day_resume_test: bool

    def validate(self) -> None:
        if self.required_cycles < 1:
            raise ValueError("REQUIRED_CYCLES_MUST_BE_POSITIVE")
        if self.maximum_failed_cycles < 0:
            raise ValueError("MAXIMUM_FAILED_CYCLES_INVALID")
        if self.maximum_consecutive_failures < 0:
            raise ValueError("MAXIMUM_CONSECUTIVE_FAILURES_INVALID")


def default_offline_policy() -> QualificationPolicy:
    return QualificationPolicy(
        required_cycles=1000,
        maximum_failed_cycles=0,
        maximum_consecutive_failures=0,
        require_restart_recovery=True,
        require_duplicate_protection=True,
        require_kill_switch_test=True,
        require_reconciliation_test=True,
        require_market_close_test=True,
        require_next_day_resume_test=True,
    )


def policy_from_dict(value: dict[str, Any]) -> QualificationPolicy:
    policy = QualificationPolicy(
        required_cycles=int(value.get("required_cycles", 1000)),
        maximum_failed_cycles=int(value.get("maximum_failed_cycles", 0)),
        maximum_consecutive_failures=int(
            value.get("maximum_consecutive_failures", 0)
        ),
        require_restart_recovery=bool(
            value.get("require_restart_recovery", True)
        ),
        require_duplicate_protection=bool(
            value.get("require_duplicate_protection", True)
        ),
        require_kill_switch_test=bool(
            value.get("require_kill_switch_test", True)
        ),
        require_reconciliation_test=bool(
            value.get("require_reconciliation_test", True)
        ),
        require_market_close_test=bool(
            value.get("require_market_close_test", True)
        ),
        require_next_day_resume_test=bool(
            value.get("require_next_day_resume_test", True)
        ),
    )
    policy.validate()
    return policy
