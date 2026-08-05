from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/ai_v2_mega_bundle_1/actual/"
               "ai_v2_mega_bundle_1_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "AI_V2_MEGA_BUNDLE_1",
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") ==
        "AI_STRATEGY_LEARNING_PORTFOLIO_RISK_OFFLINE_QUALIFIED"
    ),
    "ensemble_ready": result.get("ai_strategy_ensemble") == "READY",
    "learning_ready": (
        result.get("performance_learning_ledger") == "READY"
    ),
    "optimizer_ready": result.get("portfolio_optimizer") == "READY",
    "risk_v2_ready": (
        result.get("dynamic_risk_engine_v2") == "READY"
    ),
    "training_not_claimed": (
        result.get("actual_machine_learning_training_performed") is False
    ),
    "news_not_used": result.get("actual_news_data_used") is False,
    "market_network_unused": (
        result.get("actual_market_data_network_used") is False
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
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
    "next_bundle_fixed": (
        result.get("next_fixed_bundle") ==
        "AI_V2_MEGA_BUNDLE_2_DATA_SCANNER_NEWS_DASHBOARD"
    ),
}
verification = {
    "verification_stage": "AI_V2_MEGA_BUNDLE_1",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
