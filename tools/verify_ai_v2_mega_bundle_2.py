from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/ai_v2_mega_bundle_2/actual/"
               "ai_v2_mega_bundle_2_result.json"
    ).read_text(encoding="utf-8-sig")
)

ready_fields = (
    "stock_scanner",
    "technical_indicator_engine",
    "market_regime_detector",
    "earnings_event_framework",
    "sector_rotation_analyzer",
    "watchlist_ranking",
    "strategy_explanation_engine",
    "dashboard_v2_data_model",
    "historical_data_adapter",
)
checks = {
    "stage": result.get("stage") == "AI_V2_MEGA_BUNDLE_2",
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") == "INTELLIGENCE_PLATFORM_OFFLINE_QUALIFIED"
    ),
    "core_features_ready": all(
        result.get(field) == "READY" for field in ready_fields
    ),
    "news_framework_offline_ready": (
        result.get("news_event_framework") == "READY_OFFLINE_ONLY"
    ),
    "news_api_unused": (
        result.get("actual_external_news_api_used") is False
    ),
    "llm_api_unused": result.get("actual_llm_api_used") is False,
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
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
    "next_bundle_fixed": (
        result.get("next_fixed_bundle") ==
        "AI_V2_MEGA_BUNDLE_3_ADVANCED_RESEARCH_FINAL"
    ),
}
verification = {
    "verification_stage": "AI_V2_MEGA_BUNDLE_2",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
