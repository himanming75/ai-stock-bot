from __future__ import annotations
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saas_operations.backup import BackupManager
from saas_operations.health import HeartbeatRegistry
from saas_operations.metrics import MetricsRegistry
from saas_operations.notifications import NotificationQueue
from saas_operations.web import serve


def ensure_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument(
        "--runtime-root",
        default="runtime",
    )
    parser.add_argument(
        "--database",
        default="runtime/saas/saas.db",
    )
    args = parser.parse_args()

    runtime_root = Path(args.runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    database_path = Path(args.database)
    ensure_database(database_path)

    metrics = MetricsRegistry()
    heartbeats = HeartbeatRegistry()
    notifications = NotificationQueue()

    for service, status in (
        ("SAAS_WEB", "RUNNING"),
        ("PAPER_CONTROLLER", "UNKNOWN"),
        ("WATCHDOG", "UNKNOWN"),
        ("MARKET_POLLING", "UNKNOWN"),
    ):
        heartbeats.beat(
            service,
            status=status,
        )

    backup_manager = BackupManager(
        source_database=database_path,
        backup_root=runtime_root / "backups",
    )
    backup_items = []

    serve(
        metrics=metrics,
        heartbeats=heartbeats,
        notifications=notifications,
        runtime_root=runtime_root,
        backup_items=backup_items,
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
