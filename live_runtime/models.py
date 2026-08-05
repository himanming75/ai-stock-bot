from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LiveRuntimePolicy:
    cycle_interval_seconds: int
    maximum_cycles_per_session: int
    require_market_open: bool
    fail_closed: bool
    require_l1: bool
    require_l2_actual: bool
    require_l3_actual: bool
    require_l4_actual: bool
    require_p5_actual: bool

    def evaluate(self) -> dict[str, Any]:
        checks = {
            "cycle_interval_positive": self.cycle_interval_seconds > 0,
            "maximum_cycles_positive": self.maximum_cycles_per_session > 0,
            "market_open_required": self.require_market_open is True,
            "fail_closed": self.fail_closed is True,
            "l1_required": self.require_l1 is True,
            "l2_actual_required": self.require_l2_actual is True,
            "l3_actual_required": self.require_l3_actual is True,
            "l4_actual_required": self.require_l4_actual is True,
            "p5_actual_required": self.require_p5_actual is True,
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }
