import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from position_manager_v2.engine import evaluate
r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V240.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"POSITION_MANAGER_V2_READY", "POSITION_MANAGER_V2_REVIEW_REQUIRED"},
    "snapshot_present": (ROOT / "release/v236_01_to_v240_64/actual/position_snapshot.json").exists(),
    "ledger_present": (ROOT / "release/v236_01_to_v240_64/actual/position_manager_v2_ledger.jsonl").exists(),
    "recovery_present": (ROOT / "release/v236_01_to_v240_64/actual/position_recovery_plan.json").exists(),
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/position_manager_v2_api.py").exists(),
}
failed = [k for k, v in checks.items() if not v]
result = {
    "verification_stage": "V240.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "snapshot": r["snapshot"],
    "exposure": r["exposure"],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v236_01_to_v240_64/actual/position_manager_v2_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
