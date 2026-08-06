from __future__ import annotations
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .i18n import bilingual
from .io import append_jsonl, write_json


ALLOWED = {
    "PAUSE",
    "RESUME",
    "RELOAD_CONFIGURATION",
    "GRACEFUL_STOP",
    "PREMARKET_VALIDATE",
    "GENERATE_REPORT",
}


def enqueue_plan(
    *,
    action: str,
    reason: str,
    requested_by: str,
    latest_path: Path,
    queue_path: Path,
) -> dict:
    normalized = action.strip().upper()
    if normalized not in ALLOWED:
        raise ValueError(
            "UNSUPPORTED_COMMAND_ACTION"
        )

    now = datetime.now(
        timezone.utc
    ).isoformat()
    plan = {
        "command_id": (
            f"queue_{secrets.token_hex(8)}"
        ),
        "created_at": now,
        "action": normalized,
        "requested_by": (
            requested_by.strip() or "LOCAL_USER"
        ),
        "reason": reason.strip(),
        "status": "REVIEW_REQUIRED",
        "status_i18n": bilingual(
            "REVIEW_REQUIRED"
        ),
        "mode": "QUEUE_PLAN_ONLY",
        "execution_status": "NOT_EXECUTED",
        "process_start_enabled": False,
        "process_stop_enabled": False,
        "process_kill_enabled": False,
        "task_scheduler_write_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "order_cancel_enabled": False,
    }
    write_json(latest_path, plan)
    append_jsonl(queue_path, plan)
    return plan


def execute_queue(*args, **kwargs):
    raise PermissionError(
        "COMMAND_QUEUE_EXECUTION_DISABLED"
    )
