from __future__ import annotations
from datetime import datetime, timezone

from .i18n import bilingual


def _score_lower_better(
    value: float,
    good: float,
    bad: float,
) -> float:
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    return (
        100.0
        * (bad - value)
        / (bad - good)
    )


def calculate_health(
    *,
    cpu_percent: float,
    memory_growth_mb: float,
    polling_delay_seconds: float,
    broker_latency_ms: float,
    error_count: int,
    stale_source_count: int,
) -> dict:
    components = {
        "cpu": _score_lower_better(
            float(cpu_percent),
            35,
            90,
        ),
        "memory": _score_lower_better(
            float(memory_growth_mb),
            64,
            1024,
        ),
        "polling": _score_lower_better(
            float(polling_delay_seconds),
            35,
            180,
        ),
        "broker_latency": (
            _score_lower_better(
                float(broker_latency_ms),
                500,
                5000,
            )
        ),
        "errors": max(
            0.0,
            100.0 - int(error_count) * 20,
        ),
        "freshness": max(
            0.0,
            100.0
            - int(stale_source_count) * 50,
        ),
    }

    weights = {
        "cpu": 0.15,
        "memory": 0.15,
        "polling": 0.25,
        "broker_latency": 0.20,
        "errors": 0.15,
        "freshness": 0.10,
    }
    total = sum(
        components[name] * weights[name]
        for name in components
    )
    score = round(total, 2)
    if score >= 85:
        status = "READY"
    elif score >= 60:
        status = "DEGRADED"
    else:
        status = "BLOCKED"

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "score": score,
        "status": status,
        "status_i18n": bilingual(status),
        "components": {
            name: round(value, 2)
            for name, value in components.items()
        },
        "inputs": {
            "cpu_percent": cpu_percent,
            "memory_growth_mb": (
                memory_growth_mb
            ),
            "polling_delay_seconds": (
                polling_delay_seconds
            ),
            "broker_latency_ms": (
                broker_latency_ms
            ),
            "error_count": error_count,
            "stale_source_count": (
                stale_source_count
            ),
        },
        "automatic_recovery_enabled": False,
        "process_restart_enabled": False,
        "broker_write_enabled": False,
    }
