from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any


ROLE_PERMISSIONS = {
    "VIEWER": {
        "VIEW_STATUS",
        "VIEW_AUDIT",
    },
    "OPERATOR": {
        "VIEW_STATUS",
        "VIEW_AUDIT",
        "CREATE_CHANGE_REQUEST",
        "CREATE_RUNTIME_REQUEST",
        "CREATE_EMERGENCY_REQUEST",
    },
    "APPROVER": {
        "VIEW_STATUS",
        "VIEW_AUDIT",
        "REVIEW_CHANGE_REQUEST",
        "REVIEW_RUNTIME_REQUEST",
        "REVIEW_EMERGENCY_REQUEST",
    },
    "ADMIN": {
        "VIEW_STATUS",
        "VIEW_AUDIT",
        "CREATE_CHANGE_REQUEST",
        "CREATE_RUNTIME_REQUEST",
        "CREATE_EMERGENCY_REQUEST",
        "REVIEW_CHANGE_REQUEST",
        "REVIEW_RUNTIME_REQUEST",
        "REVIEW_EMERGENCY_REQUEST",
        "MANAGE_ROLES_PREVIEW",
    },
}


@dataclass(frozen=True)
class OperatorIdentity:
    operator_id: str
    role: str

    def permissions(self) -> set[str]:
        if self.role not in ROLE_PERMISSIONS:
            raise ValueError("UNKNOWN_OPERATOR_ROLE")
        return set(ROLE_PERMISSIONS[self.role])


class PermissionGuard:
    def require(self, identity: OperatorIdentity, permission: str) -> None:
        if permission not in identity.permissions():
            raise PermissionError(
                f"PERMISSION_DENIED:{identity.role}:{permission}"
            )


class SessionManager:
    def issue(
        self,
        *,
        identity: OperatorIdentity,
        ttl_minutes: int = 30,
    ) -> dict[str, Any]:
        if ttl_minutes < 1 or ttl_minutes > 120:
            raise ValueError("SESSION_TTL_OUT_OF_RANGE")

        now = datetime.now(timezone.utc)
        raw_token = secrets.token_urlsafe(32)
        return {
            "operator_id": identity.operator_id,
            "role": identity.role,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
            "token_fingerprint": hashlib.sha256(
                raw_token.encode("utf-8")
            ).hexdigest()[:24],
            "raw_token_printed": False,
            "raw_token_stored": False,
            "session_active_in_runtime": False,
        }


class ConfirmationChallenge:
    def create(
        self,
        *,
        request_id: str,
        operation: str,
    ) -> dict[str, Any]:
        nonce = secrets.token_hex(16)
        digest = hashlib.sha256(
            f"{request_id}:{operation}:{nonce}".encode("utf-8")
        ).hexdigest()
        return {
            "request_id": request_id,
            "operation": operation,
            "challenge_fingerprint": digest[:24],
            "expires_in_seconds": 300,
            "actual_confirmation_accepted": False,
            "actual_change_applied": False,
        }


class SensitiveValueRedactor:
    SENSITIVE_NAMES = {
        "api_key",
        "secret",
        "secret_key",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "credential",
    }

    def redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                normalized = key.lower()
                if any(name in normalized for name in self.SENSITIVE_NAMES):
                    result[key] = "[REDACTED]"
                else:
                    result[key] = self.redact(item)
            return result
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        return value
