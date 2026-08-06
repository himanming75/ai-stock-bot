from __future__ import annotations
import json
from pathlib import Path
from threading import RLock

from .models import Membership, User, Workspace, WorkspaceSettings


class SaaSStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.lock = RLock()
        self.users: dict[str, User] = {}
        self.workspaces: dict[str, Workspace] = {}
        self.memberships: list[Membership] = []
        self.settings: dict[str, WorkspaceSettings] = {}
        self.audit_events: list[dict] = []

    def add_user(self, user: User) -> None:
        with self.lock:
            if any(
                existing.email.lower() == user.email.lower()
                for existing in self.users.values()
            ):
                raise ValueError("EMAIL_ALREADY_EXISTS")
            self.users[user.user_id] = user

    def add_workspace(
        self,
        workspace: Workspace,
        membership: Membership,
    ) -> None:
        with self.lock:
            self.workspaces[workspace.workspace_id] = workspace
            self.memberships.append(membership)
            self.settings[workspace.workspace_id] = (
                WorkspaceSettings(
                    workspace_id=workspace.workspace_id
                )
            )

    def membership(
        self,
        *,
        workspace_id: str,
        user_id: str,
    ) -> Membership | None:
        return next(
            (
                item
                for item in self.memberships
                if item.workspace_id == workspace_id
                and item.user_id == user_id
            ),
            None,
        )

    def append_audit(self, event: dict) -> None:
        with self.lock:
            self.audit_events.append(dict(event))

    def snapshot(self) -> dict:
        return {
            "users": [
                item.to_dict()
                for item in self.users.values()
            ],
            "workspaces": [
                item.to_dict()
                for item in self.workspaces.values()
            ],
            "memberships": [
                item.to_dict()
                for item in self.memberships
            ],
            "settings": {
                key: value.to_dict()
                for key, value in self.settings.items()
            },
            "audit_events": list(self.audit_events),
        }

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.path.write_text(
            json.dumps(
                self.snapshot(),
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
