from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/shadow_trading_production_approval/actual/"
               "shadow_trading_production_approval_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage")
        == "SHADOW_TRADING_PRODUCTION_APPROVAL_FRAMEWORK"
    ),
    "status": result.get("status") == "PASS",
    "shadow_order_ready": result.get("shadow_order_intake") == "READY",
    "fill_ready": result.get("fill_simulation") == "READY",
    "portfolio_ready": result.get("shadow_portfolio") == "READY",
    "risk_ready": result.get("shadow_risk_metrics") == "READY",
    "approval_preview_ready": (
        result.get("production_approval_queue") == "READY_PREVIEW_ONLY"
    ),
    "deployment_lock_ready": result.get("deployment_lock") == "READY",
    "release_locked": result.get("release_gate") == "LOCKED",
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
    "fills_not_received": result.get("actual_fill_received") is False,
    "portfolio_not_modified": (
        result.get("actual_portfolio_modified") is False
    ),
    "approval_not_granted": (
        result.get("actual_production_approval_granted") is False
    ),
    "release_not_performed": (
        result.get("actual_release_performed") is False
    ),
    "emergency_stop_not_activated": (
        result.get("actual_emergency_stop_activated") is False
    ),
    "rollback_not_performed": (
        result.get("actual_rollback_performed") is False
    ),
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "SHADOW_TRADING_PRODUCTION_APPROVAL",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
