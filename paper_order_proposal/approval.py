from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib


def create_token(proposal_hash: str, ttl_seconds: int, nonce: str) -> dict:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(seconds=ttl_seconds)
    token_material = f"{proposal_hash}:{nonce}:{issued_at.isoformat()}:{expires_at.isoformat()}"
    token = hashlib.sha256(token_material.encode("utf-8")).hexdigest()
    return {
        "approval_token": token,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "ttl_seconds": ttl_seconds,
        "approved": False,
        "approval_required": True,
    }


def verify_token(record: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
    except Exception:
        return {"valid": False, "expired": True, "reason": "INVALID_EXPIRY"}
    expired = now >= expires_at
    return {
        "valid": bool(record.get("approval_token")) and not expired,
        "expired": expired,
        "reason": "EXPIRED" if expired else "",
    }
