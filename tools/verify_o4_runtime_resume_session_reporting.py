from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = ROOT / "release/o4_runtime_resume_session_reporting/actual"
resume = json.loads((actual / "resume_plan.json").read_text(encoding="utf-8-sig"))
checklist = json.loads((actual / "operator_resume_checklist.json").read_text(encoding="utf-8-sig"))
reports = list((actual / "reports").glob("*_daily_report.json"))
csvs = list((actual / "reports").glob("*_daily_summary.csv"))

checks = {
    "resume_plan_present": resume.get("stage") == "O4_RESUME_PLAN",
    "operator_review_required": resume.get("operator_review_required") is True,
    "automatic_resume_off": resume.get("automatic_resume_enabled") is False,
    "automatic_order_replay_off": resume.get("automatic_order_replay_enabled") is False,
    "checklist_present": checklist.get("stage") == "O4_OPERATOR_CHECKLIST",
    "checklist_incomplete_by_default": checklist.get("all_complete") is False,
    "daily_json_present": bool(reports),
    "daily_csv_present": bool(csvs),
    "paper_orders_zero": resume.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": resume.get("actual_live_orders_submitted") == 0,
}
result = {
    "verification_stage": "O4",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
