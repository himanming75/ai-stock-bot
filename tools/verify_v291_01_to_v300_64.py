import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paper_qualification.engine import evaluate

r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V300.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"PAPER_QUALIFIED", "PAPER_QUALIFICATION_IN_PROGRESS"},
    "reconciliation_present": bool(r["reconciliation"]),
    "coverage_present": bool(r["order_state_coverage"]),
    "recovery_present": bool(r["recovery"]),
    "metrics_present": bool(r["performance_metrics"]),
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "live_network_disabled": r["live_network_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/paper_qualification_api.py").exists(),
}
failed = [name for name, passed in checks.items() if not passed]
verification = {
    "verification_stage": "V300.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "qualification_failed_checks": r["failed"],
    "reconciliation": r["reconciliation"],
    "order_state_coverage": r["order_state_coverage"],
    "recovery": r["recovery"],
    "performance_metrics": r["performance_metrics"],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(verification, indent=2, sort_keys=True))
out = ROOT / "release/v291_01_to_v300_64/actual/paper_qualification_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
