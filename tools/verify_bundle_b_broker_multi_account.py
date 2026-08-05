from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/bundle_b_r11_to_r13_broker_multi_account/"
               "actual/bundle_b_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "BUNDLE_B_R11_TO_R13",
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") ==
        "BROKER_MULTI_ACCOUNT_OFFLINE_QUALIFIED"
    ),
    "r11_ready": (
        result.get("r11_broker_adapter_interface") == "READY"
    ),
    "r12_ready": (
        result.get("r12_multi_account_orchestrator") == "READY"
    ),
    "r13_ready": (
        result.get("r13_capability_matrix_order_routing") == "READY"
    ),
    "four_brokers": (
        result.get("capability_matrix", {}).get("broker_count") == 4
    ),
    "account_registry_valid": (
        result.get("account_registry", {}).get("valid") is True
    ),
    "future_connections_not_claimed": all(
        result.get(key) == "INTERFACE_ONLY_NOT_CONNECTED"
        for key in (
            "etrade_connection_status",
            "ibkr_connection_status",
            "schwab_connection_status",
        )
    ),
    "connections_not_performed": (
        result.get("actual_broker_connections_performed") is False
    ),
    "network_unused": result.get("actual_network_used") is False,
    "write_unused": result.get("actual_write_used") is False,
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
        "BUNDLE_C_R14_TO_R15_FINAL_OPERATIONS"
    ),
}
verification = {
    "verification_stage": "BUNDLE_B_R11_TO_R13",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
