from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/feature_engine_auto_optimization/actual/"
               "feature_engine_auto_optimization_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage")
        == "FEATURE_ENGINE_AUTO_OPTIMIZATION_FRAMEWORK"
    ),
    "status": result.get("status") == "PASS",
    "feature_engine_ready": (
        result.get("technical_feature_engine") == "READY"
    ),
    "factor_engine_ready": result.get("factor_engine") == "READY",
    "dataset_ready": result.get("dataset_builder") == "READY",
    "ensemble_ready": result.get("ensemble_scoring") == "READY",
    "grid_ready": result.get("grid_optimization") == "READY",
    "random_ready": result.get("random_optimization") == "READY",
    "history_ready": result.get("optimization_history") == "READY",
    "champion_preview_ready": (
        result.get("champion_candidate_preview") == "READY"
    ),
    "rollback_preview_ready": result.get("rollback_preview") == "READY",
    "training_not_performed": (
        result.get("actual_model_training_performed") is False
    ),
    "parameters_not_changed": (
        result.get("actual_strategy_parameters_changed") is False
    ),
    "promotion_not_performed": (
        result.get("actual_strategy_promotion_performed") is False
    ),
    "rollback_not_performed": (
        result.get("actual_rollback_performed") is False
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
    "verification_stage": "FEATURE_ENGINE_AUTO_OPTIMIZATION",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
