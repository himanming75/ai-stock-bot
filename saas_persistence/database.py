from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    plan TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS memberships (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id, user_id),
    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS workspace_settings (
    workspace_id TEXT PRIMARY KEY,
    selected_strategy TEXT NOT NULL,
    risk_profile TEXT NOT NULL,
    max_position_weight REAL NOT NULL,
    daily_loss_limit REAL NOT NULL,
    automation_profile TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id)
);

CREATE TABLE IF NOT EXISTS broker_connections (
    connection_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    broker TEXT NOT NULL,
    environment TEXT NOT NULL,
    account_alias TEXT NOT NULL,
    status TEXT NOT NULL,
    read_only INTEGER NOT NULL,
    credential_stored INTEGER NOT NULL,
    write_enabled INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    user_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details_json TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_membership_user
ON memberships(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_workspace
ON audit_events(workspace_id, event_id);
"""


class SQLiteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
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

    def append_audit(
        self,
        *,
        recorded_at: str,
        user_id: str,
        workspace_id: str,
        action: str,
        details: dict[str, Any],
    ) -> None:
        self.execute(
            """
            INSERT INTO audit_events (
                recorded_at,
                user_id,
                workspace_id,
                action,
                details_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                recorded_at,
                user_id,
                workspace_id,
                action,
                json.dumps(
                    details,
                    sort_keys=True,
                ),
            ),
        )

    def close(self) -> None:
        with self.lock:
            self.connection.close()
