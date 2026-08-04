import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v103_01_to_v103_32/actual/"
    "autonomous_cycle_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage": result.get("stage_range") == "V103.01-V103.32",
    "status": result.get("status") == "PASS",
    "allowed_state": result.get("state") in {
        "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL",
        "AUTONOMOUS_CYCLE_HOLD",
        "AUTONOMOUS_CYCLE_REVIEW_REQUIRED",
        "AUTONOMOUS_CYCLE_BLOCKED",
        "AUTONOMOUS_CYCLE_RETRY_REQUIRED",
        "AUTONOMOUS_CYCLE_DUPLICATE_BLOCKED",
    },
    "hash_valid": len(
        result.get("autonomous_cycle_certificate_sha256", "")
    ) == 64,
    "cycle_id_valid": len(str(result.get("cycle_id", ""))) == 24,
    "cycle_key_valid": len(str(result.get("cycle_key", ""))) == 64,
    "steps_valid": (
        isinstance(result.get("steps", []), list)
        if result.get("state") != "AUTONOMOUS_CYCLE_DUPLICATE_BLOCKED"
        else True
    ),
    "approval_not_granted": result.get("approval_granted") is False,
    "execution_not_authorized": result.get("execution_authorized") is False,
    "manual_approval_required": result.get("manual_approval_required") is True,
    "orders_zero": result.get("actual_orders_submitted") == 0,
    "paper_only": result.get("paper_only") is True,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "orders_disabled": result.get("order_submission_enabled") is False,
    "live_disabled": result.get("live_trading_enabled") is False,
    "network_disabled": result.get("external_network_enabled") is False,
}
failed = [name for name, passed in checks.items() if not passed]

print(json.dumps({
    "verification_stage": "V103.32",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result.get("state"),
    "cycle_id": result.get("cycle_id"),
    "cycle_date": result.get("cycle_date"),
    "source_decision": result.get("source_decision"),
    "cycle_action": result.get("cycle_action"),
    "completed_step_count": result.get("completed_step_count"),
    "failed_steps": result.get("failed_steps"),
    "duplicate": result.get("duplicate"),
    "lock": result.get("lock"),
    "lock_release": result.get("lock_release"),
    "checkpoint": result.get("checkpoint"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))

raise SystemExit(0 if not failed else 1)
