from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json


class FinalSubmissionApprovalState(str, Enum):
    WAIT_PREVIEW_PACKAGE = "WAIT_PREVIEW_PACKAGE"
    READY_FOR_HUMAN_APPROVAL = "READY_FOR_HUMAN_APPROVAL"
    APPROVED_FOR_SINGLE_PAPER_SUBMISSION = "APPROVED_FOR_SINGLE_PAPER_SUBMISSION"
    DUPLICATE_APPROVAL = "DUPLICATE_APPROVAL"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class ApprovalIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinalSubmissionApprovalToken:
    approval_id: str
    preview_id: str
    cycle_id: str
    client_order_id: str
    approved: bool
    approval_mode: str
    approved_at: str
    approval_phrase_hash: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinalSubmissionApprovalReport:
    state: FinalSubmissionApprovalState
    preview_verified: bool
    final_approval_required: bool
    human_approval_verified: bool
    approval_token_created: bool
    duplicate_approval: bool
    actual_submission_allowed: bool
    safe_mode_engaged: bool
    reason: str
    approval_id: str
    approval_token_path: str
    approval_audit_path: str
    issue_count: int
    blocking_issue_count: int
    issues: tuple[ApprovalIssue, ...]
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "preview_verified": self.preview_verified,
            "final_approval_required": self.final_approval_required,
            "human_approval_verified": self.human_approval_verified,
            "approval_token_created": self.approval_token_created,
            "duplicate_approval": self.duplicate_approval,
            "actual_submission_allowed": self.actual_submission_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
            "reason": self.reason,
            "approval_id": self.approval_id,
            "approval_token_path": self.approval_token_path,
            "approval_audit_path": self.approval_audit_path,
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "issues": [item.to_json_dict() for item in self.issues],
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class FinalPaperSubmissionApprovalGate:
    REQUIRED_PHRASE = "APPROVE EXACTLY ONE CONTROLLED ALPACA PAPER ORDER"

    def __init__(
        self,
        *,
        approval_token_path: Path,
        approval_audit_path: Path,
    ) -> None:
        self.approval_token_path = approval_token_path
        self.approval_audit_path = approval_audit_path

    def evaluate(
        self,
        *,
        preview_result: Mapping[str, Any],
        order_preview: Mapping[str, Any] | None,
        risk_snapshot: Mapping[str, Any] | None,
        exposure_snapshot: Mapping[str, Any] | None,
        approval_gate: Mapping[str, Any] | None,
        approval_phrase: str,
        approved_at: str,
        network_requests_executed: int = 0,
    ) -> FinalSubmissionApprovalReport:
        issues: list[ApprovalIssue] = []

        preview_state = _text(preview_result.get("state", "")).upper()
        preview_created = bool(preview_result.get("preview_created", False))
        payload_valid = bool(preview_result.get("payload_valid", False))
        risk_ok = bool(preview_result.get("risk_ok", False))
        exposure_ok = bool(preview_result.get("exposure_ok", False))
        upstream_safe_mode = bool(
            preview_result.get("safe_mode_engaged", False)
        )

        if upstream_safe_mode:
            return self._report(
                state=FinalSubmissionApprovalState.SAFE_MODE,
                reason="upstream_preview_safe_mode",
                preview_verified=False,
                approval_required=False,
                human_verified=False,
                token_created=False,
                duplicate=False,
                allowed=False,
                safe_mode=True,
                approval_id="",
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        if (
            preview_state == "WAIT_CYCLE_TOKEN"
            or not preview_created
            or not payload_valid
        ):
            return self._report(
                state=FinalSubmissionApprovalState.WAIT_PREVIEW_PACKAGE,
                reason="preview_package_not_ready",
                preview_verified=False,
                approval_required=False,
                human_verified=False,
                token_created=False,
                duplicate=False,
                allowed=False,
                safe_mode=False,
                approval_id="",
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        if preview_state not in {
            "READY_FOR_SUBMISSION_APPROVAL",
            "DUPLICATE_PREVIEW",
        }:
            issues.append(ApprovalIssue(
                code="UNEXPECTED_PREVIEW_STATE",
                expected="READY_FOR_SUBMISSION_APPROVAL or DUPLICATE_PREVIEW",
                actual=preview_state,
                blocking=True,
                detail="preview result is not eligible for final approval",
            ))

        if not order_preview:
            issues.append(ApprovalIssue(
                code="MISSING_ORDER_PREVIEW",
                expected="order preview present",
                actual="missing",
                blocking=True,
                detail="final approval requires order preview",
            ))
        if not risk_snapshot or not bool(risk_snapshot.get("approved", False)):
            issues.append(ApprovalIssue(
                code="RISK_SNAPSHOT_NOT_APPROVED",
                expected="approved=true",
                actual="false or missing",
                blocking=True,
                detail="risk snapshot must approve the order",
            ))
        if not exposure_snapshot or not bool(
            exposure_snapshot.get("approved", False)
        ):
            issues.append(ApprovalIssue(
                code="EXPOSURE_SNAPSHOT_NOT_APPROVED",
                expected="approved=true",
                actual="false or missing",
                blocking=True,
                detail="exposure snapshot must approve the order",
            ))
        if not approval_gate:
            issues.append(ApprovalIssue(
                code="MISSING_APPROVAL_GATE",
                expected="approval gate present",
                actual="missing",
                blocking=True,
                detail="preview approval gate file is required",
            ))
        elif bool(approval_gate.get("actual_submission_allowed", True)):
            issues.append(ApprovalIssue(
                code="PREVIEW_GATE_ALREADY_ALLOWS_SUBMISSION",
                expected="actual_submission_allowed=false",
                actual="true",
                blocking=True,
                detail="preview stage must never pre-authorize broker submission",
            ))

        preview_id = _text(
            (order_preview or {}).get(
                "preview_id",
                preview_result.get("preview_id", ""),
            )
        )
        cycle_id = _text((order_preview or {}).get("cycle_id", ""))
        client_order_id = _text(
            (order_preview or {}).get("client_order_id", "")
        )

        if not preview_id:
            issues.append(ApprovalIssue(
                code="MISSING_PREVIEW_ID",
                expected="non-empty preview_id",
                actual="",
                blocking=True,
                detail="approval requires stable preview identity",
            ))
        if not cycle_id:
            issues.append(ApprovalIssue(
                code="MISSING_CYCLE_ID",
                expected="non-empty cycle_id",
                actual="",
                blocking=True,
                detail="approval requires stable cycle identity",
            ))
        if not client_order_id:
            issues.append(ApprovalIssue(
                code="MISSING_CLIENT_ORDER_ID",
                expected="non-empty client_order_id",
                actual="",
                blocking=True,
                detail="approval requires deterministic broker order identity",
            ))

        blocking = sum(1 for item in issues if item.blocking)
        if blocking:
            return self._report(
                state=FinalSubmissionApprovalState.SAFE_MODE,
                reason="approval_package_validation_failed",
                preview_verified=False,
                approval_required=True,
                human_verified=False,
                token_created=False,
                duplicate=False,
                allowed=False,
                safe_mode=True,
                approval_id="",
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        preview_verified = (
            payload_valid and risk_ok and exposure_ok
        )
        normalized_phrase = _text(approval_phrase)
        phrase_matches = normalized_phrase == self.REQUIRED_PHRASE

        if not phrase_matches:
            return self._report(
                state=FinalSubmissionApprovalState.READY_FOR_HUMAN_APPROVAL,
                reason="awaiting_exact_human_approval_phrase",
                preview_verified=preview_verified,
                approval_required=True,
                human_verified=False,
                token_created=False,
                duplicate=False,
                allowed=False,
                safe_mode=False,
                approval_id="",
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        approval_id = self._approval_id(
            preview_id=preview_id,
            cycle_id=cycle_id,
            client_order_id=client_order_id,
        )

        if self.approval_token_path.exists():
            existing = json.loads(
                self.approval_token_path.read_text(encoding="utf-8")
            )
            if existing.get("approval_id") == approval_id:
                return self._report(
                    state=FinalSubmissionApprovalState.DUPLICATE_APPROVAL,
                    reason="approval_token_already_exists",
                    preview_verified=True,
                    approval_required=True,
                    human_verified=True,
                    token_created=False,
                    duplicate=True,
                    allowed=True,
                    safe_mode=False,
                    approval_id=approval_id,
                    issues=(),
                    network_requests_executed=network_requests_executed,
                )

            issues.append(ApprovalIssue(
                code="DIFFERENT_APPROVAL_TOKEN_EXISTS",
                expected="no token or matching approval_id",
                actual=str(existing.get("approval_id", "")),
                blocking=True,
                detail="another final approval token already exists",
            ))
            return self._report(
                state=FinalSubmissionApprovalState.SAFE_MODE,
                reason="different_approval_token_exists",
                preview_verified=True,
                approval_required=True,
                human_verified=False,
                token_created=False,
                duplicate=False,
                allowed=False,
                safe_mode=True,
                approval_id="",
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        phrase_hash = hashlib.sha256(
            normalized_phrase.encode("utf-8")
        ).hexdigest()
        token = FinalSubmissionApprovalToken(
            approval_id=approval_id,
            preview_id=preview_id,
            cycle_id=cycle_id,
            client_order_id=client_order_id,
            approved=True,
            approval_mode="EXACT_HUMAN_PHRASE",
            approved_at=approved_at,
            approval_phrase_hash=phrase_hash,
        )
        audit = {
            "event_type": "FINAL_PAPER_SUBMISSION_APPROVED",
            **token.to_json_dict(),
            "actual_submission_allowed": True,
            "broker_write_performed": False,
            "single_order_limit": 1,
        }

        for path, payload in (
            (self.approval_token_path, token.to_json_dict()),
            (self.approval_audit_path, audit),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        return self._report(
            state=FinalSubmissionApprovalState.APPROVED_FOR_SINGLE_PAPER_SUBMISSION,
            reason="exact_human_approval_verified",
            preview_verified=True,
            approval_required=True,
            human_verified=True,
            token_created=True,
            duplicate=False,
            allowed=True,
            safe_mode=False,
            approval_id=approval_id,
            issues=(),
            network_requests_executed=network_requests_executed,
        )

    def _report(
        self,
        *,
        state: FinalSubmissionApprovalState,
        reason: str,
        preview_verified: bool,
        approval_required: bool,
        human_verified: bool,
        token_created: bool,
        duplicate: bool,
        allowed: bool,
        safe_mode: bool,
        approval_id: str,
        issues: tuple[ApprovalIssue, ...],
        network_requests_executed: int,
    ) -> FinalSubmissionApprovalReport:
        return FinalSubmissionApprovalReport(
            state=state,
            preview_verified=preview_verified,
            final_approval_required=approval_required,
            human_approval_verified=human_verified,
            approval_token_created=token_created,
            duplicate_approval=duplicate,
            actual_submission_allowed=allowed,
            safe_mode_engaged=safe_mode,
            reason=reason,
            approval_id=approval_id,
            approval_token_path=str(self.approval_token_path),
            approval_audit_path=str(self.approval_audit_path),
            issue_count=len(issues),
            blocking_issue_count=sum(
                1 for item in issues if item.blocking
            ),
            issues=issues,
            network_requests_executed=network_requests_executed,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )

    @staticmethod
    def _approval_id(
        *,
        preview_id: str,
        cycle_id: str,
        client_order_id: str,
    ) -> str:
        raw = "|".join([preview_id, cycle_id, client_order_id])
        return "APPROVAL-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip()
