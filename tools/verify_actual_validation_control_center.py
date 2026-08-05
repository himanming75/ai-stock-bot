from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = (
    ROOT / "release/actual_validation_control_center/actual"
)
status = json.loads(
    (actual / "actual_validation_status.json").read_text(
        encoding="utf-8-sig"
    )
)
report = json.loads(
    (actual / "actual_validation_report.json").read_text(
        encoding="utf-8-sig"
    )
)
certificate = json.loads(
    (actual / "paper_completion_certificate.json").read_text(
        encoding="utf-8-sig"
    )
)

checks = {
    "status_stage": (
        status.get("stage") ==
        "ACTUAL_VALIDATION_CONTROL_CENTER"
    ),
    "next_action_present": bool(status.get("next_action")),
    "report_stage": (
        report.get("stage") == "ACTUAL_VALIDATION_REPORT"
    ),
    "certificate_stage": (
        certificate.get("stage") ==
        "PAPER_COMPLETION_CERTIFICATE"
    ),
    "certificate_fail_closed": (
        certificate.get("eligible") is False
        or certificate.get("paper_complete") is True
    ),
    "production_live_blocked": (
        certificate.get("production_live_allowed") is False
    ),
    "status_orders_zero": (
        status.get(
            "actual_paper_orders_submitted_by_status_check"
        ) == 0
    ),
    "live_orders_zero": (
        status.get("actual_live_orders_submitted") == 0
        and report.get("actual_live_orders_submitted") == 0
    ),
}
result = {
    "verification_stage": "ACTUAL_VALIDATION_CONTROL_CENTER",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
