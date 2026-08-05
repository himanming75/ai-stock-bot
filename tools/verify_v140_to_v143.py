from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/v140_to_v143_ai_operations/actual/"
               "v140_to_v143_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "V140_TO_V143_AI_OPERATIONS",
    "status": result.get("status") == "PASS",
    "dashboard5_ready": result.get("v140_dashboard_5") == "READY",
    "historical_lab_ready": (
        result.get("v141_historical_ai_lab") == "READY"
    ),
    "marketplace_ready": (
        result.get("v142_strategy_marketplace") == "READY"
    ),
    "portfolio_ready": (
        result.get("v143_portfolio_intelligence") == "READY"
    ),
    "read_only": result.get("read_only") is True,
    "market_network_unused": (
        result.get("actual_market_network_used") is False
    ),
    "broker_network_unused": (
        result.get("actual_broker_network_used") is False
    ),
    "broker_write_unused": (
        result.get("actual_broker_write_used") is False
    ),
    "submission_off": (
        result.get("automatic_order_submission_enabled") is False
    ),
    "strategy_activation_not_performed": (
        result.get("actual_strategy_activation_performed") is False
    ),
    "portfolio_not_modified": (
        result.get("actual_portfolio_modified") is False
    ),
    "orders_not_created": result.get("actual_orders_created") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "V140_TO_V143",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
