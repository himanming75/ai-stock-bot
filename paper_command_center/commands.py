from __future__ import annotations
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_ACTIONS = {
    "START",
    "PAUSE",
    "RESUME",
    "STOP",
    "REFRESH",
    "VALIDATE",
}


def _append_jsonl(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                payload,
                sort_keys=True,
            )
            + "\n"
        )


def create_command_plan(
    *,
    action: str,
    requested_by: str,
    reason: str,
    output_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    normalized = action.strip().upper()
    if normalized not in ALLOWED_ACTIONS:
        raise ValueError("UNSUPPORTED_ACTION")

    now = datetime.now(
        timezone.utc
    ).isoformat()
    plan = {
        "command_id": (
            f"cmd_{secrets.token_hex(8)}"
        ),
        "created_at": now,
        "action": normalized,
        "requested_by": (
            requested_by.strip() or "LOCAL_USER"
        ),
        "reason": reason.strip(),
        "mode": "DRY_RUN_ONLY",
        "approval_status": "REVIEW_REQUIRED",
        "execution_status": "NOT_EXECUTED",
        "planned_effect": {
            "START": (
                "Prepare controller start request."
            ),
            "PAUSE": (
                "Prepare controller pause request."
            ),
            "RESUME": (
                "Prepare controller resume request."
            ),
            "STOP": (
                "Prepare graceful stop request."
            ),
            "REFRESH": (
                "Prepare status refresh request."
            ),
            "VALIDATE": (
                "Prepare configuration validation request."
            ),
        }[normalized],
        "safety": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "process_execution_enabled": False,
            "process_termination_enabled": False,
            "windows_task_change_enabled": False,
        },
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            plan,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    _append_jsonl(
        audit_path,
        {
            "command_id": plan["command_id"],
            "created_at": now,
            "action": normalized,
            "mode": "DRY_RUN_ONLY",
            "execution_status": "NOT_EXECUTED",
            "requested_by": plan[
                "requested_by"
            ],
        },
    )
    return plan
