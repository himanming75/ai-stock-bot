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


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            result.append(value)
    return result


class PromotionApprovalLedger:
    def run(
        self,
        *,
        policy_path: Path,
        promotion_gate_result_path: Path,
        certificate_result_path: Path,
        approval_ledger_path: Path,
        approval_record_path: Path,
        approval_manifest_path: Path,
        certification_gate_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        approve: bool = False,
        approver: str = "",
        approval_reason: str = "",
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        loaded = {}
        for name, path in (
            ("APPROVAL_POLICY", policy_path),
            ("PROMOTION_GATE_RESULT", promotion_gate_result_path),
            ("CERTIFICATE_RESULT", certificate_result_path),
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

        policy = loaded["APPROVAL_POLICY"]
        promotion = loaded["PROMOTION_GATE_RESULT"]
        certificate = loaded["CERTIFICATE_RESULT"]

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
                    "EXPLICIT_APPROVAL_REQUIRED",
                    bool(policy.get("explicit_approval_required", False)),
                ),
                (
                    "DUPLICATE_APPROVAL_BLOCK_REQUIRED",
                    bool(policy.get("block_duplicate_approval", False)),
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "approval policy gate failed",
                    })

        promotion_ready = bool(promotion.get("promotion_ready", False))
        promotion_state = str(promotion.get("state", ""))
        certificate_verified = bool(
            certificate.get("certificate_verified", False)
        )
        certificate_id = str(
            certificate.get("certificate_id", "")
        ).strip()
        certificate_sha256 = str(
            certificate.get("certificate_sha256", "")
        ).strip()

        ledger = _read_jsonl(approval_ledger_path)
        duplicate_approval = any(
            item.get("certificate_id") == certificate_id
            and item.get("approval_status") == "APPROVED"
            for item in ledger
            if certificate_id
        )

        if approve and not approver.strip():
            issues.append({
                "code": "APPROVER_REQUIRED",
                "blocking": True,
                "detail": "",
            })
        if approve and not approval_reason.strip():
            issues.append({
                "code": "APPROVAL_REASON_REQUIRED",
                "blocking": True,
                "detail": "",
            })
        if approve and duplicate_approval:
            issues.append({
                "code": "DUPLICATE_APPROVAL_BLOCKED",
                "blocking": True,
                "detail": certificate_id,
            })

        approval_ready = bool(
            promotion_ready
            and promotion_state == "PROMOTION_READY"
            and certificate_verified
            and certificate_id
            and certificate_sha256
            and not duplicate_approval
            and not any(item.get("blocking") for item in issues)
        )

        now = datetime.now(timezone.utc).isoformat()
        approval_written = False
        approval_id = ""

        if approve and approval_ready:
            seed = "|".join([
                certificate_id,
                certificate_sha256,
                approver.strip(),
                approval_reason.strip(),
            ])
            approval_id = (
                "APR-" + hashlib.sha256(
                    seed.encode("utf-8")
                ).hexdigest()[:20].upper()
            )
            record = {
                "stage": "OP5.17",
                "approval_id": approval_id,
                "approval_status": "APPROVED",
                "approval_type": "PAPER_PILOT_PROMOTION",
                "approver": approver.strip(),
                "approval_reason": approval_reason.strip(),
                "certificate_id": certificate_id,
                "certificate_sha256": certificate_sha256,
                "promotion_state": promotion_state,
                "approved_at": now,
                "paper_only": True,
                "broker_action_performed": False,
            }
            _append(approval_ledger_path, record)
            _write(approval_record_path, record)
            approval_written = True

        approved = approval_written or duplicate_approval

        manifest = {
            "stage": "OP5.18",
            "approval_id": approval_id,
            "approval_ready": approval_ready,
            "approved": approval_written,
            "duplicate_approval": duplicate_approval,
            "certificate_id": certificate_id,
            "promotion_ready": promotion_ready,
            "paper_only": True,
            "broker_action_performed": False,
            "created_at": now,
        }
        _write(approval_manifest_path, manifest)

        certification_gate_clear = bool(
            approval_written
            and promotion_ready
            and certificate_verified
        )
        gate_reasons = []
        if not promotion_ready:
            gate_reasons.append("PROMOTION_NOT_READY")
        if not certificate_verified:
            gate_reasons.append("CERTIFICATE_NOT_VERIFIED")
        if not approval_written:
            gate_reasons.append("EXPLICIT_APPROVAL_NOT_RECORDED")

        certification_gate = {
            "stage": "OP5.19",
            "paper_pilot_certification_gate_clear": (
                certification_gate_clear
            ),
            "approval_id": approval_id,
            "certificate_id": certificate_id,
            "gate_reasons": gate_reasons,
            "paper_only": True,
            "live_trading_enabled": False,
            "created_at": now,
        }
        _write(certification_gate_path, certification_gate)

        if any(item.get("blocking") for item in issues):
            state, status = "PROMOTION_APPROVAL_SAFE_MODE", "BLOCKED"
        elif certification_gate_clear:
            state, status = "PAPER_PILOT_CERTIFICATION_READY", "PASS"
        elif not promotion_ready:
            state, status = "WAIT_PROMOTION_READY", "PASS"
        elif not approve:
            state, status = "WAIT_EXPLICIT_APPROVAL", "PASS"
        else:
            state, status = "PROMOTION_APPROVAL_BLOCKED", "PASS"

        dashboard = {
            "stage": "OP5.20",
            "approval_state": state,
            "approval_ready": approval_ready,
            "approval_written": approval_written,
            "approval_id": approval_id,
            "approver": approver.strip() if approval_written else "",
            "duplicate_approval": duplicate_approval,
            "promotion_ready": promotion_ready,
            "certificate_verified": certificate_verified,
            "certification_gate_clear": certification_gate_clear,
            "gate_reasons": gate_reasons,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": now,
        }
        _write(dashboard_state_path, dashboard)

        blocking = sum(
            1 for item in issues if item.get("blocking")
        )
        result = {
            "stage_range": "OP5.17-OP5.20",
            "implementation_type": (
                "PROMOTION_APPROVAL_LEDGER"
            ),
            "status": status,
            "state": state,
            "approval_requested": approve,
            "approval_ready": approval_ready,
            "approval_written": approval_written,
            "approval_id": approval_id,
            "approver": approver.strip() if approval_written else "",
            "duplicate_approval": duplicate_approval,
            "promotion_ready": promotion_ready,
            "promotion_state": promotion_state,
            "certificate_verified": certificate_verified,
            "certificate_id": certificate_id,
            "certification_gate_clear": certification_gate_clear,
            "approval_manifest_written": True,
            "certification_gate_written": True,
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
                "V80_PAPER_TRADING_COMPLETION"
                if certification_gate_clear
                else "OP5_17_TO_OP5_20_WAIT_APPROVAL"
            ),
            "validation_mode": (
                "LOCAL_PROMOTION_APPROVAL_LEDGER_ONLY"
            ),
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
