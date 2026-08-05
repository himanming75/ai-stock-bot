from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any


TOKEN_VERSION = "V392.07A"


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("RELEASE_TOKEN_TIMESTAMP_REQUIRED")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_release_token_payload(
    release_result: dict[str, Any],
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    evaluation = release_result.get("evaluation", {})
    return {
        "token_version": TOKEN_VERSION,
        "release_stage": release_result.get("stage"),
        "release_state": release_result.get("state"),
        "release_authorized": release_result.get("queue_release_authorized"),
        "release_id": evaluation.get("release_id"),
        "dispatch_id": evaluation.get("dispatch_id"),
        "token_id": evaluation.get("token_id"),
        "proposal_id": evaluation.get("proposal_id"),
        "queue_hash": evaluation.get("queue_hash"),
        "head_entry_hash": evaluation.get("head_entry_hash"),
        "target_environment": "PAPER",
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
        "single_use": True,
    }


def sign_release_token(payload: dict[str, Any], secret: str) -> str:
    if not secret:
        raise ValueError("RELEASE_TOKEN_SECRET_REQUIRED")
    return hmac.new(
        secret.encode("utf-8"),
        _canonical(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_release_token(
    release_result: dict[str, Any],
    secret: str,
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    payload = build_release_token_payload(
        release_result=release_result,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=nonce,
    )
    signature = sign_release_token(payload, secret)
    release_token_id = hashlib.sha256(
        f"{payload['release_id']}|{nonce}|{signature}".encode("utf-8")
    ).hexdigest()
    return {
        "release_token_id": release_token_id,
        "payload": payload,
        "signature": signature,
    }


def validate_release_token(
    release_token: dict[str, Any],
    release_result: dict[str, Any],
    secret: str,
    consumed_release_token_ids: set[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    payload = release_token.get("payload", {})
    release_token_id = str(release_token.get("release_token_id", ""))
    signature = str(release_token.get("signature", ""))
    evaluation = release_result.get("evaluation", {})

    expected_signature = sign_release_token(payload, secret)
    issued_at = _parse_utc(payload.get("issued_at"))
    expires_at = _parse_utc(payload.get("expires_at"))

    checks = {
        "release_token_id_present": bool(release_token_id),
        "token_version_valid": payload.get("token_version") == TOKEN_VERSION,
        "signature_valid": hmac.compare_digest(signature, expected_signature),
        "release_stage_valid": release_result.get("stage") == "V392.06A",
        "release_status_pass": release_result.get("status") == "PASS",
        "release_state_ready": (
            release_result.get("state") == "QUEUE_RELEASE_AUTHORIZATION_READY"
        ),
        "release_authorized": release_result.get("queue_release_authorized") is True,
        "release_token_preparation_allowed": (
            release_result.get("release_token_preparation_allowed") is True
        ),
        "release_id_matches": (
            payload.get("release_id") == evaluation.get("release_id")
        ),
        "dispatch_id_matches": (
            payload.get("dispatch_id") == evaluation.get("dispatch_id")
        ),
        "token_id_matches": payload.get("token_id") == evaluation.get("token_id"),
        "proposal_id_matches": (
            payload.get("proposal_id") == evaluation.get("proposal_id")
        ),
        "queue_hash_matches": (
            payload.get("queue_hash") == evaluation.get("queue_hash")
        ),
        "head_entry_hash_matches": (
            payload.get("head_entry_hash") == evaluation.get("head_entry_hash")
        ),
        "paper_only": payload.get("target_environment") == "PAPER",
        "single_use": payload.get("single_use") is True,
        "not_used": release_token_id not in consumed_release_token_ids,
        "issued_not_in_future": issued_at <= current_time,
        "not_expired": current_time <= expires_at,
        "positive_lifetime": expires_at > issued_at,
    }

    approved = all(checks.values())

    return {
        "state": (
            "RELEASE_TOKEN_ACCEPTED"
            if approved
            else "RELEASE_TOKEN_REJECTED"
        ),
        "approved": approved,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "release_token_id": release_token_id,
        "release_id": payload.get("release_id"),
        "dispatch_id": payload.get("dispatch_id"),
        "proposal_id": payload.get("proposal_id"),
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "consumed": approved,
        "replay_detected": not checks["not_used"],
        "required_action": (
            "ALLOW_LOCAL_DISPATCH_RELEASE_GATE"
            if approved
            else "BLOCK_LOCAL_DISPATCH_RELEASE"
        ),
    }
