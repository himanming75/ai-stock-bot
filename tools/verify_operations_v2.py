from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/operations_v2/actual/operations_v2_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "OPERATIONS_V2_MEGA_BUNDLE",
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") == "OPERATIONS_V2_OFFLINE_QUALIFIED"
    ),
    "data_quality_ready": result.get("data_quality_auditor") == "READY",
    "replay_ready": result.get("historical_replay_simulator") == "READY",
    "config_audit_ready": result.get("configuration_diff_auditor") == "READY",
    "incident_ready": result.get("incident_snapshot_builder") == "READY",
    "report_ready": result.get("daily_operator_report") == "READY",
    "export_ready": result.get("csv_json_export") == "READY",
    "dashboard_ready": result.get("dashboard_4_read_only") == "READY",
    "market_network_unused": result.get("actual_market_network_used") is False,
    "broker_network_unused": result.get("actual_broker_network_used") is False,
    "broker_write_unused": result.get("actual_broker_write_used") is False,
    "submission_off": result.get("automatic_order_submission_enabled") is False,
    "orders_not_created": result.get("actual_orders_created") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "OPERATIONS_V2",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
