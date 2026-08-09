def build_etrade_sandbox_order_v2_1_status():
    return {
        "stage":"BROKER_INTEGRATION_V2_1_ETRADE_SANDBOX_ORDER_SIMULATION",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "development_status":"COMPLETE",
        "environment":"SANDBOX_ONLY",
        "equity_preview_supported":True,
        "equity_place_supported":True,
        "cancel_replace_supported":False,
        "production_order_post_allowed":False,
        "sandbox_network_default":"LOCKED",
        "explicit_network_opt_in_required":True,
        "real_money_moved_during_build":False,
        "strategy_profitability_validated":False,
        "purpose":"ORDER_PIPELINE_AND_SERIALIZATION_TEST_ONLY",
        "contracts":{
            "canonical_broker_order_request_reused":True,
            "existing_oauth_signer_reused":True,
            "existing_v2_credentials_flow_reused":True,
            "duplicate_broker_contract_created":False,
            "production_order_submission_performed":False,
            "live_trading_enabled":False,
        },
    }
