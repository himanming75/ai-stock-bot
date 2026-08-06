from __future__ import annotations
import json
import secrets
from datetime import datetime, timedelta, timezone

from .crypto import (
    generate_totp_secret,
    hash_password,
    random_token,
    token_hash,
    verify_password,
    verify_totp,
)
from .rbac import has_permission
from .repository import SecurityRepository, utc_now


class SaaSSecurityControlPlane:
    def __init__(
        self,
        repository: SecurityRepository,
        *,
        max_failed_logins: int = 5,
    ) -> None:
        self.repository = repository
        self.max_failed_logins = max_failed_logins

    def register(
        self,
        *,
        email: str,
        password: str,
        workspace_name: str,
        ip_address: str = "127.0.0.1",
        user_agent: str = "LOCAL",
    ) -> dict:
        if self.repository.get_user_by_email(email):
            raise ValueError("EMAIL_ALREADY_EXISTS")

        user_id = f"usr_{secrets.token_hex(8)}"
        workspace_id = f"ws_{secrets.token_hex(8)}"
        user = self.repository.create_user(
            user_id=user_id,
            email=email,
            password_hash=hash_password(password),
        )
        workspace = self.repository.create_workspace(
            workspace_id=workspace_id,
            name=workspace_name,
            owner_user_id=user_id,
        )
        verification = self.create_email_verification_token(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._audit(
            actor_user_id=user_id,
            workspace_id=workspace_id,
            action="USER_REGISTERED",
            ip_address=ip_address,
            user_agent=user_agent,
            details={},
        )
        return {
            "user": self._public_user(user),
            "workspace": workspace,
            "email_verification_token": verification[
                "token"
            ],
            "email_delivery_performed": False,
        }

    def login(
        self,
        *,
        email: str,
        password: str,
        mfa_code: str | None = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "LOCAL",
    ) -> dict:
        user = self.repository.get_user_by_email(email)
        if user is None:
            self._audit(
                actor_user_id=None,
                workspace_id=None,
                action="LOGIN_FAILED_UNKNOWN_USER",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email.lower().strip()},
            )
            raise PermissionError("INVALID_CREDENTIALS")

        if not user["is_active"]:
            raise PermissionError("USER_DISABLED")
        if user["is_locked"]:
            raise PermissionError("USER_LOCKED")

        if not verify_password(
            password,
            user["password_hash"],
        ):
            failures = int(
                user["failed_login_count"]
            ) + 1
            locked = failures >= self.max_failed_logins
            self.repository.update_login_failure(
                user_id=user["user_id"],
                failure_count=failures,
                locked=locked,
            )
            self._audit(
                actor_user_id=user["user_id"],
                workspace_id=None,
                action=(
                    "ACCOUNT_LOCKED"
                    if locked
                    else "LOGIN_FAILED"
                ),
                ip_address=ip_address,
                user_agent=user_agent,
                details={"failed_login_count": failures},
            )
            raise PermissionError(
                "USER_LOCKED"
                if locked
                else "INVALID_CREDENTIALS"
            )

        if user["mfa_enabled"]:
            if not mfa_code:
                raise PermissionError("MFA_REQUIRED")
            if not verify_totp(
                user["mfa_secret"],
                mfa_code,
            ):
                raise PermissionError("INVALID_MFA_CODE")

        self.repository.reset_login_failures(
            user["user_id"]
        )

        raw_token = random_token("session")
        session_id = f"sess_{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=8)
        session = self.repository.create_session(
            session_id=session_id,
            user_id=user["user_id"],
            token_hash_value=token_hash(raw_token),
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )
        self._audit(
            actor_user_id=user["user_id"],
            workspace_id=None,
            action="LOGIN_SUCCESS",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"session_id": session_id},
        )
        return {
            "access_token": raw_token,
            "token_type": "Bearer",
            "session": session,
            "user": self._public_user(
                self.repository.get_user(
                    user["user_id"]
                )
            ),
        }

    def authenticate(self, token: str) -> dict:
        session = self.repository.get_session_by_hash(
            token_hash(token)
        )
        if session is None:
            raise PermissionError("INVALID_SESSION")
        if session["revoked_at"]:
            raise PermissionError("SESSION_REVOKED")
        if datetime.fromisoformat(
            session["expires_at"]
        ) <= datetime.now(timezone.utc):
            raise PermissionError("SESSION_EXPIRED")
        user = self.repository.get_user(
            session["user_id"]
        )
        if (
            user is None
            or not user["is_active"]
            or user["is_locked"]
        ):
            raise PermissionError("USER_NOT_AVAILABLE")
        return self._public_user(user)

    def list_sessions(self, *, user_id: str) -> list[dict]:
        return self.repository.list_sessions(user_id)

    def revoke_session(
        self,
        *,
        user_id: str,
        session_id: str,
    ) -> None:
        session = self.repository.get_session(session_id)
        if session is None or session["user_id"] != user_id:
            raise PermissionError("SESSION_ACCESS_DENIED")
        self.repository.revoke_session(session_id)

    def revoke_all_sessions(
        self,
        *,
        user_id: str,
    ) -> None:
        self.repository.revoke_all_sessions(user_id)

    def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> None:
        user = self.repository.get_user(user_id)
        if not verify_password(
            current_password,
            user["password_hash"],
        ):
            raise PermissionError(
                "CURRENT_PASSWORD_INVALID"
            )
        self.repository.update_password(
            user_id=user_id,
            password_hash=hash_password(
                new_password
            ),
        )
        self.repository.revoke_all_sessions(user_id)

    def create_password_reset_token(
        self,
        *,
        email: str,
        ip_address: str = "127.0.0.1",
        user_agent: str = "LOCAL",
    ) -> dict:
        user = self.repository.get_user_by_email(email)
        if user is None:
            return {
                "accepted": True,
                "token": None,
                "email_delivery_performed": False,
            }
        raw = random_token("reset")
        token_id = f"prt_{secrets.token_hex(8)}"
        expires = datetime.now(
            timezone.utc
        ) + timedelta(minutes=30)
        self.repository.create_recovery_token(
            table="password_reset_tokens",
            token_id=token_id,
            user_id=user["user_id"],
            token_hash_value=token_hash(raw),
            expires_at=expires.isoformat(),
        )
        self._audit(
            actor_user_id=user["user_id"],
            workspace_id=None,
            action="PASSWORD_RESET_REQUESTED",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"token_id": token_id},
        )
        return {
            "accepted": True,
            "token": raw,
            "email_delivery_performed": False,
        }

    def reset_password(
        self,
        *,
        token: str,
        new_password: str,
    ) -> None:
        item = self.repository.get_recovery_token(
            table="password_reset_tokens",
            token_hash_value=token_hash(token),
        )
        self._validate_recovery_token(item)
        self.repository.update_password(
            user_id=item["user_id"],
            password_hash=hash_password(
                new_password
            ),
        )
        self.repository.use_recovery_token(
            table="password_reset_tokens",
            token_id=item["token_id"],
        )
        self.repository.revoke_all_sessions(
            item["user_id"]
        )

    def create_email_verification_token(
        self,
        *,
        user_id: str,
        ip_address: str = "127.0.0.1",
        user_agent: str = "LOCAL",
    ) -> dict:
        raw = random_token("verify")
        token_id = f"evt_{secrets.token_hex(8)}"
        expires = datetime.now(
            timezone.utc
        ) + timedelta(hours=24)
        self.repository.create_recovery_token(
            table="email_verification_tokens",
            token_id=token_id,
            user_id=user_id,
            token_hash_value=token_hash(raw),
            expires_at=expires.isoformat(),
        )
        return {
            "token": raw,
            "email_delivery_performed": False,
        }

    def verify_email(self, token: str) -> None:
        item = self.repository.get_recovery_token(
            table="email_verification_tokens",
            token_hash_value=token_hash(token),
        )
        self._validate_recovery_token(item)
        self.repository.set_email_verified(
            item["user_id"]
        )
        self.repository.use_recovery_token(
            table="email_verification_tokens",
            token_id=item["token_id"],
        )

    def begin_mfa(self, *, user_id: str) -> dict:
        secret = generate_totp_secret()
        self.repository.set_mfa(
            user_id=user_id,
            secret=secret,
            enabled=False,
        )
        return {
            "secret": secret,
            "provisioning_uri": (
                f"otpauth://totp/AIStockBot:{user_id}"
                f"?secret={secret}&issuer=AIStockBot"
            ),
        }

    def confirm_mfa(
        self,
        *,
        user_id: str,
        code: str,
    ) -> None:
        user = self.repository.get_user(user_id)
        if not user["mfa_secret"]:
            raise ValueError("MFA_NOT_INITIALIZED")
        if not verify_totp(
            user["mfa_secret"],
            code,
        ):
            raise PermissionError("INVALID_MFA_CODE")
        self.repository.set_mfa(
            user_id=user_id,
            secret=user["mfa_secret"],
            enabled=True,
        )

    def disable_mfa(
        self,
        *,
        user_id: str,
    ) -> None:
        self.repository.set_mfa(
            user_id=user_id,
            secret=None,
            enabled=False,
        )

    def create_api_token(
        self,
        *,
        actor_user_id: str,
        workspace_id: str,
        name: str,
        scopes: list[str],
        expires_days: int = 30,
    ) -> dict:
        self._require(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission="tokens.manage",
        )
        allowed_scopes = {
            "workspace.read",
            "audit.read",
            "strategy.read",
            "risk.read",
        }
        if not scopes or not set(scopes).issubset(
            allowed_scopes
        ):
            raise ValueError("INVALID_API_TOKEN_SCOPES")

        raw = random_token("api")
        token_id = f"api_{secrets.token_hex(8)}"
        expires = datetime.now(
            timezone.utc
        ) + timedelta(days=expires_days)
        metadata = self.repository.create_api_token(
            token_id=token_id,
            user_id=actor_user_id,
            workspace_id=workspace_id,
            name=name,
            token_hash_value=token_hash(raw),
            scopes_json=json.dumps(
                sorted(scopes)
            ),
            expires_at=expires.isoformat(),
        )
        return {
            "token": raw,
            "metadata": metadata,
        }

    def revoke_api_token(
        self,
        *,
        actor_user_id: str,
        workspace_id: str,
        token_id: str,
    ) -> None:
        self._require(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission="tokens.manage",
        )
        self.repository.revoke_api_token(token_id)

    def update_member_role(
        self,
        *,
        actor_user_id: str,
        workspace_id: str,
        member_user_id: str,
        role: str,
    ) -> dict:
        self._require(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission="members.manage",
        )
        normalized = role.upper()
        if normalized not in {
            "ADMIN",
            "TRADER",
            "VIEWER",
        }:
            raise ValueError("INVALID_ROLE")
        return self.repository.update_member_role(
            workspace_id=workspace_id,
            user_id=member_user_id,
            role=normalized,
        )

    def admin_set_user_active(
        self,
        *,
        actor_user_id: str,
        workspace_id: str,
        target_user_id: str,
        active: bool,
    ) -> None:
        self._require(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission="admin.manage",
        )
        self.repository.set_active(
            user_id=target_user_id,
            active=active,
        )
        if not active:
            self.repository.revoke_all_sessions(
                target_user_id
            )

    def admin_set_user_locked(
        self,
        *,
        actor_user_id: str,
        workspace_id: str,
        target_user_id: str,
        locked: bool,
    ) -> None:
        self._require(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission="admin.manage",
        )
        self.repository.set_locked(
            user_id=target_user_id,
            locked=locked,
        )

    def admin_dashboard(
        self,
        *,
        actor_user_id: str,
        workspace_id: str,
    ) -> dict:
        self._require(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission="admin.read",
        )
        return self.repository.admin_stats()

    def audit_events(
        self,
        *,
        actor_user_id: str,
        workspace_id: str,
    ) -> list[dict]:
        self._require(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission="audit.read",
        )
        return self.repository.list_audit(
            workspace_id
        )

    def _require(
        self,
        *,
        user_id: str,
        workspace_id: str,
        permission: str,
    ) -> dict:
        membership = self.repository.get_membership(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if membership is None:
            raise PermissionError(
                "WORKSPACE_ACCESS_DENIED"
            )
        if not has_permission(
            membership["role"],
            permission,
        ):
            raise PermissionError(
                "PERMISSION_DENIED"
            )
        return membership

    def _audit(
        self,
        *,
        actor_user_id: str | None,
        workspace_id: str | None,
        action: str,
        ip_address: str,
        user_agent: str,
        details: dict,
    ) -> None:
        self.repository.append_audit(
            recorded_at=utc_now(),
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details_json=json.dumps(
                details,
                sort_keys=True,
            ),
        )

    @staticmethod
    def _validate_recovery_token(
        item: dict | None,
    ) -> None:
        if item is None:
            raise PermissionError("INVALID_TOKEN")
        if item["used_at"]:
            raise PermissionError("TOKEN_ALREADY_USED")
        if datetime.fromisoformat(
            item["expires_at"]
        ) <= datetime.now(timezone.utc):
            raise PermissionError("TOKEN_EXPIRED")

    @staticmethod
    def _public_user(user: dict) -> dict:
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "is_active": bool(user["is_active"]),
            "is_locked": bool(user["is_locked"]),
            "email_verified": bool(
                user["email_verified"]
            ),
            "mfa_enabled": bool(
                user["mfa_enabled"]
            ),
        }
