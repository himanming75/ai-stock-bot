from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/bundle_a_r7_to_r10_runtime_core/actual/"
               "bundle_a_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "BUNDLE_A_R7_TO_R10",
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") == "RUNTIME_CORE_OFFLINE_QUALIFIED"
    ),
    "three_cycles": result.get("completed_cycle_count") == 3,
    "r7_ready": result.get("r7_runtime_orchestrator") == "READY",
    "r8_ready": result.get("r8_capital_allocation_engine") == "READY",
    "r9_ready": result.get("r9_portfolio_exposure_manager") == "READY",
    "r10_ready": result.get("r10_strategy_plugin_framework") == "READY",
    "candidate_each_cycle": all(
        cycle.get("order_candidate_count") == 1
        for cycle in result.get("cycles", [])
    ),
    "activation_not_performed": (
        result.get("actual_runtime_activation_performed") is False
    ),
    "network_off": result.get("broker_network_enabled") is False,
    "write_off": result.get("broker_write_enabled") is False,
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
        "BUNDLE_B_R11_TO_R13_BROKER_MULTI_ACCOUNT"
    ),
}
verification = {
    "verification_stage": "BUNDLE_A_R7_TO_R10",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
