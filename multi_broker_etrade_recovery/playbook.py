from __future__ import annotations
from .models import RecoveryStep


PLAYBOOK = (
    RecoveryStep(
        name="TOKEN_RENEW",
        action="Renew the current E*TRADE access token",
        automatic=True,
        max_attempts=1,
        backoff_seconds=(0,),
        requires_operator=False,
    ),
    RecoveryStep(
        name="OAUTH_REAUTHORIZATION",
        action="Run browser authorization and verification-code exchange",
        automatic=False,
        max_attempts=1,
        backoff_seconds=(0,),
        requires_operator=True,
    ),
    RecoveryStep(
        name="RATE_LIMIT_BACKOFF",
        action="Pause reads and retry after a controlled delay",
        automatic=True,
        max_attempts=3,
        backoff_seconds=(60, 180, 300),
        requires_operator=False,
    ),
    RecoveryStep(
        name="TRANSIENT_RETRY",
        action="Retry read after server, network, or timeout failure",
        automatic=True,
        max_attempts=3,
        backoff_seconds=(5, 15, 45),
        requires_operator=False,
    ),
    RecoveryStep(
        name="ACCOUNT_RESTRICTION",
        action="Keep all routes blocked and contact E*TRADE support",
        automatic=False,
        max_attempts=0,
        backoff_seconds=(),
        requires_operator=True,
    ),
    RecoveryStep(
        name="SNAPSHOT_REVALIDATION",
        action="Reload account data and rerun snapshot integrity checks",
        automatic=True,
        max_attempts=2,
        backoff_seconds=(5, 15),
        requires_operator=False,
    ),
)
