from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACCEPTED_STATUSES = {"NEW", "ACCEPTED", "PENDING_NEW"}
REJECTED_STATUSES = {"REJECTED"}


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
class SubmittedOrderAcceptanceVerificationReport:
    status: str
    state: str
    client_order_id: str
    broker_order_id: str
    broker_order_status: str
    preparation_verified: bool
    submission_snapshot_verified: bool
    order_accepted: bool
    order_rejected: bool
    lifecycle_monitor_ready: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_launch_result_path: str
    source_preparation_token_path: str
    source_preview_path: str
    source_submission_snapshot_path: str
    acceptance_token_path: str
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
            "broker_order_id": self.broker_order_id,
            "broker_order_status": self.broker_order_status,
            "client_order_id": self.client_order_id,
            "implementation_type": "SUBMITTED_ORDER_ACCEPTANCE_VERIFICATION",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "lifecycle_monitor_ready": self.lifecycle_monitor_ready,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_phase": (
                "V139_09_ACTIVE_ORDER_LIFECYCLE_MONITOR"
                if self.lifecycle_monitor_ready and not self.safe_mode_engaged
                else "V139_08_WAIT_SUBMISSION_RESULT"
            ),
            "order_accepted": self.order_accepted,
            "order_rejected": self.order_rejected,
            "preparation_verified": self.preparation_verified,
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_launch_result_path": self.source_launch_result_path,
            "source_preparation_token_path": self.source_preparation_token_path,
            "source_preview_path": self.source_preview_path,
            "source_submission_snapshot_path": self.source_submission_snapshot_path,
            "stage": "V139.08",
            "state": self.state,
            "status": self.status,
            "submission_snapshot_verified": self.submission_snapshot_verified,
            "acceptance_token_path": self.acceptance_token_path,
            "validation_mode": "LOCAL_SUBMISSION_RESULT_VERIFICATION_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class SubmittedOrderAcceptanceVerification:
    def run(
        self,
        *,
        launch_result_path: Path,
        preparation_token_path: Path,
        preview_path: Path,
        submission_snapshot_path: Path,
        acceptance_token_path: Path,
        result_path: Path,
    ) -> SubmittedOrderAcceptanceVerificationReport:
        issues: list[dict[str, Any]] = []

        try:
            launch = _load_json(launch_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            launch = {}
            issues.append({"code": "INVALID_LAUNCH_RESULT", "blocking": True, "detail": str(exc)})

        if not launch:
            issues.append({
                "code": "LAUNCH_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(launch_result_path),
            })

        source_status = str(launch.get("status", "")).upper()
        source_state = str(launch.get("state", "")).upper()
        source_safe_mode = bool(launch.get("safe_mode_engaged", False))
        submission_prepared = bool(launch.get("submission_prepared", False))
        client_order_id = str(launch.get("client_order_id", "")).strip()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_LAUNCH_SAFE_MODE",
                "blocking": True,
                "detail": "V139.07 launch preparation is blocked or in safe mode",
            })

        verification_required = submission_prepared or source_state == "ORDER_SUBMISSION_PREPARED"
        preparation: dict[str, Any] = {}
        preview: dict[str, Any] = {}
        snapshot: dict[str, Any] = {}

        if verification_required:
            for code, path in (
                ("PREPARATION_TOKEN", preparation_token_path),
                ("ORDER_PREVIEW", preview_path),
                ("SUBMISSION_SNAPSHOT", submission_snapshot_path),
            ):
                try:
                    loaded = _load_json(path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    loaded = {}
                    issues.append({"code": f"INVALID_{code}", "blocking": True, "detail": str(exc)})
                if code == "PREPARATION_TOKEN":
                    preparation = loaded
                elif code == "ORDER_PREVIEW":
                    preview = loaded
                else:
                    snapshot = loaded

            if not preparation:
                issues.append({
                    "code": "PREPARATION_TOKEN_NOT_FOUND",
                    "blocking": True,
                    "detail": str(preparation_token_path),
                })
            if not preview:
                issues.append({
                    "code": "ORDER_PREVIEW_NOT_FOUND",
                    "blocking": True,
                    "detail": str(preview_path),
                })
            if not snapshot:
                issues.append({
                    "code": "SUBMISSION_SNAPSHOT_NOT_FOUND",
                    "blocking": True,
                    "detail": str(submission_snapshot_path),
                })

        prep_client_order_id = str(preparation.get("client_order_id", "")).strip()
        preview_client_order_id = str(preview.get("client_order_id", "")).strip()
        snapshot_client_order_id = str(snapshot.get("client_order_id", "")).strip()
        broker_order_id = str(snapshot.get("broker_order_id", "")).strip()
        broker_status = str(snapshot.get("status", "")).strip().upper()

        if preparation and (
            prep_client_order_id != client_order_id
            or not bool(preparation.get("submission_prepared", False))
            or bool(preparation.get("actual_submission_allowed", True))
            or bool(preparation.get("broker_network_allowed", True))
        ):
            issues.append({
                "code": "PREPARATION_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "preparation token does not match V139.07 local-only contract",
            })

        if preview and preview_client_order_id != client_order_id:
            issues.append({
                "code": "ORDER_PREVIEW_MISMATCH",
                "blocking": True,
                "detail": "preview client_order_id does not match launch result",
            })

        if snapshot:
            if snapshot_client_order_id != client_order_id:
                issues.append({
                    "code": "CLIENT_ORDER_ID_MISMATCH",
                    "blocking": True,
                    "detail": "submission snapshot client_order_id does not match preparation",
                })
            if not broker_order_id:
                issues.append({
                    "code": "BROKER_ORDER_ID_MISSING",
                    "blocking": True,
                    "detail": "submission snapshot must contain broker_order_id",
                })
            if broker_status not in ACCEPTED_STATUSES | REJECTED_STATUSES:
                issues.append({
                    "code": "UNSUPPORTED_BROKER_STATUS",
                    "blocking": True,
                    "detail": f"unsupported submission status: {broker_status or '<empty>'}",
                })
            if preview:
                comparisons = (
                    ("SYMBOL_MISMATCH", "symbol"),
                    ("SIDE_MISMATCH", "side"),
                    ("QUANTITY_MISMATCH", "quantity"),
                    ("ORDER_TYPE_MISMATCH", "order_type"),
                    ("TIME_IN_FORCE_MISMATCH", "time_in_force"),
                )
                for code, field in comparisons:
                    left = str(snapshot.get(field, "")).upper()
                    right = str(preview.get(field, "")).upper()
                    if left != right:
                        issues.append({
                            "code": code,
                            "blocking": True,
                            "detail": f"submission snapshot {field} does not match preview",
                        })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        preparation_verified = bool(
            source_status == "PASS"
            and source_state == "ORDER_SUBMISSION_PREPARED"
            and submission_prepared
            and client_order_id
            and preparation
            and preview
            and prep_client_order_id == client_order_id
            and preview_client_order_id == client_order_id
            and not safe_mode
        )
        submission_snapshot_verified = bool(
            snapshot
            and snapshot_client_order_id == client_order_id
            and broker_order_id
            and broker_status in ACCEPTED_STATUSES | REJECTED_STATUSES
            and not safe_mode
        )
        order_accepted = bool(
            preparation_verified
            and submission_snapshot_verified
            and broker_status in ACCEPTED_STATUSES
            and not safe_mode
        )
        order_rejected = bool(
            preparation_verified
            and submission_snapshot_verified
            and broker_status in REJECTED_STATUSES
            and not safe_mode
        )
        lifecycle_monitor_ready = order_accepted

        if order_accepted:
            token = {
                "client_order_id": client_order_id,
                "broker_order_id": broker_order_id,
                "broker_order_status": broker_status,
                "lifecycle_monitor_ready": True,
                "source_submission_snapshot_path": str(submission_snapshot_path.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if acceptance_token_path.exists():
                existing = _load_json(acceptance_token_path)
                if (
                    existing.get("client_order_id") != client_order_id
                    or existing.get("broker_order_id") != broker_order_id
                ):
                    issues.append({
                        "code": "ACCEPTANCE_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing acceptance token belongs to another order",
                    })
            else:
                _atomic_write_json(acceptance_token_path, token)

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        lifecycle_monitor_ready = bool(lifecycle_monitor_ready and not safe_mode)

        if safe_mode:
            state = "ACCEPTANCE_SAFE_MODE"
            status = "BLOCKED"
        elif order_accepted:
            state = "ORDER_ACCEPTED"
            status = "PASS"
        elif order_rejected:
            state = "ORDER_REJECTED"
            status = "PASS"
        else:
            state = "WAIT_SUBMISSION_RESULT"
            status = "PASS"

        report = SubmittedOrderAcceptanceVerificationReport(
            status=status,
            state=state,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            broker_order_status=broker_status,
            preparation_verified=preparation_verified,
            submission_snapshot_verified=submission_snapshot_verified,
            order_accepted=order_accepted,
            order_rejected=order_rejected,
            lifecycle_monitor_ready=lifecycle_monitor_ready,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_launch_result_path=str(launch_result_path.resolve()),
            source_preparation_token_path=str(preparation_token_path.resolve()),
            source_preview_path=str(preview_path.resolve()),
            source_submission_snapshot_path=str(submission_snapshot_path.resolve()),
            acceptance_token_path=str(acceptance_token_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
