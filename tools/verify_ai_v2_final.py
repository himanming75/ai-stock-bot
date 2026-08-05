from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/ai_v2_final/actual/"
               "ai_v2_final_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "AI_V2_FINAL_MEGA_BUNDLE",
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") == "AI_V2_FINAL_OFFLINE_QUALIFIED"
    ),
    "release_candidate_ready": (
        result.get("ai_v2_release_candidate_ready") is True
    ),
    "training_not_performed": (
        result.get("actual_machine_learning_training_performed") is False
    ),
    "bayesian_not_claimed": (
        result.get("actual_bayesian_optimization_performed") is False
    ),
    "promotion_not_performed": (
        result.get("actual_strategy_promotion_performed") is False
    ),
    "model_activation_not_performed": (
        result.get("actual_model_activation_performed") is False
    ),
    "portfolio_not_modified": (
        result.get("actual_portfolio_modified") is False
    ),
    "orders_not_created": (
        result.get("actual_orders_created") is False
    ),
    "market_network_unused": (
        result.get("actual_market_network_used") is False
    ),
    "news_api_unused": result.get("actual_news_api_used") is False,
    "llm_api_unused": result.get("actual_llm_api_used") is False,
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
}
verification = {
    "verification_stage": "AI_V2_FINAL",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
