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


def _completion_id(client_order_id: str, broker_order_id: str, status: str) -> str:
    identity = f"{client_order_id}|{broker_order_id}|{status}"
    return "completion-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class TerminalCommitCycleCompletionReport:
    status: str
    state: str
    client_order_id: str
    broker_order_id: str
    final_order_status: str
    completion_id: str
    terminal_monitor_verified: bool
    terminal_commit_verified: bool
    cycle_completed: bool
    duplicate_completion: bool
    completion_ledger_written: bool
    audit_snapshot_written: bool
    next_cycle_handoff_ready: bool
    next_order_allowed: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_lifecycle_result_path: str
    source_monitor_state_path: str
    terminal_commit_token_path: str
    cycle_completion_token_path: str
    completion_ledger_path: str
    audit_snapshot_path: str
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
            "audit_snapshot_path": self.audit_snapshot_path,
            "audit_snapshot_written": self.audit_snapshot_written,
            "blocking_issue_count": self.blocking_issue_count,
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "completion_id": self.completion_id,
            "completion_ledger_path": self.completion_ledger_path,
            "completion_ledger_written": self.completion_ledger_written,
            "cycle_completed": self.cycle_completed,
            "cycle_completion_token_path": self.cycle_completion_token_path,
            "duplicate_completion": self.duplicate_completion,
            "final_order_status": self.final_order_status,
            "implementation_type": "TERMINAL_COMMIT_AND_CYCLE_COMPLETION",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_cycle_handoff_ready": self.next_cycle_handoff_ready,
            "next_order_allowed": self.next_order_allowed,
            "next_phase": (
                "V139_02_TERMINAL_COMMIT_HANDOFF"
                if self.next_cycle_handoff_ready and not self.safe_mode_engaged
                else "V139_10_WAIT_TERMINAL"
            ),
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_lifecycle_result_path": self.source_lifecycle_result_path,
            "source_monitor_state_path": self.source_monitor_state_path,
            "stage": "V139.10",
            "state": self.state,
            "status": self.status,
            "terminal_commit_token_path": self.terminal_commit_token_path,
            "terminal_commit_verified": self.terminal_commit_verified,
            "terminal_monitor_verified": self.terminal_monitor_verified,
            "validation_mode": "LOCAL_TERMINAL_COMMIT_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class TerminalCommitCycleCompletion:
    def run(
        self,
        *,
        lifecycle_result_path: Path,
        monitor_state_path: Path,
        terminal_commit_token_path: Path,
        cycle_completion_token_path: Path,
        completion_ledger_path: Path,
        audit_snapshot_path: Path,
        result_path: Path,
    ) -> TerminalCommitCycleCompletionReport:
        issues: list[dict[str, Any]] = []

        try:
            lifecycle = _load_json(lifecycle_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            lifecycle = {}
            issues.append({"code": "INVALID_LIFECYCLE_RESULT", "blocking": True, "detail": str(exc)})

        if not lifecycle:
            issues.append({
                "code": "LIFECYCLE_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(lifecycle_result_path),
            })

        source_status = str(lifecycle.get("status", "")).upper()
        source_state = str(lifecycle.get("state", "")).upper()
        source_safe_mode = bool(lifecycle.get("safe_mode_engaged", False))
        terminal_observed = bool(lifecycle.get("terminal_observed", False))
        terminal_commit_ready = bool(lifecycle.get("terminal_commit_ready", False))
        client_order_id = str(lifecycle.get("client_order_id", "")).strip()
        broker_order_id = str(lifecycle.get("broker_order_id", "")).strip()
        final_status = str(lifecycle.get("order_status", "")).strip().upper()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_LIFECYCLE_SAFE_MODE",
                "blocking": True,
                "detail": "V139.09 lifecycle result is blocked or in safe mode",
            })

        commit_required = (
            terminal_observed
            or terminal_commit_ready
            or source_state == "TERMINAL_OBSERVED"
        )
        monitor_state: dict[str, Any] = {}
        if commit_required:
            try:
                monitor_state = _load_json(monitor_state_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                issues.append({
                    "code": "INVALID_MONITOR_STATE",
                    "blocking": True,
                    "detail": str(exc),
                })
            if not monitor_state:
                issues.append({
                    "code": "MONITOR_STATE_NOT_FOUND",
                    "blocking": True,
                    "detail": str(monitor_state_path),
                })

        monitor_client_id = str(monitor_state.get("client_order_id", "")).strip()
        monitor_broker_id = str(monitor_state.get("broker_order_id", "")).strip()
        monitor_status = str(monitor_state.get("status", "")).strip().upper()

        if terminal_observed and final_status not in TERMINAL_STATUSES:
            issues.append({
                "code": "INVALID_TERMINAL_STATUS",
                "blocking": True,
                "detail": f"terminal_observed=true but status={final_status or '<empty>'}",
            })
        if terminal_commit_ready and not terminal_observed:
            issues.append({
                "code": "COMMIT_READY_WITHOUT_TERMINAL",
                "blocking": True,
                "detail": "terminal commit cannot be ready before terminal observation",
            })
        if commit_required and not (client_order_id and broker_order_id):
            issues.append({
                "code": "TERMINAL_IDENTITY_MISSING",
                "blocking": True,
                "detail": "terminal result must contain client and broker order IDs",
            })
        if monitor_state and (
            monitor_client_id != client_order_id
            or monitor_broker_id != broker_order_id
            or monitor_status != final_status
            or not bool(monitor_state.get("terminal_observed", False))
            or bool(monitor_state.get("active_order_present", True))
        ):
            issues.append({
                "code": "MONITOR_STATE_MISMATCH",
                "blocking": True,
                "detail": "monitor state does not match terminal lifecycle result",
            })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        terminal_monitor_verified = bool(
            source_status == "PASS"
            and source_state == "TERMINAL_OBSERVED"
            and terminal_observed
            and terminal_commit_ready
            and final_status in TERMINAL_STATUSES
            and client_order_id
            and broker_order_id
            and monitor_state
            and monitor_client_id == client_order_id
            and monitor_broker_id == broker_order_id
            and monitor_status == final_status
            and not bool(monitor_state.get("active_order_present", True))
            and bool(monitor_state.get("terminal_observed", False))
            and not safe_mode
        )

        completion_id = (
            _completion_id(client_order_id, broker_order_id, final_status)
            if terminal_monitor_verified
            else ""
        )
        duplicate_completion = False
        completion_ledger_written = False
        audit_snapshot_written = False
        terminal_commit_verified = False
        cycle_completed = False

        if terminal_monitor_verified:
            terminal_payload = {
                "completion_id": completion_id,
                "client_order_id": client_order_id,
                "broker_order_id": broker_order_id,
                "final_order_status": final_status,
                "terminal_observed": True,
                "terminal_commit_verified": True,
                "source_lifecycle_result_path": str(lifecycle_result_path.resolve()),
                "source_monitor_state_path": str(monitor_state_path.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            completion_payload = {
                **terminal_payload,
                "cycle_completed": True,
                "next_cycle_handoff_ready": True,
            }

            existing_terminal = {}
            existing_completion = {}
            if terminal_commit_token_path.exists():
                try:
                    existing_terminal = _load_json(terminal_commit_token_path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    issues.append({
                        "code": "INVALID_EXISTING_TERMINAL_TOKEN",
                        "blocking": True,
                        "detail": str(exc),
                    })
            if cycle_completion_token_path.exists():
                try:
                    existing_completion = _load_json(cycle_completion_token_path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    issues.append({
                        "code": "INVALID_EXISTING_COMPLETION_TOKEN",
                        "blocking": True,
                        "detail": str(exc),
                    })

            if existing_terminal or existing_completion:
                if (
                    existing_terminal.get("completion_id") == completion_id
                    and existing_completion.get("completion_id") == completion_id
                ):
                    duplicate_completion = True
                else:
                    issues.append({
                        "code": "COMPLETION_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing terminal/completion token belongs to another order",
                    })
            else:
                _atomic_write_json(terminal_commit_token_path, terminal_payload)
                _atomic_write_json(cycle_completion_token_path, completion_payload)
                _append_jsonl(
                    completion_ledger_path,
                    {
                        "event": "TERMINAL_COMMIT_AND_CYCLE_COMPLETION",
                        **completion_payload,
                    },
                )
                completion_ledger_written = True

            blocking = sum(1 for issue in issues if issue.get("blocking"))
            if blocking == 0:
                audit_payload = {
                    "completion_id": completion_id,
                    "client_order_id": client_order_id,
                    "broker_order_id": broker_order_id,
                    "final_order_status": final_status,
                    "order_quantity": lifecycle.get("order_quantity", 0),
                    "filled_quantity": lifecycle.get("filled_quantity", 0),
                    "remaining_quantity": lifecycle.get("remaining_quantity", 0),
                    "average_fill_price": lifecycle.get("average_fill_price", 0),
                    "terminal_commit_verified": True,
                    "cycle_completed": True,
                    "duplicate_completion": duplicate_completion,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
                _atomic_write_json(audit_snapshot_path, audit_payload)
                audit_snapshot_written = True
                terminal_commit_verified = True
                cycle_completed = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        terminal_commit_verified = bool(terminal_commit_verified and not safe_mode)
        cycle_completed = bool(cycle_completed and not safe_mode)
        next_cycle_handoff_ready = bool(
            terminal_commit_verified
            and cycle_completed
            and (completion_ledger_written or duplicate_completion)
            and audit_snapshot_written
            and not safe_mode
        )
        next_order_allowed = False

        if safe_mode:
            state = "TERMINAL_COMMIT_SAFE_MODE"
            status = "BLOCKED"
        elif next_cycle_handoff_ready:
            state = "CYCLE_COMPLETED"
            status = "PASS"
        else:
            state = "WAIT_TERMINAL"
            status = "PASS"

        report = TerminalCommitCycleCompletionReport(
            status=status,
            state=state,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            final_order_status=final_status,
            completion_id=completion_id,
            terminal_monitor_verified=terminal_monitor_verified,
            terminal_commit_verified=terminal_commit_verified,
            cycle_completed=cycle_completed,
            duplicate_completion=duplicate_completion,
            completion_ledger_written=completion_ledger_written,
            audit_snapshot_written=audit_snapshot_written,
            next_cycle_handoff_ready=next_cycle_handoff_ready,
            next_order_allowed=next_order_allowed,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_lifecycle_result_path=str(lifecycle_result_path.resolve()),
            source_monitor_state_path=str(monitor_state_path.resolve()),
            terminal_commit_token_path=str(terminal_commit_token_path.resolve()),
            cycle_completion_token_path=str(cycle_completion_token_path.resolve()),
            completion_ledger_path=str(completion_ledger_path.resolve()),
            audit_snapshot_path=str(audit_snapshot_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
