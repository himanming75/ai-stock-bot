import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from exit_manager_v2.engine import evaluate
r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V245.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"EXIT_MANAGER_V2_READY", "EXIT_MANAGER_V2_REVIEW_REQUIRED"},
    "snapshot_present": (ROOT / "release/v241_01_to_v245_64/actual/exit_candidate_snapshot.json").exists(),
    "recovery_present": (ROOT / "release/v241_01_to_v245_64/actual/exit_recovery_plan.json").exists(),
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "paper_exit_orders_zero": r["actual_paper_exit_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/exit_manager_v2_api.py").exists(),
}
failed = [k for k, v in checks.items() if not v]
result = {
    "verification_stage": "V245.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "snapshot": r["snapshot"],
    "actual_paper_exit_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v241_01_to_v245_64/actual/exit_manager_v2_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
