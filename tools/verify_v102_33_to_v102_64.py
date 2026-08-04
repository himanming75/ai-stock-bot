import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v102_33_to_v102_64/actual/"
    "autonomous_decision_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage": result.get("stage_range") == "V102.33-V102.64",
    "status": result.get("status") == "PASS",
    "allowed_state": result.get("state") in {
        "AUTONOMOUS_DECISION_READY_FOR_MANUAL_APPROVAL",
        "AUTONOMOUS_DECISION_HOLD",
        "AUTONOMOUS_DECISION_REVIEW_REQUIRED",
        "AUTONOMOUS_DECISION_BLOCKED",
    },
    "hash_valid": len(
        result.get("autonomous_decision_certificate_sha256", "")
    ) == 64,
    "signals_valid": isinstance(result.get("signals", {}), dict),
    "conflicts_valid": isinstance(result.get("conflict_analysis", {}), dict),
    "veto_valid": isinstance(result.get("safety_veto", {}), dict),
    "confidence_valid": isinstance(result.get("confidence", {}), dict),
    "decision_valid": isinstance(result.get("autonomous_decision", {}), dict),
    "approval_valid": isinstance(result.get("approval_gate", {}), dict),
    "approval_not_granted": (
        result.get("approval_gate", {}).get("approval_granted") is False
    ),
    "execution_not_authorized": result.get("execution_authorized") is False,
    "manual_approval_required": result.get("manual_approval_required") is True,
    "credentials_unused": result.get("actual_credentials_used") is False,
    "network_unused": result.get("actual_external_network_used") is False,
    "orders_zero": result.get("actual_orders_submitted") == 0,
    "paper_only": result.get("paper_only") is True,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "orders_disabled": result.get("order_submission_enabled") is False,
    "live_disabled": result.get("live_trading_enabled") is False,
    "network_disabled": result.get("external_network_enabled") is False,
}
failed = [name for name, passed in checks.items() if not passed]
print(json.dumps({
    "verification_stage": "V102.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result.get("state"),
    "decision_id": result.get("decision_id"),
    "signals": result.get("signals"),
    "conflict_analysis": result.get("conflict_analysis"),
    "safety_veto": result.get("safety_veto"),
    "confidence": result.get("confidence"),
    "autonomous_decision": result.get("autonomous_decision"),
    "approval_gate": result.get("approval_gate"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
