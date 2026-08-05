from __future__ import annotations


HEALTHY_FIXTURE = {
    "oauth_status": "ACCESS_TOKEN_READY",
    "renew_required": False,
    "revoked": False,
    "latency_ms": 420,
    "successes": 95,
    "failures": 5,
    "rate_limited": False,
    "account_status": "ACTIVE",
    "snapshot_integrity_passed": True,
}

DEGRADED_FIXTURE = {
    "oauth_status": "ACCESS_TOKEN_READY",
    "renew_required": True,
    "revoked": False,
    "latency_ms": 1400,
    "successes": 80,
    "failures": 20,
    "rate_limited": False,
    "account_status": "ACTIVE",
    "snapshot_integrity_passed": True,
}

CRITICAL_FIXTURE = {
    "oauth_status": "ACCESS_TOKEN_READY",
    "renew_required": False,
    "revoked": True,
    "latency_ms": 4500,
    "successes": 20,
    "failures": 80,
    "rate_limited": True,
    "account_status": "RESTRICTED",
    "snapshot_integrity_passed": False,
}
