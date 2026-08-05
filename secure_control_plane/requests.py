from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .security import OperatorIdentity, PermissionGuard


class IdempotencyRegistry:
    def __init__(self) -> None:
        self._keys: set[str] = set()

    def register(self, key: str) -> bool:
        if not key.strip():
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
        if key in self._keys:
            return False
        self._keys.add(key)
        return True


class ChangeRequestFactory:
    ALLOWED_TYPES = {
        "CONFIGURATION_CHANGE",
        "STRATEGY_STATE_CHANGE",
        "STRATEGY_WEIGHT_CHANGE",
        "RUNTIME_STATE_CHANGE",
        "WORKER_SCALE_CHANGE",
        "SCHEDULER_CHANGE",
        "KILL_SWITCH_CHANGE",
        "EMERGENCY_STOP_REQUEST",
    }

    def __init__(self) -> None:
        self.guard = PermissionGuard()

    def create(
        self,
        *,
        identity: OperatorIdentity,
        request_type: str,
        subject: str,
        proposed_value: dict[str, Any],
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        permission = (
            "CREATE_EMERGENCY_REQUEST"
            if request_type in {
                "KILL_SWITCH_CHANGE",
                "EMERGENCY_STOP_REQUEST",
            }
            else "CREATE_RUNTIME_REQUEST"
            if request_type in {
                "RUNTIME_STATE_CHANGE",
                "WORKER_SCALE_CHANGE",
                "SCHEDULER_CHANGE",
            }
            else "CREATE_CHANGE_REQUEST"
        )
        self.guard.require(identity, permission)

        if request_type not in self.ALLOWED_TYPES:
            raise ValueError("UNSUPPORTED_CHANGE_REQUEST_TYPE")
        if not subject.strip() or not reason.strip():
            raise ValueError("SUBJECT_AND_REASON_REQUIRED")

        core = {
            "operator_id": identity.operator_id,
            "request_type": request_type,
            "subject": subject,
            "proposed_value": proposed_value,
            "reason": reason,
            "idempotency_key": idempotency_key,
        }
        raw = json.dumps(core, sort_keys=True, separators=(",", ":"))
        request_id = "control-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]

        return {
            "request_id": request_id,
            **core,
            "state": "PENDING_PREVIEW",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "requires_separate_approver": True,
            "actual_configuration_applied": False,
            "actual_runtime_action_performed": False,
            "actual_strategy_change_performed": False,
            "actual_kill_switch_changed": False,
            "actual_emergency_stop_activated": False,
        }


class ApprovalReviewer:
    def __init__(self) -> None:
        self.guard = PermissionGuard()

    def review(
        self,
        *,
        identity: OperatorIdentity,
        request: dict[str, Any],
        decision: str,
        comment: str,
    ) -> dict[str, Any]:
        request_type = request["request_type"]
        permission = (
            "REVIEW_EMERGENCY_REQUEST"
            if request_type in {
                "KILL_SWITCH_CHANGE",
                "EMERGENCY_STOP_REQUEST",
            }
            else "REVIEW_RUNTIME_REQUEST"
            if request_type in {
                "RUNTIME_STATE_CHANGE",
                "WORKER_SCALE_CHANGE",
                "SCHEDULER_CHANGE",
            }
            else "REVIEW_CHANGE_REQUEST"
        )
        self.guard.require(identity, permission)

        if identity.operator_id == request["operator_id"]:
            raise PermissionError("SELF_APPROVAL_REJECTED")
        if decision not in {"APPROVE_PREVIEW", "REJECT"}:
            raise ValueError("INVALID_REVIEW_DECISION")

        return {
            "request_id": request["request_id"],
            "reviewer_id": identity.operator_id,
            "reviewer_role": identity.role,
            "decision": decision,
            "comment": comment,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "actual_approval_applied": False,
            "actual_change_applied": False,
        }


class ControlPlaneLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
