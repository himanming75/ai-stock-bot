from __future__ import annotations
import hashlib
import hmac
import json
import secrets


def canonical_json(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def fingerprint(payload) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sign_payload(payload, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload, signature: str, secret: str) -> bool:
    return hmac.compare_digest(sign_payload(payload, secret), signature)


def nonce() -> str:
    return secrets.token_hex(16)
