from __future__ import annotations
from .models import HealthSignal


def oauth_signal(status: str, renew_required: bool, revoked: bool) -> HealthSignal:
    if revoked:
        return HealthSignal(
            "OAUTH", "CRITICAL", 0, 25, "Access token revoked"
        )
    if status not in {"ACCESS_TOKEN_READY", "ACTIVE"}:
        return HealthSignal(
            "OAUTH", "UNHEALTHY", 40, 25, "Access token unavailable"
        )
    if renew_required:
        return HealthSignal(
            "OAUTH", "DEGRADED", 70, 25, "Token renewal required"
        )
    return HealthSignal(
        "OAUTH", "HEALTHY", 100, 25, "OAuth session healthy"
    )


def latency_signal(latency_ms: int) -> HealthSignal:
    if latency_ms <= 500:
        return HealthSignal(
            "LATENCY", "HEALTHY", 100, 15, f"{latency_ms} ms"
        )
    if latency_ms <= 1500:
        return HealthSignal(
            "LATENCY", "DEGRADED", 75, 15, f"{latency_ms} ms"
        )
    if latency_ms <= 3000:
        return HealthSignal(
            "LATENCY", "UNHEALTHY", 45, 15, f"{latency_ms} ms"
        )
    return HealthSignal(
        "LATENCY", "CRITICAL", 10, 15, f"{latency_ms} ms"
    )


def error_rate_signal(successes: int, failures: int) -> HealthSignal:
    total = successes + failures
    rate = failures / total if total else 1.0
    if rate <= 0.05:
        return HealthSignal(
            "ERROR_RATE", "HEALTHY", 100, 20, f"{rate:.2%}"
        )
    if rate <= 0.20:
        return HealthSignal(
            "ERROR_RATE", "DEGRADED", 75, 20, f"{rate:.2%}"
        )
    if rate <= 0.50:
        return HealthSignal(
            "ERROR_RATE", "UNHEALTHY", 40, 20, f"{rate:.2%}"
        )
    return HealthSignal(
        "ERROR_RATE", "CRITICAL", 0, 20, f"{rate:.2%}"
    )


def rate_limit_signal(rate_limited: bool) -> HealthSignal:
    return (
        HealthSignal(
            "RATE_LIMIT", "UNHEALTHY", 35, 10, "Rate limit active"
        )
        if rate_limited
        else HealthSignal(
            "RATE_LIMIT", "HEALTHY", 100, 10, "No rate limit"
        )
    )


def account_status_signal(status: str) -> HealthSignal:
    value = str(status or "UNKNOWN").upper()
    if value in {"ACTIVE", "OPEN"}:
        return HealthSignal(
            "ACCOUNT_STATUS", "HEALTHY", 100, 20, value
        )
    if value in {"RESTRICTED", "SUSPENDED", "BLOCKED"}:
        return HealthSignal(
            "ACCOUNT_STATUS", "CRITICAL", 0, 20, value
        )
    return HealthSignal(
        "ACCOUNT_STATUS", "UNHEALTHY", 40, 20, value
    )


def snapshot_integrity_signal(passed: bool) -> HealthSignal:
    return (
        HealthSignal(
            "SNAPSHOT_INTEGRITY", "HEALTHY", 100, 10, "Snapshot valid"
        )
        if passed
        else HealthSignal(
            "SNAPSHOT_INTEGRITY", "CRITICAL", 0, 10, "Snapshot invalid"
        )
    )
