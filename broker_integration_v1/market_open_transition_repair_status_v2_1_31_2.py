def build_v2_1_31_2_status():
    return {
        "stage":"BROKER_INTEGRATION_V2_1_31_2_MARKET_OPEN_TRANSITION_REPAIR",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "base_commit":"61ba6906",
        "transient_broker_failure_grace_seconds":1800,
        "v2_1_30_internal_read_retry_reused":True,
        "overnight_wait_continues_after_transient_failure":True,
        "market_open_recovery_recheck":True,
        "market_open_risk_recheck":True,
        "persistent_broker_outage_fail_closed":True,
        "new_signal_engine_created":False,
        "new_order_engine_created":False,
        "new_trading_state_machine_created":False,
        "install_test_broker_network":False,
        "install_test_paper_orders":0,
        "install_test_live_orders":0,
        "live_trading_enabled":False,
    }
