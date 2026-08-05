from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .policies import ControlPolicyEngine, KillSwitchState
from .requests import (
    ApprovalReviewer,
    ChangeRequestFactory,
    ControlPlaneLedger,
    IdempotencyRegistry,
)
from .security import (
    ConfirmationChallenge,
    OperatorIdentity,
    SensitiveValueRedactor,
    SessionManager,
)
from .status import OperationalStatusAggregator


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/secure_control_plane_operator_console/actual"
    actual.mkdir(parents=True, exist_ok=True)

    operator = OperatorIdentity("operator-james", "OPERATOR")
    approver = OperatorIdentity("approver-safety", "APPROVER")
    viewer = OperatorIdentity("viewer-audit", "VIEWER")

    sessions = [
        SessionManager().issue(identity=operator),
        SessionManager().issue(identity=approver),
        SessionManager().issue(identity=viewer),
    ]

    registry = IdempotencyRegistry()
    factory = ChangeRequestFactory()
    policy = ControlPolicyEngine()
    ledger_path = actual / "control_plane_ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()
    ledger = ControlPlaneLedger(ledger_path)

    definitions = [
        (
            "CONFIGURATION_CHANGE",
            "offline runtime configuration",
            {
                "worker_count": 4,
                "broker_mode": "paper",
                "write_enabled": False,
                "automatic_order_submission_enabled": False,
            },
            "Prepare a reviewed worker-count configuration change.",
        ),
        (
            "STRATEGY_STATE_CHANGE",
            "momentum_v3",
            {"target_state": "ENABLE_PREVIEW"},
            "Preview enabling momentum strategy.",
        ),
        (
            "STRATEGY_WEIGHT_CHANGE",
            "ensemble momentum weight",
            {"weight": 0.35},
            "Preview a bounded strategy weight change.",
        ),
        (
            "RUNTIME_STATE_CHANGE",
            "paper runtime",
            {"target_state": "START_PREVIEW"},
            "Preview runtime startup without starting it.",
        ),
        (
            "WORKER_SCALE_CHANGE",
            "scanner worker pool",
            {"worker_count": 4},
            "Preview worker pool scaling.",
        ),
        (
            "SCHEDULER_CHANGE",
            "scanner interval",
            {"interval_seconds": 60},
            "Preview scheduler interval change.",
        ),
        (
            "KILL_SWITCH_CHANGE",
            "global trading kill switch",
            {"target_state": "ACTIVATE_PREVIEW"},
            "Preview global kill switch activation.",
        ),
        (
            "EMERGENCY_STOP_REQUEST",
            "all paper runtime processes",
            {"target_state": "ACTIVATE_PREVIEW"},
            "Preview emergency runtime stop.",
        ),
    ]

    requests = []
    policy_results = []
    reviews = []
    challenges = []

    for index, (request_type, subject, value, reason) in enumerate(
        definitions, start=1
    ):
        key = f"offline-control-{index}"
        if not registry.register(key):
            raise RuntimeError("UNEXPECTED_DUPLICATE_REQUEST")

        request = factory.create(
            identity=operator,
            request_type=request_type,
            subject=subject,
            proposed_value=value,
            reason=reason,
            idempotency_key=key,
        )
        policy_result = policy.evaluate(request)
        request["policy_pass"] = policy_result["policy_pass"]

        review = ApprovalReviewer().review(
            identity=approver,
            request=request,
            decision="APPROVE_PREVIEW",
            comment="Offline preview accepted; no change may be applied.",
        )
        challenge = ConfirmationChallenge().create(
            request_id=request["request_id"],
            operation=request_type,
        )

        requests.append(request)
        policy_results.append(policy_result)
        reviews.append(review)
        challenges.append(challenge)
        ledger.append({"record_type": "REQUEST", **request})
        ledger.append({"record_type": "POLICY", **policy_result})
        ledger.append({"record_type": "REVIEW", **review})
        ledger.append({"record_type": "CHALLENGE", **challenge})

    duplicate_suppressed = registry.register(
        "offline-control-1"
    ) is False

    self_approval_rejected = False
    try:
        ApprovalReviewer().review(
            identity=operator,
            request=requests[0],
            decision="APPROVE_PREVIEW",
            comment="This should fail.",
        )
    except PermissionError:
        self_approval_rejected = True

    redacted = SensitiveValueRedactor().redact({
        "api_key": "raw-key-value",
        "nested": {
            "secret_key": "raw-secret-value",
            "safe_value": "visible",
        },
    })

    kill_switch = KillSwitchState().preview("ACTIVATE_PREVIEW")
    operational_status = OperationalStatusAggregator().collect(root)

    checks = {
        "three_sessions_created": len(sessions) == 3,
        "tokens_not_stored": all(
            session["raw_token_stored"] is False
            for session in sessions
        ),
        "eight_requests_created": len(requests) == 8,
        "all_requests_pending_preview": all(
            request["state"] == "PENDING_PREVIEW"
            for request in requests
        ),
        "all_policies_pass": all(
            result["policy_pass"] is True
            for result in policy_results
        ),
        "eight_preview_reviews": len(reviews) == 8,
        "all_reviews_not_applied": all(
            review["actual_change_applied"] is False
            for review in reviews
        ),
        "eight_confirmation_challenges": len(challenges) == 8,
        "self_approval_rejected": self_approval_rejected,
        "duplicate_request_suppressed": duplicate_suppressed,
        "sensitive_values_redacted": (
            redacted["api_key"] == "[REDACTED]"
            and redacted["nested"]["secret_key"] == "[REDACTED]"
            and redacted["nested"]["safe_value"] == "visible"
        ),
        "kill_switch_preview_only": (
            kill_switch["actual_kill_switch_changed"] is False
        ),
        "p2_pass": operational_status["p2_status"] == "PASS",
        "broker_write_off": (
            operational_status["broker_write_enabled"] is False
        ),
        "automatic_orders_off": (
            operational_status[
                "automatic_order_submission_enabled"
            ] is False
        ),
        "live_trading_off": (
            operational_status["live_trading_enabled"] is False
        ),
    }

    result = {
        "stage": "SECURE_CONTROL_PLANE_OPERATOR_CONSOLE_MEGA_BUNDLE",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "role_permission_model": "READY",
        "session_management": "READY_PREVIEW_ONLY",
        "two_step_confirmation": "READY_PREVIEW_ONLY",
        "configuration_change_request": "READY_PREVIEW_ONLY",
        "strategy_state_control": "READY_PREVIEW_ONLY",
        "strategy_weight_control": "READY_PREVIEW_ONLY",
        "runtime_state_control": "READY_PREVIEW_ONLY",
        "worker_scale_control": "READY_PREVIEW_ONLY",
        "scheduler_control": "READY_PREVIEW_ONLY",
        "kill_switch_control": "READY_PREVIEW_ONLY",
        "emergency_stop_control": "READY_PREVIEW_ONLY",
        "approval_inbox": "READY_PREVIEW_ONLY",
        "audit_ledger": "READY",
        "sensitive_value_redaction": "READY",
        "idempotency_protection": "READY",
        "operator_console": "READY_READ_ONLY",
        "operational_status_aggregation": "READY",
        "operator_sessions": sessions,
        "change_requests": requests,
        "policy_results": policy_results,
        "approval_reviews": reviews,
        "confirmation_challenges": challenges,
        "kill_switch_preview": kill_switch,
        "redaction_fixture": redacted,
        "operational_status": operational_status,
        "actual_configuration_applied": False,
        "actual_strategy_change_performed": False,
        "actual_runtime_started": False,
        "actual_runtime_stopped": False,
        "actual_worker_scale_changed": False,
        "actual_scheduler_changed": False,
        "actual_kill_switch_changed": False,
        "actual_emergency_stop_activated": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_offline_development": (
            "RUNTIME_SERVICE_PACKAGING_AND_INSTALLATION_PREVIEW"
        ),
        "next_market_dependent_action": (
            "P3_ACTUAL_PAPER_ORDER_VALIDATION"
        ),
    }
    (actual / "secure_control_plane_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
