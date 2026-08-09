def build_v2_1_10_status():
    return {
        "stage":"BROKER_INTEGRATION_V2_1_10_ELIGIBLE_SIGNAL_TO_ETRADE_SANDBOX_BRIDGE",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "development_status":"COMPLETE",
        "v2_1_9_signal_result_supported":True,
        "v2_1_5_eligible_queue_reused":True,
        "v2_1_4_bounded_controller_reused":True,
        "hold_zero_order_enforced":True,
        "maximum_sandbox_cycles":3,
        "duplicate_guard_reused":True,
        "kill_switch_reused":True,
        "sandbox_only":True,
        "production_order_post_allowed":False,
        "live_trading_enabled":False,
        "profitability_validation":False,
        "contracts":{
            "duplicate_order_engine_created":False,
            "duplicate_signal_engine_created":False,
            "duplicate_ledger_created":False,
            "duplicate_reconciliation_engine_created":False,
        },
    }
