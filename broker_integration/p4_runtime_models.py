from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimePolicy:
    cycle_interval_seconds: int
    maximum_cycles_per_session: int
    require_market_open: bool
    require_p2_actual_validation: bool
    require_p3_actual_validation: bool
    fail_closed: bool

    def validate(self) -> None:
        if self.cycle_interval_seconds < 1:
            raise ValueError("CYCLE_INTERVAL_MUST_BE_POSITIVE")
        if self.maximum_cycles_per_session < 1:
            raise ValueError("MAXIMUM_CYCLES_MUST_BE_POSITIVE")
        if not self.fail_closed:
            raise ValueError("P4_FAIL_CLOSED_REQUIRED")


def default_policy() -> RuntimePolicy:
    return RuntimePolicy(
        cycle_interval_seconds=60,
        maximum_cycles_per_session=390,
        require_market_open=True,
        require_p2_actual_validation=True,
        require_p3_actual_validation=True,
        fail_closed=True,
    )


def policy_from_dict(value: dict[str, Any]) -> RuntimePolicy:
    policy = RuntimePolicy(
        cycle_interval_seconds=int(
            value.get("cycle_interval_seconds", 60)
        ),
        maximum_cycles_per_session=int(
            value.get("maximum_cycles_per_session", 390)
        ),
        require_market_open=bool(
            value.get("require_market_open", True)
        ),
        require_p2_actual_validation=bool(
            value.get("require_p2_actual_validation", True)
        ),
        require_p3_actual_validation=bool(
            value.get("require_p3_actual_validation", True)
        ),
        fail_closed=bool(value.get("fail_closed", True)),
    )
    policy.validate()
    return policy
