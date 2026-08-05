from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/auto_report_notification/actual/"
               "auto_report_notification_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "AUTO_REPORT_NOTIFICATION_FRAMEWORK",
    "status": result.get("status") == "PASS",
    "reports_ready": result.get("auto_report_system") == "READY",
    "notification_preview_ready": (
        result.get("notification_framework") == "READY_PREVIEW_ONLY"
    ),
    "quiet_hours_ready": result.get("quiet_hours_policy") == "READY",
    "dedup_ready": result.get("alert_deduplication") == "READY",
    "send_not_performed": (
        result.get("actual_external_send_performed") is False
    ),
    "network_unused": result.get("actual_external_network_used") is False,
    "broker_read_unused": (
        result.get("actual_broker_read_performed") is False
    ),
    "broker_write_unused": (
        result.get("actual_broker_write_performed") is False
    ),
    "orders_not_submitted": (
        result.get("actual_order_submission_performed") is False
    ),
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "AUTO_REPORT_NOTIFICATION",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
