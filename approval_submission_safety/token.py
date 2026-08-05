from __future__ import annotations
from datetime import datetime, timedelta, timezone

from .crypto import fingerprint, nonce, sign_payload, verify_signature
from .models import parse_time


def create_token(scope: dict, secret: str, ttl_seconds: int = 300) -> dict:
    now = datetime.now(timezone.utc)
    body = {
        "token_version": 1,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "nonce": nonce(),
        "scope": scope,
        "scope_fingerprint": fingerprint(scope),
        "single_use": True,
    }
    return {
        "body": body,
        "signature": sign_payload(body, secret),
    }


def validate_token(
    token: dict,
    *,
    expected_scope: dict,
    secret: str,
    consumed_nonces: set[str],
    now: datetime,
) -> list[str]:
    blockers = []
    body = token.get("body", {})
    signature = token.get("signature", "")

    if body.get("token_version") != 1:
        blockers.append("TOKEN_VERSION_INVALID")
    if not verify_signature(body, signature, secret):
        blockers.append("TOKEN_SIGNATURE_INVALID")
    if body.get("scope_fingerprint") != fingerprint(expected_scope):
        blockers.append("TOKEN_SCOPE_MISMATCH")

    expires_at = parse_time(body.get("expires_at"))
    if not expires_at or now >= expires_at:
        blockers.append("TOKEN_EXPIRED")

    issued_at = parse_time(body.get("issued_at"))
    if not issued_at or issued_at > now:
        blockers.append("TOKEN_ISSUED_AT_INVALID")

    token_nonce = body.get("nonce")
    if not token_nonce:
        blockers.append("TOKEN_NONCE_MISSING")
    elif token_nonce in consumed_nonces:
        blockers.append("TOKEN_NONCE_ALREADY_CONSUMED")

    return blockers
