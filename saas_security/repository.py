from __future__ import annotations
import json
from datetime import datetime, timezone

from .database import SecurityDatabase


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SecurityRepository:
    def __init__(self, db: SecurityDatabase) -> None:
        self.db = db

    def create_user(
        self,
        *,
        user_id: str,
        email: str,
        password_hash: str,
    ) -> dict:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO security_users (
                user_id, email, password_hash,
                is_active, is_locked,
                failed_login_count, email_verified,
                mfa_enabled, created_at, updated_at
            ) VALUES (?, ?, ?, 1, 0, 0, 0, 0, ?, ?)
            """,
            (
                user_id,
                email.lower().strip(),
                password_hash,
                now,
                now,
            ),
        )
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> dict | None:
        return self.db.query_one(
            "SELECT * FROM security_users WHERE user_id = ?",
            (user_id,),
        )

    def get_user_by_email(
        self,
        email: str,
    ) -> dict | None:
        return self.db.query_one(
            "SELECT * FROM security_users WHERE email = ?",
            (email.lower().strip(),),
        )

    def update_login_failure(
        self,
        *,
        user_id: str,
        failure_count: int,
        locked: bool,
    ) -> None:
        self.db.execute(
            """
            UPDATE security_users
            SET failed_login_count = ?,
                is_locked = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                failure_count,
                1 if locked else 0,
                utc_now(),
                user_id,
            ),
        )

    def reset_login_failures(self, user_id: str) -> None:
        self.update_login_failure(
            user_id=user_id,
            failure_count=0,
            locked=False,
        )

    def set_active(
        self,
        *,
        user_id: str,
        active: bool,
    ) -> None:
        self.db.execute(
            """
            UPDATE security_users
            SET is_active = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (
                1 if active else 0,
                utc_now(),
                user_id,
            ),
        )

    def set_locked(
        self,
        *,
        user_id: str,
        locked: bool,
    ) -> None:
        self.db.execute(
            """
            UPDATE security_users
            SET is_locked = ?,
                failed_login_count = CASE
                    WHEN ? = 0 THEN 0
                    ELSE failed_login_count
                END,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                1 if locked else 0,
                1 if locked else 0,
                utc_now(),
                user_id,
            ),
        )

    def update_password(
        self,
        *,
        user_id: str,
        password_hash: str,
    ) -> None:
        self.db.execute(
            """
            UPDATE security_users
            SET password_hash = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (
                password_hash,
                utc_now(),
                user_id,
            ),
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
            INSERT INTO security_workspaces (
                workspace_id, name,
                owner_user_id, created_at
            ) VALUES (?, ?, ?, ?)
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
            INSERT INTO security_memberships (
                workspace_id, user_id,
                role, created_at
            ) VALUES (?, ?, 'OWNER', ?)
            """,
            (
                workspace_id,
                owner_user_id,
                now,
            ),
        )
        return self.db.query_one(
            """
            SELECT *
            FROM security_workspaces
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        )

    def get_membership(
        self,
        *,
        workspace_id: str,
        user_id: str,
    ) -> dict | None:
        return self.db.query_one(
            """
            SELECT *
            FROM security_memberships
            WHERE workspace_id = ?
              AND user_id = ?
            """,
            (
                workspace_id,
                user_id,
            ),
        )

    def update_member_role(
        self,
        *,
        workspace_id: str,
        user_id: str,
        role: str,
    ) -> dict:
        self.db.execute(
            """
            UPDATE security_memberships
            SET role = ?
            WHERE workspace_id = ?
              AND user_id = ?
            """,
            (
                role,
                workspace_id,
                user_id,
            ),
        )
        return self.get_membership(
            workspace_id=workspace_id,
            user_id=user_id,
        )

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        token_hash_value: str,
        user_agent: str,
        ip_address: str,
        created_at: str,
        expires_at: str,
    ) -> dict:
        self.db.execute(
            """
            INSERT INTO sessions (
                session_id, user_id,
                token_hash, user_agent,
                ip_address, created_at,
                expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                token_hash_value,
                user_agent,
                ip_address,
                created_at,
                expires_at,
            ),
        )
        return self.get_session(session_id)

    def get_session(
        self,
        session_id: str,
    ) -> dict | None:
        return self.db.query_one(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )

    def get_session_by_hash(
        self,
        token_hash_value: str,
    ) -> dict | None:
        return self.db.query_one(
            """
            SELECT *
            FROM sessions
            WHERE token_hash = ?
            """,
            (token_hash_value,),
        )

    def list_sessions(
        self,
        user_id: str,
    ) -> list[dict]:
        return self.db.query_all(
            """
            SELECT
                session_id,
                user_agent,
                ip_address,
                created_at,
                expires_at,
                revoked_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )

    def revoke_session(self, session_id: str) -> None:
        self.db.execute(
            """
            UPDATE sessions
            SET revoked_at = ?
            WHERE session_id = ?
            """,
            (
                utc_now(),
                session_id,
            ),
        )

    def revoke_all_sessions(
        self,
        user_id: str,
    ) -> None:
        self.db.execute(
            """
            UPDATE sessions
            SET revoked_at = ?
            WHERE user_id = ?
              AND revoked_at IS NULL
            """,
            (
                utc_now(),
                user_id,
            ),
        )

    def create_recovery_token(
        self,
        *,
        table: str,
        token_id: str,
        user_id: str,
        token_hash_value: str,
        expires_at: str,
    ) -> None:
        if table not in {
            "password_reset_tokens",
            "email_verification_tokens",
        }:
            raise ValueError("INVALID_TOKEN_TABLE")
        self.db.execute(
            f"""
            INSERT INTO {table} (
                token_id, user_id,
                token_hash, expires_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                token_id,
                user_id,
                token_hash_value,
                expires_at,
                utc_now(),
            ),
        )

    def get_recovery_token(
        self,
        *,
        table: str,
        token_hash_value: str,
    ) -> dict | None:
        if table not in {
            "password_reset_tokens",
            "email_verification_tokens",
        }:
            raise ValueError("INVALID_TOKEN_TABLE")
        return self.db.query_one(
            f"""
            SELECT *
            FROM {table}
            WHERE token_hash = ?
            """,
            (token_hash_value,),
        )

    def use_recovery_token(
        self,
        *,
        table: str,
        token_id: str,
    ) -> None:
        if table not in {
            "password_reset_tokens",
            "email_verification_tokens",
        }:
            raise ValueError("INVALID_TOKEN_TABLE")
        self.db.execute(
            f"""
            UPDATE {table}
            SET used_at = ?
            WHERE token_id = ?
            """,
            (
                utc_now(),
                token_id,
            ),
        )

    def set_email_verified(
        self,
        user_id: str,
    ) -> None:
        self.db.execute(
            """
            UPDATE security_users
            SET email_verified = 1,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                utc_now(),
                user_id,
            ),
        )

    def set_mfa(
        self,
        *,
        user_id: str,
        secret: str | None,
        enabled: bool,
    ) -> None:
        self.db.execute(
            """
            UPDATE security_users
            SET mfa_secret = ?,
                mfa_enabled = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                secret,
                1 if enabled else 0,
                utc_now(),
                user_id,
            ),
        )

    def create_api_token(
        self,
        *,
        token_id: str,
        user_id: str,
        workspace_id: str,
        name: str,
        token_hash_value: str,
        scopes_json: str,
        expires_at: str,
    ) -> dict:
        self.db.execute(
            """
            INSERT INTO api_tokens (
                token_id, user_id,
                workspace_id, name,
                token_hash, scopes_json,
                created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token_id,
                user_id,
                workspace_id,
                name,
                token_hash_value,
                scopes_json,
                utc_now(),
                expires_at,
            ),
        )
        return self.db.query_one(
            """
            SELECT
                token_id, user_id,
                workspace_id, name,
                scopes_json,
                created_at, expires_at,
                revoked_at
            FROM api_tokens
            WHERE token_id = ?
            """,
            (token_id,),
        )

    def revoke_api_token(
        self,
        token_id: str,
    ) -> None:
        self.db.execute(
            """
            UPDATE api_tokens
            SET revoked_at = ?
            WHERE token_id = ?
            """,
            (
                utc_now(),
                token_id,
            ),
        )

    def list_api_tokens(
        self,
        workspace_id: str,
    ) -> list[dict]:
        return self.db.query_all(
            """
            SELECT
                token_id, user_id,
                workspace_id, name,
                scopes_json,
                created_at, expires_at,
                revoked_at
            FROM api_tokens
            WHERE workspace_id = ?
            ORDER BY created_at DESC
            """,
            (workspace_id,),
        )

    def append_audit(
        self,
        *,
        recorded_at: str,
        actor_user_id: str | None,
        workspace_id: str | None,
        action: str,
        ip_address: str,
        user_agent: str,
        details_json: str,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO security_audit (
                recorded_at,
                actor_user_id,
                workspace_id,
                action,
                ip_address,
                user_agent,
                details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recorded_at,
                actor_user_id,
                workspace_id,
                action,
                ip_address,
                user_agent,
                details_json,
            ),
        )

    def list_audit(
        self,
        workspace_id: str | None = None,
    ) -> list[dict]:
        if workspace_id is None:
            return self.db.query_all(
                """
                SELECT *
                FROM security_audit
                ORDER BY event_id DESC
                LIMIT 500
                """
            )
        return self.db.query_all(
            """
            SELECT *
            FROM security_audit
            WHERE workspace_id = ?
            ORDER BY event_id DESC
            LIMIT 500
            """,
            (workspace_id,),
        )

    def admin_stats(self) -> dict:
        return {
            "users": self.db.query_one(
                "SELECT COUNT(*) AS count FROM security_users"
            )["count"],
            "active_users": self.db.query_one(
                """
                SELECT COUNT(*) AS count
                FROM security_users
                WHERE is_active = 1
                """
            )["count"],
            "locked_users": self.db.query_one(
                """
                SELECT COUNT(*) AS count
                FROM security_users
                WHERE is_locked = 1
                """
            )["count"],
            "workspaces": self.db.query_one(
                """
                SELECT COUNT(*) AS count
                FROM security_workspaces
                """
            )["count"],
            "sessions": self.db.query_one(
                """
                SELECT COUNT(*) AS count
                FROM sessions
                """
            )["count"],
            "api_tokens": self.db.query_one(
                """
                SELECT COUNT(*) AS count
                FROM api_tokens
                """
            )["count"],
            "audit_events": self.db.query_one(
                """
                SELECT COUNT(*) AS count
                FROM security_audit
                """
            )["count"],
        }
