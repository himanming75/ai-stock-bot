from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {"FILLED", "CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}


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


def _handoff_id(source: dict[str, Any]) -> str:
    identity = {
        "final_order_status": str(source.get("final_order_status", "")).upper(),
        "observed_at": str(source.get("observed_at", "")),
        "source_cycle_result_path": str(source.get("source_cycle_result_path", "")),
        "source_readiness_path": str(source.get("source_readiness_path", "")),
        "stage": str(source.get("stage", "")),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "handoff-" + hashlib.sha256(encoded).hexdigest()[:24]


@dataclass(frozen=True)
class TerminalCommitHandoffReport:
    status: str
    state: str
    final_order_status: str
    terminal_observed: bool
    terminal_commit_verified: bool
    handoff_allowed: bool
    handoff_created: bool
    duplicate_handoff: bool
    next_cycle_unlock_ready: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    handoff_id: str
    source_monitor_result_path: str
    handoff_token_path: str
    recovery_ledger_path: str
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
            "duplicate_handoff": self.duplicate_handoff,
            "final_order_status": self.final_order_status,
            "handoff_allowed": self.handoff_allowed,
            "handoff_created": self.handoff_created,
            "handoff_id": self.handoff_id,
            "handoff_token_path": self.handoff_token_path,
            "implementation_type": "TERMINAL_COMMIT_HANDOFF",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_cycle_unlock_ready": self.next_cycle_unlock_ready,
            "next_phase": (
                "V139_03_NEXT_CYCLE_UNLOCK"
                if self.next_cycle_unlock_ready and not self.safe_mode_engaged
                else "V139_02_WAIT_TERMINAL_COMMIT_HANDOFF"
            ),
            "recovery_ledger_path": self.recovery_ledger_path,
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_monitor_result_path": self.source_monitor_result_path,
            "stage": "V139.02",
            "state": self.state,
            "status": self.status,
            "terminal_commit_verified": self.terminal_commit_verified,
            "terminal_observed": self.terminal_observed,
            "validation_mode": "ACTUAL_SAVED_STATE_LOCAL_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class TerminalCommitHandoff:
    def run(
        self,
        *,
        monitor_result_path: Path,
        handoff_token_path: Path,
        recovery_ledger_path: Path,
        result_path: Path,
    ) -> TerminalCommitHandoffReport:
        issues: list[dict[str, Any]] = []
        try:
            source = _load_json(monitor_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            source = {}
            issues.append(
                {
                    "code": "INVALID_MONITOR_RESULT",
                    "blocking": True,
                    "detail": str(exc),
                }
            )

        if not source:
            issues.append(
                {
                    "code": "MONITOR_RESULT_NOT_FOUND",
                    "blocking": True,
                    "detail": str(monitor_result_path),
                }
            )

        final_status = str(source.get("final_order_status", "")).strip().upper()
        terminal_observed = bool(source.get("terminal_observed", False))
        terminal_commit_verified = bool(source.get("terminal_commit_verified", False))
        source_next_order_allowed = bool(source.get("next_order_allowed", False))
        source_safe_mode = bool(source.get("safe_mode_engaged", False))
        source_status = str(source.get("status", "")).strip().upper()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append(
                {
                    "code": "SOURCE_MONITOR_SAFE_MODE",
                    "blocking": True,
                    "detail": "V139.01 monitor result is blocked or in safe mode",
                }
            )
        if terminal_observed and final_status not in TERMINAL_STATUSES:
            issues.append(
                {
                    "code": "INVALID_TERMINAL_STATUS",
                    "blocking": True,
                    "detail": f"terminal_observed=true but status={final_status or '<empty>'}",
                }
            )
        if terminal_commit_verified and not terminal_observed:
            issues.append(
                {
                    "code": "COMMIT_WITHOUT_TERMINAL",
                    "blocking": True,
                    "detail": "terminal commit cannot be verified before terminal observation",
                }
            )
        if source_next_order_allowed and not (
            terminal_observed and terminal_commit_verified
        ):
            issues.append(
                {
                    "code": "INVALID_SOURCE_UNLOCK",
                    "blocking": True,
                    "detail": "source next_order_allowed conflicts with terminal commit state",
                }
            )

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        handoff_allowed = bool(
            terminal_observed
            and terminal_commit_verified
            and source_next_order_allowed
            and not safe_mode
        )

        handoff_id = _handoff_id(source) if handoff_allowed else ""
        handoff_created = False
        duplicate_handoff = False

        if handoff_allowed:
            token_payload = {
                "handoff_id": handoff_id,
                "source_stage": str(source.get("stage", "V139.01")),
                "source_state": str(source.get("state", "")),
                "final_order_status": final_status,
                "terminal_observed": True,
                "terminal_commit_verified": True,
                "next_cycle_unlock_ready": True,
                "source_monitor_result_path": str(monitor_result_path.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            if handoff_token_path.exists():
                try:
                    existing = _load_json(handoff_token_path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    existing = {}
                    issues.append(
                        {
                            "code": "INVALID_EXISTING_HANDOFF_TOKEN",
                            "blocking": True,
                            "detail": str(exc),
                        }
                    )
                if existing.get("handoff_id") == handoff_id:
                    duplicate_handoff = True
                else:
                    issues.append(
                        {
                            "code": "HANDOFF_TOKEN_CONFLICT",
                            "blocking": True,
                            "detail": "existing handoff token belongs to a different terminal state",
                        }
                    )
            else:
                _atomic_write_json(handoff_token_path, token_payload)
                _append_jsonl(
                    recovery_ledger_path,
                    {
                        "event": "TERMINAL_COMMIT_HANDOFF_CREATED",
                        **token_payload,
                    },
                )
                handoff_created = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        next_cycle_unlock_ready = bool(
            handoff_allowed
            and (handoff_created or duplicate_handoff)
            and not safe_mode
        )

        if safe_mode:
            state = "HANDOFF_SAFE_MODE"
            status = "BLOCKED"
        elif next_cycle_unlock_ready:
            state = "HANDOFF_READY"
            status = "PASS"
        else:
            state = "WAIT_TERMINAL_COMMIT"
            status = "PASS"

        report = TerminalCommitHandoffReport(
            status=status,
            state=state,
            final_order_status=final_status,
            terminal_observed=terminal_observed,
            terminal_commit_verified=terminal_commit_verified,
            handoff_allowed=handoff_allowed,
            handoff_created=handoff_created,
            duplicate_handoff=duplicate_handoff,
            next_cycle_unlock_ready=next_cycle_unlock_ready,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            handoff_id=handoff_id,
            source_monitor_result_path=str(monitor_result_path.resolve()),
            handoff_token_path=str(handoff_token_path.resolve()),
            recovery_ledger_path=str(recovery_ledger_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
