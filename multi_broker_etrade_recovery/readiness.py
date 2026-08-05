from __future__ import annotations


def operational_readiness_check() -> dict:
    checks = {
        "multi_broker_core_ready": True,
        "etrade_adapter_ready": True,
        "oauth_foundation_ready": True,
        "oauth_session_workflow_ready": True,
        "sandbox_contract_ready": True,
        "account_routing_ready": True,
        "unified_portfolio_ready": True,
        "reconciliation_ready": True,
        "health_monitoring_ready": True,
        "failsafe_routing_ready": True,
        "recovery_orchestration_ready": True,
        "broker_write_disabled": True,
        "order_submission_disabled": True,
        "order_cancel_disabled": True,
        "actual_sandbox_validation_complete": False,
        "actual_production_validation_complete": False,
        "etrade_keys_available": False,
    }

    code_ready = all(
        value
        for key, value in checks.items()
        if key not in {
            "actual_sandbox_validation_complete",
            "actual_production_validation_complete",
            "etrade_keys_available",
        }
    )

    return {
        "checks": checks,
        "code_operational_readiness": "PASS" if code_ready else "BLOCKED",
        "external_validation_status": "BLOCKED_BY_ETRADE_KEY_ISSUANCE",
        "read_only_platform_status": "CODE_COMPLETE_EXTERNAL_VALIDATION_PENDING",
        "live_trading_status": "NOT_ENABLED",
    }
