from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .resume_manager import build_resume_plan


def build_operator_checklist(root: Path) -> dict[str, Any]:
    plan = build_resume_plan(root)
    checklist = [
        {
            "item": "Verify Alpaca Paper endpoint",
            "required": True,
            "complete": False,
        },
        {
            "item": "Verify fresh Paper API credentials are local only",
            "required": True,
            "complete": False,
        },
        {
            "item": "Review Kill Switch state",
            "required": True,
            "complete": False,
        },
        {
            "item": "Review open orders and positions",
            "required": True,
            "complete": False,
        },
        {
            "item": "Run P4 actual preflight",
            "required": True,
            "complete": False,
        },
        {
            "item": "Confirm no duplicate runtime lock or cycle",
            "required": True,
            "complete": False,
        },
        {
            "item": "Confirm operator-controlled resume",
            "required": True,
            "complete": False,
        },
    ]

    value = {
        "stage": "O4_OPERATOR_CHECKLIST",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resume_plan": plan,
        "checklist": checklist,
        "all_complete": False,
        "automatic_resume_enabled": False,
        "automatic_order_replay_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    path = (
        root / "release/o4_runtime_resume_session_reporting/actual/"
               "operator_resume_checklist.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
