from __future__ import annotations
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    plan TEXT NOT NULL,
    status TEXT NOT NULL,
    current_period_start TEXT NOT NULL,
    current_period_end TEXT NOT NULL,
    trial_end TEXT,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    external_provider TEXT,
    external_customer_id TEXT,
    external_subscription_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    workspace_id TEXT,
    metric TEXT NOT NULL,
    quantity REAL NOT NULL,
    recorded_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    subscription_id TEXT NOT NULL,
    amount_due_usd REAL NOT NULL,
    amount_paid_usd REAL NOT NULL,
    status TEXT NOT NULL,
    line_items_json TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    paid_at TEXT
);

CREATE TABLE IF NOT EXISTS licenses (
    license_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    license_key_hash TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL,
    machine_limit INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS billing_audit (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    actor_user_id TEXT,
    action TEXT NOT NULL,
    details_json TEXT NOT NULL
);
"""


class BillingDatabase:
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
