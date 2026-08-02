from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_STATUSES = {
    "NEW",
    "ACCEPTED",
    "PENDING_NEW",
    "PARTIALLY_FILLED",
    "PENDING_CANCEL",
    "PENDING_REPLACE",
}
TERMINAL_STATUSES = {"FILLED", "CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}
STATUS_RANK = {
    "NEW": 1,
    "PENDING_NEW": 2,
    "ACCEPTED": 3,
    "PARTIALLY_FILLED": 4,
    "PENDING_CANCEL": 5,
    "PENDING_REPLACE": 5,
    "FILLED": 10,
    "CANCELED": 10,
    "CANCELLED": 10,
    "EXPIRED": 10,
    "REJECTED": 10,
}


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


@dataclass(frozen=True)
class ActiveOrderLifecycleMonitorReport:
    status: str
    state: str
    client_order_id: str
    broker_order_id: str
    order_status: str
    order_quantity: float
    filled_quantity: float
    remaining_quantity: float
    average_fill_price: float
    acceptance_verified: bool
    lifecycle_snapshot_verified: bool
    active_order_present: bool
    partial_fill_observed: bool
    terminal_observed: bool
    terminal_commit_ready: bool
    next_order_allowed: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_acceptance_result_path: str
    source_acceptance_token_path: str
    source_lifecycle_snapshot_path: str
    previous_lifecycle_snapshot_path: str
    monitor_state_path: str
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
            "acceptance_verified": self.acceptance_verified,
            "active_order_present": self.active_order_present,
            "average_fill_price": self.average_fill_price,
            "blocking_issue_count": self.blocking_issue_count,
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "filled_quantity": self.filled_quantity,
            "implementation_type": "ACTIVE_ORDER_LIFECYCLE_MONITOR",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "lifecycle_snapshot_verified": self.lifecycle_snapshot_verified,
            "live_orders_submitted": self.live_orders_submitted,
            "monitor_state_path": self.monitor_state_path,
            "network_requests_executed": self.network_requests_executed,
            "next_order_allowed": self.next_order_allowed,
            "next_phase": (
                "V139_10_TERMINAL_COMMIT_AND_CYCLE_COMPLETION"
                if self.terminal_commit_ready and not self.safe_mode_engaged
                else "V139_09_CONTINUE_ACTIVE_ORDER_MONITOR"
            ),
            "order_quantity": self.order_quantity,
            "order_status": self.order_status,
            "partial_fill_observed": self.partial_fill_observed,
            "previous_lifecycle_snapshot_path": self.previous_lifecycle_snapshot_path,
            "remaining_quantity": self.remaining_quantity,
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_acceptance_result_path": self.source_acceptance_result_path,
            "source_acceptance_token_path": self.source_acceptance_token_path,
            "source_lifecycle_snapshot_path": self.source_lifecycle_snapshot_path,
            "stage": "V139.09",
            "state": self.state,
            "status": self.status,
            "terminal_commit_ready": self.terminal_commit_ready,
            "terminal_observed": self.terminal_observed,
            "validation_mode": "LOCAL_LIFECYCLE_SNAPSHOT_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class ActiveOrderLifecycleMonitor:
    def run(
        self,
        *,
        acceptance_result_path: Path,
        acceptance_token_path: Path,
        lifecycle_snapshot_path: Path,
        previous_lifecycle_snapshot_path: Path,
        monitor_state_path: Path,
        result_path: Path,
    ) -> ActiveOrderLifecycleMonitorReport:
        issues: list[dict[str, Any]] = []

        try:
            acceptance = _load_json(acceptance_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            acceptance = {}
            issues.append({"code": "INVALID_ACCEPTANCE_RESULT", "blocking": True, "detail": str(exc)})

        if not acceptance:
            issues.append({
                "code": "ACCEPTANCE_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(acceptance_result_path),
            })

        source_status = str(acceptance.get("status", "")).upper()
        source_state = str(acceptance.get("state", "")).upper()
        source_safe_mode = bool(acceptance.get("safe_mode_engaged", False))
        lifecycle_ready = bool(acceptance.get("lifecycle_monitor_ready", False))
        client_order_id = str(acceptance.get("client_order_id", "")).strip()
        broker_order_id = str(acceptance.get("broker_order_id", "")).strip()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_ACCEPTANCE_SAFE_MODE",
                "blocking": True,
                "detail": "V139.08 acceptance verification is blocked or in safe mode",
            })

        monitor_required = lifecycle_ready or source_state == "ORDER_ACCEPTED"
        token: dict[str, Any] = {}
        snapshot: dict[str, Any] = {}
        previous: dict[str, Any] = {}

        if monitor_required:
            for code, path in (
                ("ACCEPTANCE_TOKEN", acceptance_token_path),
                ("LIFECYCLE_SNAPSHOT", lifecycle_snapshot_path),
            ):
                try:
                    loaded = _load_json(path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    loaded = {}
                    issues.append({"code": f"INVALID_{code}", "blocking": True, "detail": str(exc)})
                if code == "ACCEPTANCE_TOKEN":
                    token = loaded
                else:
                    snapshot = loaded

            if not token:
                issues.append({
                    "code": "ACCEPTANCE_TOKEN_NOT_FOUND",
                    "blocking": True,
                    "detail": str(acceptance_token_path),
                })
            if not snapshot:
                issues.append({
                    "code": "LIFECYCLE_SNAPSHOT_NOT_FOUND",
                    "blocking": True,
                    "detail": str(lifecycle_snapshot_path),
                })

        try:
            previous = _load_json(previous_lifecycle_snapshot_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append({
                "code": "INVALID_PREVIOUS_LIFECYCLE_SNAPSHOT",
                "blocking": True,
                "detail": str(exc),
            })

        token_client_id = str(token.get("client_order_id", "")).strip()
        token_broker_id = str(token.get("broker_order_id", "")).strip()
        snapshot_client_id = str(snapshot.get("client_order_id", "")).strip()
        snapshot_broker_id = str(snapshot.get("broker_order_id", "")).strip()
        order_status = str(snapshot.get("status", "")).strip().upper()

        try:
            order_quantity = float(snapshot.get("quantity", 0) or 0)
            filled_quantity = float(snapshot.get("filled_quantity", 0) or 0)
            average_fill_price = float(snapshot.get("average_fill_price", 0) or 0)
        except (TypeError, ValueError):
            order_quantity = filled_quantity = average_fill_price = 0.0
            issues.append({
                "code": "INVALID_NUMERIC_LIFECYCLE_VALUES",
                "blocking": True,
                "detail": "quantity, filled_quantity, and average_fill_price must be numeric",
            })

        remaining_quantity = max(order_quantity - filled_quantity, 0.0)

        if token and (
            token_client_id != client_order_id
            or token_broker_id != broker_order_id
            or not bool(token.get("lifecycle_monitor_ready", False))
        ):
            issues.append({
                "code": "ACCEPTANCE_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "acceptance token does not match V139.08 result",
            })

        if snapshot:
            if snapshot_client_id != client_order_id:
                issues.append({
                    "code": "CLIENT_ORDER_ID_MISMATCH",
                    "blocking": True,
                    "detail": "lifecycle snapshot client_order_id mismatch",
                })
            if snapshot_broker_id != broker_order_id:
                issues.append({
                    "code": "BROKER_ORDER_ID_MISMATCH",
                    "blocking": True,
                    "detail": "lifecycle snapshot broker_order_id mismatch",
                })
            if order_status not in ACTIVE_STATUSES | TERMINAL_STATUSES:
                issues.append({
                    "code": "UNSUPPORTED_LIFECYCLE_STATUS",
                    "blocking": True,
                    "detail": f"unsupported lifecycle status: {order_status or '<empty>'}",
                })
            if order_quantity <= 0:
                issues.append({
                    "code": "INVALID_ORDER_QUANTITY",
                    "blocking": True,
                    "detail": "quantity must be greater than zero",
                })
            if filled_quantity < 0 or filled_quantity > order_quantity:
                issues.append({
                    "code": "FILLED_QUANTITY_OUT_OF_RANGE",
                    "blocking": True,
                    "detail": "filled_quantity must be between zero and quantity",
                })
            if order_status == "FILLED" and filled_quantity != order_quantity:
                issues.append({
                    "code": "FILLED_STATUS_QUANTITY_MISMATCH",
                    "blocking": True,
                    "detail": "FILLED requires filled_quantity equal to quantity",
                })
            if order_status == "PARTIALLY_FILLED" and not (0 < filled_quantity < order_quantity):
                issues.append({
                    "code": "PARTIAL_FILL_QUANTITY_MISMATCH",
                    "blocking": True,
                    "detail": "PARTIALLY_FILLED requires 0 < filled_quantity < quantity",
                })

        if previous and snapshot:
            previous_status = str(previous.get("status", "")).strip().upper()
            try:
                previous_filled = float(previous.get("filled_quantity", 0) or 0)
            except (TypeError, ValueError):
                previous_filled = 0.0
            if filled_quantity < previous_filled:
                issues.append({
                    "code": "FILLED_QUANTITY_REGRESSION",
                    "blocking": True,
                    "detail": "filled quantity cannot decrease",
                })
            if (
                previous_status in STATUS_RANK
                and order_status in STATUS_RANK
                and STATUS_RANK[order_status] < STATUS_RANK[previous_status]
            ):
                issues.append({
                    "code": "ORDER_STATUS_REGRESSION",
                    "blocking": True,
                    "detail": f"status cannot regress from {previous_status} to {order_status}",
                })
            if previous_status in TERMINAL_STATUSES and order_status != previous_status:
                issues.append({
                    "code": "TERMINAL_STATUS_CHANGED",
                    "blocking": True,
                    "detail": "terminal status must remain immutable",
                })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        acceptance_verified = bool(
            source_status == "PASS"
            and source_state == "ORDER_ACCEPTED"
            and lifecycle_ready
            and client_order_id
            and broker_order_id
            and token
            and token_client_id == client_order_id
            and token_broker_id == broker_order_id
            and not safe_mode
        )
        lifecycle_snapshot_verified = bool(
            snapshot
            and snapshot_client_id == client_order_id
            and snapshot_broker_id == broker_order_id
            and order_status in ACTIVE_STATUSES | TERMINAL_STATUSES
            and order_quantity > 0
            and 0 <= filled_quantity <= order_quantity
            and not safe_mode
        )
        active_order_present = bool(
            acceptance_verified
            and lifecycle_snapshot_verified
            and order_status in ACTIVE_STATUSES
            and not safe_mode
        )
        partial_fill_observed = bool(
            active_order_present
            and order_status == "PARTIALLY_FILLED"
            and 0 < filled_quantity < order_quantity
        )
        terminal_observed = bool(
            acceptance_verified
            and lifecycle_snapshot_verified
            and order_status in TERMINAL_STATUSES
            and not safe_mode
        )
        terminal_commit_ready = terminal_observed
        next_order_allowed = False

        if lifecycle_snapshot_verified:
            monitor_payload = {
                "client_order_id": client_order_id,
                "broker_order_id": broker_order_id,
                "status": order_status,
                "quantity": order_quantity,
                "filled_quantity": filled_quantity,
                "remaining_quantity": remaining_quantity,
                "average_fill_price": average_fill_price,
                "active_order_present": active_order_present,
                "terminal_observed": terminal_observed,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            _atomic_write_json(monitor_state_path, monitor_payload)
            _atomic_write_json(previous_lifecycle_snapshot_path, monitor_payload)

        if safe_mode:
            state = "LIFECYCLE_SAFE_MODE"
            status = "BLOCKED"
        elif terminal_observed:
            state = "TERMINAL_OBSERVED"
            status = "PASS"
        elif partial_fill_observed:
            state = "PARTIALLY_FILLED"
            status = "PASS"
        elif active_order_present:
            state = "ACTIVE_ORDER_MONITORING"
            status = "PASS"
        else:
            state = "WAIT_ACCEPTANCE"
            status = "PASS"

        report = ActiveOrderLifecycleMonitorReport(
            status=status,
            state=state,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            order_status=order_status,
            order_quantity=order_quantity,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            average_fill_price=average_fill_price,
            acceptance_verified=acceptance_verified,
            lifecycle_snapshot_verified=lifecycle_snapshot_verified,
            active_order_present=active_order_present,
            partial_fill_observed=partial_fill_observed,
            terminal_observed=terminal_observed,
            terminal_commit_ready=terminal_commit_ready,
            next_order_allowed=next_order_allowed,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_acceptance_result_path=str(acceptance_result_path.resolve()),
            source_acceptance_token_path=str(acceptance_token_path.resolve()),
            source_lifecycle_snapshot_path=str(lifecycle_snapshot_path.resolve()),
            previous_lifecycle_snapshot_path=str(previous_lifecycle_snapshot_path.resolve()),
            monitor_state_path=str(monitor_state_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
