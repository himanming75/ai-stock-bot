from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any

TOKEN_VERSION = "V392.02A"
TOKEN_SECRET_LABEL = "LOCAL_PAPER_AUTHORIZATION_TOKEN"


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("TOKEN_TIMESTAMP_REQUIRED")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_token_payload(
    authorization_result: dict[str, Any],
    proposal: dict[str, Any],
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    return {
        "token_version": TOKEN_VERSION,
        "authorization_stage": authorization_result.get("stage"),
        "authorization_state": authorization_result.get("state"),
        "authorization_approved": authorization_result.get("authorization_approved"),
        "proposal_id": authorization_result.get("proposal_id"),
        "proposal_hash": authorization_result.get("proposal_hash"),
        "policy_hash": authorization_result.get("policy_hash"),
        "proposal_symbol": proposal.get("symbol"),
        "proposal_side": proposal.get("side"),
        "target_environment": "PAPER",
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
        "single_use": True,
    }


def sign_token(payload: dict[str, Any], secret: str) -> str:
    if not secret:
        raise ValueError("TOKEN_SECRET_REQUIRED")
    message = _canonical(payload).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def create_token(
    authorization_result: dict[str, Any],
    proposal: dict[str, Any],
    secret: str,
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    payload = build_token_payload(
        authorization_result=authorization_result,
        proposal=proposal,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=nonce,
    )
    signature = sign_token(payload, secret)
    token_id = hashlib.sha256(
        f"{payload['proposal_id']}|{nonce}|{signature}".encode("utf-8")
    ).hexdigest()
    return {
        "token_id": token_id,
        "payload": payload,
        "signature": signature,
    }


def validate_token(
    token: dict[str, Any],
    authorization_result: dict[str, Any],
    proposal: dict[str, Any],
    secret: str,
    consumed_token_ids: set[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    payload = token.get("payload", {})
    token_id = str(token.get("token_id", ""))
    signature = str(token.get("signature", ""))

    expected_signature = sign_token(payload, secret)
    issued_at = _parse_utc(payload.get("issued_at"))
    expires_at = _parse_utc(payload.get("expires_at"))

    checks = {
        "token_id_present": bool(token_id),
        "token_version_valid": payload.get("token_version") == TOKEN_VERSION,
        "signature_valid": hmac.compare_digest(signature, expected_signature),
        "authorization_stage_valid": (
            authorization_result.get("stage") == "V392.01A"
        ),
        "authorization_approved": (
            authorization_result.get("authorization_approved") is True
        ),
        "authorization_allowed": (
            authorization_result.get("execution_authorization_allowed") is True
        ),
        "proposal_id_matches": (
            payload.get("proposal_id") == authorization_result.get("proposal_id")
            == proposal.get("proposal_id")
        ),
        "proposal_hash_matches": (
            payload.get("proposal_hash") == authorization_result.get("proposal_hash")
        ),
        "policy_hash_matches": (
            payload.get("policy_hash") == authorization_result.get("policy_hash")
        ),
        "symbol_matches": payload.get("proposal_symbol") == proposal.get("symbol"),
        "side_matches": payload.get("proposal_side") == proposal.get("side"),
        "paper_only": payload.get("target_environment") == "PAPER",
        "single_use": payload.get("single_use") is True,
        "not_used": token_id not in consumed_token_ids,
        "issued_not_in_future": issued_at <= current_time,
        "not_expired": current_time <= expires_at,
        "positive_lifetime": expires_at > issued_at,
    }

    approved = all(checks.values())

    return {
        "state": (
            "AUTHORIZATION_TOKEN_ACCEPTED"
            if approved
            else "AUTHORIZATION_TOKEN_REJECTED"
        ),
        "approved": approved,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "token_id": token_id,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "consumed": approved,
        "replay_detected": not checks["not_used"],
        "required_action": (
            "ALLOW_DISPATCH_GATE_PREPARATION"
            if approved
            else "BLOCK_DISPATCH_PREPARATION"
        ),
    }
