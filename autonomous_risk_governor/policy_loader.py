from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

from .io import read_json
from .validation import validate


def _hash(policy: dict[str, Any]) -> str:
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_and_validate(path: Path) -> dict[str, Any]:
    policy = read_json(path)
    validation = validate(policy)

    return {
        "stage": "V391.01A",
        "state": (
            "RISK_POLICY_READY"
            if validation["valid"]
            else "RISK_POLICY_BLOCKED"
        ),
        "status": "PASS",
        "policy_path": str(path),
        "policy_hash": _hash(policy),
        "policy": policy,
        "validation": validation,
        "risk_operations_allowed": (
            validation["valid"]
            and policy.get("kill_switch_active") is False
            and policy.get("risk_operations_allowed") is True
        ),
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V391_02A_DAILY_LOSS_GUARD",
    }
