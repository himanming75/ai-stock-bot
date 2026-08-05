from __future__ import annotations


SCENARIOS = [
    {"name": "HEALTHY", "trigger": "HEALTHY", "attempt": 0},
    {
        "name": "TOKEN_RENEW",
        "trigger": "TOKEN_RENEW_REQUIRED",
        "attempt": 0,
    },
    {
        "name": "TOKEN_REVOKED",
        "trigger": "TOKEN_REVOKED",
        "attempt": 0,
    },
    {
        "name": "RATE_LIMIT_SECOND_ATTEMPT",
        "trigger": "RATE_LIMIT",
        "attempt": 1,
    },
    {
        "name": "SERVER_ERROR_THIRD_ATTEMPT",
        "trigger": "SERVER_ERROR",
        "attempt": 2,
    },
    {
        "name": "ACCOUNT_RESTRICTED",
        "trigger": "ACCOUNT_RESTRICTED",
        "attempt": 0,
    },
    {
        "name": "SNAPSHOT_FAILED",
        "trigger": "SNAPSHOT_INTEGRITY_FAILED",
        "attempt": 0,
    },
    {
        "name": "UNKNOWN",
        "trigger": "UNCLASSIFIED_FAILURE",
        "attempt": 0,
    },
]
