from __future__ import annotations
from .models import ModuleHealth


CRITICAL_MODULES = {
    "MARKET_DATA",
    "RISK_ENGINE",
    "PORTFOLIO_AI",
    "BROKER_ADAPTER",
    "LEDGER",
}


def aggregate_health(
    items: list[ModuleHealth],
) -> dict:
    status_order = {
        "HEALTHY": 0,
        "DEGRADED": 1,
        "UNHEALTHY": 2,
        "CRITICAL": 3,
    }

    worst = "HEALTHY"
    critical_modules = []
    degraded_modules = []

    for item in items:
        value = item.status.upper()
        if status_order.get(value, 3) > status_order[worst]:
            worst = value
        if value == "CRITICAL":
            critical_modules.append(item.name)
        elif value in {"DEGRADED", "UNHEALTHY"}:
            degraded_modules.append(item.name)

    emergency_stop = any(
        name in CRITICAL_MODULES
        for name in critical_modules
    )

    return {
        "overall_status": worst,
        "critical_modules": critical_modules,
        "degraded_modules": degraded_modules,
        "emergency_stop_required": emergency_stop,
    }
