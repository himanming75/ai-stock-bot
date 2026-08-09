def build_v2_1_8_status():
    return {
        "stage":"BROKER_INTEGRATION_V2_1_8_HISTORICAL_BOOTSTRAP_LIVE_CONTINUATION",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "development_status":"COMPLETE",
        "historical_bootstrap_ready":True,
        "live_continuation_ready":True,
        "alpaca_rest_readonly":True,
        "alpaca_websocket_v2_1_7_reused":True,
        "v2_1_7_signal_bridge_reused":True,
        "v79_indicator_signal_engines_reused":True,
        "broker_order_submission_from_stage":False,
        "production_order_post_allowed":False,
        "live_trading_enabled":False,
        "profitability_validation":False,
        "contracts":{
            "duplicate_indicator_engine_created":False,
            "duplicate_signal_engine_created":False,
            "duplicate_order_engine_created":False,
            "market_data_credentials_only":True,
            "trading_endpoint_used":False,
        },
    }
