
FEATURE_CATALOG = {
    "credential_manager": {
        "required": True,
        "patterns": ["credential", "api_key", "secret_key", "dotenv", "environment"],
    },
    "paper_endpoint_enforcement": {
        "required": True,
        "patterns": ["paper-api", "paper_endpoint", "paper trading", "base_url"],
    },
    "account_read": {
        "required": True,
        "patterns": ["get_account", "account_equity", "buying_power"],
    },
    "positions_read": {
        "required": True,
        "patterns": ["get_all_positions", "list_positions", "positions"],
    },
    "open_orders_read": {
        "required": True,
        "patterns": ["get_orders", "list_orders", "open_orders"],
    },
    "market_clock": {
        "required": True,
        "patterns": ["get_clock", "market_clock", "is_open"],
    },
    "asset_tradability": {
        "required": True,
        "patterns": ["get_asset", "tradable", "fractionable"],
    },
    "order_submit": {
        "required": True,
        "patterns": ["submit_order", "place_order", "order_submission"],
    },
    "market_order": {
        "required": True,
        "patterns": ["marketorderrequest", "order_type.market", '"market"'],
    },
    "limit_order": {
        "required": True,
        "patterns": ["limitorderrequest", "limit_price", "order_type.limit"],
    },
    "buy_sell": {
        "required": True,
        "patterns": ["orderside.buy", "orderside.sell", '"buy"', '"sell"'],
    },
    "client_order_id": {
        "required": True,
        "patterns": ["client_order_id", "clientorderid"],
    },
    "idempotency": {
        "required": True,
        "patterns": ["idempot", "duplicate_order", "replay_protection"],
    },
    "cancel_order": {
        "required": True,
        "patterns": ["cancel_order", "cancel_orders"],
    },
    "replace_order": {
        "required": True,
        "patterns": ["replace_order", "replace_order_by_id"],
    },
    "order_status_sync": {
        "required": True,
        "patterns": ["order_status", "partially_filled", "filled", "rejected", "expired"],
    },
    "fill_sync": {
        "required": True,
        "patterns": ["fill_sync", "trade_update", "fill_event"],
    },
    "portfolio_sync": {
        "required": True,
        "patterns": ["portfolio_sync", "position_sync", "account_sync"],
    },
    "cash_equity_reconciliation": {
        "required": True,
        "patterns": ["cash_reconciliation", "equity_reconciliation", "portfolio_reconciliation"],
    },
    "timeout_retry": {
        "required": True,
        "patterns": ["timeout", "retry", "backoff"],
    },
    "rate_limit": {
        "required": True,
        "patterns": ["rate_limit", "429", "throttle"],
    },
    "network_recovery": {
        "required": True,
        "patterns": ["network_recovery", "connection_recovery", "reconnect"],
    },
    "kill_switch": {
        "required": True,
        "patterns": ["kill_switch", "killswitch"],
    },
    "market_hours_scheduler": {
        "required": True,
        "patterns": ["market_hours", "scheduler", "schedule"],
    },
    "state_checkpoint": {
        "required": True,
        "patterns": ["checkpoint", "saved_state", "state_store"],
    },
    "crash_restart_recovery": {
        "required": True,
        "patterns": ["crash_recovery", "restart_recovery", "resume"],
    },
    "stale_order_detection": {
        "required": True,
        "patterns": ["stale_order", "order_age", "stale"],
    },
    "daily_reset": {
        "required": True,
        "patterns": ["daily_reset", "session_reset", "trading_day"],
    },
    "graceful_shutdown": {
        "required": True,
        "patterns": ["graceful_shutdown", "shutdown", "signal_handler"],
    },
    "audit_ledger": {
        "required": True,
        "patterns": ["audit_ledger", "append_jsonl", "ledger"],
    },
    "hash_integrity": {
        "required": True,
        "patterns": ["sha256", "canonical_hash", "hash_integrity"],
    },
    "long_run_qualification": {
        "required": True,
        "patterns": ["long_run", "qualification", "successful_cycles"],
    },
}
