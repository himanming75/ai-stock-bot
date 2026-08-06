from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RuntimeSample:
    timestamp: str
    cycle_count: int
    memory_mb: Decimal
    cpu_percent: Decimal
    polling_delay_seconds: Decimal
    exception_count: int
    restart_count: int
    ledger_sequence: int

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "memory_mb",
            "cpu_percent",
            "polling_delay_seconds",
        ):
            value[key] = str(value[key])
        return value


def evaluate_samples(samples: list[RuntimeSample]) -> dict:
    if len(samples) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "sample_count": len(samples),
        }

    first = samples[0]
    last = samples[-1]
    memory_growth = last.memory_mb - first.memory_mb
    cycle_increase = last.cycle_count - first.cycle_count
    ledger_increase = (
        last.ledger_sequence - first.ledger_sequence
    )

    exceptions = sum(
        item.exception_count
        for item in samples
    )
    max_delay = max(
        item.polling_delay_seconds
        for item in samples
    )
    max_cpu = max(
        item.cpu_percent
        for item in samples
    )

    checks = {
        "cycles_increasing": cycle_increase > 0,
        "ledger_increasing": ledger_increase > 0,
        "exceptions_zero": exceptions == 0,
        "memory_growth_within_limit": (
            memory_growth <= Decimal("50")
        ),
        "polling_delay_within_limit": (
            max_delay <= Decimal("45")
        ),
        "cpu_within_limit": max_cpu <= Decimal("90"),
    }

    return {
        "status": (
            "PASS"
            if all(checks.values())
            else "BLOCKED"
        ),
        "sample_count": len(samples),
        "memory_growth_mb": str(memory_growth),
        "cycle_increase": cycle_increase,
        "ledger_increase": ledger_increase,
        "exception_count": exceptions,
        "max_polling_delay_seconds": str(max_delay),
        "max_cpu_percent": str(max_cpu),
        "checks": checks,
    }
