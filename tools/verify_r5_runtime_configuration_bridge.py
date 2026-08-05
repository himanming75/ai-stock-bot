from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/r5_runtime_configuration_bridge/actual/"
               "last_runtime_bridge_preview.json"
    ).read_text(encoding="utf-8-sig")
)

runtime = result.get("runtime_configuration", {})
strategy = result.get("strategy_binding", {})
risk = result.get("risk_binding", {})
router = result.get("order_router_binding", {})

checks = {
    "stage": result.get("stage") == "R5_RUNTIME_BRIDGE_PREVIEW",
    "status": result.get("status") == "PASS",
    "paper_profile": result.get("broker_mode") == "paper",
    "ultra_short_horizon": result.get("horizon") == "ultra_short",
    "allocation_preserved": (
        strategy.get("allocation_enabled") is True
    ),
    "multi_account_preserved": (
        "multi_account_enabled" in strategy
    ),
    "risk_enforcement_present": (
        risk.get("risk_enforcement_enabled") is True
    ),
    "router_network_off": (
        router.get("broker_network_enabled") is False
    ),
    "router_write_off": (
        router.get("broker_write_enabled") is False
    ),
    "runtime_network_off": (
        runtime.get("broker_network_enabled") is False
    ),
    "runtime_write_off": (
        runtime.get("broker_write_enabled") is False
    ),
    "automatic_submission_off": (
        result.get("automatic_order_submission_enabled") is False
    ),
    "activation_not_performed": (
        result.get("actual_runtime_activation_performed") is False
    ),
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
}
verification = {
    "verification_stage": "R5_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
