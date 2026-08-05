from __future__ import annotations
import hashlib
from typing import Any


def fingerprint(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def evaluate_credentials(
    *,
    paper_key: str,
    paper_secret: str,
    live_key: str,
    live_secret: str,
) -> dict[str, Any]:
    paper_key_fp = fingerprint(paper_key)
    paper_secret_fp = fingerprint(paper_secret)
    live_key_fp = fingerprint(live_key)
    live_secret_fp = fingerprint(live_secret)

    checks = {
        "paper_key_present": bool(paper_key),
        "paper_secret_present": bool(paper_secret),
        "live_key_present_or_deferred": True,
        "live_secret_present_or_deferred": True,
        "paper_live_key_separated": (
            not live_key or paper_key_fp != live_key_fp
        ),
        "paper_live_secret_separated": (
            not live_secret or paper_secret_fp != live_secret_fp
        ),
        "raw_credentials_not_returned": True,
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "paper_key_fingerprint": paper_key_fp,
        "paper_secret_fingerprint": paper_secret_fp,
        "live_key_fingerprint": live_key_fp,
        "live_secret_fingerprint": live_secret_fp,
        "valid": all(checks.values()),
    }
