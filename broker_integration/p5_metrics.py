from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class QualificationMetrics:
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    consecutive_failures: int = 0
    maximum_observed_consecutive_failures: int = 0
    duplicate_cycles_blocked: int = 0
    restart_recoveries_passed: int = 0
    kill_switch_tests_passed: int = 0
    reconciliation_tests_passed: int = 0
    market_close_tests_passed: int = 0
    next_day_resume_tests_passed: int = 0
    actual_paper_orders_submitted: int = 0
    actual_live_orders_submitted: int = 0

    def record_success(self) -> None:
        self.total_cycles += 1
        self.successful_cycles += 1
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.total_cycles += 1
        self.failed_cycles += 1
        self.consecutive_failures += 1
        self.maximum_observed_consecutive_failures = max(
            self.maximum_observed_consecutive_failures,
            self.consecutive_failures,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
