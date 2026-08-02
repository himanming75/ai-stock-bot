from __future__ import annotations

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


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"JSON object required at {path}:{line_number}")
        rows.append(payload)
    return rows


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


@dataclass(frozen=True)
class RecoveryValidationReport:
    status: str
    state: str
    unlock_id: str
    handoff_id: str
    unlock_result_verified: bool
    unlock_token_verified: bool
    unlock_ledger_verified: bool
    recovery_snapshot_verified: bool
    recovery_validated: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_unlock_result_path: str
    source_unlock_token_path: str
    source_unlock_ledger_path: str
    source_recovery_snapshot_path: str
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
            "handoff_id": self.handoff_id,
            "implementation_type": "RECOVERY_VALIDATION",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_phase": (
                "V139_05_AUTONOMOUS_CYCLE_RESUME"
                if self.recovery_validated and not self.safe_mode_engaged
                else "V139_04_WAIT_UNLOCK"
            ),
            "recovery_snapshot_verified": self.recovery_snapshot_verified,
            "recovery_validated": self.recovery_validated,
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_recovery_snapshot_path": self.source_recovery_snapshot_path,
            "source_unlock_ledger_path": self.source_unlock_ledger_path,
            "source_unlock_result_path": self.source_unlock_result_path,
            "source_unlock_token_path": self.source_unlock_token_path,
            "stage": "V139.04",
            "state": self.state,
            "status": self.status,
            "unlock_id": self.unlock_id,
            "unlock_ledger_verified": self.unlock_ledger_verified,
            "unlock_result_verified": self.unlock_result_verified,
            "unlock_token_verified": self.unlock_token_verified,
            "validation_mode": "ACTUAL_SAVED_STATE_LOCAL_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class RecoveryValidation:
    def run(
        self,
        *,
        unlock_result_path: Path,
        unlock_token_path: Path,
        unlock_ledger_path: Path,
        recovery_snapshot_path: Path,
        result_path: Path,
    ) -> RecoveryValidationReport:
        issues: list[dict[str, Any]] = []

        try:
            unlock_result = _load_json(unlock_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            unlock_result = {}
            issues.append({
                "code": "INVALID_UNLOCK_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not unlock_result:
            issues.append({
                "code": "UNLOCK_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(unlock_result_path),
            })

        source_status = str(unlock_result.get("status", "")).upper()
        source_state = str(unlock_result.get("state", "")).upper()
        source_safe_mode = bool(unlock_result.get("safe_mode_engaged", False))
        source_ready = bool(unlock_result.get("next_cycle_ready", False))
        unlock_id = str(unlock_result.get("unlock_id", "")).strip()
        handoff_id = str(unlock_result.get("handoff_id", "")).strip()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_UNLOCK_SAFE_MODE",
                "blocking": True,
                "detail": "V139.03 unlock result is blocked or in safe mode",
            })

        unlock_required = source_ready or source_state == "NEXT_CYCLE_UNLOCKED"
        token: dict[str, Any] = {}
        ledger: list[dict[str, Any]] = []
        snapshot: dict[str, Any] = {}

        if unlock_required:
            for code, path, loader in (
                ("UNLOCK_TOKEN", unlock_token_path, _load_json),
                ("UNLOCK_LEDGER", unlock_ledger_path, _load_jsonl),
                ("RECOVERY_SNAPSHOT", recovery_snapshot_path, _load_json),
            ):
                try:
                    loaded = loader(path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    loaded = {} if loader is _load_json else []
                    issues.append({
                        "code": f"INVALID_{code}",
                        "blocking": True,
                        "detail": str(exc),
                    })
                if code == "UNLOCK_TOKEN":
                    token = loaded
                elif code == "UNLOCK_LEDGER":
                    ledger = loaded
                else:
                    snapshot = loaded

            if not token:
                issues.append({
                    "code": "UNLOCK_TOKEN_NOT_FOUND",
                    "blocking": True,
                    "detail": str(unlock_token_path),
                })
            if not ledger:
                issues.append({
                    "code": "UNLOCK_LEDGER_NOT_FOUND",
                    "blocking": True,
                    "detail": str(unlock_ledger_path),
                })
            if not snapshot:
                issues.append({
                    "code": "RECOVERY_SNAPSHOT_NOT_FOUND",
                    "blocking": True,
                    "detail": str(recovery_snapshot_path),
                })

        token_unlock_id = str(token.get("unlock_id", "")).strip()
        token_handoff_id = str(token.get("handoff_id", "")).strip()
        matching_ledger = [
            row for row in ledger
            if row.get("event") == "NEXT_CYCLE_UNLOCK_CREATED"
            and row.get("unlock_id") == unlock_id
            and row.get("handoff_id") == handoff_id
        ]
        snapshot_unlock_id = str(snapshot.get("unlock_id", "")).strip()
        snapshot_handoff_id = str(snapshot.get("handoff_id", "")).strip()

        if token and (token_unlock_id != unlock_id or token_handoff_id != handoff_id):
            issues.append({
                "code": "UNLOCK_TOKEN_ID_MISMATCH",
                "blocking": True,
                "detail": "unlock result and token IDs do not match",
            })
        if ledger and len(matching_ledger) != 1:
            issues.append({
                "code": "UNLOCK_LEDGER_SEQUENCE_MISMATCH",
                "blocking": True,
                "detail": f"expected exactly one matching unlock event, found {len(matching_ledger)}",
            })
        if snapshot and (
            snapshot_unlock_id != unlock_id
            or snapshot_handoff_id != handoff_id
            or not bool(snapshot.get("unlock_token_verified", False))
            or not bool(snapshot.get("next_cycle_ready", False))
        ):
            issues.append({
                "code": "RECOVERY_SNAPSHOT_MISMATCH",
                "blocking": True,
                "detail": "recovery snapshot does not match verified unlock state",
            })
        if unlock_required and not (unlock_id and handoff_id):
            issues.append({
                "code": "UNLOCK_IDENTITY_MISSING",
                "blocking": True,
                "detail": "unlock_id or handoff_id is empty",
            })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        unlock_result_verified = bool(
            source_status == "PASS"
            and source_state == "NEXT_CYCLE_UNLOCKED"
            and source_ready
            and unlock_id
            and handoff_id
            and not safe_mode
        )
        unlock_token_verified = bool(
            token
            and token_unlock_id == unlock_id
            and token_handoff_id == handoff_id
            and bool(token.get("next_cycle_ready", False))
            and not safe_mode
        )
        unlock_ledger_verified = bool(len(matching_ledger) == 1 and not safe_mode)
        recovery_snapshot_verified = bool(
            snapshot
            and snapshot_unlock_id == unlock_id
            and snapshot_handoff_id == handoff_id
            and bool(snapshot.get("unlock_token_verified", False))
            and bool(snapshot.get("next_cycle_ready", False))
            and not safe_mode
        )
        recovery_validated = bool(
            unlock_result_verified
            and unlock_token_verified
            and unlock_ledger_verified
            and recovery_snapshot_verified
            and not safe_mode
        )

        if safe_mode:
            state = "RECOVERY_SAFE_MODE"
            status = "BLOCKED"
        elif recovery_validated:
            state = "RECOVERY_VALIDATED"
            status = "PASS"
        else:
            state = "WAIT_UNLOCK"
            status = "PASS"

        report = RecoveryValidationReport(
            status=status,
            state=state,
            unlock_id=unlock_id,
            handoff_id=handoff_id,
            unlock_result_verified=unlock_result_verified,
            unlock_token_verified=unlock_token_verified,
            unlock_ledger_verified=unlock_ledger_verified,
            recovery_snapshot_verified=recovery_snapshot_verified,
            recovery_validated=recovery_validated,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_unlock_result_path=str(unlock_result_path.resolve()),
            source_unlock_token_path=str(unlock_token_path.resolve()),
            source_unlock_ledger_path=str(unlock_ledger_path.resolve()),
            source_recovery_snapshot_path=str(recovery_snapshot_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
