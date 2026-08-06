from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import secrets
import time


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = 210_000,
) -> str:
    if len(password) < 10:
        raise ValueError("PASSWORD_TOO_SHORT")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return (
        f"pbkdf2_sha256${iterations}$"
        f"{base64.urlsafe_b64encode(salt).decode()}$"
        f"{base64.urlsafe_b64encode(digest).decode()}"
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        calculated = hash_password(
            password,
            salt=base64.urlsafe_b64decode(
                salt.encode()
            ),
            iterations=int(iterations),
        )
        return hmac.compare_digest(
            calculated,
            encoded,
        )
    except (ValueError, TypeError):
        return False


class SessionSigner:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 32:
            raise ValueError("SESSION_SECRET_TOO_SHORT")
        self.secret = secret

    def issue(
        self,
        *,
        user_id: str,
        ttl_seconds: int = 3600,
    ) -> str:
        payload = {
            "user_id": user_id,
            "expires_at": int(time.time())
            + ttl_seconds,
            "nonce": secrets.token_hex(8),
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        body = base64.urlsafe_b64encode(
            raw
        ).decode()
        signature = hmac.new(
            self.secret,
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{body}.{signature}"

    def verify(self, token: str) -> dict:
        try:
            body, signature = token.rsplit(".", 1)
            expected = hmac.new(
                self.secret,
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(
                signature,
                expected,
            ):
                raise ValueError("INVALID_SIGNATURE")
            payload = json.loads(
                base64.urlsafe_b64decode(
                    body.encode()
                )
            )
            if int(payload["expires_at"]) < int(
                time.time()
            ):
                raise ValueError("SESSION_EXPIRED")
            return payload
        except Exception as exc:
            raise ValueError(
                "INVALID_SESSION"
            ) from exc
