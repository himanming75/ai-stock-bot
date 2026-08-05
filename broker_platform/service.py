from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .accounts import (
    load_account_registry,
    validate_account_registry,
)
from .adapters import build_default_registry
from .routing import MultiAccountRouter


def run_bundle_b_offline_qualification(
    root: Path,
) -> dict[str, Any]:
    bundle_a_path = (
        root / "release/bundle_a_r7_to_r10_runtime_core/actual/"
               "bundle_a_result.json"
    )
    bundle_a = json.loads(
        bundle_a_path.read_text(encoding="utf-8-sig")
    )
    candidates = bundle_a["cycles"][0]["order_candidates"]

    account_path = (
        root / "release/bundle_b_r11_to_r13_broker_multi_account/"
               "config/account_registry.json"
    )
    accounts = load_account_registry(account_path)
    account_validation = validate_account_registry(accounts)

    registry = build_default_registry()
    matrix = registry.capability_matrix()
    router = MultiAccountRouter(registry=registry)

    routing_results = [
        router.route_candidate(
            root=root,
            candidate=candidate,
            accounts=accounts,
        )
        for candidate in candidates
    ]

    checks = {
        "bundle_a_candidate_present": len(candidates) == 1,
        "account_registry_valid": account_validation["valid"],
        "four_broker_adapters_registered": (
            matrix["broker_count"] == 4
        ),
        "alpaca_route_preview_allowed": all(
            result["allowed_route_count"] == 1
            for result in routing_results
        ),
        "future_brokers_not_routed": all(
            all(
                route["route_allowed"] is False
                for route in result["routes"]
                if route["broker_id"] != "alpaca"
            )
            for result in routing_results
        ),
        "all_submit_flags_off": all(
            all(route["submit_allowed"] is False for route in result["routes"])
            for result in routing_results
        ),
        "network_unused": all(
            result["actual_network_used"] is False
            for result in routing_results
        ),
        "write_unused": all(
            result["actual_write_used"] is False
            for result in routing_results
        ),
    }

    return {
        "stage": "BUNDLE_B_R11_TO_R13",
        "state": "BROKER_MULTI_ACCOUNT_OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "r11_broker_adapter_interface": "READY",
        "r12_multi_account_orchestrator": "READY",
        "r13_capability_matrix_order_routing": "READY",
        "account_registry": account_validation,
        "capability_matrix": matrix,
        "routing_results": routing_results,
        "etrade_connection_status": "INTERFACE_ONLY_NOT_CONNECTED",
        "ibkr_connection_status": "INTERFACE_ONLY_NOT_CONNECTED",
        "schwab_connection_status": "INTERFACE_ONLY_NOT_CONNECTED",
        "alpaca_connection_status": "PREPARED_OFFLINE_ONLY",
        "actual_broker_connections_performed": False,
        "actual_network_used": False,
        "actual_write_used": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_bundle": "BUNDLE_C_R14_TO_R15_FINAL_OPERATIONS",
    }
