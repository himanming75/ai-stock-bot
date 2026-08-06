from __future__ import annotations
import os


REQUIRED_PRODUCTION_ENV = {
    "APP_ENV",
    "APP_SECRET_KEY",
    "DATABASE_URL",
    "PUBLIC_BASE_URL",
    "TRUSTED_PROXY_COUNT",
}


def validate_environment(
    env: dict[str, str] | None = None,
) -> dict:
    source = env or dict(os.environ)
    missing = sorted(
        key
        for key in REQUIRED_PRODUCTION_ENV
        if not source.get(key)
    )
    insecure = []

    if source.get("APP_ENV") == "production":
        if source.get("PUBLIC_BASE_URL", "").startswith(
            "http://"
        ):
            insecure.append("PUBLIC_BASE_URL_NOT_HTTPS")
        if len(source.get("APP_SECRET_KEY", "")) < 32:
            insecure.append("APP_SECRET_KEY_TOO_SHORT")

    return {
        "missing": missing,
        "insecure": insecure,
        "valid": not missing and not insecure,
    }
