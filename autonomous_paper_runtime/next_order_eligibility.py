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


def _eligibility_id(cycle_id: str, snapshot: dict[str, Any]) -> str:
    identity = {
        "cycle_id": cycle_id,
        "account_active": bool(snapshot.get("account_active", False)),
        "market_is_open": bool(snapshot.get("market_is_open", False)),
        "open_order_count": int(snapshot.get("open_order_count", 0) or 0),
        "position_count": int(snapshot.get("position_count", 0) or 0),
        "risk_approved": bool(snapshot.get("risk_approved", False)),
        "trading_blocked": bool(snapshot.get("trading_blocked", False)),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "eligibility-" + hashlib.sha256(encoded).hexdigest()[:24]


@dataclass(frozen=True)
class NextOrderEligibilityReport:
    status: str
    state: str
    cycle_id: str
    eligibility_id: str
    cycle_verified: bool
    eligibility_snapshot_verified: bool
    eligible: bool
    eligibility_token_written: bool
    safe_mode_engaged: bool
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]
    source_cycle_result_path: str
    source_eligibility_snapshot_path: str
    eligibility_token_path: str
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
            "cycle_id": self.cycle_id,
            "cycle_verified": self.cycle_verified,
            "eligibility_id": self.eligibility_id,
            "eligibility_snapshot_verified": self.eligibility_snapshot_verified,
            "eligibility_token_path": self.eligibility_token_path,
            "eligibility_token_written": self.eligibility_token_written,
            "eligible": self.eligible,
            "implementation_type": "NEXT_ORDER_ELIGIBILITY",
            "issue_count": self.issue_count,
            "issues": self.issues,
            "live_orders_submitted": self.live_orders_submitted,
            "network_requests_executed": self.network_requests_executed,
            "next_phase": (
                "V139_07_AUTONOMOUS_PAPER_ORDER_LAUNCH"
                if self.eligible and not self.safe_mode_engaged
                else "V139_06_WAIT_ELIGIBILITY"
            ),
            "result_path": self.result_path,
            "safe_mode_engaged": self.safe_mode_engaged,
            "source_cycle_result_path": self.source_cycle_result_path,
            "source_eligibility_snapshot_path": self.source_eligibility_snapshot_path,
            "stage": "V139.06",
            "state": self.state,
            "status": self.status,
            "validation_mode": "ACTUAL_SAVED_STATE_LOCAL_ONLY",
            "write_requests_executed": self.write_requests_executed,
        }


class NextOrderEligibility:
    def run(
        self,
        *,
        cycle_result_path: Path,
        eligibility_snapshot_path: Path,
        eligibility_token_path: Path,
        result_path: Path,
    ) -> NextOrderEligibilityReport:
        issues: list[dict[str, Any]] = []
        try:
            cycle = _load_json(cycle_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            cycle = {}
            issues.append({"code": "INVALID_CYCLE_RESULT", "blocking": True, "detail": str(exc)})

        if not cycle:
            issues.append({"code": "CYCLE_RESULT_NOT_FOUND", "blocking": True, "detail": str(cycle_result_path)})

        source_status = str(cycle.get("status", "")).upper()
        source_state = str(cycle.get("state", "")).upper()
        source_safe_mode = bool(cycle.get("safe_mode_engaged", False))
        source_ready = bool(cycle.get("next_order_eligibility_ready", False))
        cycle_id = str(cycle.get("cycle_id", "")).strip()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_CYCLE_SAFE_MODE",
                "blocking": True,
                "detail": "V139.05 cycle resume is blocked or in safe mode",
            })

        snapshot_required = source_ready or source_state == "CYCLE_RESUMED"
        snapshot: dict[str, Any] = {}
        if snapshot_required:
            try:
                snapshot = _load_json(eligibility_snapshot_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                issues.append({"code": "INVALID_ELIGIBILITY_SNAPSHOT", "blocking": True, "detail": str(exc)})
            if not snapshot:
                issues.append({
                    "code": "ELIGIBILITY_SNAPSHOT_NOT_FOUND",
                    "blocking": True,
                    "detail": str(eligibility_snapshot_path),
                })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        cycle_verified = bool(
            source_status == "PASS"
            and source_state == "CYCLE_RESUMED"
            and source_ready
            and cycle_id
            and not safe_mode
        )

        if snapshot:
            checks = [
                ("ACCOUNT_INACTIVE", bool(snapshot.get("account_active", False)), "account_active=true"),
                ("TRADING_BLOCKED", not bool(snapshot.get("trading_blocked", False)), "trading_blocked=false"),
                ("MARKET_CLOSED", bool(snapshot.get("market_is_open", False)), "market_is_open=true"),
                ("ACTIVE_ORDER_PRESENT", int(snapshot.get("open_order_count", 0) or 0) == 0, "open_order_count=0"),
                ("RISK_NOT_APPROVED", bool(snapshot.get("risk_approved", False)), "risk_approved=true"),
                ("SAFE_MODE_ACTIVE", not bool(snapshot.get("safe_mode_engaged", False)), "safe_mode_engaged=false"),
            ]
            for code, passed, expected in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": f"eligibility condition failed; expected {expected}",
                    })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        eligibility_snapshot_verified = bool(snapshot and not safe_mode)
        eligible = bool(cycle_verified and eligibility_snapshot_verified and not safe_mode)
        eligibility_id = _eligibility_id(cycle_id, snapshot) if eligible else ""
        eligibility_token_written = False

        if eligible:
            token = {
                "eligibility_id": eligibility_id,
                "cycle_id": cycle_id,
                "eligible": True,
                "account_active": True,
                "market_is_open": True,
                "open_order_count": 0,
                "risk_approved": True,
                "trading_blocked": False,
                "source_cycle_result_path": str(cycle_result_path.resolve()),
                "source_eligibility_snapshot_path": str(eligibility_snapshot_path.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if eligibility_token_path.exists():
                existing = _load_json(eligibility_token_path)
                if (
                    existing.get("eligibility_id") != eligibility_id
                    or existing.get("cycle_id") != cycle_id
                ):
                    issues.append({
                        "code": "ELIGIBILITY_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing eligibility token belongs to another cycle or snapshot",
                    })
                else:
                    eligibility_token_written = True
            else:
                _atomic_write_json(eligibility_token_path, token)
                eligibility_token_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        eligible = bool(eligible and eligibility_token_written and not safe_mode)

        if safe_mode:
            state = "ELIGIBILITY_SAFE_MODE"
            status = "BLOCKED"
        elif eligible:
            state = "NEXT_ORDER_ELIGIBLE"
            status = "PASS"
        else:
            state = "WAIT_CYCLE_RESUME"
            status = "PASS"

        report = NextOrderEligibilityReport(
            status=status,
            state=state,
            cycle_id=cycle_id,
            eligibility_id=eligibility_id,
            cycle_verified=cycle_verified,
            eligibility_snapshot_verified=eligibility_snapshot_verified,
            eligible=eligible,
            eligibility_token_written=eligibility_token_written,
            safe_mode_engaged=safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=issues,
            source_cycle_result_path=str(cycle_result_path.resolve()),
            source_eligibility_snapshot_path=str(eligibility_snapshot_path.resolve()),
            eligibility_token_path=str(eligibility_token_path.resolve()),
            result_path=str(result_path.resolve()),
        )
        payload = report.to_json_dict()
        payload["observed_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(result_path, payload)
        return report
