from __future__ import annotations
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS security_users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_locked INTEGER NOT NULL DEFAULT 0,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    email_verified INTEGER NOT NULL DEFAULT 0,
    mfa_enabled INTEGER NOT NULL DEFAULT 0,
    mfa_secret TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS security_workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES security_users(user_id)
);

CREATE TABLE IF NOT EXISTS security_memberships (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id, user_id),
    FOREIGN KEY(workspace_id) REFERENCES security_workspaces(workspace_id),
    FOREIGN KEY(user_id) REFERENCES security_users(user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    user_agent TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY(user_id) REFERENCES security_users(user_id)
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES security_users(user_id)
);

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES security_users(user_id)
);

CREATE TABLE IF NOT EXISTS api_tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    scopes_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY(user_id) REFERENCES security_users(user_id),
    FOREIGN KEY(workspace_id) REFERENCES security_workspaces(workspace_id)
);

CREATE TABLE IF NOT EXISTS security_audit (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    actor_user_id TEXT,
    workspace_id TEXT,
    action TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    user_agent TEXT NOT NULL,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user
ON sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_security_audit_workspace
ON security_audit(workspace_id, event_id);

CREATE INDEX IF NOT EXISTS idx_api_tokens_workspace
ON api_tokens(workspace_id);
"""


class SecurityDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.connection = sqlite3.connect(
            str(path),
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        with self.lock:
            self.connection.executescript(SCHEMA)
            self.connection.commit()

    def execute(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> sqlite3.Cursor:
        with self.lock:
            cursor = self.connection.execute(sql, params)
            self.connection.commit()
            return cursor

    def query_one(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute(
                sql,
                params,
            ).fetchone()
            return dict(row) if row else None

    def query_all(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute(
                sql,
                params,
            ).fetchall()
            return [dict(row) for row in rows]

    def close(self) -> None:
        with self.lock:
            self.connection.close()
