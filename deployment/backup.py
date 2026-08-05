from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


STATE_PATHS = (
    "release/p1_broker_consolidation/actual",
    "release/p2_actual_paper_execution/actual",
    "release/p3_order_fill_portfolio_sync/actual",
    "release/p4_autonomous_paper_runtime/actual",
    "release/p5_paper_long_run_qualification/actual",
    "release/operations_bundle/actual",
    "release/o3_autonomous_operations/actual",
    "release/o4_runtime_resume_session_reporting/actual",
    "release/l1_live_safety_boundary/actual",
    "release/l2_live_read_only_preparation/actual",
    "release/l3_live_micro_execution_preparation/actual",
    "release/l4_live_reconciliation_preparation/actual",
    "release/l5_live_autonomous_runtime_preparation/actual",
    "release/l6_live_long_run_qualification_preparation/actual",
    "release/actual_validation_control_center/actual",
)


def build_backup_inventory(root: Path) -> dict[str, Any]:
    files = []
    for rel in STATE_PATHS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            content = path.read_bytes()
            files.append({
                "path": path.relative_to(root).as_posix(),
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            })

    return {
        "stage": "R1_BACKUP_INVENTORY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": files,
        "contains_credentials": False,
        "automatic_restore_enabled": False,
        "operator_review_required": True,
    }


def write_restore_plan(path: Path) -> dict[str, Any]:
    value = {
        "stage": "R1_RESTORE_PLAN",
        "automatic_restore_enabled": False,
        "automatic_order_replay_enabled": False,
        "required_sequence": [
            "ACTIVATE_PAPER_AND_LIVE_KILL_SWITCHES",
            "STOP_ALL_RUNTIMES",
            "VERIFY_BACKUP_HASHES",
            "RESTORE_STATE_TO_STAGING_DIRECTORY",
            "COMPARE_OPEN_ORDERS_POSITIONS_AND_CASH",
            "RUN_P4_OR_L5_PREFLIGHT_AS_APPLICABLE",
            "REQUIRE_OPERATOR_APPROVAL",
            "RESTART_WITH_NEW_SESSION_ID",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
