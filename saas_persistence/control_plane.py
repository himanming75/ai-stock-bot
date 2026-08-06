from __future__ import annotations
import secrets
from datetime import datetime, timezone

from .rbac import has_permission
from .repository import SaaSRepository
from .security import SessionSigner, hash_password, verify_password


ALLOWED_ROLES = {
    "OWNER",
    "ADMIN",
    "TRADER",
    "VIEWER",
}

ALLOWED_STRATEGIES = {
    "MOMENTUM",
    "BREAKOUT",
    "MEAN_REVERSION",
    "MULTI_AI",
}


class PersistentSaaSControlPlane:
    def __init__(
        self,
        *,
        repository: SaaSRepository,
        signer: SessionSigner,
    ) -> None:
        self.repository = repository
        self.signer = signer

    def register(
        self,
        *,
        email: str,
        password: str,
        workspace_name: str,
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
            name=workspace_name.strip(),
            owner_user_id=user_id,
        )
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="USER_REGISTERED",
            details={},
        )
        return {
            "user": self._public_user(user),
            "workspace": workspace,
        }

    def login(
        self,
        *,
        email: str,
        password: str,
    ) -> dict:
        user = self.repository.get_user_by_email(email)
        if (
            user is None
            or not user["is_active"]
            or not verify_password(
                password,
                user["password_hash"],
            )
        ):
            raise PermissionError("INVALID_CREDENTIALS")
        return {
            "access_token": self.signer.issue(
                user_id=user["user_id"]
            ),
            "token_type": "Bearer",
            "user": self._public_user(user),
        }

    def authenticate(self, token: str) -> dict:
        payload = self.signer.verify(token)
        user = self.repository.get_user(
            payload["user_id"]
        )
        if user is None or not user["is_active"]:
            raise PermissionError("USER_NOT_ACTIVE")
        return self._public_user(user)

    def list_workspaces(self, *, user_id: str) -> list[dict]:
        return self.repository.list_workspaces_for_user(
            user_id
        )

    def workspace_summary(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> dict:
        membership = self._require(
            user_id=user_id,
            workspace_id=workspace_id,
            permission="workspace.read",
        )
        return {
            "workspace": self.repository.get_workspace(
                workspace_id
            ),
            "membership": membership,
            "settings": self.repository.get_settings(
                workspace_id
            ),
            "members": self.repository.list_members(
                workspace_id
            ),
            "broker_connections": (
                self.repository.list_broker_connections(
                    workspace_id
                )
            ),
            "broker_write_enabled": False,
            "order_submission_enabled": False,
        }

    def update_strategy(
        self,
        *,
        user_id: str,
        workspace_id: str,
        strategy: str,
    ) -> dict:
        self._require(
            user_id=user_id,
            workspace_id=workspace_id,
            permission="strategy.manage",
        )
        normalized = strategy.upper()
        if normalized not in ALLOWED_STRATEGIES:
            raise ValueError("INVALID_STRATEGY")
        settings = self.repository.update_strategy(
            workspace_id=workspace_id,
            strategy=normalized,
        )
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="STRATEGY_UPDATED",
            details={"strategy": normalized},
        )
        return settings

    def update_risk(
        self,
        *,
        user_id: str,
        workspace_id: str,
        risk_profile: str,
        max_position_weight: float,
        daily_loss_limit: float,
    ) -> dict:
        self._require(
            user_id=user_id,
            workspace_id=workspace_id,
            permission="risk.manage",
        )
        if not 0 < max_position_weight <= 0.20:
            raise ValueError("INVALID_MAX_POSITION_WEIGHT")
        if not 0 < daily_loss_limit <= 0.05:
            raise ValueError("INVALID_DAILY_LOSS_LIMIT")
        settings = self.repository.update_risk(
            workspace_id=workspace_id,
            risk_profile=risk_profile.upper(),
            max_position_weight=max_position_weight,
            daily_loss_limit=daily_loss_limit,
        )
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="RISK_UPDATED",
            details={
                "risk_profile": risk_profile.upper(),
                "max_position_weight": max_position_weight,
                "daily_loss_limit": daily_loss_limit,
            },
        )
        return settings

    def add_member(
        self,
        *,
        user_id: str,
        workspace_id: str,
        member_email: str,
        role: str,
    ) -> dict:
        self._require(
            user_id=user_id,
            workspace_id=workspace_id,
            permission="members.manage",
        )
        normalized = role.upper()
        if normalized not in ALLOWED_ROLES:
            raise ValueError("INVALID_ROLE")
        member = self.repository.get_user_by_email(
            member_email
        )
        if member is None:
            raise ValueError("USER_NOT_FOUND")
        result = self.repository.add_member(
            workspace_id=workspace_id,
            user_id=member["user_id"],
            role=normalized,
        )
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="MEMBER_ADDED",
            details={
                "member_user_id": member["user_id"],
                "role": normalized,
            },
        )
        return result

    def add_broker_metadata(
        self,
        *,
        user_id: str,
        workspace_id: str,
        broker: str,
        environment: str,
        account_alias: str,
    ) -> dict:
        self._require(
            user_id=user_id,
            workspace_id=workspace_id,
            permission="broker.manage",
        )
        result = self.repository.add_broker_connection(
            connection_id=f"broker_{secrets.token_hex(6)}",
            workspace_id=workspace_id,
            broker=broker.upper(),
            environment=environment.upper(),
            account_alias=account_alias,
        )
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="BROKER_METADATA_ADDED",
            details={
                "broker": broker.upper(),
                "environment": environment.upper(),
            },
        )
        return result

    def audit_events(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> list[dict]:
        self._require(
            user_id=user_id,
            workspace_id=workspace_id,
            permission="audit.read",
        )
        return self.repository.list_audit_events(
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
            raise PermissionError("WORKSPACE_ACCESS_DENIED")
        if not has_permission(
            membership["role"],
            permission,
        ):
            raise PermissionError("PERMISSION_DENIED")
        return membership

    def _audit(
        self,
        *,
        user_id: str,
        workspace_id: str,
        action: str,
        details: dict,
    ) -> None:
        self.repository.db.append_audit(
            recorded_at=datetime.now(
                timezone.utc
            ).isoformat(),
            user_id=user_id,
            workspace_id=workspace_id,
            action=action,
            details=details,
        )

    @staticmethod
    def _public_user(user: dict) -> dict:
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "is_active": bool(user["is_active"]),
            "created_at": user["created_at"],
        }
