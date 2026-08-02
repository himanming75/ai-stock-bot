from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERMINAL_STATUSES = {"FILLED", "CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}
ACTIVE_STATUSES = {"NEW", "ACCEPTED", "PENDING_NEW", "PARTIALLY_FILLED", "PENDING_CANCEL", "PENDING_REPLACE"}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object required: {path}")
    return data


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


@dataclass(frozen=True)
class ActualTerminalMonitorContinuationReport:
    status: str
    state: str
    final_order_status: str
    terminal_observed: bool
    continue_monitoring: bool
    next_order_allowed: bool
    terminal_commit_verified: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_readiness_path: str
    source_cycle_result_path: str
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
            "continue_monitoring": self.continue_monitoring,
            "final_order_status": self.final_order_status,
            "implementation_type": "ACTUAL_SAVED_STATE_TERMINAL_MONITOR_CONTINUATION",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_order_allowed": self.next_order_allowed,
            "next_phase": (
                "V139_02_TERMINAL_COMMIT_HANDOFF"
                if self.terminal_observed and not self.safe_mode_engaged
                else "V139_01_CONTINUE_ACTUAL_TERMINAL_MONITOR"
            ),
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_cycle_result_path": self.source_cycle_result_path,
            "source_readiness_path": self.source_readiness_path,
            "stage": "V139.01",
            "state": self.state,
            "status": self.status,
            "terminal_commit_verified": self.terminal_commit_verified,
            "terminal_observed": self.terminal_observed,
            "validation_mode": "ACTUAL_SAVED_STATE_LOCAL_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class ActualSavedStateTerminalMonitorContinuation:
    def run(self, *, readiness_path: Path, cycle_result_path: Path, result_path: Path) -> ActualTerminalMonitorContinuationReport:
        issues: list[dict[str, Any]] = []
        try:
            readiness = _load_json(readiness_path)
            cycle = _load_json(cycle_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append({"code": "INVALID_SAVED_STATE", "blocking": True, "detail": str(exc)})
            readiness, cycle = {}, {}

        if not readiness:
            issues.append({"code": "READINESS_NOT_FOUND", "blocking": True, "detail": str(readiness_path)})
        if not cycle:
            issues.append({"code": "CYCLE_RESULT_NOT_FOUND", "blocking": True, "detail": str(cycle_result_path)})

        raw_status = str(
            readiness.get("order_status")
            or readiness.get("active_order_status")
            or cycle.get("final_order_status")
            or cycle.get("order_status")
            or ""
        ).strip().upper()
        active_present = bool(readiness.get("active_order_present", False))
        open_count = int(readiness.get("open_order_count", 0) or 0)
        terminal_commit_verified = bool(readiness.get("terminal_commit_verified", False))

        if not raw_status and active_present:
            raw_status = "ACCEPTED"

        terminal = raw_status in TERMINAL_STATUSES
        active = raw_status in ACTIVE_STATUSES or active_present or open_count > 0

        if terminal and (active_present or open_count > 0):
            issues.append({
                "code": "TERMINAL_ACTIVE_STATE_CONFLICT",
                "blocking": True,
                "detail": f"terminal status={raw_status} conflicts with active_order_present={active_present}, open_orders={open_count}",
            })
        if not terminal and not active and readiness:
            issues.append({
                "code": "ORDER_STATE_UNRESOLVED",
                "blocking": True,
                "detail": f"unable to classify saved order state: status={raw_status or '<empty>'}",
            })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        if safe_mode:
            state = "MONITOR_SAFE_MODE"
            continue_monitoring = False
        elif terminal:
            state = "TERMINAL_OBSERVED"
            continue_monitoring = False
        else:
            state = "WAIT_ACTIVE_ORDER"
            continue_monitoring = True

        report = ActualTerminalMonitorContinuationReport(
            status="PASS" if not safe_mode else "BLOCKED",
            state=state,
            final_order_status=raw_status,
            terminal_observed=terminal,
            continue_monitoring=continue_monitoring,
            next_order_allowed=bool(terminal and terminal_commit_verified and not safe_mode),
            terminal_commit_verified=terminal_commit_verified,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_readiness_path=str(readiness_path.resolve()),
            source_cycle_result_path=str(cycle_result_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
