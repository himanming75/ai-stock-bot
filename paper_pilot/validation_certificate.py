from __future__ import annotations

import hashlib
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


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))


def _write_pretty(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ValidationCertificateFoundation:
    def run(
        self,
        *,
        policy_path: Path,
        validation_summary_path: Path,
        validation_gate_path: Path,
        analytics_result_path: Path,
        certificate_path: Path,
        seal_path: Path,
        manifest_path: Path,
        verify_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        issue_certificate: bool = False,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        loaded: dict[str, dict[str, Any]] = {}

        for name, path in (
            ("CERTIFICATE_POLICY", policy_path),
            ("VALIDATION_SUMMARY", validation_summary_path),
            ("VALIDATION_GATE", validation_gate_path),
            ("ANALYTICS_RESULT", analytics_result_path),
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

        policy = loaded["CERTIFICATE_POLICY"]
        summary = loaded["VALIDATION_SUMMARY"]
        gate = loaded["VALIDATION_GATE"]
        analytics = loaded["ANALYTICS_RESULT"]

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
                    "HASH_ALGORITHM_INVALID",
                    policy.get("hash_algorithm") == "SHA-256",
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "certificate policy gate failed",
                    })

        validation_complete = bool(
            summary.get("validation_complete", False)
        )
        validation_gate_clear = bool(
            gate.get("validation_gate_clear", False)
        )
        analytics_complete = (
            analytics.get("state") == "VALIDATION_ANALYTICS_COMPLETE"
        )
        issuance_ready = bool(
            validation_complete
            and validation_gate_clear
            and analytics_complete
            and not any(item.get("blocking") for item in issues)
        )

        now = datetime.now(timezone.utc).isoformat()
        certificate_written = False
        manifest_written = False
        seal_written = False
        verified = False
        certificate_id = ""
        digest = ""

        if issue_certificate and issuance_ready:
            identity_seed = "|".join([
                str(summary.get("pilot_id", "")),
                str(summary.get("session_id", "")),
                str(summary.get("validation_days", 0)),
                str(summary.get("healthy_days", 0)),
                str(analytics.get("average_return_pct", 0)),
                str(analytics.get("maximum_drawdown_pct", 0)),
            ])
            certificate_id = (
                "VAL-" + hashlib.sha256(
                    identity_seed.encode("utf-8")
                ).hexdigest()[:20].upper()
            )
            certificate = {
                "certificate_version": "1.0",
                "certificate_id": certificate_id,
                "certificate_type": "PAPER_VALIDATION",
                "issued_at": now,
                "pilot_id": summary.get("pilot_id", ""),
                "session_id": summary.get("session_id", ""),
                "validation_days": int(
                    summary.get("validation_days", 0) or 0
                ),
                "healthy_days": int(
                    summary.get("healthy_days", 0) or 0
                ),
                "unhealthy_days": int(
                    summary.get("unhealthy_days", 0) or 0
                ),
                "consecutive_healthy_days": int(
                    summary.get("consecutive_healthy_days", 0) or 0
                ),
                "average_return_pct": float(
                    analytics.get("average_return_pct", 0) or 0
                ),
                "maximum_drawdown_pct": float(
                    analytics.get("maximum_drawdown_pct", 0) or 0
                ),
                "healthy_rate_pct": float(
                    analytics.get("healthy_rate_pct", 0) or 0
                ),
                "validation_result": "PASS",
                "paper_only": True,
                "broker_write_enabled": False,
                "live_trading_enabled": False,
            }
            _write_json(certificate_path, certificate)
            certificate_written = True

            digest = hashlib.sha256(
                certificate_path.read_bytes()
            ).hexdigest()
            seal_path.parent.mkdir(parents=True, exist_ok=True)
            seal_path.write_text(digest + "\n", encoding="utf-8")
            seal_written = True

            manifest = {
                "stage": "OP5.10",
                "certificate_id": certificate_id,
                "certificate_file": certificate_path.name,
                "hash_algorithm": "SHA-256",
                "certificate_sha256": digest,
                "certificate_size_bytes": certificate_path.stat().st_size,
                "issued_at": now,
                "paper_only": True,
            }
            _write_pretty(manifest_path, manifest)
            manifest_written = True

            actual_digest = hashlib.sha256(
                certificate_path.read_bytes()
            ).hexdigest()
            verified = actual_digest == digest

        elif certificate_path.exists() and seal_path.exists():
            expected = seal_path.read_text(encoding="utf-8").strip()
            actual = hashlib.sha256(
                certificate_path.read_bytes()
            ).hexdigest()
            digest = expected
            verified = bool(expected and expected == actual)
            try:
                certificate_id = str(
                    _load(certificate_path).get("certificate_id", "")
                )
            except Exception:
                verified = False

        verify_payload = {
            "stage": "OP5.12",
            "certificate_present": certificate_path.exists(),
            "seal_present": seal_path.exists(),
            "certificate_id": certificate_id,
            "hash_algorithm": "SHA-256",
            "certificate_sha256": digest,
            "verified": verified,
            "verified_at": now,
            "paper_only": True,
        }
        _write_pretty(verify_path, verify_payload)

        if any(item.get("blocking") for item in issues):
            state, status = "VALIDATION_CERTIFICATE_SAFE_MODE", "BLOCKED"
        elif verified:
            state, status = "VALIDATION_CERTIFICATE_VERIFIED", "PASS"
        elif not issuance_ready:
            state, status = "WAIT_VALIDATION_COMPLETE", "PASS"
        elif issue_certificate:
            state, status = "VALIDATION_CERTIFICATE_ISSUE_FAILED", "BLOCKED"
        else:
            state, status = "VALIDATION_CERTIFICATE_READY", "PASS"

        dashboard = {
            "stage": "OP5.11",
            "certificate_state": state,
            "certificate_id": certificate_id,
            "issuance_ready": issuance_ready,
            "certificate_present": certificate_path.exists(),
            "certificate_verified": verified,
            "certificate_sha256": digest,
            "validation_complete": validation_complete,
            "validation_gate_clear": validation_gate_clear,
            "analytics_complete": analytics_complete,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": now,
        }
        _write_pretty(dashboard_state_path, dashboard)

        blocking = sum(
            1 for item in issues if item.get("blocking")
        )
        result = {
            "stage_range": "OP5.09-OP5.12",
            "implementation_type": (
                "VALIDATION_CERTIFICATE_FOUNDATION"
            ),
            "status": status,
            "state": state,
            "issue_certificate_requested": issue_certificate,
            "issuance_ready": issuance_ready,
            "validation_complete": validation_complete,
            "validation_gate_clear": validation_gate_clear,
            "analytics_complete": analytics_complete,
            "certificate_id": certificate_id,
            "certificate_written": certificate_written,
            "seal_written": seal_written,
            "manifest_written": manifest_written,
            "verify_result_written": True,
            "dashboard_state_written": True,
            "certificate_verified": verified,
            "certificate_sha256": digest,
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
                "OP5_13_TO_OP5_16_PROMOTION_GATE"
                if verified
                else "OP5_09_TO_OP5_12_WAIT_CERTIFICATE"
            ),
            "validation_mode": (
                "LOCAL_VALIDATION_CERTIFICATE_ONLY"
            ),
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write_pretty(result_path, result)
        return result
