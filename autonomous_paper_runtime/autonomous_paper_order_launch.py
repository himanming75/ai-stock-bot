from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVAL_PHRASE = "APPROVE V139.07 PAPER ORDER PREPARATION"
ALLOWED_SIDES = {"BUY", "SELL"}
ALLOWED_ORDER_TYPES = {"MARKET", "LIMIT"}
ALLOWED_TIME_IN_FORCE = {"DAY", "GTC"}


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


def _client_order_id(cycle_id: str, eligibility_id: str, candidate: dict[str, Any]) -> str:
    identity = {
        "cycle_id": cycle_id,
        "eligibility_id": eligibility_id,
        "symbol": str(candidate.get("symbol", "")).upper(),
        "side": str(candidate.get("side", "")).upper(),
        "quantity": str(candidate.get("quantity", "")),
        "order_type": str(candidate.get("order_type", "")).upper(),
        "limit_price": str(candidate.get("limit_price", "")),
        "time_in_force": str(candidate.get("time_in_force", "")).upper(),
        "signal_id": str(candidate.get("signal_id", "")),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "v13907-" + hashlib.sha256(encoded).hexdigest()[:24]


@dataclass(frozen=True)
class AutonomousPaperOrderLaunchReport:
    status: str
    state: str
    cycle_id: str
    eligibility_id: str
    client_order_id: str
    eligibility_verified: bool
    candidate_verified: bool
    preview_ready: bool
    approval_required: bool
    approval_verified: bool
    submission_enabled: bool
    submission_prepared: bool
    duplicate_preview: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_eligibility_result_path: str
    source_eligibility_token_path: str
    source_order_candidate_path: str
    preview_path: str
    preparation_token_path: str
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
            "approval_required": self.approval_required,
            "approval_verified": self.approval_verified,
            "blocking_issue_count": self.blocking_issue_count,
            "candidate_verified": self.candidate_verified,
            "client_order_id": self.client_order_id,
            "cycle_id": self.cycle_id,
            "duplicate_preview": self.duplicate_preview,
            "eligibility_id": self.eligibility_id,
            "eligibility_verified": self.eligibility_verified,
            "implementation_type": "AUTONOMOUS_PAPER_ORDER_LAUNCH_PREPARATION",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_phase": (
                "V139_08_SUBMITTED_ORDER_ACCEPTANCE_VERIFICATION"
                if self.submission_prepared and not self.safe_mode_engaged
                else "V139_07_WAIT_ORDER_LAUNCH_GATE"
            ),
            "preparation_token_path": self.preparation_token_path,
            "preview_path": self.preview_path,
            "preview_ready": self.preview_ready,
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_eligibility_result_path": self.source_eligibility_result_path,
            "source_eligibility_token_path": self.source_eligibility_token_path,
            "source_order_candidate_path": self.source_order_candidate_path,
            "stage": "V139.07",
            "state": self.state,
            "status": self.status,
            "submission_enabled": self.submission_enabled,
            "submission_prepared": self.submission_prepared,
            "validation_mode": "LOCAL_PREVIEW_APPROVAL_GATE_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class AutonomousPaperOrderLaunch:
    def run(
        self,
        *,
        eligibility_result_path: Path,
        eligibility_token_path: Path,
        order_candidate_path: Path,
        preview_path: Path,
        preparation_token_path: Path,
        result_path: Path,
        approval_phrase: str = "",
        enable_submission: bool = False,
    ) -> AutonomousPaperOrderLaunchReport:
        issues: list[dict[str, Any]] = []

        try:
            eligibility_result = _load_json(eligibility_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            eligibility_result = {}
            issues.append({"code": "INVALID_ELIGIBILITY_RESULT", "blocking": True, "detail": str(exc)})

        if not eligibility_result:
            issues.append({
                "code": "ELIGIBILITY_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(eligibility_result_path),
            })

        source_status = str(eligibility_result.get("status", "")).upper()
        source_state = str(eligibility_result.get("state", "")).upper()
        source_safe_mode = bool(eligibility_result.get("safe_mode_engaged", False))
        source_eligible = bool(eligibility_result.get("eligible", False))
        cycle_id = str(eligibility_result.get("cycle_id", "")).strip()
        eligibility_id = str(eligibility_result.get("eligibility_id", "")).strip()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_ELIGIBILITY_SAFE_MODE",
                "blocking": True,
                "detail": "V139.06 eligibility is blocked or in safe mode",
            })

        gate_required = source_eligible or source_state == "NEXT_ORDER_ELIGIBLE"
        eligibility_token: dict[str, Any] = {}
        candidate: dict[str, Any] = {}

        if gate_required:
            for code, path in (
                ("ELIGIBILITY_TOKEN", eligibility_token_path),
                ("ORDER_CANDIDATE", order_candidate_path),
            ):
                try:
                    loaded = _load_json(path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    loaded = {}
                    issues.append({"code": f"INVALID_{code}", "blocking": True, "detail": str(exc)})
                if code == "ELIGIBILITY_TOKEN":
                    eligibility_token = loaded
                else:
                    candidate = loaded

            if not eligibility_token:
                issues.append({
                    "code": "ELIGIBILITY_TOKEN_NOT_FOUND",
                    "blocking": True,
                    "detail": str(eligibility_token_path),
                })
            if not candidate:
                issues.append({
                    "code": "ORDER_CANDIDATE_NOT_FOUND",
                    "blocking": True,
                    "detail": str(order_candidate_path),
                })

        token_cycle_id = str(eligibility_token.get("cycle_id", "")).strip()
        token_eligibility_id = str(eligibility_token.get("eligibility_id", "")).strip()
        if eligibility_token and (
            token_cycle_id != cycle_id
            or token_eligibility_id != eligibility_id
            or not bool(eligibility_token.get("eligible", False))
        ):
            issues.append({
                "code": "ELIGIBILITY_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "eligibility result and token do not match",
            })

        symbol = str(candidate.get("symbol", "")).strip().upper()
        side = str(candidate.get("side", "")).strip().upper()
        order_type = str(candidate.get("order_type", "")).strip().upper()
        time_in_force = str(candidate.get("time_in_force", "DAY")).strip().upper()
        quantity_raw = candidate.get("quantity", 0)
        try:
            quantity = float(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0.0

        if candidate:
            checks = [
                ("SYMBOL_MISSING", bool(symbol), "non-empty symbol"),
                ("INVALID_SIDE", side in ALLOWED_SIDES, "BUY or SELL"),
                ("INVALID_QUANTITY", quantity > 0, "quantity > 0"),
                ("INVALID_ORDER_TYPE", order_type in ALLOWED_ORDER_TYPES, "MARKET or LIMIT"),
                ("INVALID_TIME_IN_FORCE", time_in_force in ALLOWED_TIME_IN_FORCE, "DAY or GTC"),
                ("RISK_NOT_APPROVED", bool(candidate.get("risk_approved", False)), "risk_approved=true"),
            ]
            if order_type == "LIMIT":
                try:
                    limit_price = float(candidate.get("limit_price", 0))
                except (TypeError, ValueError):
                    limit_price = 0.0
                checks.append(("INVALID_LIMIT_PRICE", limit_price > 0, "limit_price > 0"))
            for code, passed, expected in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": f"order candidate failed validation; expected {expected}",
                    })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        eligibility_verified = bool(
            source_status == "PASS"
            and source_state == "NEXT_ORDER_ELIGIBLE"
            and source_eligible
            and cycle_id
            and eligibility_id
            and eligibility_token
            and token_cycle_id == cycle_id
            and token_eligibility_id == eligibility_id
            and not safe_mode
        )
        candidate_verified = bool(candidate and not safe_mode)
        client_order_id = (
            _client_order_id(cycle_id, eligibility_id, candidate)
            if eligibility_verified and candidate_verified
            else ""
        )
        preview_ready = bool(eligibility_verified and candidate_verified and client_order_id)
        duplicate_preview = False

        if preview_ready:
            preview_payload = {
                "client_order_id": client_order_id,
                "cycle_id": cycle_id,
                "eligibility_id": eligibility_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity_raw,
                "order_type": order_type,
                "limit_price": candidate.get("limit_price"),
                "time_in_force": time_in_force,
                "signal_id": str(candidate.get("signal_id", "")),
                "strategy": str(candidate.get("strategy", "")),
                "risk_approved": True,
                "submission_enabled": False,
                "broker_network_allowed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if preview_path.exists():
                existing = _load_json(preview_path)
                if existing.get("client_order_id") == client_order_id:
                    duplicate_preview = True
                else:
                    issues.append({
                        "code": "ORDER_PREVIEW_CONFLICT",
                        "blocking": True,
                        "detail": "existing preview belongs to another order identity",
                    })
            else:
                _atomic_write_json(preview_path, preview_payload)

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        preview_ready = bool(preview_ready and not safe_mode)
        approval_verified = bool(approval_phrase == APPROVAL_PHRASE)
        submission_enabled = bool(enable_submission)

        # V139.07 intentionally stops at a local preparation token.
        submission_prepared = bool(
            preview_ready
            and approval_verified
            and submission_enabled
            and not safe_mode
        )

        if submission_prepared:
            preparation_payload = {
                "client_order_id": client_order_id,
                "cycle_id": cycle_id,
                "eligibility_id": eligibility_id,
                "submission_prepared": True,
                "actual_submission_allowed": False,
                "broker_network_allowed": False,
                "approval_phrase_verified": True,
                "source_preview_path": str(preview_path.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if preparation_token_path.exists():
                existing = _load_json(preparation_token_path)
                if existing.get("client_order_id") != client_order_id:
                    issues.append({
                        "code": "PREPARATION_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing preparation token belongs to another order",
                    })
            else:
                _atomic_write_json(preparation_token_path, preparation_payload)

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        submission_prepared = bool(submission_prepared and not safe_mode)

        if safe_mode:
            state = "ORDER_LAUNCH_SAFE_MODE"
            status = "BLOCKED"
        elif submission_prepared:
            state = "ORDER_SUBMISSION_PREPARED"
            status = "PASS"
        elif preview_ready and not approval_verified:
            state = "WAIT_APPROVAL"
            status = "PASS"
        elif preview_ready and approval_verified and not submission_enabled:
            state = "SUBMISSION_DISABLED"
            status = "PASS"
        else:
            state = "WAIT_ELIGIBILITY"
            status = "PASS"

        report = AutonomousPaperOrderLaunchReport(
            status=status,
            state=state,
            cycle_id=cycle_id,
            eligibility_id=eligibility_id,
            client_order_id=client_order_id,
            eligibility_verified=eligibility_verified,
            candidate_verified=candidate_verified,
            preview_ready=preview_ready,
            approval_required=True,
            approval_verified=approval_verified,
            submission_enabled=submission_enabled,
            submission_prepared=submission_prepared,
            duplicate_preview=duplicate_preview,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_eligibility_result_path=str(eligibility_result_path.resolve()),
            source_eligibility_token_path=str(eligibility_token_path.resolve()),
            source_order_candidate_path=str(order_candidate_path.resolve()),
            preview_path=str(preview_path.resolve()),
            preparation_token_path=str(preparation_token_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
