from __future__ import annotations
from .models import RecoveryDecision


def decide_recovery(trigger: str, attempt: int = 0) -> RecoveryDecision:
    value = str(trigger or "UNKNOWN").upper()

    if value == "TOKEN_RENEW_REQUIRED":
        return RecoveryDecision(
            trigger=value,
            state="RENEWING_TOKEN",
            read_allowed=False,
            write_allowed=False,
            next_action="RENEW_ACCESS_TOKEN",
            retry_after_seconds=0,
            requires_operator=False,
        )

    if value in {"TOKEN_REVOKED", "TOKEN_EXPIRED", "OAUTH_INVALID"}:
        return RecoveryDecision(
            trigger=value,
            state="REAUTHORIZATION_REQUIRED",
            read_allowed=False,
            write_allowed=False,
            next_action="START_OAUTH_REAUTHORIZATION",
            retry_after_seconds=0,
            requires_operator=True,
        )

    if value == "RATE_LIMIT":
        schedule = (60, 180, 300)
        delay = schedule[min(attempt, len(schedule) - 1)]
        return RecoveryDecision(
            trigger=value,
            state="RATE_LIMIT_BACKOFF",
            read_allowed=False,
            write_allowed=False,
            next_action="WAIT_AND_RETRY_READ",
            retry_after_seconds=delay,
            requires_operator=False,
        )

    if value in {"SERVER_ERROR", "NETWORK_ERROR", "TIMEOUT"}:
        schedule = (5, 15, 45)
        delay = schedule[min(attempt, len(schedule) - 1)]
        return RecoveryDecision(
            trigger=value,
            state="TRANSIENT_RETRY",
            read_allowed=False,
            write_allowed=False,
            next_action="RETRY_READ",
            retry_after_seconds=delay,
            requires_operator=False,
        )

    if value in {"ACCOUNT_RESTRICTED", "ACCOUNT_BLOCKED", "ACCOUNT_SUSPENDED"}:
        return RecoveryDecision(
            trigger=value,
            state="MANUAL_ACCOUNT_RECOVERY",
            read_allowed=False,
            write_allowed=False,
            next_action="CONTACT_ETRADE_SUPPORT",
            retry_after_seconds=0,
            requires_operator=True,
        )

    if value == "SNAPSHOT_INTEGRITY_FAILED":
        return RecoveryDecision(
            trigger=value,
            state="SNAPSHOT_REVALIDATION",
            read_allowed=False,
            write_allowed=False,
            next_action="RELOAD_AND_REVALIDATE_SNAPSHOT",
            retry_after_seconds=5,
            requires_operator=False,
        )

    if value == "HEALTHY":
        return RecoveryDecision(
            trigger=value,
            state="READ_ONLY_OPERATIONAL",
            read_allowed=True,
            write_allowed=False,
            next_action="CONTINUE_MONITORING",
            retry_after_seconds=0,
            requires_operator=False,
        )

    return RecoveryDecision(
        trigger=value,
        state="FAILSAFE_BLOCKED",
        read_allowed=False,
        write_allowed=False,
        next_action="REVIEW_UNKNOWN_FAILURE",
        retry_after_seconds=0,
        requires_operator=True,
    )
