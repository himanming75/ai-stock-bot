from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/multi_broker_strategy_plugins/actual/"
               "multi_broker_strategy_plugins_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "MULTI_BROKER_STRATEGY_PLUGIN_FRAMEWORK",
    "status": result.get("status") == "PASS",
    "broker_interface_ready": (
        result.get("common_broker_interface") == "READY"
    ),
    "mock_ready": result.get("mock_broker_adapter") == "READY_OFFLINE",
    "plugins_ready": result.get("strategy_plugin_interface") == "READY",
    "registry_ready": result.get("plugin_registry") == "READY",
    "hot_swap_preview_only": (
        result.get("strategy_hot_swap") == "READY_PREVIEW_ONLY"
    ),
    "network_unused": result.get("actual_external_network_used") is False,
    "broker_read_unused": (
        result.get("actual_broker_read_performed") is False
    ),
    "broker_write_unused": (
        result.get("actual_broker_write_performed") is False
    ),
    "strategy_not_activated": (
        result.get("actual_strategy_activation_performed") is False
    ),
    "hot_swap_not_performed": (
        result.get("actual_hot_swap_performed") is False
    ),
    "orders_not_submitted": (
        result.get("actual_order_submission_performed") is False
    ),
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "MULTI_BROKER_STRATEGY_PLUGINS",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
