from __future__ import annotations
import base64
import hashlib
import hmac
import os
import secrets
import struct
import time


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = 210_000,
) -> str:
    if len(password) < 12:
        raise ValueError("PASSWORD_TOO_SHORT")
    if not any(ch.isupper() for ch in password):
        raise ValueError("PASSWORD_REQUIRES_UPPERCASE")
    if not any(ch.islower() for ch in password):
        raise ValueError("PASSWORD_REQUIRES_LOWERCASE")
    if not any(ch.isdigit() for ch in password):
        raise ValueError("PASSWORD_REQUIRES_DIGIT")
    if not any(not ch.isalnum() for ch in password):
        raise ValueError("PASSWORD_REQUIRES_SYMBOL")

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
        algorithm, iterations, salt, _ = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        calculated = hash_password(
            password,
            salt=base64.urlsafe_b64decode(
                salt.encode()
            ),
            iterations=int(iterations),
        )
        return hmac.compare_digest(calculated, encoded)
    except Exception:
        return False


def random_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def token_hash(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def generate_totp_secret() -> str:
    return base64.b32encode(
        os.urandom(20)
    ).decode("ascii").rstrip("=")


def totp_code(
    secret: str,
    *,
    at_time: int | None = None,
    period: int = 30,
    digits: int = 6,
) -> str:
    moment = int(at_time or time.time())
    counter = moment // period
    padding = "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(secret + padding)
    message = struct.pack(">Q", counter)
    digest = hmac.new(
        key,
        message,
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    value = (
        struct.unpack(
            ">I",
            digest[offset:offset + 4],
        )[0]
        & 0x7FFFFFFF
    )
    return str(value % (10 ** digits)).zfill(digits)


def verify_totp(
    secret: str,
    code: str,
    *,
    at_time: int | None = None,
    window: int = 1,
) -> bool:
    moment = int(at_time or time.time())
    for step in range(-window, window + 1):
        expected = totp_code(
            secret,
            at_time=moment + step * 30,
        )
        if hmac.compare_digest(expected, str(code)):
            return True
    return False
