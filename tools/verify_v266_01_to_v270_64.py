import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from windows_autostart_recovery.supervisor import run

result = run(ROOT, execute_child=False)
checks = {
    "stage": result["stage"] == "V270.64",
    "status": result["status"] == "PASS",
    "allowed_state": result["state"] in {
        "WINDOWS_AUTOSTART_RECOVERY_ACTIVE",
        "WINDOWS_AUTOSTART_RECOVERY_READY_BLOCKED",
    },
    "supervisor_default_off": "SUPERVISOR_DISABLED" in result["blocking_reasons"],
    "child_not_authorized": "CHILD_EXECUTION_NOT_AUTHORIZED" in result["blocking_reasons"],
    "recovery_present": bool(result["recovery"]),
    "live_submission_disabled": result["live_submission_enabled"] is False,
    "live_network_disabled": result["live_network_enabled"] is False,
    "broker_write_disabled": result["broker_write_enabled"] is False,
    "live_orders_zero": result["actual_live_orders_submitted"] == 0,
    "web_api_present": (
        ROOT / "web_controller/windows_autostart_recovery_api.py"
    ).exists(),
}
failed = [name for name, passed in checks.items() if not passed]
verification = {
    "verification_stage": "V270.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result["state"],
    "checks": checks,
    "failed": failed,
    "blocking_reasons": result["blocking_reasons"],
    "actual_live_orders_submitted": 0,
}
print(json.dumps(verification, indent=2, sort_keys=True))
out = ROOT / "release/v266_01_to_v270_64/actual/windows_autostart_recovery_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
