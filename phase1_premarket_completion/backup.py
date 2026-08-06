from __future__ import annotations
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .i18n import bilingual
from .io import write_json


ALLOWED_ACTIONS = {
    "BACKUP",
    "SNAPSHOT",
    "RESTORE",
    "ROLLBACK",
    "EXPORT",
}


def build_backup_plan(
    *,
    action: str,
    source_paths: list[str],
    destination: str,
    output_path: Path,
) -> dict:
    normalized = action.strip().upper()
    if normalized not in ALLOWED_ACTIONS:
        raise ValueError(
            "UNSUPPORTED_BACKUP_ACTION"
        )
    if not source_paths:
        raise ValueError(
            "SOURCE_PATH_REQUIRED"
        )

    plan = {
        "plan_id": (
            f"backup_{secrets.token_hex(8)}"
        ),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "action": normalized,
        "status": "REVIEW_REQUIRED",
        "status_i18n": bilingual(
            "REVIEW_REQUIRED"
        ),
        "mode": "DRY_RUN_ONLY",
        "source_paths": source_paths,
        "destination": destination,
        "estimated_file_count": len(
            source_paths
        ),
        "filesystem_write_enabled": False,
        "filesystem_delete_enabled": False,
        "restore_enabled": False,
        "rollback_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
    }
    write_json(output_path, plan)
    return plan


def execute_backup(*args, **kwargs):
    raise PermissionError(
        "BACKUP_RESTORE_EXECUTION_DISABLED"
    )
