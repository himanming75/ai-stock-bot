def build_etrade_sandbox_autonomous_cycle_v2_1_3_status():
    return {
        "stage":"BROKER_INTEGRATION_V2_1_3_SANDBOX_AUTONOMOUS_CYCLE",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "development_status":"COMPLETE",
        "one_cycle_supported":True,
        "canonical_order_request_reused":True,
        "preview_place_pipeline_reused":True,
        "ledger_reconciliation_reused":True,
        "automatic_repeat_enabled":False,
        "production_order_post_allowed":False,
        "live_trading_enabled":False,
        "profitability_validation":False,
        "contracts":{
            "duplicate_order_engine_created":False,
            "duplicate_ledger_created":False,
            "duplicate_reconciliation_engine_created":False,
            "sandbox_only":True,
            "real_money_moved":False,
            "production_order_submission_performed":False,
        },
    }
