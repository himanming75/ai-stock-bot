from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class DeploymentLock:
    def evaluate(
        self,
        *,
        p2_validated: bool,
        p3_validated: bool,
        p4_validated: bool,
        p5_validated: bool,
        emergency_stop_active: bool,
    ) -> dict[str, Any]:
        blockers = []
        if not p2_validated:
            blockers.append("P2_NOT_VALIDATED")
        if not p3_validated:
            blockers.append("P3_NOT_VALIDATED")
        if not p4_validated:
            blockers.append("P4_NOT_VALIDATED")
        if not p5_validated:
            blockers.append("P5_NOT_VALIDATED")
        if emergency_stop_active:
            blockers.append("EMERGENCY_STOP_ACTIVE")

        return {
            "blockers": blockers,
            "production_release_allowed": not blockers,
            "actual_release_performed": False,
            "operator_approval_required": True,
        }


class EmergencyStop:
    def preview(self, *, requested: bool) -> dict[str, Any]:
        return {
            "requested": requested,
            "emergency_stop_state": (
                "WOULD_ACTIVATE" if requested else "INACTIVE"
            ),
            "actual_emergency_stop_activated": False,
            "broker_cancel_attempted": False,
            "network_used": False,
        }


class ApprovalQueue:
    def create(
        self,
        *,
        approval_type: str,
        subject: str,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        raw = json.dumps(
            {
                "approval_type": approval_type,
                "subject": subject,
                "evidence": evidence,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        approval_id = "approval-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]
        return {
            "approval_id": approval_id,
            "approval_type": approval_type,
            "subject": subject,
            "evidence": evidence,
            "state": "PENDING_PREVIEW",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "actual_approval_granted": False,
            "actual_change_applied": False,
        }


class ApprovalLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


class RollbackApprovalPreview:
    def build(
        self,
        *,
        current_release: str,
        target_release: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "current_release": current_release,
            "target_release": target_release,
            "reason": reason,
            "rollback_approval_required": True,
            "rollback_preview_allowed": bool(target_release and reason),
            "actual_rollback_approved": False,
            "actual_rollback_performed": False,
        }
