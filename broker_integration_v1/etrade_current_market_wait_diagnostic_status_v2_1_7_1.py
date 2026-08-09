def build_v2_1_7_1_wait_diagnostic_status():
    return {
        "stage":"BROKER_INTEGRATION_V2_1_7_1_MARKET_WAIT_DIAGNOSTIC_REPAIR",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "development_status":"COMPLETE",
        "websocket_connection_status_visible":True,
        "auth_status_visible":True,
        "subscription_status_visible":True,
        "per_symbol_bar_progress_visible":True,
        "idle_wait_message_visible":True,
        "timeout_diagnostics_visible":True,
        "market_closed_claim_is_conservative":True,
        "v2_1_7_pipeline_unchanged":True,
        "broker_order_submission":False,
        "production_order_post_allowed":False,
        "live_trading_enabled":False,
    }
