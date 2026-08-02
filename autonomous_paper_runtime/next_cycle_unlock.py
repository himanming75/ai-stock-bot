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


def _unlock_id(handoff_id: str) -> str:
    digest = hashlib.sha256(handoff_id.encode("utf-8")).hexdigest()[:24]
    return f"unlock-{digest}"


@dataclass(frozen=True)
class NextCycleUnlockReport:
    status: str
    state: str
    handoff_id: str
    unlock_id: str
    handoff_verified: bool
    unlock_allowed: bool
    unlock_created: bool
    duplicate_unlock: bool
    recovery_snapshot_written: bool
    next_cycle_ready: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_handoff_result_path: str
    source_handoff_token_path: str
    unlock_token_path: str
    unlock_ledger_path: str
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
            "duplicate_unlock": self.duplicate_unlock,
            "handoff_id": self.handoff_id,
            "handoff_verified": self.handoff_verified,
            "implementation_type": "NEXT_CYCLE_UNLOCK",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_cycle_ready": self.next_cycle_ready,
            "next_phase": (
                "V139_04_RECOVERY_VALIDATION"
                if self.next_cycle_ready and not self.safe_mode_engaged
                else "V139_03_WAIT_HANDOFF"
            ),
            "recovery_snapshot_path": self.recovery_snapshot_path,
            "recovery_snapshot_written": self.recovery_snapshot_written,
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_handoff_result_path": self.source_handoff_result_path,
            "source_handoff_token_path": self.source_handoff_token_path,
            "stage": "V139.03",
            "state": self.state,
            "status": self.status,
            "unlock_allowed": self.unlock_allowed,
            "unlock_created": self.unlock_created,
            "unlock_id": self.unlock_id,
            "unlock_ledger_path": self.unlock_ledger_path,
            "unlock_token_path": self.unlock_token_path,
            "validation_mode": "ACTUAL_SAVED_STATE_LOCAL_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class NextCycleUnlock:
    def run(
        self,
        *,
        handoff_result_path: Path,
        handoff_token_path: Path,
        unlock_token_path: Path,
        unlock_ledger_path: Path,
        recovery_snapshot_path: Path,
        result_path: Path,
    ) -> NextCycleUnlockReport:
        issues: list[dict[str, Any]] = []
        try:
            handoff_result = _load_json(handoff_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            handoff_result = {}
            issues.append({
                "code": "INVALID_HANDOFF_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not handoff_result:
            issues.append({
                "code": "HANDOFF_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(handoff_result_path),
            })

        source_status = str(handoff_result.get("status", "")).upper()
        source_state = str(handoff_result.get("state", "")).upper()
        source_safe_mode = bool(handoff_result.get("safe_mode_engaged", False))
        source_ready = bool(handoff_result.get("next_cycle_unlock_ready", False))
        result_handoff_id = str(handoff_result.get("handoff_id", "")).strip()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_HANDOFF_SAFE_MODE",
                "blocking": True,
                "detail": "V139.02 handoff is blocked or in safe mode",
            })

        token: dict[str, Any] = {}
        token_required = source_ready or source_state == "HANDOFF_READY"
        if token_required:
            try:
                token = _load_json(handoff_token_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                issues.append({
                    "code": "INVALID_HANDOFF_TOKEN",
                    "blocking": True,
                    "detail": str(exc),
                })
            if not token:
                issues.append({
                    "code": "HANDOFF_TOKEN_NOT_FOUND",
                    "blocking": True,
                    "detail": str(handoff_token_path),
                })

        token_handoff_id = str(token.get("handoff_id", "")).strip()
        if token and result_handoff_id != token_handoff_id:
            issues.append({
                "code": "HANDOFF_ID_MISMATCH",
                "blocking": True,
                "detail": (
                    f"result handoff_id={result_handoff_id or '<empty>'}, "
                    f"token handoff_id={token_handoff_id or '<empty>'}"
                ),
            })
        if token and not bool(token.get("next_cycle_unlock_ready", False)):
            issues.append({
                "code": "HANDOFF_TOKEN_NOT_READY",
                "blocking": True,
                "detail": "handoff token does not permit next-cycle unlock",
            })
        if token and not (
            bool(token.get("terminal_observed", False))
            and bool(token.get("terminal_commit_verified", False))
        ):
            issues.append({
                "code": "HANDOFF_TERMINAL_PROOF_MISSING",
                "blocking": True,
                "detail": "handoff token lacks terminal observation or commit proof",
            })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        handoff_verified = bool(
            source_ready
            and source_state == "HANDOFF_READY"
            and token
            and result_handoff_id
            and result_handoff_id == token_handoff_id
            and not safe_mode
        )
        unlock_allowed = handoff_verified
        unlock_id = _unlock_id(result_handoff_id) if unlock_allowed else ""
        unlock_created = False
        duplicate_unlock = False
        recovery_snapshot_written = False

        if unlock_allowed:
            token_payload = {
                "unlock_id": unlock_id,
                "handoff_id": result_handoff_id,
                "source_stage": "V139.02",
                "source_state": source_state,
                "next_cycle_ready": True,
                "source_handoff_result_path": str(handoff_result_path.resolve()),
                "source_handoff_token_path": str(handoff_token_path.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            if unlock_token_path.exists():
                try:
                    existing = _load_json(unlock_token_path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    existing = {}
                    issues.append({
                        "code": "INVALID_EXISTING_UNLOCK_TOKEN",
                        "blocking": True,
                        "detail": str(exc),
                    })
                if (
                    existing.get("unlock_id") == unlock_id
                    and existing.get("handoff_id") == result_handoff_id
                ):
                    duplicate_unlock = True
                else:
                    issues.append({
                        "code": "UNLOCK_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing unlock token belongs to a different handoff",
                    })
            else:
                _atomic_write_json(unlock_token_path, token_payload)
                _append_jsonl(
                    unlock_ledger_path,
                    {"event": "NEXT_CYCLE_UNLOCK_CREATED", **token_payload},
                )
                unlock_created = True

            blocking = sum(1 for issue in issues if issue.get("blocking"))
            if blocking == 0:
                recovery_payload = {
                    "unlock_id": unlock_id,
                    "handoff_id": result_handoff_id,
                    "unlock_token_verified": True,
                    "next_cycle_ready": True,
                    "duplicate_unlock": duplicate_unlock,
                    "source_handoff_result_path": str(handoff_result_path.resolve()),
                    "source_handoff_token_path": str(handoff_token_path.resolve()),
                    "unlock_token_path": str(unlock_token_path.resolve()),
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
                _atomic_write_json(recovery_snapshot_path, recovery_payload)
                recovery_snapshot_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        next_cycle_ready = bool(
            unlock_allowed
            and (unlock_created or duplicate_unlock)
            and recovery_snapshot_written
            and not safe_mode
        )

        if safe_mode:
            state = "UNLOCK_SAFE_MODE"
            status = "BLOCKED"
        elif next_cycle_ready:
            state = "NEXT_CYCLE_UNLOCKED"
            status = "PASS"
        else:
            state = "WAIT_HANDOFF"
            status = "PASS"

        report = NextCycleUnlockReport(
            status=status,
            state=state,
            handoff_id=result_handoff_id,
            unlock_id=unlock_id,
            handoff_verified=handoff_verified,
            unlock_allowed=unlock_allowed,
            unlock_created=unlock_created,
            duplicate_unlock=duplicate_unlock,
            recovery_snapshot_written=recovery_snapshot_written,
            next_cycle_ready=next_cycle_ready,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_handoff_result_path=str(handoff_result_path.resolve()),
            source_handoff_token_path=str(handoff_token_path.resolve()),
            unlock_token_path=str(unlock_token_path.resolve()),
            unlock_ledger_path=str(unlock_ledger_path.resolve()),
            recovery_snapshot_path=str(recovery_snapshot_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
