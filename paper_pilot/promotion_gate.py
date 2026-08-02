from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class PaperPilotPromotionGate:
    def run(
        self,
        *,
        policy_path: Path,
        validation_summary_path: Path,
        validation_gate_path: Path,
        analytics_result_path: Path,
        certificate_result_path: Path,
        risk_result_path: Path,
        promotion_manifest_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        loaded: dict[str, dict[str, Any]] = {}

        for name, path in (
            ("PROMOTION_POLICY", policy_path),
            ("VALIDATION_SUMMARY", validation_summary_path),
            ("VALIDATION_GATE", validation_gate_path),
            ("ANALYTICS_RESULT", analytics_result_path),
            ("CERTIFICATE_RESULT", certificate_result_path),
            ("RISK_RESULT", risk_result_path),
        ):
            try:
                payload = _load(path)
            except Exception as exc:
                payload = {}
                issues.append({
                    "code": f"INVALID_{name}",
                    "blocking": True,
                    "detail": str(exc),
                })
            if not payload:
                issues.append({
                    "code": f"{name}_NOT_FOUND",
                    "blocking": True,
                    "detail": str(path),
                })
            loaded[name] = payload

        policy = loaded["PROMOTION_POLICY"]
        summary = loaded["VALIDATION_SUMMARY"]
        validation_gate = loaded["VALIDATION_GATE"]
        analytics = loaded["ANALYTICS_RESULT"]
        certificate = loaded["CERTIFICATE_RESULT"]
        risk = loaded["RISK_RESULT"]

        if policy:
            checks = [
                ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
                ("READ_ONLY_REQUIRED", bool(policy.get("read_only", False))),
                (
                    "BROKER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("broker_write_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "MIN_HEALTHY_RATE_INVALID",
                    0 <= float(policy.get("minimum_healthy_rate_pct", -1)) <= 100,
                ),
                (
                    "MAX_DRAWDOWN_INVALID",
                    0 < float(policy.get("maximum_drawdown_pct", 0)) <= 25,
                ),
                (
                    "MIN_AVERAGE_RETURN_INVALID",
                    -10 <= float(policy.get("minimum_average_return_pct", -99)) <= 100,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "promotion policy gate failed",
                    })

        validation_complete = bool(
            summary.get("validation_complete", False)
        )
        validation_gate_clear = bool(
            validation_gate.get("validation_gate_clear", False)
        )
        analytics_complete = (
            analytics.get("state") == "VALIDATION_ANALYTICS_COMPLETE"
        )
        certificate_verified = bool(
            certificate.get("certificate_verified", False)
        )
        emergency_stop_required = bool(
            risk.get("emergency_stop_required", False)
        )
        risk_state = str(risk.get("state", ""))

        validation_days = int(summary.get("validation_days", 0) or 0)
        healthy_rate_pct = _number(analytics.get("healthy_rate_pct", 0))
        average_return_pct = _number(analytics.get("average_return_pct", 0))
        maximum_drawdown_pct = _number(
            analytics.get("maximum_drawdown_pct", 0)
        )

        reasons: list[str] = []
        if not validation_complete:
            reasons.append("VALIDATION_NOT_COMPLETE")
        if not validation_gate_clear:
            reasons.append("VALIDATION_GATE_NOT_CLEAR")
        if not analytics_complete:
            reasons.append("ANALYTICS_NOT_COMPLETE")
        if not certificate_verified:
            reasons.append("CERTIFICATE_NOT_VERIFIED")
        if validation_days < int(policy.get("minimum_validation_days", 0) or 0):
            reasons.append("MINIMUM_VALIDATION_DAYS_NOT_MET")
        if healthy_rate_pct < float(
            policy.get("minimum_healthy_rate_pct", 0)
        ):
            reasons.append("HEALTHY_RATE_BELOW_THRESHOLD")
        if average_return_pct < float(
            policy.get("minimum_average_return_pct", 0)
        ):
            reasons.append("AVERAGE_RETURN_BELOW_THRESHOLD")
        if maximum_drawdown_pct > float(
            policy.get("maximum_drawdown_pct", 0)
        ):
            reasons.append("MAXIMUM_DRAWDOWN_EXCEEDED")
        if emergency_stop_required:
            reasons.append("EMERGENCY_STOP_REQUIRED")
        if risk_state not in {"PAPER_RISK_HEALTHY", "WAIT_PILOT_START"}:
            reasons.append("RISK_STATE_UNSAFE")

        promotion_ready = bool(
            not reasons
            and not any(item.get("blocking") for item in issues)
        )

        if any(item.get("blocking") for item in issues):
            state, status = "PROMOTION_GATE_SAFE_MODE", "BLOCKED"
        elif not validation_complete:
            state, status = "WAIT_VALIDATION_COMPLETE", "PASS"
        elif not certificate_verified:
            state, status = "WAIT_CERTIFICATE_VERIFICATION", "PASS"
        elif promotion_ready:
            state, status = "PROMOTION_READY", "PASS"
        else:
            state, status = "PROMOTION_BLOCKED", "PASS"

        observed_at = datetime.now(timezone.utc).isoformat()

        manifest = {
            "stage": "OP5.16",
            "promotion_type": "PAPER_PILOT_PROMOTION",
            "promotion_state": state,
            "promotion_ready": promotion_ready,
            "promotion_reasons": reasons,
            "certificate_id": certificate.get("certificate_id", ""),
            "certificate_sha256": certificate.get(
                "certificate_sha256", ""
            ),
            "validation_days": validation_days,
            "healthy_rate_pct": healthy_rate_pct,
            "average_return_pct": average_return_pct,
            "maximum_drawdown_pct": maximum_drawdown_pct,
            "emergency_stop_required": emergency_stop_required,
            "paper_only": True,
            "broker_action_performed": False,
            "created_at": observed_at,
        }
        _write(promotion_manifest_path, manifest)

        dashboard = {
            "stage": "OP5.13-OP5.16",
            "promotion_state": state,
            "promotion_ready": promotion_ready,
            "promotion_reasons": reasons,
            "validation_complete": validation_complete,
            "validation_gate_clear": validation_gate_clear,
            "analytics_complete": analytics_complete,
            "certificate_verified": certificate_verified,
            "risk_state": risk_state,
            "emergency_stop_required": emergency_stop_required,
            "validation_days": validation_days,
            "healthy_rate_pct": healthy_rate_pct,
            "average_return_pct": average_return_pct,
            "maximum_drawdown_pct": maximum_drawdown_pct,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": observed_at,
        }
        _write(dashboard_state_path, dashboard)

        blocking = sum(
            1 for item in issues if item.get("blocking")
        )
        result = {
            "stage_range": "OP5.13-OP5.16",
            "implementation_type": "PAPER_PILOT_PROMOTION_GATE",
            "status": status,
            "state": state,
            "promotion_ready": promotion_ready,
            "promotion_reasons": reasons,
            "validation_complete": validation_complete,
            "validation_gate_clear": validation_gate_clear,
            "analytics_complete": analytics_complete,
            "certificate_verified": certificate_verified,
            "validation_days": validation_days,
            "healthy_rate_pct": healthy_rate_pct,
            "average_return_pct": average_return_pct,
            "maximum_drawdown_pct": maximum_drawdown_pct,
            "risk_state": risk_state,
            "emergency_stop_required": emergency_stop_required,
            "promotion_manifest_written": True,
            "dashboard_state_written": True,
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "cancel_enabled": False,
            "position_close_enabled": False,
            "continuous_loop_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": blocking > 0,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP5_17_TO_OP5_20_PROMOTION_APPROVAL_LEDGER"
                if promotion_ready
                else "OP5_13_TO_OP5_16_WAIT_PROMOTION_GATE"
            ),
            "validation_mode": "LOCAL_PAPER_PROMOTION_GATE_ONLY",
            "observed_at": observed_at,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
