from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


class PreInstallAuditor:
    def audit(self, *, root: Path, required: list[str]) -> dict[str, Any]:
        checks = {item: (root / item).exists() for item in required}
        return {
            "checks": checks,
            "failed": [key for key, value in checks.items() if not value],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "actual_install_performed": False,
        }


class BackupPlanBuilder:
    def build(
        self,
        *,
        sources: list[str],
        destination: str,
    ) -> dict[str, Any]:
        return {
            "sources": sources,
            "destination": destination,
            "retention_count": 5,
            "compression": "ZIP",
            "actual_backup_performed": False,
            "actual_files_copied": False,
        }


class RestorePreview:
    def build(
        self,
        *,
        backup_path: str,
        target_root: str,
    ) -> dict[str, Any]:
        return {
            "backup_path": backup_path,
            "target_root": target_root,
            "restore_steps": [
                "VERIFY_BACKUP_SHA256",
                "STOP_RUNTIME_PREVIEW",
                "RESTORE_TO_STAGING_PREVIEW",
                "VERIFY_STAGING_PREVIEW",
                "SWAP_DIRECTORIES_PREVIEW",
            ],
            "actual_restore_performed": False,
            "actual_target_modified": False,
        }


class RollbackPreview:
    def build(
        self,
        *,
        current_version: str,
        target_version: str,
    ) -> dict[str, Any]:
        return {
            "current_version": current_version,
            "target_version": target_version,
            "rollback_allowed_preview": bool(target_version),
            "operator_approval_required": True,
            "actual_rollback_performed": False,
            "actual_release_changed": False,
        }


class DeploymentAuditLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, *, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "event_type": event_type,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "actual_change_applied": False,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
