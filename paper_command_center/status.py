from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .config import CommandCenterPaths
from .reader import read_json, read_jsonl_tail


def _first(
    payload: dict,
    *keys: str,
    default=None,
):
    for key in keys:
        if key in payload:
            return payload[key]
    return default


def build_status(
    paths: CommandCenterPaths,
) -> dict[str, Any]:
    controller = read_json(
        paths.controller_summary
    )
    checkpoint = read_json(paths.checkpoint)
    execution = read_json(paths.execution_plan)
    tickets = read_json(
        paths.order_ticket_snapshot
    )
    watchdog = read_json(
        paths.watchdog_summary
    )
    daily = read_json(
        paths.daily_session_summary
    )
    polling = read_jsonl_tail(
        paths.polling_ledger,
        limit=12,
    )

    controller_state = str(
        _first(
            controller,
            "state",
            "status",
            "controller_state",
            default="UNKNOWN",
        )
    )
    watchdog_state = str(
        _first(
            watchdog,
            "state",
            "status",
            "watchdog_state",
            default="UNKNOWN",
        )
    )
    session_state = str(
        _first(
            daily,
            "state",
            "status",
            "session_state",
            default="UNKNOWN",
        )
    )

    available_count = sum(
        bool(item.get("_available"))
        for item in (
            controller,
            checkpoint,
            execution,
            tickets,
            watchdog,
            daily,
        )
    )
    if available_count == 6:
        overall = "READY"
    elif available_count > 0:
        overall = "DEGRADED"
    else:
        overall = "NO_DATA"

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "overall_status": overall,
        "mode": "READ_ONLY_COMMAND_PLANNING",
        "controller": {
            "state": controller_state,
            "available": controller.get(
                "_available",
                False,
            ),
            "summary": controller,
        },
        "watchdog": {
            "state": watchdog_state,
            "available": watchdog.get(
                "_available",
                False,
            ),
            "summary": watchdog,
        },
        "daily_session": {
            "state": session_state,
            "available": daily.get(
                "_available",
                False,
            ),
            "summary": daily,
        },
        "checkpoint": checkpoint,
        "execution_plan": execution,
        "order_tickets": tickets,
        "polling": polling,
        "safety": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "process_start_enabled": False,
            "process_stop_enabled": False,
            "task_scheduler_write_enabled": False,
            "command_execution_enabled": False,
        },
    }
