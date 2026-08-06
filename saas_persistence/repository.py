from __future__ import annotations
import json
from datetime import datetime, timezone

from .database import SQLiteDatabase


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SaaSRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.db = database

    def create_user(
        self,
        *,
        user_id: str,
        email: str,
        password_hash: str,
    ) -> dict:
        self.db.execute(
            """
            INSERT INTO users (
                user_id,
                email,
                password_hash,
                is_active,
                created_at
            ) VALUES (?, ?, ?, 1, ?)
            """,
            (
                user_id,
                email.lower().strip(),
                password_hash,
                utc_now(),
            ),
        )
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> dict | None:
        return self.db.query_one(
            """
            SELECT user_id, email, password_hash, is_active, created_at
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )

    def get_user_by_email(self, email: str) -> dict | None:
        return self.db.query_one(
            """
            SELECT user_id, email, password_hash, is_active, created_at
            FROM users
            WHERE email = ?
            """,
            (email.lower().strip(),),
        )

    def create_workspace(
        self,
        *,
        workspace_id: str,
        name: str,
        owner_user_id: str,
    ) -> dict:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO workspaces (
                workspace_id,
                name,
                owner_user_id,
                plan,
                created_at
            ) VALUES (?, ?, ?, 'FOUNDATION', ?)
            """,
            (
                workspace_id,
                name,
                owner_user_id,
                now,
            ),
        )
        self.db.execute(
            """
            INSERT INTO memberships (
                workspace_id,
                user_id,
                role,
                created_at
            ) VALUES (?, ?, 'OWNER', ?)
            """,
            (
                workspace_id,
                owner_user_id,
                now,
            ),
        )
        self.db.execute(
            """
            INSERT INTO workspace_settings (
                workspace_id,
                selected_strategy,
                risk_profile,
                max_position_weight,
                daily_loss_limit,
                automation_profile,
                updated_at
            ) VALUES (?, 'MOMENTUM', 'CONSERVATIVE', 0.10, 0.02, 'ALL_STOP', ?)
            """,
            (
                workspace_id,
                now,
            ),
        )
        return self.get_workspace(workspace_id)

    def get_workspace(
        self,
        workspace_id: str,
    ) -> dict | None:
        return self.db.query_one(
            """
            SELECT workspace_id, name, owner_user_id, plan, created_at
            FROM workspaces
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        )

    def list_workspaces_for_user(
        self,
        user_id: str,
    ) -> list[dict]:
        return self.db.query_all(
            """
            SELECT
                w.workspace_id,
                w.name,
                w.owner_user_id,
                w.plan,
                m.role
            FROM workspaces w
            JOIN memberships m
              ON m.workspace_id = w.workspace_id
            WHERE m.user_id = ?
            ORDER BY w.created_at
            """,
            (user_id,),
        )

    def get_membership(
        self,
        *,
        workspace_id: str,
        user_id: str,
    ) -> dict | None:
        return self.db.query_one(
            """
            SELECT workspace_id, user_id, role, created_at
            FROM memberships
            WHERE workspace_id = ? AND user_id = ?
            """,
            (
                workspace_id,
                user_id,
            ),
        )

    def add_member(
        self,
        *,
        workspace_id: str,
        user_id: str,
        role: str,
    ) -> dict:
        self.db.execute(
            """
            INSERT INTO memberships (
                workspace_id,
                user_id,
                role,
                created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                workspace_id,
                user_id,
                role,
                utc_now(),
            ),
        )
        return self.get_membership(
            workspace_id=workspace_id,
            user_id=user_id,
        )

    def list_members(
        self,
        workspace_id: str,
    ) -> list[dict]:
        return self.db.query_all(
            """
            SELECT
                m.workspace_id,
                m.user_id,
                m.role,
                u.email
            FROM memberships m
            JOIN users u ON u.user_id = m.user_id
            WHERE m.workspace_id = ?
            ORDER BY u.email
            """,
            (workspace_id,),
        )

    def get_settings(
        self,
        workspace_id: str,
    ) -> dict | None:
        return self.db.query_one(
            """
            SELECT
                workspace_id,
                selected_strategy,
                risk_profile,
                max_position_weight,
                daily_loss_limit,
                automation_profile,
                updated_at
            FROM workspace_settings
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        )

    def update_strategy(
        self,
        *,
        workspace_id: str,
        strategy: str,
    ) -> dict:
        self.db.execute(
            """
            UPDATE workspace_settings
            SET selected_strategy = ?, updated_at = ?
            WHERE workspace_id = ?
            """,
            (
                strategy,
                utc_now(),
                workspace_id,
            ),
        )
        return self.get_settings(workspace_id)

    def update_risk(
        self,
        *,
        workspace_id: str,
        risk_profile: str,
        max_position_weight: float,
        daily_loss_limit: float,
    ) -> dict:
        self.db.execute(
            """
            UPDATE workspace_settings
            SET
                risk_profile = ?,
                max_position_weight = ?,
                daily_loss_limit = ?,
                updated_at = ?
            WHERE workspace_id = ?
            """,
            (
                risk_profile,
                max_position_weight,
                daily_loss_limit,
                utc_now(),
                workspace_id,
            ),
        )
        return self.get_settings(workspace_id)

    def add_broker_connection(
        self,
        *,
        connection_id: str,
        workspace_id: str,
        broker: str,
        environment: str,
        account_alias: str,
    ) -> dict:
        self.db.execute(
            """
            INSERT INTO broker_connections (
                connection_id,
                workspace_id,
                broker,
                environment,
                account_alias,
                status,
                read_only,
                credential_stored,
                write_enabled,
                created_at
            ) VALUES (?, ?, ?, ?, ?, 'METADATA_ONLY', 1, 0, 0, ?)
            """,
            (
                connection_id,
                workspace_id,
                broker,
                environment,
                account_alias,
                utc_now(),
            ),
        )
        return self.db.query_one(
            """
            SELECT *
            FROM broker_connections
            WHERE connection_id = ?
            """,
            (connection_id,),
        )

    def list_broker_connections(
        self,
        workspace_id: str,
    ) -> list[dict]:
        return self.db.query_all(
            """
            SELECT *
            FROM broker_connections
            WHERE workspace_id = ?
            ORDER BY created_at
            """,
            (workspace_id,),
        )

    def list_audit_events(
        self,
        workspace_id: str,
    ) -> list[dict]:
        rows = self.db.query_all(
            """
            SELECT
                event_id,
                recorded_at,
                user_id,
                workspace_id,
                action,
                details_json
            FROM audit_events
            WHERE workspace_id = ?
            ORDER BY event_id DESC
            """,
            (workspace_id,),
        )
        for row in rows:
            row["details"] = json.loads(
                row.pop("details_json")
            )
        return rows
