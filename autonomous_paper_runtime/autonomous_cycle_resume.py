from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _cycle_id(unlock_id: str) -> str:
    digest = hashlib.sha256(unlock_id.encode("utf-8")).hexdigest()[:24]
    return f"cycle-{digest}"


@dataclass(frozen=True)
class AutonomousCycleResumeReport:
    status: str
    state: str
    unlock_id: str
    handoff_id: str
    cycle_id: str
    cycle_sequence: int
    recovery_verified: bool
    resume_allowed: bool
    cycle_created: bool
    duplicate_cycle: bool
    resume_token_written: bool
    recovery_snapshot_written: bool
    next_order_eligibility_ready: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_recovery_result_path: str
    resume_token_path: str
    cycle_ledger_path: str
    recovery_snapshot_path: str
    result_path: str
    actual_credentials_used: bool = False
    actual_external_network_used: bool = False
    network_requests_executed: int = 0
    write_requests_executed: int = 0
    actual_paper_orders_submitted: int = 0
    live_orders_submitted: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "actual_credentials_used": self.actual_credentials_used,
            "actual_external_network_used": self.actual_external_network_used,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "blocking_issue_count": self.blocking_issue_count,
            "cycle_created": self.cycle_created,
            "cycle_id": self.cycle_id,
            "cycle_sequence": self.cycle_sequence,
            "duplicate_cycle": self.duplicate_cycle,
            "handoff_id": self.handoff_id,
            "implementation_type": "AUTONOMOUS_CYCLE_RESUME",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_order_eligibility_ready": self.next_order_eligibility_ready,
            "next_phase": (
                "V139_06_NEXT_ORDER_ELIGIBILITY"
                if self.next_order_eligibility_ready and not self.safe_mode_engaged
                else "V139_05_WAIT_RECOVERY_VALIDATION"
            ),
            "recovery_snapshot_path": self.recovery_snapshot_path,
            "recovery_snapshot_written": self.recovery_snapshot_written,
            "recovery_verified": self.recovery_verified,
            "result_path": self.result_path,
            "resume_allowed": self.resume_allowed,
            "resume_token_path": self.resume_token_path,
            "resume_token_written": self.resume_token_written,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_recovery_result_path": self.source_recovery_result_path,
            "stage": "V139.05",
            "state": self.state,
            "status": self.status,
            "unlock_id": self.unlock_id,
            "cycle_ledger_path": self.cycle_ledger_path,
            "validation_mode": "ACTUAL_SAVED_STATE_LOCAL_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class AutonomousCycleResume:
    def run(
        self,
        *,
        recovery_result_path: Path,
        resume_token_path: Path,
        cycle_ledger_path: Path,
        recovery_snapshot_path: Path,
        result_path: Path,
    ) -> AutonomousCycleResumeReport:
        issues: list[dict[str, Any]] = []

        try:
            recovery = _load_json(recovery_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            recovery = {}
            issues.append({
                "code": "INVALID_RECOVERY_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not recovery:
            issues.append({
                "code": "RECOVERY_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(recovery_result_path),
            })

        source_status = str(recovery.get("status", "")).upper()
        source_state = str(recovery.get("state", "")).upper()
        source_safe_mode = bool(recovery.get("safe_mode_engaged", False))
        recovery_validated = bool(recovery.get("recovery_validated", False))
        unlock_id = str(recovery.get("unlock_id", "")).strip()
        handoff_id = str(recovery.get("handoff_id", "")).strip()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_RECOVERY_SAFE_MODE",
                "blocking": True,
                "detail": "V139.04 recovery validation is blocked or in safe mode",
            })
        if recovery_validated and source_state != "RECOVERY_VALIDATED":
            issues.append({
                "code": "RECOVERY_STATE_MISMATCH",
                "blocking": True,
                "detail": "recovery_validated=true without RECOVERY_VALIDATED state",
            })
        if recovery_validated and not (unlock_id and handoff_id):
            issues.append({
                "code": "RECOVERY_IDENTITY_MISSING",
                "blocking": True,
                "detail": "validated recovery must contain unlock_id and handoff_id",
            })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        recovery_verified = bool(
            source_status == "PASS"
            and source_state == "RECOVERY_VALIDATED"
            and recovery_validated
            and unlock_id
            and handoff_id
            and not safe_mode
        )
        resume_allowed = recovery_verified
        cycle_id = _cycle_id(unlock_id) if resume_allowed else ""
        cycle_sequence = 1 if resume_allowed else 0
        cycle_created = False
        duplicate_cycle = False
        resume_token_written = False
        recovery_snapshot_written = False

        if resume_allowed:
            token_payload = {
                "cycle_id": cycle_id,
                "cycle_sequence": cycle_sequence,
                "previous_cycle_id": "",
                "unlock_id": unlock_id,
                "handoff_id": handoff_id,
                "cycle_state": "RESUMED",
                "next_order_eligibility_ready": True,
                "source_recovery_result_path": str(recovery_result_path.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            if resume_token_path.exists():
                try:
                    existing = _load_json(resume_token_path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    existing = {}
                    issues.append({
                        "code": "INVALID_EXISTING_RESUME_TOKEN",
                        "blocking": True,
                        "detail": str(exc),
                    })
                if (
                    existing.get("cycle_id") == cycle_id
                    and existing.get("unlock_id") == unlock_id
                ):
                    duplicate_cycle = True
                else:
                    issues.append({
                        "code": "RESUME_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing resume token belongs to another unlock",
                    })
            else:
                _atomic_write_json(resume_token_path, token_payload)
                _append_jsonl(
                    cycle_ledger_path,
                    {"event": "AUTONOMOUS_CYCLE_RESUMED", **token_payload},
                )
                cycle_created = True
                resume_token_written = True

            blocking = sum(1 for issue in issues if issue.get("blocking"))
            if blocking == 0:
                snapshot = {
                    "cycle_id": cycle_id,
                    "cycle_sequence": cycle_sequence,
                    "unlock_id": unlock_id,
                    "handoff_id": handoff_id,
                    "resume_token_verified": True,
                    "next_order_eligibility_ready": True,
                    "duplicate_cycle": duplicate_cycle,
                    "resume_token_path": str(resume_token_path.resolve()),
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
                _atomic_write_json(recovery_snapshot_path, snapshot)
                recovery_snapshot_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        next_order_eligibility_ready = bool(
            resume_allowed
            and (cycle_created or duplicate_cycle)
            and recovery_snapshot_written
            and not safe_mode
        )

        if safe_mode:
            state = "CYCLE_RESUME_SAFE_MODE"
            status = "BLOCKED"
        elif next_order_eligibility_ready:
            state = "CYCLE_RESUMED"
            status = "PASS"
        else:
            state = "WAIT_RECOVERY_VALIDATION"
            status = "PASS"

        report = AutonomousCycleResumeReport(
            status=status,
            state=state,
            unlock_id=unlock_id,
            handoff_id=handoff_id,
            cycle_id=cycle_id,
            cycle_sequence=cycle_sequence,
            recovery_verified=recovery_verified,
            resume_allowed=resume_allowed,
            cycle_created=cycle_created,
            duplicate_cycle=duplicate_cycle,
            resume_token_written=resume_token_written,
            recovery_snapshot_written=recovery_snapshot_written,
            next_order_eligibility_ready=next_order_eligibility_ready,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_recovery_result_path=str(recovery_result_path.resolve()),
            resume_token_path=str(resume_token_path.resolve()),
            cycle_ledger_path=str(cycle_ledger_path.resolve()),
            recovery_snapshot_path=str(recovery_snapshot_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
