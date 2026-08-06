from __future__ import annotations
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class BackupManager:
    def __init__(
        self,
        *,
        source_database: Path,
        backup_root: Path,
    ) -> None:
        self.source_database = source_database
        self.backup_root = backup_root

    def create_backup(self) -> dict:
        if not self.source_database.exists():
            raise FileNotFoundError(
                self.source_database
            )

        self.backup_root.mkdir(
            parents=True,
            exist_ok=True,
        )
        timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%dT%H%M%SZ")
        destination = (
            self.backup_root
            / f"saas_backup_{timestamp}.db"
        )

        source = sqlite3.connect(
            str(self.source_database)
        )
        target = sqlite3.connect(
            str(destination)
        )
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        digest = hashlib.sha256(
            destination.read_bytes()
        ).hexdigest()
        manifest = {
            "backup_path": str(destination),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "sha256": digest,
            "size_bytes": destination.stat().st_size,
        }
        destination.with_suffix(
            ".manifest.json"
        ).write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        return manifest

    def validate_backup(
        self,
        backup_path: Path,
    ) -> dict:
        connection = sqlite3.connect(
            str(backup_path)
        )
        try:
            result = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        finally:
            connection.close()
        return {
            "backup_path": str(backup_path),
            "integrity_check": result,
            "valid": result == "ok",
        }

    def restore_dry_run(
        self,
        backup_path: Path,
    ) -> dict:
        validation = self.validate_backup(
            backup_path
        )
        return {
            **validation,
            "restore_performed": False,
            "mode": "DRY_RUN",
        }
