from __future__ import annotations
import secrets
from datetime import datetime, timezone

from .models import Membership, User, Workspace
from .rbac import has_permission
from .security import SessionSigner, hash_password, verify_password
from .store import SaaSStore


class SaaSControlPlane:
    def __init__(
        self,
        *,
        store: SaaSStore,
        signer: SessionSigner,
    ) -> None:
        self.store = store
        self.signer = signer

    def register(
        self,
        *,
        email: str,
        password: str,
        workspace_name: str,
    ) -> dict:
        user_id = f"usr_{secrets.token_hex(8)}"
        workspace_id = f"ws_{secrets.token_hex(8)}"
        user = User(
            user_id=user_id,
            email=email.strip().lower(),
            password_hash=hash_password(password),
        )
        workspace = Workspace(
            workspace_id=workspace_id,
            name=workspace_name.strip(),
            owner_user_id=user_id,
        )
        membership = Membership(
            workspace_id=workspace_id,
            user_id=user_id,
            role="OWNER",
        )
        self.store.add_user(user)
        self.store.add_workspace(workspace, membership)
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="USER_REGISTERED",
        )
        return {
            "user": user.to_dict(),
            "workspace": workspace.to_dict(),
        }

    def login(self, *, email: str, password: str) -> str:
        user = next(
            (
                item
                for item in self.store.users.values()
                if item.email == email.strip().lower()
            ),
            None,
        )
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.password_hash)
        ):
            raise PermissionError("INVALID_CREDENTIALS")
        return self.signer.issue(user_id=user.user_id)

    def authenticate(self, token: str) -> User:
        payload = self.signer.verify(token)
        user = self.store.users.get(payload["user_id"])
        if user is None or not user.is_active:
            raise PermissionError("USER_NOT_ACTIVE")
        return user

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
            "workspace": self.store.workspaces[
                workspace_id
            ].to_dict(),
            "membership": membership.to_dict(),
            "settings": self.store.settings[
                workspace_id
            ].to_dict(),
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
        allowed = {
            "MOMENTUM",
            "BREAKOUT",
            "MEAN_REVERSION",
            "MULTI_AI",
        }
        normalized = strategy.upper()
        if normalized not in allowed:
            raise ValueError("INVALID_STRATEGY")
        settings = self.store.settings[workspace_id]
        settings.selected_strategy = normalized
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="STRATEGY_UPDATED",
            details={"strategy": normalized},
        )
        return settings.to_dict()

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
        settings = self.store.settings[workspace_id]
        settings.risk_profile = risk_profile.upper()
        settings.max_position_weight = max_position_weight
        settings.daily_loss_limit = daily_loss_limit
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="RISK_UPDATED",
            details={
                "risk_profile": settings.risk_profile,
                "max_position_weight": max_position_weight,
                "daily_loss_limit": daily_loss_limit,
            },
        )
        return settings.to_dict()

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
        connection = {
            "connection_id": f"broker_{secrets.token_hex(6)}",
            "broker": broker.upper(),
            "environment": environment.upper(),
            "account_alias": account_alias,
            "credential_stored": False,
            "read_only": True,
            "write_enabled": False,
            "status": "METADATA_ONLY",
        }
        self.store.settings[
            workspace_id
        ].broker_connections.append(connection)
        self._audit(
            user_id=user_id,
            workspace_id=workspace_id,
            action="BROKER_METADATA_ADDED",
            details={
                "broker": connection["broker"],
                "environment": connection["environment"],
            },
        )
        return connection

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
        return [
            item
            for item in self.store.audit_events
            if item["workspace_id"] == workspace_id
        ]

    def _require(
        self,
        *,
        user_id: str,
        workspace_id: str,
        permission: str,
    ) -> Membership:
        membership = self.store.membership(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if membership is None:
            raise PermissionError("WORKSPACE_ACCESS_DENIED")
        if not has_permission(membership.role, permission):
            raise PermissionError("PERMISSION_DENIED")
        return membership

    def _audit(
        self,
        *,
        user_id: str,
        workspace_id: str,
        action: str,
        details: dict | None = None,
    ) -> None:
        self.store.append_audit({
            "recorded_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "user_id": user_id,
            "workspace_id": workspace_id,
            "action": action,
            "details": details or {},
        })
