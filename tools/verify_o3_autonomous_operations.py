from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = ROOT / "release/o3_autonomous_operations/actual"
health = json.loads((actual / "health_score.json").read_text(encoding="utf-8-sig"))
diagnostics = json.loads((actual / "diagnostic_report.json").read_text(encoding="utf-8-sig"))
export_json = actual / "export/o3_audit_export.json"
export_csv = actual / "export/o3_timeline_export.csv"

checks = {
    "health_valid": health.get("state") in {"HEALTHY", "DEGRADED"},
    "health_score_shape": 0 <= int(health.get("score", -1)) <= 100,
    "diagnostics_present": diagnostics.get("stage") == "O3_DIAGNOSTICS",
    "audit_json_present": export_json.exists(),
    "audit_csv_present": export_csv.exists(),
    "live_network_off": (
        diagnostics.get("safety", {}).get("live_network_enabled") is False
    ),
    "live_write_off": (
        diagnostics.get("safety", {}).get("live_write_enabled") is False
    ),
    "auto_replay_off": (
        diagnostics.get("safety", {}).get(
            "automatic_order_replay_enabled"
        ) is False
    ),
    "paper_orders_zero": (
        diagnostics.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        diagnostics.get("actual_live_orders_submitted") == 0
    ),
}
result = {
    "verification_stage": "O3",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
